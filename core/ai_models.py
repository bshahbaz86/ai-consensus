from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Overview(BaseModel):
    """Overview of a section of text using structured analysis."""
    summary: str = Field(description="Provide a concise 2-3 sentence summary. Avoid numbered lists, explanatory phrases like 'Here's how', or detailed breakdowns.")
    
    
class KeyPoint(BaseModel):
    """Individual key point from content analysis."""
    point: str = Field(description="A specific important fact as a short phrase, not an explanation")
    importance: Literal["high", "medium", "low"] = Field(description="Importance level of this point")


class EnhancedSummaryResponse(BaseModel):
    """Comprehensive structured summary with rich metadata."""
    summary: str = Field(description="Concise 2-3 sentence summary. Avoid numbered lists, explanatory phrases like 'Here's how', or detailed breakdowns.")
    key_points: List[KeyPoint] = Field(description="2-4 most important facts as short phrases, not explanations")
    complexity_level: Literal["basic", "intermediate", "advanced", "expert"] = Field(
        description="Complexity level of the content"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence in the accuracy of this summary (0.0-1.0)"
    )
    primary_topics: List[str] = Field(
        description="Main topics or themes covered in the content",
        max_items=5
    )
    tone: Literal["formal", "informal", "technical", "conversational", "educational", "persuasive"] = Field(
        description="Overall tone of the content"
    )
    actionability: Literal["high", "medium", "low", "none"] = Field(
        description="How actionable or practical the content is"
    )
    follow_up_questions: List[str] = Field(
        description="Suggested follow-up questions based on the content",
        max_items=3
    )
    related_concepts: List[str] = Field(
        description="Related concepts or topics that connect to this content",
        max_items=5
    )
    content_type: Literal["informational", "instructional", "analytical", "opinion", "narrative", "technical"] = Field(
        description="Type of content being summarized"
    )


class SummaryMetadata(BaseModel):
    """Metadata about the summarization process."""
    model_used: str = Field(description="AI model used for summarization")
    processing_time: Optional[float] = Field(description="Time taken to generate summary in seconds")
    word_count_original: Optional[int] = Field(description="Word count of original content")
    word_count_summary: Optional[int] = Field(description="Word count of generated summary")
    compression_ratio: Optional[float] = Field(description="Ratio of summary length to original length")


class StructuredSummaryResult(BaseModel):
    """Complete result from structured summarization process."""
    enhanced_summary: EnhancedSummaryResponse
    legacy_summary: str = Field(description="Traditional 45-word summary for backward compatibility")
    metadata: SummaryMetadata
    success: bool = Field(description="Whether summarization was successful")
    error_message: Optional[str] = Field(description="Error message if summarization failed")