import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from django.conf import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class RekaSearchClient:
    """
    Async Reka Research API client with web search capabilities.
    Uses OpenAI-compatible API with reka-flash-research model.
    """

    BASE_URL = "https://api.reka.ai/v1"
    MODEL = "reka-flash-research"

    def __init__(self):
        self.api_key = getattr(settings, 'REKA_API_KEY', None)
        self.client = None

        if not self.api_key:
            logger.warning("REKA_API_KEY not configured")

    async def __aenter__(self):
        """Async context manager entry"""
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.close()

    def is_configured(self) -> bool:
        """Check if the client is properly configured"""
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        user_location: Optional[Dict[str, str]] = None,
        retry_count: int = 2
    ) -> Dict[str, Any]:
        """
        Perform a Reka Research query with web search.

        Args:
            query: Search query string
            user_location: Optional dict with city, region, country, timezone
            retry_count: Number of retries on failure

        Returns:
            Dictionary containing search results and metadata
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'Reka API not configured',
                'results': []
            }

        if not self.client:
            raise RuntimeError("Client not initialized. Use async with statement.")

        # Build web_search configuration
        web_search_config = {
            'max_uses': 2,  # Limit to 2 searches per request as specified
        }

        # Add user location if provided
        if user_location:
            location_data = {}
            if user_location.get('city'):
                location_data['city'] = user_location['city']
            if user_location.get('region'):
                location_data['region'] = user_location['region']
            if user_location.get('country'):
                location_data['country'] = user_location['country']

            if location_data:
                web_search_config['user_location'] = {
                    'approximate': location_data
                }

        for attempt in range(retry_count + 1):
            try:
                logger.info(f"Attempting Reka search (attempt {attempt + 1}): {query[:50]}...")

                # Make request to Reka Research API with timeout
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": query,
                            },
                        ],
                        extra_body={
                            "research": {
                                "web_search": web_search_config,
                            }
                        },
                        timeout=30.0,  # 30 second timeout
                    ),
                    timeout=35.0  # Overall timeout slightly longer
                )

                logger.info(f"Reka search completed successfully")
                # Process the response
                return self._process_search_results(response, query)

            except asyncio.TimeoutError:
                logger.error(f"Reka search timeout on attempt {attempt + 1}")
                if attempt < retry_count:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': 'Reka search timed out',
                        'results': []
                    }
            except Exception as e:
                logger.error(f"Reka search error on attempt {attempt + 1}: {str(e)}", exc_info=True)
                if attempt < retry_count:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'Reka search failed: {str(e)}',
                        'results': []
                    }

        return {
            'success': False,
            'error': 'Max retries exceeded',
            'results': []
        }

    def _process_search_results(self, response: Any, query: str) -> Dict[str, Any]:
        """Process and normalize Reka search results"""
        try:
            # Extract content from response
            content = response.choices[0].message.content if response.choices else ""

            # Extract sources/citations if available
            # Note: Reka may include citations in the response
            # We'll parse the content to extract web sources
            results = self._parse_content_for_sources(content)

            return {
                'success': True,
                'query': query,
                'results': results,
                'content': content,
                'total_results': str(len(results)),
                'timestamp': datetime.now().isoformat(),
                'model': self.MODEL
            }

        except Exception as e:
            logger.error(f"Error processing Reka search results: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to process results: {str(e)}',
                'results': []
            }

    def _parse_content_for_sources(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse Reka response content to extract web sources.
        Reka typically includes citations in markdown format or as references.
        """
        results = []

        # For now, create a single result with the research content
        # In production, you'd parse actual citations from Reka's response
        if content:
            results.append({
                'title': 'Reka Research Result',
                'url': '',  # Reka may not provide direct URLs
                'snippet': content[:500] if len(content) > 500 else content,
                'display_url': 'reka.ai',
                'published_date': None,
                'content': content
            })

        return results


class RekaSearchError(Exception):
    """Custom exception for Reka Search API errors"""
    pass
