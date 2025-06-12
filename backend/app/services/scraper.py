"""Note article scraping service."""

import asyncio
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from backend.app.models.article import Article, NoteArticleData
from backend.app.utils.logger import get_logger, log_execution_time
from backend.app.utils.rate_limiter import rate_limiter
from config.config import get_urls_config

logger = get_logger(__name__)


class NoteScraper:
    """Note article scraper."""
    
    def __init__(self) -> None:
        """Initialize scraper."""
        self.config = get_urls_config()
        self.session: Optional[httpx.AsyncClient] = None
        self.collection_settings = self.config.get("collection_settings", {})
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=self.collection_settings.get("timeout_seconds", 30),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    @log_execution_time
    async def collect_articles(self) -> List[Article]:
        """Collect articles from all configured URLs.
        
        Returns:
            List of collected articles
        """
        all_articles = []
        collection_urls = self.config.get("collection_urls", [])
        
        logger.info(f"Starting article collection from {len(collection_urls)} sources")
        
        for url_config in collection_urls:
            try:
                articles = await self._collect_from_source(url_config)
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {url_config['name']}")
                
                # Delay between sources
                delay = self.collection_settings.get("request_delay_seconds", 1.0)
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to collect from {url_config['name']}: {e}")
                continue
        
        # Remove duplicates by ID
        unique_articles = {}
        for article in all_articles:
            unique_articles[article.id] = article
        
        final_articles = list(unique_articles.values())
        logger.info(f"Collected {len(final_articles)} unique articles total")
        
        return final_articles
    
    async def _collect_from_source(self, url_config: Dict[str, Any]) -> List[Article]:
        """Collect articles from a single source.
        
        Args:
            url_config: URL configuration
            
        Returns:
            List of articles from this source
        """
        articles = []
        base_url = url_config["url"]
        category = url_config["category"]
        max_pages = self.collection_settings.get("max_pages_per_category", 5)
        
        logger.info(f"Collecting from {url_config['name']} (category: {category})")
        
        for page in range(1, max_pages + 1):
            try:
                # Apply rate limiting
                await rate_limiter.await_if_needed("note")
                
                # Construct URL with page parameter
                page_url = f"{base_url}&page={page}"
                
                # Fetch page
                page_articles = await self._fetch_page_articles(page_url, category)
                
                if not page_articles:
                    logger.info(f"No articles found on page {page}, stopping collection")
                    break
                
                # Check if we should stop due to old articles
                if self._should_stop_collection(page_articles):
                    logger.info(f"Found old articles on page {page}, stopping collection")
                    # Add articles from this page that are still recent
                    recent_articles = self._filter_recent_articles(page_articles)
                    articles.extend(recent_articles)
                    break
                
                articles.extend(page_articles)
                rate_limiter.record_request("note")
                
                logger.debug(f"Collected {len(page_articles)} articles from page {page}")
                
                # Delay between pages
                delay = self.collection_settings.get("request_delay_seconds", 1.0)
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error collecting page {page} from {url_config['name']}: {e}")
                break
        
        return articles
    
    async def _fetch_page_articles(self, url: str, category: str) -> List[Article]:
        """Fetch articles from a single page.
        
        Args:
            url: Page URL
            category: Article category
            
        Returns:
            List of articles from this page
        """
        max_retries = self.collection_settings.get("max_retries", 3)
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1})")
                
                response = await self.session.get(url)
                response.raise_for_status()
                
                # Try to parse as JSON first (API response)
                try:
                    data = response.json()
                    return self._parse_json_response(data, category)
                except ValueError:
                    # If not JSON, try to parse as HTML
                    return await self._parse_html_response(response.text, category)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt == max_retries - 1:
                    raise
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    def _parse_json_response(self, data: Dict[str, Any], category: str) -> List[Article]:
        """Parse JSON API response.
        
        Args:
            data: JSON response data
            category: Article category
            
        Returns:
            List of parsed articles
        """
        articles = []
        
        # Handle different API response structures
        items = data.get("data", {}).get("notes", [])
        if not items:
            items = data.get("notes", [])
        if not items:
            items = data.get("items", [])
        
        for item in items:
            try:
                # Convert to NoteArticleData and then to Article
                note_data = NoteArticleData(**item)
                article = note_data.to_article(category)
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"Failed to parse article item: {e}")
                continue
        
        return articles
    
    async def _parse_html_response(self, html: str, category: str) -> List[Article]:
        """Parse HTML response (fallback method).
        
        Args:
            html: HTML content
            category: Article category
            
        Returns:
            List of parsed articles
        """
        articles = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for article elements (this is a fallback and may need adjustment)
        article_elements = soup.find_all(['article', 'div'], class_=re.compile(r'note|article|post'))
        
        for element in article_elements:
            try:
                article = await self._parse_html_article_element(element, category)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to parse HTML article element: {e}")
                continue
        
        return articles
    
    async def _parse_html_article_element(self, element, category: str) -> Optional[Article]:
        """Parse individual article element from HTML.
        
        Args:
            element: BeautifulSoup element
            category: Article category
            
        Returns:
            Parsed article or None
        """
        try:
            # Extract title
            title_element = element.find(['h1', 'h2', 'h3', 'a'], class_=re.compile(r'title|heading'))
            if not title_element:
                return None
            title = title_element.get_text(strip=True)
            
            # Extract URL
            link_element = element.find('a', href=True)
            if not link_element:
                return None
            url = link_element['href']
            if not url.startswith('http'):
                url = urljoin('https://note.com', url)
            
            # Extract article ID from URL
            import re
            id_match = re.search(r'/n/([a-f0-9]+)', url)
            if not id_match:
                return None
            article_id = id_match.group(1)
            
            # Extract author
            author_element = element.find(['span', 'div'], class_=re.compile(r'author|user|creator'))
            author = author_element.get_text(strip=True) if author_element else "Unknown"
            
            # Extract thumbnail
            img_element = element.find('img', src=True)
            thumbnail = img_element['src'] if img_element else None
            
            # For HTML parsing, we use current time as published_at
            # This is not ideal but works as a fallback
            published_at = datetime.now()
            
            return Article(
                id=article_id,
                title=title,
                url=url,
                thumbnail=thumbnail,
                published_at=published_at,
                author=author,
                category=category,
            )
            
        except Exception as e:
            logger.warning(f"Error parsing HTML article element: {e}")
            return None
    
    def _should_stop_collection(self, articles: List[Article]) -> bool:
        """Check if collection should stop based on article ages.
        
        Args:
            articles: List of articles to check
            
        Returns:
            True if collection should stop
        """
        if not self.collection_settings.get("stop_after_old_articles", True):
            return False
        
        threshold_days = self.collection_settings.get("old_article_threshold_days", 1)
        threshold_date = datetime.now() - timedelta(days=threshold_days)
        
        # If any article is older than threshold, stop collection
        for article in articles:
            if article.published_at < threshold_date:
                return True
        
        return False
    
    def _filter_recent_articles(self, articles: List[Article]) -> List[Article]:
        """Filter articles to only include recent ones.
        
        Args:
            articles: List of articles to filter
            
        Returns:
            List of recent articles
        """
        threshold_days = self.collection_settings.get("old_article_threshold_days", 1)
        threshold_date = datetime.now() - timedelta(days=threshold_days)
        
        return [
            article for article in articles
            if article.published_at >= threshold_date
        ]


# Convenience function for synchronous usage
def collect_articles_sync() -> List[Article]:
    """Collect articles synchronously.
    
    Returns:
        List of collected articles
    """
    async def _collect():
        async with NoteScraper() as scraper:
            return await scraper.collect_articles()
    
    return asyncio.run(_collect())