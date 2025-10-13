import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from .reka_search_client import RekaSearchClient

User = get_user_model()
logger = logging.getLogger(__name__)


class WebSearchCoordinator:
    """
    Coordinates web search requests with caching, rate limiting, and intelligent search strategy.
    Uses Reka Research API for web search capabilities.
    """

    # Cache settings
    CACHE_TTL = 15 * 60  # 15 minutes as specified
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    MAX_SEARCHES_PER_USER_PER_HOUR = 20  # Per-user rate limit

    def __init__(self):
        self.client = RekaSearchClient()
        self._active_searches = {}  # Deduplication of concurrent requests
    
    async def search_for_query(
        self,
        user_query: str,
        user: Optional[User] = None,
        context: Optional[Dict[str, Any]] = None,
        user_location: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for web search using Reka Research API.
        Reka handles intelligent search internally.

        Args:
            user_query: The user's search query
            user: User object for rate limiting
            context: Additional context that might influence search strategy
            user_location: Optional location data (city, region, country, timezone)

        Returns:
            Dictionary containing search results and metadata
        """

        # Check if user has exceeded rate limits
        if user and not self._check_rate_limit(user):
            return {
                'success': False,
                'error': 'Rate limit exceeded. Please try again later.',
                'results': [],
                'sources': [],
                'search_calls_made': 0
            }

        # Generate cache key for deduplication
        cache_key = self._generate_cache_key(user_query, user_location)

        # Check if we already have this search cached
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached search results for query: {user_query[:50]}...")
            return cached_result

        # Check for concurrent requests for the same query
        if cache_key in self._active_searches:
            logger.info(f"Waiting for concurrent search: {user_query[:50]}...")
            return await self._active_searches[cache_key]

        # Create future for this search to handle concurrent requests
        search_future = asyncio.create_task(self._perform_search(user_query, user, context, user_location))
        self._active_searches[cache_key] = search_future

        try:
            result = await search_future

            # Cache the result
            cache.set(cache_key, result, self.CACHE_TTL)

            # Update rate limiting
            if user:
                self._update_rate_limit(user, result.get('search_calls_made', 1))

            return result

        finally:
            # Clean up active search tracking
            self._active_searches.pop(cache_key, None)
    
    async def _perform_search(
        self,
        user_query: str,
        user: Optional[User],
        context: Optional[Dict[str, Any]],
        user_location: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Performs Reka Research API search with web search capabilities.
        """
        try:
            async with self.client as search_client:
                logger.info(f"Performing Reka search for: {user_query[:50]}...")

                # Perform Reka search
                search_result = await search_client.search(
                    query=user_query,
                    user_location=user_location
                )

                if search_result['success']:
                    # Reka returns formatted content directly
                    processed_results = self._process_reka_results(search_result, user_query)
                    sources = self._extract_sources_from_reka(search_result)

                    logger.info(f"Reka search completed: {search_result.get('total_results', 0)} sources")

                    return {
                        'success': True,
                        'query': user_query,
                        'results': processed_results,
                        'sources': sources,
                        'search_calls_made': 1,
                        'content': search_result.get('content', ''),
                        'model': search_result.get('model', 'reka-flash-research'),
                        'timestamp': search_result.get('timestamp', datetime.now().isoformat())
                    }
                else:
                    error_msg = search_result.get('error', 'Unknown error')
                    logger.warning(f"Reka search failed: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'results': [],
                        'sources': [],
                        'search_calls_made': 1
                    }

        except Exception as e:
            logger.error(f"Web search coordination failed: {str(e)}")
            return {
                'success': False,
                'error': f'Search coordination failed: {str(e)}',
                'results': [],
                'sources': [],
                'search_calls_made': 0
            }
    
    def _process_reka_results(
        self,
        search_result: Dict[str, Any],
        original_query: str
    ) -> List[Dict[str, Any]]:
        """
        Process Reka search results into a format optimized for AI consumption.
        Reka provides formatted research content with citations.
        """
        # Extract the main content from Reka
        content = search_result.get('content', '')
        results = search_result.get('results', [])

        processed = []

        for i, result in enumerate(results):
            processed.append({
                'rank': i + 1,
                'title': result.get('title', 'Reka Research Result'),
                'snippet': result.get('snippet', result.get('content', '')[:500]),
                'url': result.get('url', ''),
                'source': result.get('display_url', 'reka.ai'),
                'published_date': result.get('published_date'),
                'content': result.get('content', '')
            })

        return processed

    def _extract_sources_from_reka(self, search_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract source metadata from Reka search results for frontend display.
        Parses citations from Reka's response content.
        """
        results = search_result.get('results', [])
        sources = []

        for result in results:
            sources.append({
                'title': result.get('title', 'Reka Research Result'),
                'url': result.get('url', ''),
                'domain': result.get('display_url', 'reka.ai'),
                'snippet': result.get('snippet', '')[:150] + '...' if result.get('snippet', '') else '',
                'published_date': result.get('published_date')
            })

        return sources
    
    def _generate_cache_key(
        self,
        query: str,
        user_location: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a cache key for the search query.
        """
        # Include date to ensure daily cache invalidation for time-sensitive queries
        date_str = datetime.now().strftime('%Y-%m-%d')
        normalized_query = query.lower().strip()
        location_payload = ''
        if user_location:
            # Normalize location keys/values so different orderings hash identically
            sanitized_location = {
                key.lower(): (value.strip().lower() if isinstance(value, str) else value)
                for key, value in user_location.items()
                if value
            }
            if sanitized_location:
                location_payload = json.dumps(sanitized_location, sort_keys=True, separators=(',', ':'))

        raw_cache_key = f"{normalized_query}|{location_payload}|{date_str}"
        query_hash = hashlib.md5(raw_cache_key.encode()).hexdigest()
        return f"web_search:{query_hash}"
    
    def _check_rate_limit(self, user: User) -> bool:
        """
        Check if user has exceeded rate limits.
        """
        rate_key = f"web_search_rate:{user.id}"
        current_count = cache.get(rate_key, 0)
        return current_count < self.MAX_SEARCHES_PER_USER_PER_HOUR
    
    def _update_rate_limit(self, user: User, search_calls_made: int):
        """
        Update rate limiting counters.
        """
        rate_key = f"web_search_rate:{user.id}"
        current_count = cache.get(rate_key, 0)
        new_count = current_count + search_calls_made
        cache.set(rate_key, new_count, self.RATE_LIMIT_WINDOW)
