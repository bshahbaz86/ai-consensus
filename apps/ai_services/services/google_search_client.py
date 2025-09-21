import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GoogleCustomSearchClient:
    """
    Async Google Custom Search API client with retry logic and rate limiting.
    Handles max 2 search calls per user query as specified.
    """
    
    BASE_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_CSE_API_KEY', None)
        self.cx = getattr(settings, 'GOOGLE_CSE_CX', None)
        self.session = None
        
        if not self.api_key:
            logger.warning("GOOGLE_CSE_API_KEY not configured")
        if not self.cx:
            logger.warning("GOOGLE_CSE_CX not configured")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={'User-Agent': 'ChatAI-App/1.0'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def is_configured(self) -> bool:
        """Check if the client is properly configured"""
        return bool(self.api_key and self.cx)
    
    async def search(
        self,
        query: str,
        num_results: int = 5,
        date_restrict: Optional[str] = None,
        retry_count: int = 2
    ) -> Dict[str, Any]:
        """
        Perform a Google Custom Search query.
        
        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            date_restrict: Date restriction (e.g., 'd1' for past day, 'm1' for past month)
            retry_count: Number of retries on failure
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not self.is_configured():
            return {
                'success': False,
                'error': 'Google Custom Search not configured',
                'results': []
            }
        
        if not self.session:
            raise RuntimeError("Client not initialized. Use async with statement.")
        
        params = {
            'key': self.api_key,
            'cx': self.cx,
            'q': query,
            'num': min(num_results, 10),  # Google API max is 10
            'safe': 'active',
            'fields': 'items(title,link,snippet,pagemap,displayLink),searchInformation'
        }
        
        if date_restrict:
            params['dateRestrict'] = date_restrict
        
        for attempt in range(retry_count + 1):
            try:
                async with self.session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._process_search_results(data, query)
                    
                    elif response.status == 429:  # Rate limited
                        if attempt < retry_count:
                            wait_time = (2 ** attempt) * 1  # Exponential backoff
                            logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': 'Rate limited by Google API',
                                'results': []
                            }
                    
                    elif response.status == 403:
                        error_data = await response.json()
                        error_msg = error_data.get('error', {}).get('message', 'API quota exceeded')
                        return {
                            'success': False,
                            'error': f'Google API error: {error_msg}',
                            'results': []
                        }
                    
                    else:
                        logger.warning(f"Google API returned status {response.status}")
                        if attempt < retry_count:
                            await asyncio.sleep(1)
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'Google API error: HTTP {response.status}',
                                'results': []
                            }
            
            except asyncio.TimeoutError:
                if attempt < retry_count:
                    logger.warning(f"Search timeout, retrying... (attempt {attempt + 1})")
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': 'Search request timed out',
                        'results': []
                    }
            
            except Exception as e:
                logger.error(f"Search error on attempt {attempt + 1}: {str(e)}")
                if attempt < retry_count:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f'Search failed: {str(e)}',
                        'results': []
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'results': []
        }
    
    def _process_search_results(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Process and normalize Google search results"""
        try:
            items = data.get('items', [])
            search_info = data.get('searchInformation', {})
            
            processed_results = []
            for item in items:
                result = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'display_url': item.get('displayLink', ''),
                    'published_date': self._extract_publish_date(item),
                }
                processed_results.append(result)
            
            return {
                'success': True,
                'query': query,
                'results': processed_results,
                'total_results': search_info.get('totalResults', '0'),
                'search_time': search_info.get('searchTime', 0),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error processing search results: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to process results: {str(e)}',
                'results': []
            }
    
    def _extract_publish_date(self, item: Dict[str, Any]) -> Optional[str]:
        """Try to extract publish date from search result metadata"""
        try:
            pagemap = item.get('pagemap', {})
            
            # Try different sources for publication date
            for source in ['metatags', 'article', 'newsarticle']:
                if source in pagemap:
                    for meta in pagemap[source]:
                        for date_field in ['article:published_time', 'datePublished', 'publishedDate', 'dateCreated']:
                            if date_field in meta:
                                return meta[date_field]
            
            return None
        except Exception:
            return None
    
    def _is_recent_content(self, result: Dict[str, Any], days_threshold: int = 30) -> bool:
        """Check if content is recent based on publish date"""
        try:
            if not result.get('published_date'):
                return False
            
            pub_date = datetime.fromisoformat(result['published_date'].replace('Z', '+00:00'))
            threshold_date = datetime.now() - timedelta(days=days_threshold)
            
            return pub_date >= threshold_date
        except Exception:
            return False


class GoogleSearchError(Exception):
    """Custom exception for Google Search API errors"""
    pass