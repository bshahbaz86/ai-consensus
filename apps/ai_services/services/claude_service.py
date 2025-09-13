import aiohttp
import json
from typing import Dict, Any, Optional
from .base import BaseAIService


class ClaudeService(BaseAIService):
    BASE_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = kwargs.get('model', 'claude-3-haiku-20240307')
        self.default_max_tokens = kwargs.get('max_tokens', 4096)
    
    @property
    def service_name(self) -> str:
        return "Claude"
    
    @property
    def max_tokens(self) -> int:
        return self.default_max_tokens
    
    def validate_api_key(self) -> bool:
        return self.api_key and self.api_key.startswith('sk-ant-')
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.validate_api_key():
            return self.format_error_response(Exception("Invalid Claude API key"))
        
        try:
            headers = {
                'x-api-key': self.api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            }
            
            prepared_context = self.prepare_context(context)
            messages = self._build_messages(prompt, prepared_context)
            
            payload = {
                'model': self.model,
                'max_tokens': prepared_context.get('max_tokens', self.max_tokens),
                'temperature': prepared_context.get('temperature', 0),
                'messages': messages
            }
            
            if prepared_context.get('system_prompt'):
                payload['system'] = prepared_context['system_prompt']
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                        return self.format_error_response(Exception(f"Claude API error: {error_msg}"))
                    
                    content = response_data.get('content', [{}])[0].get('text', '')
                    metadata = {
                        'model': self.model,
                        'usage': response_data.get('usage', {}),
                        'stop_reason': response_data.get('stop_reason')
                    }
                    
                    return self.format_success_response(content, metadata)
                    
        except Exception as e:
            return self.format_error_response(e)
    
    def _build_messages(self, prompt: str, context: Dict[str, Any]) -> list:
        messages = []
        
        conversation_history = context.get('conversation_history', [])
        for msg in conversation_history:
            messages.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })
        
        messages.append({
            'role': 'user',
            'content': prompt
        })
        
        return messages