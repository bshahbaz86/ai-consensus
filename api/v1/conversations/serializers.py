"""
DRF serializers for conversations API.
"""
from rest_framework import serializers
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, Count, F, Sum
from django.db import models
from django.utils import timezone

from apps.conversations.models import Conversation, Message, ConversationContext
from apps.responses.models import AIResponse
from apps.ai_services.models import AIQuery


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'timestamp',
            'tokens_used', 'metadata', 'query_session'
        ]
        read_only_fields = ['id', 'timestamp']


class ConversationContextSerializer(serializers.ModelSerializer):
    """Serializer for ConversationContext model."""

    class Meta:
        model = ConversationContext
        fields = [
            'selected_ai_service', 'context_data',
            'last_selected_response_id', 'updated_at'
        ]
        read_only_fields = ['updated_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation list view."""

    last_message_at = serializers.SerializerMethodField()
    last_message_excerpt = serializers.SerializerMethodField()
    ai_services_used = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'created_at', 'updated_at', 'agent_mode',
            'total_messages', 'total_tokens_used', 'last_message_at',
            'last_message_excerpt', 'ai_services_used', 'total_cost'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_messages', 'total_tokens_used']

    def get_last_message_at(self, obj):
        """Get timestamp of the last message."""
        last_message = obj.messages.order_by('-timestamp').first()
        return last_message.timestamp if last_message else obj.updated_at

    def get_last_message_excerpt(self, obj):
        """Get excerpt of last user message for preview."""
        last_user_message = obj.messages.filter(role='user').order_by('-timestamp').first()
        if last_user_message and last_user_message.content:
            content = last_user_message.content.strip()
            return content[:100] + "..." if len(content) > 100 else content
        return ""

    def get_ai_services_used(self, obj):
        """Get list of AI services used in this conversation."""
        services = AIResponse.objects.filter(
            query__conversation=obj
        ).values_list('service__name', flat=True).distinct()
        return list(services)

    def get_total_cost(self, obj):
        """Calculate total cost of this conversation from database view."""
        from django.db import connection

        # Format UUID based on database backend: SQLite uses 32-char strings without hyphens, PostgreSQL uses canonical format
        conversation_id = str(obj.id).replace('-', '') if connection.vendor == 'sqlite' else str(obj.id)

        sql = "SELECT total_cost FROM conversation_cost_view WHERE conversation_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [conversation_id])
            row = cursor.fetchone()
            return float(row[0]) if row else 0.0


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for conversation with messages and context."""

    messages = MessageSerializer(many=True, read_only=True)
    context = ConversationContextSerializer(read_only=True)
    recent_queries = serializers.SerializerMethodField()
    ai_services_used = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'is_active', 'is_archived', 'created_at', 'updated_at',
            'agent_mode', 'total_messages', 'total_tokens_used',
            'messages', 'context', 'recent_queries', 'ai_services_used', 'total_cost'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'total_messages', 'total_tokens_used'
        ]

    def get_recent_queries(self, obj):
        """Get recent AI queries for this conversation."""
        queries = obj.ai_queries.order_by('-started_at')[:5]
        return [
            {
                'id': str(q.id),
                'status': q.status,
                'started_at': q.started_at,
                'completed_at': q.completed_at,
                'total_responses': q.total_responses
            }
            for q in queries
        ]

    def get_ai_services_used(self, obj):
        """Get detailed AI services usage."""
        services = AIResponse.objects.filter(
            query__conversation=obj
        ).values('service__name', 'service__display_name').annotate(
            response_count=Count('id'),
            total_tokens=Sum('tokens_used'),
            total_cost=Sum('cost')
        )
        return list(services)

    def get_total_cost(self, obj):
        """Calculate total cost of this conversation from database view."""
        from django.db import connection

        # Format UUID based on database backend: SQLite uses 32-char strings without hyphens, PostgreSQL uses canonical format
        conversation_id = str(obj.id).replace('-', '') if connection.vendor == 'sqlite' else str(obj.id)

        sql = "SELECT total_cost FROM conversation_cost_view WHERE conversation_id = %s"
        with connection.cursor() as cursor:
            cursor.execute(sql, [conversation_id])
            row = cursor.fetchone()
            return float(row[0]) if row else 0.0


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new conversations."""

    class Meta:
        model = Conversation
        fields = ['title', 'agent_mode']

    def create(self, validated_data):
        """Create conversation with user from request context if authenticated."""
        from django.contrib.auth import get_user_model

        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        else:
            # Use default demo user for unauthenticated conversations (enables cost tracking)
            User = get_user_model()
            try:
                demo_user = User.objects.get(username='testuser')
                validated_data['user'] = demo_user
            except User.DoesNotExist:
                # Keep anonymous conversations unowned for privacy
                validated_data['user'] = None
        return super().create(validated_data)


class ConversationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating conversations (title, archive, etc.)."""

    class Meta:
        model = Conversation
        fields = ['title', 'is_active', 'agent_mode']


class ConversationSearchSerializer(serializers.Serializer):
    """Serializer for conversation search parameters."""

    q = serializers.CharField(required=False, help_text="Search query")
    date_from = serializers.DateTimeField(required=False, help_text="Filter from date")
    date_to = serializers.DateTimeField(required=False, help_text="Filter to date")
    service = serializers.CharField(required=False, help_text="AI service filter")
    min_tokens = serializers.IntegerField(required=False, help_text="Minimum tokens used")
    archived = serializers.BooleanField(required=False, help_text="Include archived conversations")
    ordering = serializers.ChoiceField(
        choices=['-updated_at', '-created_at', 'title', '-total_tokens_used'],
        default='-updated_at',
        help_text="Ordering field"
    )


class ConversationForkSerializer(serializers.Serializer):
    """Serializer for forking conversations."""

    title = serializers.CharField(required=False, help_text="Title for new conversation")
    from_message_id = serializers.UUIDField(
        required=False,
        help_text="Message ID to fork from (includes context up to this point)"
    )

    def validate(self, data):
        """Validate fork parameters."""
        conversation_id = self.context.get('conversation_id')
        if not conversation_id:
            raise serializers.ValidationError("Conversation ID required for forking")

        # Validate from_message_id belongs to this conversation
        if 'from_message_id' in data:
            try:
                message = Message.objects.get(
                    id=data['from_message_id'],
                    conversation_id=conversation_id
                )
            except Message.DoesNotExist:
                raise serializers.ValidationError("Message not found in this conversation")

        return data
