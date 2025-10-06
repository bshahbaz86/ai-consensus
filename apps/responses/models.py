"""
AI response models for ChatAI.
"""
from django.db import models
from django.conf import settings
import uuid


class AIResponse(models.Model):
    """
    Individual AI service response to a query.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.ForeignKey('ai_services.AIQuery', on_delete=models.CASCADE, related_name='responses')
    service = models.ForeignKey('ai_services.AIService', on_delete=models.CASCADE)
    
    # Response content
    content = models.TextField()
    raw_response = models.JSONField(default=dict)  # Full API response for debugging
    
    # AI-generated analysis (Step 4 from PRD)
    summary = models.CharField(max_length=200, blank=True)  # 50-word summary
    reasoning = models.CharField(max_length=100, blank=True)  # 20-word reasoning
    is_preferred = models.BooleanField(default=False)  # Star-marked by AI
    
    # Metadata
    tokens_used = models.PositiveIntegerField(default=0)  # Total tokens (kept for backwards compatibility)
    input_tokens = models.PositiveIntegerField(default=0)  # Input/prompt tokens
    output_tokens = models.PositiveIntegerField(default=0)  # Output/completion tokens
    response_time_ms = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)  # Calculated by DB view
    
    # Status and timing
    created_at = models.DateTimeField(auto_now_add=True)
    
    # User interaction
    is_selected = models.BooleanField(default=False)  # Selected by user for continuation
    view_count = models.PositiveIntegerField(default=0)  # How many times user viewed
    
    class Meta:
        db_table = 'ai_responses'
        ordering = ['-is_preferred', '-created_at']
        verbose_name = 'AI Response'
        verbose_name_plural = 'AI Responses'
        indexes = [
            models.Index(fields=['query', 'service']),
            models.Index(fields=['is_preferred', 'is_selected']),
        ]
    
    def __str__(self):
        return f"{self.service.name} response: {self.content[:50]}..."
    
    def increment_view_count(self):
        """Increment the view count when user expands this response."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def select_for_continuation(self):
        """Mark this response as selected and unselect others in the same query."""
        # Unselect all other responses for this query
        AIResponse.objects.filter(query=self.query).update(is_selected=False)
        
        # Select this response
        self.is_selected = True
        self.save(update_fields=['is_selected'])
        
        # Update conversation context
        context, created = self.query.conversation.context.get_or_create(
            defaults={'selected_ai_service': self.service.name}
        )
        context.last_selected_response_id = self.id
        context.selected_ai_service = self.service.name
        context.save(update_fields=['last_selected_response_id', 'selected_ai_service'])
