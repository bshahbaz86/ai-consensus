"""
Notification models for ChatAI real-time updates.
"""
from django.db import models
from django.conf import settings
import uuid


class Notification(models.Model):
    """
    Real-time notifications for users.
    """
    TYPE_CHOICES = [
        ('query_started', 'Query Started'),
        ('query_progress', 'Query Progress'),
        ('query_completed', 'Query Completed'),
        ('response_ready', 'Response Ready'),
        ('analysis_complete', 'Analysis Complete'),
        ('error', 'Error'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    
    # Notification details
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    conversation_id = models.UUIDField(null=True, blank=True)
    query_id = models.UUIDField(null=True, blank=True)
    response_id = models.UUIDField(null=True, blank=True)
    
    # Notification state
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)  # Sent via WebSocket
    
    # Metadata
    data = models.JSONField(default=dict)  # Additional data for frontend
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.type}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class WebSocketConnection(models.Model):
    """
    Track active WebSocket connections for real-time updates.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='websocket_connections')
    channel_name = models.CharField(max_length=255, unique=True)
    conversation_id = models.UUIDField(null=True, blank=True)  # Subscribed conversation
    
    # Connection metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    connected_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'websocket_connections'
        verbose_name = 'WebSocket Connection'
        verbose_name_plural = 'WebSocket Connections'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['conversation_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.channel_name}"
