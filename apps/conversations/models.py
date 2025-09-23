"""
Conversation and message models for ChatAI.
"""
from django.db import models
from django.conf import settings
import uuid


class Conversation(models.Model):
    """
    A chat conversation session.
    """
    AGENT_MODE_CHOICES = [
        ('standard', 'Standard Chat'),
        ('agent', 'LangChain Agent with Tools'),
        ('structured', 'Structured Summary Mode'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations', null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Mode configuration
    agent_mode = models.CharField(max_length=20, choices=AGENT_MODE_CHOICES, default='standard')
    
    # Conversation metadata
    total_messages = models.PositiveIntegerField(default=0)
    total_tokens_used = models.PositiveIntegerField(default=0)

    # Chat history enhancement fields
    last_message_at = models.DateTimeField(null=True, blank=True, help_text='Timestamp of last message')
    last_user_message_excerpt = models.CharField(max_length=200, blank=True, help_text='Excerpt of last user message for preview')
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0, help_text='Total cost of this conversation')
    is_archived = models.BooleanField(default=False, help_text='Whether conversation is archived')

    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='conv_user_updated_idx'),
            models.Index(fields=['user', '-created_at'], name='conv_user_created_idx'),
            models.Index(fields=['user', 'is_active'], name='conv_user_active_idx'),
            models.Index(fields=['user', 'is_archived'], name='conv_user_archived_idx'),
            models.Index(fields=['-total_cost'], name='conv_cost_idx'),
            models.Index(fields=['-total_tokens_used'], name='conv_tokens_idx'),
        ]
    
    def __str__(self):
        return self.title or f"Conversation {self.id.hex[:8]}"
    
    def generate_title(self):
        """Generate a title based on the first message."""
        first_message = self.messages.filter(role='user').first()
        if first_message and first_message.content:
            # Take first 50 characters and add ellipsis if needed
            title = first_message.content[:50]
            if len(first_message.content) > 50:
                title += "..."
            self.title = title
            self.save(update_fields=['title'])
    
    
    def is_structured_mode(self):
        """Check if this conversation is using structured summary mode."""
        return self.agent_mode == 'structured'
    
    
    
    def enable_structured_mode(self):
        """Enable structured summary mode."""
        self.agent_mode = 'structured'
        self.save(update_fields=['agent_mode'])
    
    def disable_structured_mode(self):
        """Disable structured mode and return to standard chat."""
        self.agent_mode = 'standard'
        self.save(update_fields=['agent_mode'])

    def update_conversation_metadata(self):
        """Update conversation metadata from messages and AI responses."""
        from django.db.models import Sum
        from apps.responses.models import AIResponse

        # Update message count and last message info
        messages = self.messages.all()
        self.total_messages = messages.count()

        # Get last message timestamp
        last_message = messages.order_by('-timestamp').first()
        if last_message:
            self.last_message_at = last_message.timestamp

        # Get last user message excerpt
        last_user_message = messages.filter(role='user').order_by('-timestamp').first()
        if last_user_message and last_user_message.content:
            content = last_user_message.content.strip()
            self.last_user_message_excerpt = content[:200] if len(content) > 200 else content

        # Update token count
        self.total_tokens_used = messages.aggregate(
            total=Sum('tokens_used')
        )['total'] or 0

        # Update total cost from AI responses
        total_cost = AIResponse.objects.filter(
            query__conversation=self
        ).aggregate(
            total=Sum('cost')
        )['total'] or 0
        self.total_cost = total_cost

        self.save(update_fields=[
            'total_messages', 'last_message_at', 'last_user_message_excerpt',
            'total_tokens_used', 'total_cost'
        ])


class Message(models.Model):
    """
    Individual messages in a conversation.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Message metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    tokens_used = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, help_text="Additional metadata like processing info, etc.")
    
    # For multi-AI responses, this links to the query that generated multiple responses
    query_session = models.UUIDField(null=True, blank=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
            models.Index(fields=['query_session']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ConversationContext(models.Model):
    """
    Stores conversation context and state for continuity.
    """
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='context')
    
    # Selected AI service for this conversation
    selected_ai_service = models.CharField(max_length=50, null=True, blank=True)
    
    # Context data (JSON field for flexible storage)
    context_data = models.JSONField(default=dict)
    
    # Last selected response (for continuing conversation)
    last_selected_response_id = models.UUIDField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversation_contexts'
        verbose_name = 'Conversation Context'
        verbose_name_plural = 'Conversation Contexts'
    
    def __str__(self):
        return f"Context for {self.conversation}"
