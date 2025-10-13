import asyncio
import logging
import re
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
            'max_uses': 1,  # Limit to 1 searches per request as specified
        }

        # Add user location if provided and valid
        if user_location:
            # Validate location data before sending to Reka
            location_data = self._validate_and_format_location(user_location)

            if location_data:
                web_search_config['user_location'] = {
                    'approximate': location_data
                }
            else:
                logger.warning("Invalid location data provided, proceeding without location filter")

        for attempt in range(retry_count + 1):
            try:
                # If this is a retry and we have location, try without it
                current_config = web_search_config.copy()
                if attempt > 0 and 'user_location' in current_config:
                    logger.info(f"Retry attempt {attempt + 1} without location filter")
                    current_config.pop('user_location', None)

                logger.info(f"Attempting Reka search (attempt {attempt + 1}): {query[:50]}...")

                # Make request to Reka Research API with timeout
                # Reka Research API typically takes 50-60 seconds for web search
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
                                "web_search": current_config,
                            }
                        },
                        timeout=90.0,  # 90 second timeout per attempt (Reka needs ~55s)
                    ),
                    timeout=95.0  # Overall timeout slightly longer
                )

                logger.info(f"Reka search completed successfully on attempt {attempt + 1}")
                # Process the response
                return self._process_search_results(response, query)

            except asyncio.TimeoutError:
                logger.warning(f"Reka search timeout on attempt {attempt + 1}")
                if attempt < retry_count:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': 'Reka search timed out after all retries',
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
        Parse Reka response content to extract web sources from citations.
        Reka includes citations in inline markdown format like ([domain.com](url)).
        """
        results = []

        # Extract markdown-style citations: ([text](url)) or [text](url)
        from urllib.parse import urlparse

        # Pattern matches: ([text](url)) or [text](url)
        citation_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
        citations = list(re.finditer(citation_pattern, content))

        # Track unique URLs to avoid duplicates
        seen_urls = set()

        for match in citations:
            link_text, url = match.groups()
            # Skip if we've already added this URL
            if url in seen_urls:
                continue

            seen_urls.add(url)

            # Extract domain for display
            parsed = urlparse(url)
            domain = parsed.netloc or 'Unknown Source'

            snippet = self._extract_snippet_from_content(content, match.start(), match.end())
            cleaned_snippet = self._clean_markdown_text(snippet) if snippet else ''
            if not cleaned_snippet:
                # Fallback to link text or domain when no meaningful snippet is found
                cleaned_snippet = link_text if link_text and not link_text.isdigit() else domain

            content_summary = cleaned_snippet
            if url:
                content_summary = f"{cleaned_snippet} (Source: {url})".strip()

            results.append({
                'title': link_text if not link_text.isdigit() else domain,
                'url': url,
                'snippet': cleaned_snippet,
                'display_url': domain,
                'published_date': None,
                'content': content_summary,
                'source': domain
            })

        logger.info(f"Extracted {len(results)} sources from Reka response")
        return results

    def _extract_snippet_from_content(self, content: str, start_idx: int, end_idx: int) -> str:
        """
        Extract a relevant snippet surrounding a citation in the Reka response content.
        Prefers the line/sentence containing the citation, with fallback to a windowed excerpt.
        """
        if not content:
            return ''

        # Try to capture the line containing the citation
        line_start = content.rfind('\n', 0, start_idx)
        line_end = content.find('\n', end_idx)

        if line_start == -1:
            line_start = 0
        else:
            line_start += 1  # move past newline

        if line_end == -1:
            line_end = len(content)

        line_snippet = content[line_start:line_end].strip()
        if line_snippet:
            return line_snippet

        # Fallback: take a window around the citation
        window_before = 200
        window_after = 200
        window_start = max(0, start_idx - window_before)
        window_end = min(len(content), end_idx + window_after)
        return content[window_start:window_end].strip()

    def _clean_markdown_text(self, text: str) -> str:
        """
        Convert markdown-formatted text to a cleaner plain-text snippet.
        Removes bold/italic markers and converts [text](url) to text.
        """
        if not text:
            return ''

        # Replace markdown links with just the link text
        cleaned = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'\1', text)
        # Remove emphasis markers
        cleaned = cleaned.replace('**', '').replace('__', '')
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    def _validate_and_format_location(self, user_location: Dict[str, str]) -> Optional[Dict[str, str]]:
        """
        Validate and format location data to ensure it meets Reka API requirements.
        Country must be ISO 3166-1 two-letter code.
        If validation fails, returns None to skip location filtering.
        """
        if not user_location:
            return None

        # Extract country code
        country = user_location.get('country', '').strip().upper()

        # Validate country code format (must be exactly 2 letters)
        if country and len(country) != 2:
            logger.warning(
                f"Invalid country code '{country}' - must be ISO 3166-1 two-letter code. "
                f"Skipping location filter."
            )
            return None

        # Validate that country code contains only letters
        if country and not country.isalpha():
            logger.warning(
                f"Invalid country code '{country}' - must contain only letters. "
                f"Skipping location filter."
            )
            return None

        # Build validated location data
        location_data = {}

        if country:
            location_data['country'] = country

        # Only add city and region if we have a valid country code
        if country and user_location.get('city'):
            location_data['city'] = user_location['city'].strip()

        if country and user_location.get('region'):
            location_data['region'] = user_location['region'].strip()

        # Return None if we don't have at least a country code
        if not location_data.get('country'):
            logger.info("No valid country code provided, skipping location filter")
            return None

        logger.info(f"Using location filter: {location_data}")
        return location_data


class RekaSearchError(Exception):
    """Custom exception for Reka Search API errors"""
    pass
