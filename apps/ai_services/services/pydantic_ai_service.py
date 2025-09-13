"""
Unified service for structured outputs across all AI providers.
Manual implementation without pydantic-ai dependency for compatibility.
"""
import json
import asyncio
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
import logging
from django.conf import settings
from openai import AsyncOpenAI
import aiohttp

logger = logging.getLogger(__name__)


class UnifiedStructuredService:
    """
    Unified service for structured AI outputs across all providers.
    Uses provider-specific APIs with JSON schema for structured responses.
    """
    
    # Model mappings for each provider
    PROVIDER_MODELS = {
        'openai': 'gpt-4o',
        'claude': 'claude-3-5-sonnet-latest', 
        'gemini': 'gemini-1.5-pro'
    }
    
    def __init__(self):
        self._openai_client = None
    
    def get_openai_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if not self._openai_client:
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client
    
    async def generate_structured_response(
        self, 
        provider: str,
        prompt: str, 
        response_model: Type[BaseModel],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate structured response using provider-specific APIs.
        
        Args:
            provider: 'openai', 'claude', or 'gemini'
            prompt: The input prompt
            response_model: Pydantic model class for structured output
            **kwargs: Additional parameters
        
        Returns:
            Dict with success, structured_data, and error information
        """
        try:
            if provider.lower() == 'openai':
                return await self._generate_openai_structured(prompt, response_model)
            elif provider.lower() == 'claude':
                return await self._generate_claude_structured(prompt, response_model)
            elif provider.lower() == 'gemini':
                return await self._generate_gemini_structured(prompt, response_model)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
        except Exception as e:
            logger.error(f"Error generating structured response with {provider}: {str(e)}")
            return {
                'success': False,
                'structured_data': None,
                'raw_result': None,
                'provider': provider,
                'model': self.PROVIDER_MODELS.get(provider),
                'error': str(e)
            }
    
    async def _generate_openai_structured(self, prompt: str, response_model: Type[BaseModel]) -> Dict[str, Any]:
        """Generate structured response using OpenAI's JSON mode."""
        try:
            client = self.get_openai_client()
            
            # Create JSON schema from Pydantic model
            schema = response_model.model_json_schema()
            
            enhanced_prompt = f"""{prompt}

Please respond with a JSON object that matches this schema:
{json.dumps(schema, indent=2)}

Make sure the response is valid JSON only."""

            response = await client.chat.completions.create(
                model=self.PROVIDER_MODELS['openai'],
                messages=[{"role": "user", "content": enhanced_prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            content = response.choices[0].message.content
            parsed_data = json.loads(content)
            
            # Validate with Pydantic
            validated_data = response_model(**parsed_data)
            
            return {
                'success': True,
                'structured_data': validated_data.model_dump(),
                'raw_result': content,
                'provider': 'openai',
                'model': self.PROVIDER_MODELS['openai'],
                'error': None
            }
            
        except Exception as e:
            logger.error(f"OpenAI structured generation failed: {str(e)}")
            return {
                'success': False,
                'structured_data': None,
                'raw_result': None,
                'provider': 'openai',
                'model': self.PROVIDER_MODELS['openai'],
                'error': str(e)
            }
    
    async def _generate_claude_structured(self, prompt: str, response_model: Type[BaseModel]) -> Dict[str, Any]:
        """Generate structured response using Claude API."""
        try:
            schema = response_model.model_json_schema()
            
            enhanced_prompt = f"""{prompt}

Please respond with a JSON object that matches this schema:
{json.dumps(schema, indent=2)}

Return only valid JSON, no additional text."""

            headers = {
                'Content-Type': 'application/json',
                'x-api-key': settings.CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01'
            }
            
            data = {
                'model': self.PROVIDER_MODELS['claude'],
                'max_tokens': 1000,
                'messages': [{'role': 'user', 'content': enhanced_prompt}],
                'temperature': 0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.anthropic.com/v1/messages',
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['content'][0]['text']
                        
                        # Parse and validate JSON
                        parsed_data = json.loads(content)
                        validated_data = response_model(**parsed_data)
                        
                        return {
                            'success': True,
                            'structured_data': validated_data.model_dump(),
                            'raw_result': content,
                            'provider': 'claude',
                            'model': self.PROVIDER_MODELS['claude'],
                            'error': None
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Claude API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Claude structured generation failed: {str(e)}")
            return {
                'success': False,
                'structured_data': None,
                'raw_result': None,
                'provider': 'claude',
                'model': self.PROVIDER_MODELS['claude'],
                'error': str(e)
            }
    
    async def _generate_gemini_structured(self, prompt: str, response_model: Type[BaseModel]) -> Dict[str, Any]:
        """Generate structured response using Gemini API."""
        try:
            schema = response_model.model_json_schema()
            
            enhanced_prompt = f"""{prompt}

Please respond with a JSON object that matches this schema:
{json.dumps(schema, indent=2)}

Return only valid JSON, no additional text."""

            headers = {'Content-Type': 'application/json'}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.PROVIDER_MODELS['gemini']}:generateContent?key={settings.GEMINI_API_KEY}"
            
            data = {
                'contents': [{'parts': [{'text': enhanced_prompt}]}],
                'generationConfig': {
                    'temperature': 0,
                    'maxOutputTokens': 1000
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        
                        # Parse and validate JSON
                        parsed_data = json.loads(content)
                        validated_data = response_model(**parsed_data)
                        
                        return {
                            'success': True,
                            'structured_data': validated_data.model_dump(),
                            'raw_result': content,
                            'provider': 'gemini',
                            'model': self.PROVIDER_MODELS['gemini'],
                            'error': None
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"Gemini API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Gemini structured generation failed: {str(e)}")
            return {
                'success': False,
                'structured_data': None,
                'raw_result': None,
                'provider': 'gemini',
                'model': self.PROVIDER_MODELS['gemini'],
                'error': str(e)
            }
    
    async def generate_enhanced_summary(
        self,
        provider: str,
        content: str,
        summary_model: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Generate enhanced summary using structured output.
        
        Args:
            provider: AI provider ('openai', 'claude', 'gemini')
            content: Content to summarize
            summary_model: Pydantic model for summary structure
        
        Returns:
            Structured summary result
        """
        prompt = f"""
        Analyze the following content and provide a structured summary:
        
        Content: {content[:4000]}
        
        Requirements:
        - Summary: Maximum 2-3 sentences, capture the core message only
        - Key points: Extract 2-4 most important facts, each as a single short phrase
        - Be direct and concise - avoid explanatory text like "Here's how..." or numbered breakdowns
        - Focus on essential information only, not methodology or process descriptions
        
        Extract the essential information without verbose explanations.
        """
        
        return await self.generate_structured_response(
            provider=provider,
            prompt=prompt,
            response_model=summary_model
        )
    
    def get_available_providers(self) -> list:
        """Get list of supported providers."""
        return list(self.PROVIDER_MODELS.keys())
    
    def supports_provider(self, provider: str) -> bool:
        """Check if provider is supported."""
        return provider.lower() in self.PROVIDER_MODELS


# Global instance
pydantic_ai_service = UnifiedStructuredService()