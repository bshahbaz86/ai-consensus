"""
API v1 conversations views.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, Prefetch
from django.db import connection
from django.shortcuts import get_object_or_404
import uuid

from apps.conversations.models import Conversation, Message
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    ConversationCreateSerializer, ConversationUpdateSerializer,
    ConversationSearchSerializer, ConversationForkSerializer,
    MessageSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.

    Provides CRUD operations, search, and conversation forking.
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'messages__content']
    ordering_fields = ['created_at', 'updated_at', 'total_tokens_used', 'title']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Return conversations for the authenticated user only."""
        queryset = Conversation.objects.filter(user=self.request.user)

        # Optimize queries based on action
        if self.action == 'list':
            # For list view, only show conversations with messages and prefetch related data
            queryset = queryset.filter(total_messages__gt=0).prefetch_related(
                Prefetch('messages', queryset=Message.objects.select_related().order_by('-timestamp'))
            ).select_related('user')
        elif self.action == 'retrieve':
            # For detail view, prefetch all related data
            queryset = queryset.prefetch_related(
                'messages',
                'ai_queries__responses__service',
                'context'
            ).select_related('user')

        return queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ConversationUpdateSerializer
        return ConversationDetailSerializer

    def create(self, request, *args, **kwargs):
        """Override create to return detailed conversation after creation."""
        # Use the create serializer for input validation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Perform the creation
        self.perform_create(serializer)

        # Return the full conversation details using DetailSerializer
        instance = serializer.instance
        detail_serializer = ConversationDetailSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(detail_serializer.data)

        from rest_framework import status
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """Create conversation for the authenticated user."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search with full-text search and filters.
        """
        serializer = ConversationSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset()

        # Apply search query
        search_query = serializer.validated_data.get('q')
        if search_query:
            if connection.vendor == 'postgresql':
                queryset = queryset.annotate(
                    search=SearchVector('title', 'messages__content'),
                    rank=SearchRank(SearchVector('title', 'messages__content'), SearchQuery(search_query))
                ).filter(search=SearchQuery(search_query)).order_by('-rank', '-updated_at')
            else:
                queryset = queryset.filter(
                    Q(title__icontains=search_query) |
                    Q(messages__content__icontains=search_query)
                ).distinct().order_by('-updated_at')

        # Apply filters
        date_from = serializer.validated_data.get('date_from')
        if date_from:
            queryset = queryset.filter(updated_at__gte=date_from)

        date_to = serializer.validated_data.get('date_to')
        if date_to:
            queryset = queryset.filter(updated_at__lte=date_to)

        service = serializer.validated_data.get('service')
        if service:
            queryset = queryset.filter(ai_queries__responses__service__name=service).distinct()

        min_tokens = serializer.validated_data.get('min_tokens')
        if min_tokens:
            queryset = queryset.filter(total_tokens_used__gte=min_tokens)

        archived = serializer.validated_data.get('archived')
        if archived is not None:
            queryset = queryset.filter(is_archived=archived)

        # Apply ordering
        ordering = serializer.validated_data.get('ordering', '-updated_at')
        queryset = queryset.order_by(ordering)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ConversationListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ConversationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def fork(self, request, pk=None):
        """
        Fork a conversation to create a new one with conversation context.
        """
        conversation = self.get_object()
        serializer = ConversationForkSerializer(
            data=request.data,
            context={'conversation_id': conversation.id}
        )
        serializer.is_valid(raise_exception=True)

        # Create new conversation
        title = serializer.validated_data.get('title') or f"Fork of {conversation.title}"
        new_conversation = Conversation.objects.create(
            user=request.user,
            title=title,
            agent_mode=conversation.agent_mode
        )

        # Copy messages up to specified point
        from_message_id = serializer.validated_data.get('from_message_id')
        if from_message_id:
            # Copy messages up to and including the specified message
            messages_to_copy = conversation.messages.filter(
                timestamp__lte=Message.objects.get(id=from_message_id).timestamp
            ).order_by('timestamp')
        else:
            # Copy all messages
            messages_to_copy = conversation.messages.all().order_by('timestamp')

        # Create new messages in the forked conversation
        for message in messages_to_copy:
            Message.objects.create(
                conversation=new_conversation,
                role=message.role,
                content=message.content,
                tokens_used=message.tokens_used,
                metadata=message.metadata.copy() if message.metadata else {}
            )

        # Update conversation totals
        total_messages = messages_to_copy.count()
        total_tokens = sum(msg.tokens_used for msg in messages_to_copy)
        new_conversation.total_messages = total_messages
        new_conversation.total_tokens_used = total_tokens
        new_conversation.save(update_fields=['total_messages', 'total_tokens_used'])

        # Copy context if it exists
        if hasattr(conversation, 'context'):
            from apps.conversations.models import ConversationContext
            ConversationContext.objects.create(
                conversation=new_conversation,
                selected_ai_service=conversation.context.selected_ai_service,
                context_data=conversation.context.context_data.copy() if conversation.context.context_data else {}
            )

        serializer = ConversationDetailSerializer(new_conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def archive(self, request, pk=None):
        """Archive/unarchive a conversation."""
        conversation = self.get_object()
        conversation.is_active = not conversation.is_active
        conversation.save(update_fields=['is_active'])

        serializer = self.get_serializer(conversation)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages within conversations.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['timestamp']
    ordering = ['timestamp']
    pagination_class = None  # Messages within a conversation are loaded all at once

    def get_queryset(self):
        """Return messages for a specific conversation owned by the authenticated user."""
        conversation_id = self.kwargs.get('conversation_pk')
        if not conversation_id:
            return Message.objects.none()

        # Get the conversation and verify ownership
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=self.request.user
        )

        return Message.objects.filter(conversation=conversation)

    def perform_create(self, serializer):
        """Create message for the conversation owned by the authenticated user."""
        conversation_id = self.kwargs.get('conversation_pk')
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=self.request.user
        )

        # Save the message
        message = serializer.save(conversation=conversation)

        # Update conversation metadata
        conversation.update_conversation_metadata()

        return message
