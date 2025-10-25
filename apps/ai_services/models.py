"""
AI service and configuration models for ChatAI.
"""
from django.db import models
from django.conf import settings
import uuid


class AIService(models.Model):
    """
    Configuration for available AI services.
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Service configuration
    api_base_url = models.URLField()
    model_name = models.CharField(max_length=100)
    max_tokens = models.PositiveIntegerField(default=4000)
    
    # Service status
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    
    # Pricing (per 1K tokens)
    input_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    output_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_services'
        verbose_name = 'AI Service'
        verbose_name_plural = 'AI Services'
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name


class AIQuery(models.Model):
    """
    A query sent to multiple AI services simultaneously.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_queries',
        null=True,
        blank=True
    )
    conversation = models.ForeignKey('conversations.Conversation', on_delete=models.CASCADE, related_name='ai_queries')
    
    # Query details
    prompt = models.TextField()
    context = models.JSONField(default=dict)  # Previous conversation context
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Services to query
    services_requested = models.JSONField(default=list)  # List of service names
    services_completed = models.JSONField(default=list)  # List of completed services
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    total_responses = models.PositiveIntegerField(default=0)
    preferred_response_id = models.UUIDField(null=True, blank=True)  # AI-selected best response
    web_search_calls = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'ai_queries'
        ordering = ['-started_at']
        verbose_name = 'AI Query'
        verbose_name_plural = 'AI Queries'
    
    def __str__(self):
        return f"Query {self.id.hex[:8]} - {self.prompt[:50]}..."
    
    @property
    def is_complete(self):
        return len(self.services_completed) == len(self.services_requested)
    
    def mark_service_complete(self, service_name):
        """Mark a service as completed."""
        if service_name not in self.services_completed:
            self.services_completed.append(service_name)
            if self.is_complete:
                self.status = 'completed'
                from django.utils import timezone
                self.completed_at = timezone.now()
            self.save(update_fields=['services_completed', 'status', 'completed_at'])


class AIServiceTask(models.Model):
    """
    Individual task for a specific AI service within a query.
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.ForeignKey(AIQuery, on_delete=models.CASCADE, related_name='service_tasks')
    service = models.ForeignKey(AIService, on_delete=models.CASCADE)
    
    # Task details
    prompt = models.TextField()
    context = models.JSONField(default=dict)
    
    # Status and timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    class Meta:
        db_table = 'ai_service_tasks'
        unique_together = ['query', 'service']
        verbose_name = 'AI Service Task'
        verbose_name_plural = 'AI Service Tasks'
        indexes = [
            models.Index(fields=['status', 'started_at']),
            models.Index(fields=['celery_task_id']),
        ]
    
    def __str__(self):
        return f"{self.service.name} task for query {self.query.id.hex[:8]}"
