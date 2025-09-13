import time
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from core.ai_models import (
    Overview, 
    EnhancedSummaryResponse, 
    SummaryMetadata, 
    StructuredSummaryResult,
    KeyPoint
)
from apps.ai_services.services.pydantic_ai_service import pydantic_ai_service
from .summarization import ResponseSummarizer

logger = logging.getLogger(__name__)


class StructuredSummaryService:
    """
    Service for generating intelligent, structured summaries using Pydantic AI.
    Supports consistent structured outputs across OpenAI, Claude, and Gemini.
    """
    
    def __init__(self):
        self.legacy_summarizer = ResponseSummarizer()
        self.summary_prompt_template = """
        Analyze the following content and provide a structured summary:
        
        Content: {content}
        
        Requirements:
        - Summary: Maximum 2-3 sentences, capture the core message only
        - Key points: Extract 2-4 most important facts, each as a single short phrase
        - Be direct and concise - avoid explanatory text like "Here's how..." or numbered breakdowns
        - Focus on essential information only, not methodology or process descriptions
        
        Extract the essential information without verbose explanations.
        """
    
    async def generate_structured_summary(
        self, 
        content: str, 
        ai_service_name: str = "openai",
        use_enhanced: bool = True
    ) -> StructuredSummaryResult:
        """
        Generate a structured summary using the Enhanced model or fallback to simple Overview.
        Implements the pattern from the user's request.
        """
        start_time = time.time()
        
        try:
            # Get legacy summary for backward compatibility
            legacy_summary_data = self.legacy_summarizer.generate_summary(content)
            legacy_summary = legacy_summary_data.get('summary', 'No summary available')
            
            if use_enhanced:
                enhanced_summary = await self._generate_enhanced_summary(content, ai_service_name)
            else:
                enhanced_summary = await self._generate_simple_overview(content, ai_service_name)
            
            processing_time = time.time() - start_time
            
            # Create metadata
            metadata = SummaryMetadata(
                model_used=ai_service_name,
                processing_time=processing_time,
                word_count_original=len(content.split()),
                word_count_summary=len(enhanced_summary.summary.split()) if enhanced_summary else 0,
                compression_ratio=(
                    len(enhanced_summary.summary.split()) / len(content.split()) 
                    if enhanced_summary and len(content.split()) > 0 else 0
                )
            )
            
            return StructuredSummaryResult(
                enhanced_summary=enhanced_summary,
                legacy_summary=legacy_summary,
                metadata=metadata,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Error generating structured summary: {str(e)}")
            processing_time = time.time() - start_time
            
            # Return fallback result with legacy summary
            legacy_summary_data = self.legacy_summarizer.generate_summary(content)
            fallback_enhanced = self._create_fallback_enhanced_summary(content, legacy_summary_data)
            
            metadata = SummaryMetadata(
                model_used="fallback",
                processing_time=processing_time,
                word_count_original=len(content.split()),
                word_count_summary=len(fallback_enhanced.summary.split()),
                compression_ratio=len(fallback_enhanced.summary.split()) / len(content.split()) if len(content.split()) > 0 else 0
            )
            
            return StructuredSummaryResult(
                enhanced_summary=fallback_enhanced,
                legacy_summary=legacy_summary_data.get('summary', 'Error generating summary'),
                metadata=metadata,
                success=False,
                error_message=str(e)
            )
    
    async def _generate_enhanced_summary(self, content: str, ai_service_name: str) -> EnhancedSummaryResponse:
        """Generate enhanced summary using Pydantic AI for all providers."""
        # Check if provider is supported by Pydantic AI
        if not pydantic_ai_service.supports_provider(ai_service_name):
            logger.warning(f"Provider {ai_service_name} not supported by Pydantic AI, using fallback")
            return await self._generate_simple_overview_as_enhanced(content, ai_service_name)
        
        # Use unified Pydantic AI service for structured output
        response = await pydantic_ai_service.generate_enhanced_summary(
            provider=ai_service_name,
            content=content,
            summary_model=EnhancedSummaryResponse
        )
        
        if response.get('success') and response.get('structured_data'):
            return EnhancedSummaryResponse(**response['structured_data'])
        else:
            logger.warning(f"Pydantic AI failed for {ai_service_name}: {response.get('error')}")
            # Fallback to manual creation
            return self._create_fallback_enhanced_summary(content, self.legacy_summarizer.generate_summary(content))
    
    async def _generate_simple_overview(self, content: str, ai_service_name: str) -> EnhancedSummaryResponse:
        """Generate simple overview and convert to enhanced format."""
        if pydantic_ai_service.supports_provider(ai_service_name):
            prompt = f"Provide a concise 2-3 sentence summary of this content (avoid numbered lists or explanatory phrases):\n\n{content[:4000]}"
            
            response = await pydantic_ai_service.generate_structured_response(
                provider=ai_service_name,
                prompt=prompt,
                response_model=Overview
            )
            
            if response.get('success') and response.get('structured_data'):
                overview_data = response['structured_data']
                return self._convert_overview_to_enhanced(overview_data, content)
        
        # Fallback for unsupported providers or failures
        return await self._generate_simple_overview_as_enhanced(content, ai_service_name)
    
    async def _generate_simple_overview_as_enhanced(self, content: str, ai_service_name: str) -> EnhancedSummaryResponse:
        """Generate overview using Pydantic AI and convert to enhanced format."""
        try:
            # Use Pydantic AI for simple overview generation
            prompt = f"Provide a concise 2-3 sentence summary of this content (avoid numbered lists or explanatory phrases):\n\n{content[:4000]}"
            
            response = await pydantic_ai_service.generate_structured_response(
                provider=ai_service_name,
                prompt=prompt,
                response_model=Overview
            )
            
            if response.get('success') and response.get('structured_data'):
                overview_data = response['structured_data']
                return self._convert_overview_to_enhanced(overview_data, content)
        except Exception as e:
            logger.warning(f"Pydantic AI failed for {ai_service_name}: {str(e)}")
        
        # Final fallback
        legacy_data = self.legacy_summarizer.generate_summary(content)
        return self._create_fallback_enhanced_summary(content, legacy_data)
    
    def _convert_overview_to_enhanced(self, overview_data: Dict[str, Any], content: str) -> EnhancedSummaryResponse:
        """Convert simple Overview to EnhancedSummaryResponse format."""
        summary = overview_data.get('summary', 'No summary available')
        
        return EnhancedSummaryResponse(
            summary=summary,
            key_points=[
                KeyPoint(point="Main content analyzed", importance="high")
            ],
            complexity_level=self._assess_complexity(content),
            confidence_score=0.8,
            primary_topics=self._extract_topics(content),
            tone=self._assess_tone(content),
            actionability=self._assess_actionability(content),
            follow_up_questions=self._generate_follow_up_questions(summary),
            related_concepts=self._extract_related_concepts(content),
            content_type=self._assess_content_type(content)
        )
    
    def _convert_text_to_enhanced(self, summary_text: str, content: str) -> EnhancedSummaryResponse:
        """Convert plain text summary to EnhancedSummaryResponse format."""
        return EnhancedSummaryResponse(
            summary=summary_text,
            key_points=self._extract_key_points_from_content(content),
            complexity_level=self._assess_complexity(content),
            confidence_score=0.7,
            primary_topics=self._extract_topics(content),
            tone=self._assess_tone(content),
            actionability=self._assess_actionability(content),
            follow_up_questions=self._generate_follow_up_questions(summary_text),
            related_concepts=self._extract_related_concepts(content),
            content_type=self._assess_content_type(content)
        )
    
    def _create_fallback_enhanced_summary(self, content: str, legacy_data: Dict[str, Any]) -> EnhancedSummaryResponse:
        """Create enhanced summary from legacy ResponseSummarizer data."""
        return EnhancedSummaryResponse(
            summary=legacy_data.get('summary', 'No summary available'),
            key_points=[
                KeyPoint(point=point, importance="medium") 
                for point in legacy_data.get('key_points', [])[:3]
            ],
            complexity_level=self._assess_complexity(content),
            confidence_score=0.6,
            primary_topics=self._extract_topics(content),
            tone=self._assess_tone(content),
            actionability=self._assess_actionability(content),
            follow_up_questions=self._generate_follow_up_questions(legacy_data.get('summary', '')),
            related_concepts=self._extract_related_concepts(content),
            content_type=self._assess_content_type(content)
        )
    
    # Helper methods for content analysis
    def _assess_complexity(self, content: str) -> str:
        """Assess content complexity level."""
        word_count = len(content.split())
        technical_terms = len([word for word in content.lower().split() 
                             if any(tech in word for tech in ['api', 'algorithm', 'framework', 'implementation'])])
        
        if word_count > 1000 or technical_terms > 10:
            return "expert"
        elif word_count > 500 or technical_terms > 5:
            return "advanced"
        elif word_count > 200 or technical_terms > 2:
            return "intermediate"
        return "basic"
    
    def _extract_topics(self, content: str) -> list:
        """Extract primary topics from content."""
        # Simple keyword extraction
        words = content.lower().split()
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        filtered_words = [word.strip('.,!?";') for word in words if word not in common_words and len(word) > 3]
        
        # Count frequency and return top topics
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        return sorted(word_freq.keys(), key=word_freq.get, reverse=True)[:5]
    
    def _assess_tone(self, content: str) -> str:
        """Assess content tone."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['should', 'must', 'important', 'critical']):
            return "formal"
        elif any(word in content_lower for word in ['api', 'function', 'implementation', 'algorithm']):
            return "technical"
        elif any(word in content_lower for word in ['learn', 'understand', 'explain', 'tutorial']):
            return "educational"
        elif any(word in content_lower for word in ['recommend', 'suggest', 'believe', 'think']):
            return "persuasive"
        elif '?' in content and 'how' in content_lower:
            return "conversational"
        return "informal"
    
    def _assess_actionability(self, content: str) -> str:
        """Assess how actionable the content is."""
        action_words = ['do', 'create', 'implement', 'build', 'install', 'configure', 'setup', 'run', 'execute']
        content_lower = content.lower()
        
        action_count = sum(1 for word in action_words if word in content_lower)
        
        if action_count > 5:
            return "high"
        elif action_count > 2:
            return "medium"
        elif action_count > 0:
            return "low"
        return "none"
    
    def _generate_follow_up_questions(self, summary: str) -> list:
        """Generate follow-up questions based on summary."""
        questions = []
        
        if 'implement' in summary.lower():
            questions.append("What are the specific implementation steps?")
        if 'benefit' in summary.lower() or 'advantage' in summary.lower():
            questions.append("What are the potential drawbacks or challenges?")
        if 'how' in summary.lower():
            questions.append("Are there alternative approaches to consider?")
        
        # Default questions
        if not questions:
            questions = [
                "Can you provide more specific details?",
                "What are the next steps?",
                "Are there any related considerations?"
            ]
        
        return questions[:3]
    
    def _extract_related_concepts(self, content: str) -> list:
        """Extract related concepts from content."""
        # Simple concept extraction based on common patterns
        concepts = []
        content_lower = content.lower()
        
        concept_patterns = {
            'ai': ['machine learning', 'neural networks', 'artificial intelligence'],
            'web': ['frontend', 'backend', 'api', 'database'],
            'programming': ['algorithm', 'data structure', 'software engineering'],
            'django': ['python', 'web framework', 'orm', 'mvc'],
            'summary': ['analysis', 'comprehension', 'extraction']
        }
        
        for key, related in concept_patterns.items():
            if key in content_lower:
                concepts.extend(related)
        
        return list(set(concepts))[:5]
    
    def _assess_content_type(self, content: str) -> str:
        """Assess the type of content."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['step', 'first', 'then', 'next', 'finally']):
            return "instructional"
        elif any(word in content_lower for word in ['analyze', 'compare', 'evaluate', 'assessment']):
            return "analytical"
        elif any(word in content_lower for word in ['opinion', 'believe', 'think', 'feel']):
            return "opinion"
        elif any(word in content_lower for word in ['story', 'narrative', 'experience']):
            return "narrative"
        elif any(word in content_lower for word in ['api', 'function', 'class', 'method']):
            return "technical"
        return "informational"
    
    def _extract_key_points_from_content(self, content: str) -> list:
        """Extract key points with importance assessment."""
        legacy_points = self.legacy_summarizer._extract_key_points(content)
        
        return [
            KeyPoint(
                point=point,
                importance="high" if i == 0 else "medium" if i == 1 else "low"
            )
            for i, point in enumerate(legacy_points[:3])
        ]