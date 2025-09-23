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
                'anthropic-beta': 'pdfs-2024-09-25,prompt-caching-2024-07-31,computer-use-2024-10-22',
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

        # Check if we have web search results for citations
        if self._has_web_search_results(context):
            content_blocks = self._build_content_with_citations(prompt, context)
        else:
            # Fallback to simple text content
            enhanced_prompt = self._enhance_prompt_with_web_search(prompt, context)
            content_blocks = enhanced_prompt

        messages.append({
            'role': 'user',
            'content': content_blocks
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

    def _has_web_search_results(self, context: Dict[str, Any]) -> bool:
        """Check if context contains web search results suitable for citations."""
        web_search = context.get('web_search', {})
        return (
            web_search.get('enabled', False) and
            web_search.get('results') and
            len(web_search.get('results', [])) > 0
        )

    def _build_content_with_citations(self, prompt: str, context: Dict[str, Any]) -> list:
        """Build content blocks using Claude's citations format for web search results."""
        content_blocks = []

        # Add the user's question as text
        content_blocks.append({
            "type": "text",
            "text": f"User question: {prompt}\n\nPlease provide a comprehensive response using the provided web search results. Use citations to reference specific information from the sources."
        })

        # Add each web search result as a document with citations enabled
        web_search = context.get('web_search', {})
        search_results = web_search.get('results', [])

        for i, result in enumerate(search_results[:6], 1):  # Limit to top 6 results
            # Create document content from search result
            doc_content = []
            doc_content.append(f"Title: {result.get('title', 'No title')}")
            doc_content.append(f"Source: {result.get('source', 'Unknown source')}")

            if result.get('published_date'):
                doc_content.append(f"Published: {result['published_date']}")

            if result.get('snippet'):
                doc_content.append(f"Content: {result['snippet']}")

            if result.get('relevance_note'):
                doc_content.append(f"Relevance: {result['relevance_note']}")

            # Add document block with citations enabled
            content_blocks.append({
                "type": "document",
                "source": {
                    "type": "text",
                    "media_type": "text/plain",
                    "data": "\n".join(doc_content)
                },
                "citations": {"enabled": True}
            })

        return content_blocks