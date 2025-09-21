from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.config = kwargs
        
    @abstractmethod
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        pass
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def max_tokens(self) -> int:
        pass
    
    def prepare_context(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not context:
            return {}
        
        prepared_context = {
            'conversation_history': context.get('conversation_history', []),
            'system_prompt': context.get('system_prompt', ''),
            'temperature': context.get('temperature', 0.7),
            'max_tokens': context.get('max_tokens', self.max_tokens)
        }
        
        # Add external knowledge from web search if available
        external_knowledge = context.get('external_knowledge')
        if external_knowledge and external_knowledge.get('status') == 'success':
            prepared_context['external_knowledge'] = external_knowledge
            prepared_context['has_web_search'] = True
        else:
            prepared_context['has_web_search'] = False
        
        return prepared_context
    
    def format_error_response(self, error: Exception) -> Dict[str, Any]:
        logger.error(f"{self.service_name} API error: {str(error)}")
        return {
            'success': False,
            'error': str(error),
            'service': self.service_name,
            'content': None,
            'metadata': {}
        }
    
    def format_success_response(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            'success': True,
            'error': None,
            'service': self.service_name,
            'content': content,
            'metadata': metadata or {}
        }