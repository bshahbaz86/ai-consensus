import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from .google_search_client import GoogleCustomSearchClient

User = get_user_model()
logger = logging.getLogger(__name__)


class WebSearchCoordinator:
    """
    Coordinates web search requests with caching, rate limiting, and intelligent search strategy.
    Implements max 2 search calls per user query as specified.
    """
    
    # Cache settings
    CACHE_TTL = 15 * 60  # 15 minutes as specified
    RATE_LIMIT_WINDOW = 3600  # 1 hour
    MAX_SEARCHES_PER_USER_PER_HOUR = 20  # Per-user rate limit
    
    # Recency detection keywords
    RECENCY_KEYWORDS = {
        'time_sensitive': [
            'latest', 'recent', 'current', 'today', 'yesterday', 'this week',
            'this month', 'now', 'breaking', 'news', 'update', 'new'
        ],
        'year_indicators': ['2024', '2025'],
        'temporal_phrases': [
            'what happened', 'current status', 'latest news', 'recent events',
            'today\'s', 'this year', 'currently'
        ]
    }
    
    def __init__(self):
        self.client = GoogleCustomSearchClient()
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
        Reka handles intelligent search with max 2 API calls internally.

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
        cache_key = self._generate_cache_key(user_query)
        
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
                self._update_rate_limit(user, result.get('search_calls_made', 0))
            
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
        Performs Google Custom Search (up to 2 searches with recency detection).
        """
        search_calls_made = 0
        all_results = []
        sources = []
        errors = []

        try:
            async with self.client as search_client:
                # First search: Raw user query
                logger.info(f"Performing first search for: {user_query[:50]}...")
                first_search = await search_client.search(
                    query=user_query,
                    num_results=5
                )
                search_calls_made += 1

                if first_search['success']:
                    all_results.extend(first_search['results'])
                    logger.info(f"First search returned {len(first_search['results'])} results")
                else:
                    errors.append(f"First search failed: {first_search.get('error', 'Unknown error')}")
                    logger.warning(f"First search failed: {first_search.get('error')}")

                # Determine if we need a second search
                needs_recency = self._assess_recency_need(user_query, context)
                has_recent_results = self._has_recent_results(all_results) if all_results else False

                # Second search: Only if recency is important and first search lacks recent results
                if needs_recency and not has_recent_results and search_calls_made < 2:
                    logger.info(f"Performing second search with recency focus...")

                    # Enhance query for recency
                    recent_query = self._enhance_query_for_recency(user_query)

                    second_search = await search_client.search(
                        query=recent_query,
                        num_results=5,
                        date_restrict='m1'  # Past month
                    )
                    search_calls_made += 1

                    if second_search['success']:
                        # Merge results, prioritizing newer content
                        recent_results = second_search['results']
                        all_results = self._merge_and_deduplicate_results(all_results, recent_results)
                        logger.info(f"Second search added {len(recent_results)} recent results")
                    else:
                        errors.append(f"Second search failed: {second_search.get('error', 'Unknown error')}")
                        logger.warning(f"Second search failed: {second_search.get('error')}")

                # Process results for AI consumption
                if all_results:
                    processed_results = self._process_results_for_ai(all_results, user_query)
                    sources = self._extract_sources_metadata(all_results)

                    return {
                        'success': True,
                        'query': user_query,
                        'results': processed_results,
                        'sources': sources,
                        'search_calls_made': search_calls_made,
                        'recency_focused': needs_recency,
                        'has_recent_content': self._has_recent_results(all_results),
                        'timestamp': datetime.now().isoformat(),
                        'errors': errors if errors else None
                    }
                else:
                    return {
                        'success': False,
                        'error': 'No search results found',
                        'results': [],
                        'sources': [],
                        'search_calls_made': search_calls_made,
                        'errors': errors
                    }
        
        except Exception as e:
            logger.error(f"Web search coordination failed: {str(e)}")
            return {
                'success': False,
                'error': f'Search coordination failed: {str(e)}',
                'results': [],
                'sources': [],
                'search_calls_made': search_calls_made
            }
    
    def _assess_recency_need(self, query: str, context: Optional[Dict[str, Any]]) -> bool:
        """
        Assess if the query requires recent/current information.
        """
        query_lower = query.lower()
        
        # Check for explicit recency keywords
        for keyword in self.RECENCY_KEYWORDS['time_sensitive']:
            if keyword in query_lower:
                return True
        
        # Check for temporal phrases
        for phrase in self.RECENCY_KEYWORDS['temporal_phrases']:
            if phrase in query_lower:
                return True
        
        # Check for current year indicators
        for year in self.RECENCY_KEYWORDS['year_indicators']:
            if year in query:
                return True
        
        # Topic-based heuristics
        recency_topics = [
            'news', 'weather', 'stock', 'price', 'event', 'announcement',
            'release', 'update', 'version', 'status', 'election', 'covid',
            'pandemic', 'war', 'conflict', 'economy', 'market'
        ]
        
        for topic in recency_topics:
            if topic in query_lower:
                return True
        
        return False
    
    def _has_recent_results(self, results: List[Dict[str, Any]], days_threshold: int = 30) -> bool:
        """
        Check if results contain recent content.
        """
        recent_count = 0
        for result in results:
            if result.get('published_date'):
                try:
                    pub_date = datetime.fromisoformat(result['published_date'].replace('Z', '+00:00'))
                    threshold_date = datetime.now() - timedelta(days=days_threshold)
                    if pub_date >= threshold_date:
                        recent_count += 1
                except Exception:
                    continue
        
        # Consider "recent" if at least 40% of results are from last 30 days
        return (recent_count / len(results)) >= 0.4 if results else False
    
    def _enhance_query_for_recency(self, original_query: str) -> str:
        """
        Enhance query to focus on recent content.
        """
        current_year = datetime.now().year
        
        # Add temporal modifier if not already present
        temporal_modifiers = ['latest', 'recent', 'current', f'{current_year}']
        
        for modifier in temporal_modifiers:
            if modifier.lower() not in original_query.lower():
                return f"{modifier} {original_query}"
        
        return original_query
    
    def _merge_and_deduplicate_results(
        self,
        first_results: List[Dict[str, Any]],
        second_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge and deduplicate search results, prioritizing newer content.
        """
        seen_urls = set()
        merged_results = []
        
        # First add recent results
        for result in second_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged_results.append(result)
        
        # Then add remaining first results
        for result in first_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged_results.append(result)
        
        # Limit to top 8 results
        return merged_results[:8]
    
    def _process_results_for_ai(
        self,
        results: List[Dict[str, Any]],
        original_query: str
    ) -> List[Dict[str, Any]]:
        """
        Process search results into a format optimized for AI consumption.
        """
        processed = []
        
        for i, result in enumerate(results):
            processed.append({
                'rank': i + 1,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'url': result.get('url', ''),
                'source': result.get('display_url', ''),
                'published_date': result.get('published_date'),
                'relevance_note': self._assess_relevance(result, original_query)
            })
        
        return processed
    
    def _extract_sources_metadata(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract source metadata for frontend display.
        """
        sources = []
        
        for result in results:
            sources.append({
                'title': result.get('title', ''),
                'url': result.get('url', ''),
                'domain': result.get('display_url', ''),
                'snippet': result.get('snippet', '')[:150] + '...' if result.get('snippet', '') else '',
                'published_date': result.get('published_date')
            })
        
        return sources
    
    def _assess_relevance(self, result: Dict[str, Any], query: str) -> str:
        """
        Provide a brief relevance assessment for the AI.
        """
        query_words = set(query.lower().split())
        title_words = set(result.get('title', '').lower().split())
        snippet_words = set(result.get('snippet', '').lower().split())
        
        title_overlap = len(query_words.intersection(title_words))
        snippet_overlap = len(query_words.intersection(snippet_words))
        
        if title_overlap >= 2:
            return "High relevance - query terms in title"
        elif snippet_overlap >= 3:
            return "Good relevance - query terms in content"
        else:
            return "Related content"
    
    def _generate_cache_key(self, query: str) -> str:
        """
        Generate a cache key for the search query.
        """
        # Include date to ensure daily cache invalidation for time-sensitive queries
        date_str = datetime.now().strftime('%Y-%m-%d')
        query_hash = hashlib.md5(f"{query.lower().strip()}_{date_str}".encode()).hexdigest()
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