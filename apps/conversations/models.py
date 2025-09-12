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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Agent mode configuration
    agent_mode = models.CharField(max_length=20, choices=AGENT_MODE_CHOICES, default='standard')
    enabled_tools = models.JSONField(default=list, help_text="List of enabled tool names for agent mode")
    
    # Conversation metadata
    total_messages = models.PositiveIntegerField(default=0)
    total_tokens_used = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
    
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
    
    def is_agent_enabled(self):
        """Check if this conversation is using agent mode."""
        return self.agent_mode == 'agent'
    
    def is_structured_mode(self):
        """Check if this conversation is using structured summary mode."""
        return self.agent_mode == 'structured'
    
    def get_enabled_tools(self):
        """Get list of enabled tool names."""
        return self.enabled_tools or []
    
    def enable_agent_mode(self, tools=None):
        """Enable agent mode with specified tools."""
        self.agent_mode = 'agent'
        if tools:
            self.enabled_tools = tools
        elif not self.enabled_tools:
            # Default tools
            self.enabled_tools = ['web_search', 'calculator', 'content_summarizer', 'datetime']
        self.save(update_fields=['agent_mode', 'enabled_tools'])
    
    def enable_structured_mode(self):
        """Enable structured summary mode."""
        self.agent_mode = 'structured'
        self.save(update_fields=['agent_mode'])
    
    def disable_agent_mode(self):
        """Disable agent mode and return to standard chat."""
        self.agent_mode = 'standard'
        self.save(update_fields=['agent_mode'])


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
    metadata = models.JSONField(default=dict, help_text="Additional metadata like agent processing info, tools used, etc.")
    
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
