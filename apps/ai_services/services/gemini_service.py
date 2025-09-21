import aiohttp
import json
import logging
from typing import Dict, Any
from .base import BaseAIService

logger = logging.getLogger(__name__)


class GeminiService(BaseAIService):
    """
    Google Gemini AI service implementation using the Gemini API
    """
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = kwargs.get('model', 'gemini-1.5-flash')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.default_max_tokens = kwargs.get('max_tokens', 1000)
    
    @property
    def service_name(self) -> str:
        return "Gemini"
    
    @property
    def max_tokens(self) -> int:
        return self.default_max_tokens
    
    def validate_api_key(self) -> bool:
        return self.api_key and len(self.api_key) > 10
        
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a response using Google Gemini API
        
        Args:
            prompt: The input prompt
            context: Optional context with max_tokens, temperature, etc.
            
        Returns:
            Dict containing success status, content, and metadata
        """
        try:
            prepared_context = self.prepare_context(context)
            max_tokens = prepared_context.get('max_tokens', self.max_tokens)
            temperature = prepared_context.get('temperature', 0)
            url = f"{self.base_url}/{self.model}:generateContent"
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            # Enhance prompt with web search results if available
            enhanced_prompt = self._enhance_prompt_with_web_search(prompt, prepared_context)
            
            # Gemini API request format
            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": enhanced_prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            # Add API key as query parameter
            params = {
                'key': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, 
                    headers=headers, 
                    json=data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract content from Gemini response
                        try:
                            content = result['candidates'][0]['content']['parts'][0]['text']
                            
                            return {
                                'success': True,
                                'content': content.strip(),
                                'metadata': {
                                    'model': self.model,
                                    'usage': result.get('usageMetadata', {}),
                                    'finish_reason': result['candidates'][0].get('finishReason', 'unknown'),
                                    'service': 'gemini'
                                }
                            }
                            
                        except (KeyError, IndexError, TypeError) as e:
                            logger.error(f"Error parsing Gemini response: {e}")
                            logger.error(f"Raw response: {result}")
                            
                            return {
                                'success': False,
                                'content': None,
                                'error': f'Failed to parse Gemini response: {str(e)}',
                                'metadata': {'service': 'gemini'}
                            }
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Gemini API error {response.status}: {error_text}")
                        
                        return {
                            'success': False,
                            'content': None,
                            'error': f'Gemini API error {response.status}: {error_text}',
                            'metadata': {'service': 'gemini'}
                        }
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Gemini API: {e}")
            return {
                'success': False,
                'content': None,
                'error': f'Network error: {str(e)}',
                'metadata': {'service': 'gemini'}
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in Gemini service: {e}")
            return {
                'success': False,
                'content': None,
                'error': f'Unexpected error: {str(e)}',
                'metadata': {'service': 'gemini'}
            }
    
    async def validate_api_key(self) -> bool:
        """
        Validate the Gemini API key by making a simple test request
        
        Returns:
            bool: True if API key is valid
        """
        try:
            # Make a simple test request
            response = await self.generate_response("Hello", max_tokens=10)
            return response['success']
            
        except Exception as e:
            logger.error(f"Gemini API key validation failed: {e}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about this service
        
        Returns:
            Dict containing service information
        """
        return {
            'name': 'Google Gemini',
            'model': self.model,
            'provider': 'Google',
            'capabilities': ['text_generation', 'conversation'],
            'max_tokens': 8192,
            'supported_models': [
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-1.0-pro'
            ]
        }
    
    def _enhance_prompt_with_web_search(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        Enhance the user prompt with web search results if available.
        """
        if not context.get('has_web_search', False):
            return prompt
        
        external_knowledge = context.get('external_knowledge', {})
        if external_knowledge.get('status') != 'success':
            return prompt
        
        # Build enhanced prompt with search context
        enhanced_parts = []
        
        # Add web search context
        search_content = external_knowledge.get('formatted_content', '')
        if search_content:
            enhanced_parts.append("Current web information:")
            enhanced_parts.append(search_content)
            enhanced_parts.append("\n" + "="*50 + "\n")
        
        # Add original user query
        enhanced_parts.append("User question:")
        enhanced_parts.append(prompt)
        
        # Add instruction for using web data
        enhanced_parts.append("\nPlease provide a comprehensive response using both the current web information above and your knowledge. Cite sources when referencing specific information from the web search results.")
        
        return "\n\n".join(enhanced_parts)