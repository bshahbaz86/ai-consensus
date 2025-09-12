import re
from typing import Dict, List, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class ResponseSummarizer:
    def __init__(self):
        self.max_summary_words = 45
        self.max_reasoning_words = 20
        self._structured_service = None
    
    def generate_summary(self, content: str) -> Dict[str, Any]:
        try:
            summary = self._extract_summary(content)
            reasoning = self._extract_reasoning(content)
            key_points = self._extract_key_points(content)
            
            return {
                'summary': summary,
                'reasoning': reasoning,
                'key_points': key_points,
                'content_length': len(content.split()),
                'summarization_ratio': len(summary.split()) / max(len(content.split()), 1)
            }
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return {
                'summary': self._fallback_summary(content),
                'reasoning': 'Auto-generated',
                'key_points': [],
                'content_length': len(content.split()),
                'summarization_ratio': 0.1
            }
    
    def _extract_summary(self, content: str) -> str:
        sentences = self._split_into_sentences(content)
        
        if not sentences:
            return "No content available."
        
        # Create an actual summary by extracting key information
        content_lower = content.lower()
        
        # Look for key summary patterns and create meaningful summary
        if 'affect' in content_lower or 'impact' in content_lower:
            # For cause-effect content, summarize the relationship
            summary = self._create_cause_effect_summary(content, sentences)
        elif 'ways' in content_lower and ':' in content:
            # For numbered lists, summarize the main points
            summary = self._create_list_summary(content, sentences)
        elif len(sentences) >= 3:
            # For longer content, combine first and last sentences for context
            summary = self._create_contextual_summary(sentences)
        else:
            # Fallback to first sentence
            summary = sentences[0] if sentences else "Response provided."
        
        # Ensure summary is within word limit
        return self._truncate_to_complete_sentence(summary, self.max_summary_words)
    
    def _extract_reasoning(self, content: str) -> str:
        reasoning_patterns = [
            r'because\s+(.{1,100})',
            r'since\s+(.{1,100})',
            r'due to\s+(.{1,100})',
            r'therefore\s+(.{1,100})',
            r'thus\s+(.{1,100})',
            r'consequently\s+(.{1,100})'
        ]
        
        for pattern in reasoning_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                reasoning = match.group(1).strip()
                return self._truncate_to_words(reasoning, self.max_reasoning_words)
        
        sentences = self._split_into_sentences(content)
        if len(sentences) >= 2:
            second_sentence = sentences[1]
            return self._truncate_to_words(second_sentence, self.max_reasoning_words)
        
        return self._truncate_to_words(content, self.max_reasoning_words)
    
    def _extract_key_points(self, content: str) -> List[str]:
        key_points = []
        
        bullet_points = re.findall(r'[•\-\*]\s*(.+)', content)
        if bullet_points:
            key_points.extend([point.strip() for point in bullet_points[:3]])
        
        numbered_points = re.findall(r'\d+\.\s*(.+)', content)
        if numbered_points:
            key_points.extend([point.strip() for point in numbered_points[:3]])
        
        if not key_points:
            sentences = self._split_into_sentences(content)
            if len(sentences) > 2:
                key_points = [
                    self._truncate_to_words(sentences[0], 15),
                    self._truncate_to_words(sentences[len(sentences)//2], 15),
                    self._truncate_to_words(sentences[-1], 15)
                ]
        
        return key_points[:3]
    
    def _split_into_sentences(self, content: str) -> List[str]:
        content = re.sub(r'\s+', ' ', content.strip())
        
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _find_topic_sentence(self, sentences: List[str]) -> str:
        if not sentences:
            return ""
        
        topic_indicators = ['main', 'key', 'important', 'primary', 'essential', 'core', 'fundamental']
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in topic_indicators):
                return sentence
        
        return sentences[0] if sentences else ""
    
    def _truncate_to_words(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        
        truncated = ' '.join(words[:max_words])
        return truncated + "..."
    
    def _create_cause_effect_summary(self, content: str, sentences: List[str]) -> str:
        # Extract the main cause and effect relationship
        if 'affect' in content.lower():
            parts = content.split('affect', 1)
            if len(parts) == 2:
                cause = parts[0].strip()[-50:] if len(parts[0]) > 50 else parts[0].strip()
                effect_part = parts[1].strip()[:100] if len(parts[1]) > 100 else parts[1].strip()
                return f"{cause.lstrip()} affects {effect_part}".strip()
        
        # Fallback to first sentence
        return sentences[0] if sentences else "Cause-effect relationship described."
    
    def _create_list_summary(self, content: str, sentences: List[str]) -> str:
        # For content with numbered lists, summarize the main topic and number of points
        if ':' in content:
            intro_part = content.split(':', 1)[0].strip()
            # Count numbered points
            numbered_points = len([line for line in content.split('\n') if line.strip() and line.strip()[0].isdigit()])
            if numbered_points > 0:
                return f"{intro_part} through {numbered_points} key factors."
        
        # Fallback to first sentence  
        return sentences[0] if sentences else "Multiple factors outlined."
    
    def _create_contextual_summary(self, sentences: List[str]) -> str:
        # Combine key information from first and last sentences
        first = sentences[0].strip()
        last = sentences[-1].strip() if len(sentences) > 1 else ""
        
        # Try to create a coherent summary
        if len(first.split()) <= 25 and len(last.split()) <= 15:
            if last and not last.lower().startswith(('this', 'these', 'it', 'that')):
                return f"{first} {last}".strip()
        
        return first

    def _truncate_to_complete_sentence(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            # Ensure it ends with proper punctuation
            text = text.rstrip()
            if not text.endswith(('.', '!', '?')):
                text += '.'
            return text
        
        # Take first max_words and ensure it ends with proper sentence
        truncated_words = words[:max_words]
        truncated_text = ' '.join(truncated_words)
        
        # Remove any trailing punctuation and add period
        truncated_text = truncated_text.rstrip('.!?,:;')
        return truncated_text + '.'
    
    def _fallback_summary(self, content: str) -> str:
        words = content.split()
        if len(words) <= self.max_summary_words:
            text = content.rstrip()
            if not text.endswith(('.', '!', '?')):
                text += '.'
            return text
        
        # Use the complete sentence truncation method
        return self._truncate_to_complete_sentence(content, self.max_summary_words)
    
    async def generate_enhanced_summary(
        self, 
        content: str, 
        ai_service_name: str = "openai",
        use_structured: bool = True
    ) -> Dict[str, Any]:
        """
        Generate enhanced summary using structured summarization.
        Combines legacy summary with intelligent structured analysis.
        """
        try:
            # Get legacy summary for backward compatibility
            legacy_result = self.generate_summary(content)
            
            if use_structured:
                # Lazy import to avoid circular imports
                if self._structured_service is None:
                    from .structured_summary import StructuredSummaryService
                    self._structured_service = StructuredSummaryService()
                
                # Generate structured summary
                structured_result = await self._structured_service.generate_structured_summary(
                    content=content,
                    ai_service_name=ai_service_name,
                    use_enhanced=True
                )
                
                # Combine results
                return {
                    **legacy_result,  # Include legacy fields for backward compatibility
                    'structured_summary': structured_result.enhanced_summary.model_dump(),
                    'metadata': structured_result.metadata.model_dump(),
                    'enhanced_success': structured_result.success,
                    'enhanced_error': structured_result.error_message,
                    'summary_type': 'enhanced'
                }
            else:
                return {
                    **legacy_result,
                    'summary_type': 'legacy'
                }
                
        except Exception as e:
            logger.error(f"Error generating enhanced summary: {str(e)}")
            # Fallback to legacy summary
            legacy_result = self.generate_summary(content)
            return {
                **legacy_result,
                'enhanced_success': False,
                'enhanced_error': str(e),
                'summary_type': 'legacy_fallback'
            }
    
    def generate_summary_sync(self, content: str, use_structured: bool = False) -> Dict[str, Any]:
        """
        Synchronous wrapper for enhanced summary generation.
        Useful for maintaining existing interfaces.
        """
        if use_structured:
            try:
                # Run async method in event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, schedule the task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(self.generate_enhanced_summary(content))
                        )
                        return future.result(timeout=30)
                else:
                    return loop.run_until_complete(self.generate_enhanced_summary(content))
            except Exception as e:
                logger.error(f"Error in sync enhanced summary: {str(e)}")
                return self.generate_summary(content)
        else:
            return self.generate_summary(content)


class ResponseRanker:
    def __init__(self):
        self.ranking_weights = {
            'relevance': 0.4,
            'completeness': 0.3,
            'clarity': 0.2,
            'conciseness': 0.1
        }
    
    def rank_responses(self, responses: List[Any], query: str) -> List[Dict[str, Any]]:
        scored_responses = []
        
        for response in responses:
            score = self._calculate_response_score(response, query)
            scored_responses.append({
                'response': response,
                'score': score,
                'metrics': self._get_response_metrics(response, query)
            })
        
        scored_responses.sort(key=lambda x: x['score'], reverse=True)
        
        for i, item in enumerate(scored_responses):
            item['rank'] = i + 1
        
        return scored_responses
    
    def _calculate_response_score(self, response, query: str) -> float:
        metrics = self._get_response_metrics(response, query)
        
        score = 0.0
        for metric, weight in self.ranking_weights.items():
            score += metrics.get(metric, 0.0) * weight
        
        return min(max(score, 0.0), 1.0)
    
    def _get_response_metrics(self, response, query: str) -> Dict[str, float]:
        content = getattr(response, 'content', '')
        
        return {
            'relevance': self._calculate_relevance(content, query),
            'completeness': self._calculate_completeness(content),
            'clarity': self._calculate_clarity(content),
            'conciseness': self._calculate_conciseness(content)
        }
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(content_words))
        relevance = overlap / len(query_words)
        
        return min(relevance, 1.0)
    
    def _calculate_completeness(self, content: str) -> float:
        word_count = len(content.split())
        
        if word_count < 10:
            return 0.2
        elif word_count < 50:
            return 0.6
        elif word_count < 200:
            return 1.0
        else:
            return 0.8
    
    def _calculate_clarity(self, content: str) -> float:
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        
        if avg_sentence_length > 30:
            return 0.4
        elif avg_sentence_length > 20:
            return 0.7
        else:
            return 1.0
    
    def _calculate_conciseness(self, content: str) -> float:
        word_count = len(content.split())
        
        if word_count < 50:
            return 1.0
        elif word_count < 150:
            return 0.8
        elif word_count < 300:
            return 0.6
        else:
            return 0.3