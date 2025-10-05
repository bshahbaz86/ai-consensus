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


class ResponseAnalysis(models.Model):
    """
    Analysis and comparison of multiple responses (Step 4 processing).
    """
    query = models.OneToOneField('ai_services.AIQuery', on_delete=models.CASCADE, related_name='analysis')
    
    # AI-generated analysis
    analysis_prompt = models.TextField()  # Prompt used for analysis
    analysis_response = models.TextField()  # Full analysis response
    
    # Preferred response selection
    preferred_response = models.ForeignKey(AIResponse, on_delete=models.CASCADE, null=True, blank=True)
    selection_reasoning = models.TextField()  # Why this response was preferred
    
    # Analysis metadata
    analysis_service = models.CharField(max_length=50, default='claude')  # Service used for analysis
    analysis_tokens_used = models.PositiveIntegerField(default=0)
    analysis_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'response_analyses'
        verbose_name = 'Response Analysis'
        verbose_name_plural = 'Response Analyses'
    
    def __str__(self):
        return f"Analysis for query {self.query.id.hex[:8]}"


class ResponseMetrics(models.Model):
    """
    Metrics and performance tracking for responses.
    """
    response = models.OneToOneField(AIResponse, on_delete=models.CASCADE, related_name='metrics')
    
    # Quality metrics (can be populated later with user feedback)
    user_rating = models.PositiveIntegerField(null=True, blank=True)  # 1-5 rating
    accuracy_score = models.FloatField(null=True, blank=True)  # AI-calculated accuracy
    relevance_score = models.FloatField(null=True, blank=True)  # AI-calculated relevance
    
    # Performance metrics
    latency_score = models.FloatField(default=0)  # Response time score
    cost_efficiency = models.FloatField(default=0)  # Cost per quality unit
    
    # User behavior
    time_to_selection = models.PositiveIntegerField(null=True, blank=True)  # Seconds
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'response_metrics'
        verbose_name = 'Response Metrics'
        verbose_name_plural = 'Response Metrics'
    
    def __str__(self):
        return f"Metrics for {self.response}"
