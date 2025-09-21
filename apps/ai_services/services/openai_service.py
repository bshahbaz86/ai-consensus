import aiohttp
import json
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel
from .base import BaseAIService
from core.ai_utils import convert_pydantic_to_openai_function, JsonOutputFunctionsParser


class OpenAIService(BaseAIService):
    BASE_URL = "https://api.openai.com/v1/chat/completions"
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.model = kwargs.get('model', 'gpt-4')
        self.default_max_tokens = kwargs.get('max_tokens', 4096)
    
    @property
    def service_name(self) -> str:
        return "OpenAI"
    
    @property
    def max_tokens(self) -> int:
        return self.default_max_tokens
    
    def validate_api_key(self) -> bool:
        return self.api_key and self.api_key.startswith('sk-')
    
    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a standard chat response."""
        return await self._make_request(prompt, context)
    
    async def generate_function_response(
        self, 
        prompt: str, 
        functions: List[Dict[str, Any]], 
        function_call: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a response using function calling."""
        return await self._make_request(prompt, context, functions=functions, function_call=function_call)
    
    async def generate_structured_response(
        self, 
        prompt: str, 
        response_model: Type[BaseModel],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a structured response using a Pydantic model."""
        function_schema = convert_pydantic_to_openai_function(response_model)
        function_call = {"name": response_model.__name__}
        
        response = await self.generate_function_response(
            prompt=prompt,
            functions=[function_schema],
            function_call=function_call,
            context=context
        )
        
        if response.get('success'):
            parser = JsonOutputFunctionsParser()
            parsed_data = parser.parse(response.get('raw_response', {}))
            
            if 'error' not in parsed_data:
                try:
                    structured_result = response_model(**parsed_data)
                    response['structured_data'] = structured_result.model_dump()
                except Exception as e:
                    response['success'] = False
                    response['error'] = f"Failed to validate structured response: {str(e)}"
        
        return response
    
    async def _make_request(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        if not self.validate_api_key():
            return self.format_error_response(Exception("Invalid OpenAI API key"))
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            prepared_context = self.prepare_context(context)
            messages = self._build_messages(prompt, prepared_context)
            
            payload = {
                'model': self.model,
                'messages': messages,
                'max_tokens': prepared_context.get('max_tokens', self.max_tokens),
                'temperature': prepared_context.get('temperature', 0)
            }
            
            # Add function calling parameters if provided
            if functions:
                payload['functions'] = functions
                if function_call:
                    payload['function_call'] = function_call
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                        return self.format_error_response(Exception(f"OpenAI API error: {error_msg}"))
                    
                    choices = response_data.get('choices', [])
                    if not choices:
                        return self.format_error_response(Exception("No response choices returned"))
                    
                    message = choices[0].get('message', {})
                    content = message.get('content', '')
                    
                    # Handle function calling response
                    if functions and message.get('function_call'):
                        content = message.get('function_call', {}).get('arguments', '')
                    
                    metadata = {
                        'model': self.model,
                        'usage': response_data.get('usage', {}),
                        'finish_reason': choices[0].get('finish_reason'),
                        'function_call': message.get('function_call')
                    }
                    
                    response_result = self.format_success_response(content, metadata)
                    response_result['raw_response'] = response_data
                    
                    return response_result
                    
        except Exception as e:
            return self.format_error_response(e)
    
    def _build_messages(self, prompt: str, context: Dict[str, Any]) -> list:
        messages = []
        
        if context.get('system_prompt'):
            messages.append({
                'role': 'system',
                'content': context['system_prompt']
            })
        
        conversation_history = context.get('conversation_history', [])
        for msg in conversation_history:
            messages.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })
        
        # Enhance prompt with web search results if available
        enhanced_prompt = self._enhance_prompt_with_web_search(prompt, context)
        
        messages.append({
            'role': 'user',
            'content': enhanced_prompt
        })
        
        return messages
    
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