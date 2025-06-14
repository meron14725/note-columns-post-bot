"""Note article scraping service."""

import asyncio
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup

from backend.app.models.article import (
    Article, 
    NoteArticleMetadata as NoteArticleData,  # エイリアスで互換性維持
    ArticleReference
)
from backend.app.utils.logger import get_logger, log_execution_time
from backend.app.utils.rate_limiter import rate_limiter
from config.config import config 

logger = get_logger(__name__)


class NoteScraper:
    """Note article scraper."""
    
    def __init__(self) -> None:
        """Initialize scraper."""
        self.config = config.urls_config  
        self.collection_settings = config.get_collection_settings()
        self.collection_urls = config.get_collection_urls()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
        })
        self.client_code = None
        self.xsrf_token = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.session.close()
    
    def _get_session_tokens(self, url: str) -> bool:
        """Get session tokens from note page.
        
        Args:
            url: Note page URL
            
        Returns:
            True if client code was successfully obtained
        """
        try:
            response = self.session.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to get session page: {response.status_code}")
                return False
            
            html = response.text
            
            # Extract client code (ccd) from HTML - this is required
            ccd_match = re.search(r'ccd:\s*"([a-f0-9]{64})"', html)
            if not ccd_match:
                # Alternative pattern
                ccd_match = re.search(r'window\.__INITIAL_STATE__.*?"ccd":"([a-f0-9]{64})"', html)
            
            if ccd_match:
                self.client_code = ccd_match.group(1)
                logger.info(f"Got client code: {self.client_code[:10]}...")
            else:
                logger.warning("Could not find client code in HTML")
                return False
            
            # Extract XSRF-TOKEN from cookies (optional - note.com API works without it)
            self.xsrf_token = None
            for cookie in self.session.cookies:
                if cookie.name == 'XSRF-TOKEN':
                    self.xsrf_token = cookie.value
                    logger.info(f"Got XSRF token: {self.xsrf_token[:10]}...")
                    break
            
            if not self.xsrf_token:
                logger.info("No XSRF-TOKEN found in cookies (this is normal for current note.com)")
            
            # Success if we have client code (XSRF token is optional)
            return True
            
        except Exception as e:
            logger.error(f"Error getting session tokens: {e}")
            return False
    
    @log_execution_time
    async def collect_article_list(self) -> List[Dict[str, Any]]:
        """Collect article list (key, urlname) from all configured URLs.
        
        Returns:
            List of article metadata (key, urlname, category, etc.)
        """
        all_articles = []
        collection_urls = self.config.get("collection_urls", [])
        
        logger.info(f"Starting article list collection from {len(collection_urls)} sources")
        
        for url_config in collection_urls:
            try:
                articles = await self._collect_list_from_source(url_config)
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} article references from {url_config['name']}")
                
                # Delay between sources
                delay = self.collection_settings.get("request_delay_seconds", 1.0)
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to collect from {url_config['name']}: {e}")
                continue
        
        # Remove duplicates by key
        unique_articles = {}
        for article in all_articles:
            unique_articles[article['key']] = article
        
        final_articles = list(unique_articles.values())
        logger.info(f"Collected {len(final_articles)} unique article references total")
        
        return final_articles
    
    @log_execution_time
    async def collect_articles(self) -> List[Article]:
        """Collect articles from all configured URLs (backward compatibility).
        
        Returns:
            List of collected articles
        """
        # First, collect article list
        article_list = await self.collect_article_list()
        
        # Convert article references to Article objects without fetching details
        # (Details can be fetched later using collect_article_with_details if needed)
        articles = []
        for ref in article_list:
            article = Article(
                id=ref['id'],
                title=ref['title'],
                url=ref['url'],
                thumbnail=ref.get('thumbnail'),
                published_at=ref.get('published_at', datetime.now(timezone.utc)),
                author=ref.get('author', 'Unknown'),
                category=ref.get('category', 'article'),
                content_preview='',  # Will be filled when details are fetched
                note_data=ref.get('note_data')
            )
            articles.append(article)
        
        return articles
    
    async def _collect_list_from_source(self, url_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect article list from a single source (key, urlname only).
        
        Args:
            url_config: URL configuration
            
        Returns:
            List of article references (not full Article objects)
        """
        articles = []
        base_url = url_config["url"]
        category = url_config["category"]
        
        logger.info(f"Collecting article list from {url_config['name']} (category: {category})")
        
        try:
            # Get session tokens if not already obtained
            if not self.client_code:
                if not self._get_session_tokens(base_url):
                    logger.error("Failed to get session tokens")
                    return articles
            
            # Extract label name from URL if it's an interests page
            label_name = None
            if '/interests/' in base_url:
                label_match = re.search(r'/interests/([^/?]+)', base_url)
                if label_match:
                    from urllib.parse import unquote
                    encoded_label = label_match.group(1)
                    label_name = unquote(encoded_label)  # URLデコードして日本語に戻す
                    logger.info(f"Extracted label name: {label_name}")
            
            # Fetch article list using API
            if label_name:
                page_articles = await self._fetch_api_article_list(label_name, category)
            else:
                # Fallback to HTML parsing for non-interest pages
                page_articles = await self._fetch_page_article_list(base_url, category)
            
            if not page_articles:
                logger.info(f"No articles found from {url_config['name']}")
                return articles
            
            # Filter recent articles
            recent_articles = self._filter_recent_article_list(page_articles)
            articles.extend(recent_articles)
            
            logger.info(f"Collected {len(articles)} article references from {url_config['name']}")
            
        except Exception as e:
            logger.error(f"Error collecting from {url_config['name']}: {e}")
        
        return articles
    
    async def _fetch_api_article_list(self, label_name: str, category: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Fetch article list using note API (key, urlname only).
        
        Args:
            label_name: Label name (e.g., 'K-POP')
            category: Article category
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of article references
        """
        articles = []
        
        for page in range(1, max_pages + 1):
            try:
                # Build API URL with proper encoding
                encoded_label = quote(label_name, safe='')
                api_url = f"https://note.com/api/v3/mkit_layouts/json?context=top_keyword&page={page}&args[label_name]={encoded_label}"
                
                # Update headers with tokens
                headers = {
                    **self.session.headers,
                    "X-Note-Client-Code": self.client_code,
                    "Referer": f"https://note.com/interests/{encoded_label}",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                }
                
                # Add XSRF token if available (optional)
                if self.xsrf_token:
                    headers["X-Xsrf-Token"] = self.xsrf_token
                
                response = self.session.get(api_url, headers=headers)
                
                if response.status_code == 429:
                    # Rate limit exceeded, wait longer
                    logger.warning(f"Rate limit exceeded, waiting 30 seconds...")
                    await asyncio.sleep(30)
                    continue
                elif response.status_code != 200:
                    logger.warning(f"API request failed: {response.status_code}")
                    if response.status_code >= 500:
                        # Server error, wait and retry
                        logger.info("Server error, waiting 10 seconds before retry...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        # Client error, stop trying
                        break
                
                data = response.json()
                
                # Check if last page
                is_last = data.get('data', {}).get('isLast', True)
                
                # Extract notes from sections
                sections = data.get('data', {}).get('sections', [])
                for section in sections:
                    notes = section.get('notes', [])
                    for note in notes:
                        article_ref = self._parse_api_note_reference(note, category)
                        if article_ref:
                            articles.append(article_ref)
                
                page_ref_count = 0
                for section in sections:
                    page_ref_count += len(section.get('notes', []))
                
                logger.info(f"Fetched {page_ref_count} article references from page {page}")
                
                if is_last:
                    break
                
                # Rate limiting
                await asyncio.sleep(self.collection_settings.get("request_delay_seconds", 1.0))
                
            except Exception as e:
                logger.error(f"Error fetching API page {page}: {e}")
                break
        
        return articles
    
    def _parse_api_note_reference(self, note: Dict[str, Any], category: str) -> Optional[Dict[str, Any]]:
        """Parse note reference from API response (key, urlname only).
        
        Args:
            note: Note data from API
            category: Article category
            
        Returns:
            Article reference dictionary
        """
        try:
            # Extract basic fields
            note_id = str(note.get('id', ''))
            key = note.get('key', '')
            title = note.get('name', '')
            
            if not note_id or not title:
                return None
            
            # Extract user data
            user_data = note.get('user', {})
            urlname = user_data.get('urlname', '')
            
            if not urlname:
                return None
            
            # Build URL
            url = f"https://note.com/{urlname}/n/{key}"
            
            # Extract publish date
            published_at = datetime.now(timezone.utc)
            publish_at_str = note.get('publish_at')
            if publish_at_str:
                try:
                    publish_at_str = publish_at_str.replace('+09:00', '+0900')
                    published_at = datetime.strptime(publish_at_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                except:
                    try:
                        # Parse as naive datetime and assume UTC
                        naive_dt = datetime.strptime(publish_at_str[:19], '%Y-%m-%dT%H:%M:%S')
                        published_at = naive_dt.replace(tzinfo=timezone.utc)
                    except:
                        pass
            
            return {
                'id': note_id,
                'key': key,
                'urlname': urlname,
                'title': title,
                'url': url,
                'thumbnail': note.get('eyecatch_url'),
                'published_at': published_at,
                'author': user_data.get('nickname', 'Unknown'),
                'category': category,
                'note_data': NoteArticleData(
                    note_type=note.get('type', 'TextNote'),
                    like_count=note.get('like_count', 0),
                    price=note.get('price', 0),
                    can_read=note.get('can_read', True),
                    is_liked=note.get('is_liked', False)
                )
            }
            
        except Exception as e:
            logger.warning(f"Error parsing API note reference: {e}")
            return None
    
    async def _fetch_page_article_list(self, url: str, category: str) -> List[Dict[str, Any]]:
        """Fetch article list from HTML page (fallback method).
        
        Args:
            url: Page URL
            category: Article category
            
        Returns:
            List of article references
        """
        try:
            response = self.session.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {url}: {response.status_code}")
                return []
            
            html = response.text
            articles = []
            
            # Extract JSON data from __INITIAL_STATE__
            if 'window.__INITIAL_STATE__' in html:
                parsed_articles = self._parse_note_initial_state(html, category)
                # Convert Article objects to references
                for article in parsed_articles:
                    article_ref = {
                        'id': article.id,
                        'key': article.id,  # Assuming ID is the key
                        'urlname': self._extract_urlname_from_url(article.url),
                        'title': article.title,
                        'url': article.url,
                        'thumbnail': article.thumbnail,
                        'published_at': article.published_at,
                        'author': article.author,
                        'category': category,
                        'note_data': article.note_data
                    }
                    articles.append(article_ref)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching page article list from {url}: {e}")
            return []
    
    def _extract_urlname_from_url(self, url: str) -> str:
        """Extract urlname from note URL.
        
        Args:
            url: Note article URL
            
        Returns:
            User's urlname
        """
        import re
        match = re.search(r'note\.com/([^/]+)/', url)
        return match.group(1) if match else 'unknown'
    
    def _filter_recent_article_list(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter article list to only include recent ones.
        
        Args:
            articles: List of article references
            
        Returns:
            List of recent article references
        """
        threshold_days = self.collection_settings.get("old_article_threshold_days", 1)
        threshold_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)
        
        filtered_articles = []
        for article in articles:
            published_at = article.get('published_at', datetime.now(timezone.utc))
            # Ensure both dates have timezone info for comparison
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            if threshold_date.tzinfo is None:
                threshold_date = threshold_date.replace(tzinfo=timezone.utc)
            
            if published_at >= threshold_date:
                filtered_articles.append(article)
        
        return filtered_articles
    
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
        
        logger.info(f"Collecting from {url_config['name']} (category: {category})")
        
        try:
            # Get session tokens if not already obtained
            if not self.client_code:
                if not self._get_session_tokens(base_url):
                    logger.error("Failed to get session tokens")
                    return articles
            
            # Extract label name from URL if it's an interests page
            label_name = None
            if '/interests/' in base_url:
                label_match = re.search(r'/interests/([^/?]+)', base_url)
                if label_match:
                    from urllib.parse import unquote
                    encoded_label = label_match.group(1)
                    label_name = unquote(encoded_label)  # URLデコードして日本語に戻す
                    logger.info(f"Extracted label name: {label_name}")
            
            # Fetch articles using API
            if label_name:
                page_articles = await self._fetch_api_articles(label_name, category)
            else:
                # Fallback to HTML parsing for non-interest pages
                page_articles = await self._fetch_page_articles(base_url, category)
            
            if not page_articles:
                logger.info(f"No articles found from {url_config['name']}")
                return articles
            
            # Filter recent articles
            recent_articles = self._filter_recent_articles(page_articles)
            articles.extend(recent_articles)
            
            logger.info(f"Collected {len(articles)} articles from {url_config['name']}")
            
        except Exception as e:
            logger.error(f"Error collecting from {url_config['name']}: {e}")
        
        return articles
    
    async def _fetch_api_articles(self, label_name: str, category: str, max_pages: int = 5) -> List[Article]:
        """Fetch articles using note API.
        
        Args:
            label_name: Label name (e.g., 'K-POP')
            category: Article category
            max_pages: Maximum number of pages to fetch
            
        Returns:
            List of articles
        """
        articles = []
        
        for page in range(1, max_pages + 1):
            try:
                # Build API URL with proper encoding
                encoded_label = quote(label_name, safe='')
                api_url = f"https://note.com/api/v3/mkit_layouts/json?context=top_keyword&page={page}&args[label_name]={encoded_label}"
                
                # Update headers with tokens
                headers = {
                    **self.session.headers,
                    "X-Note-Client-Code": self.client_code,
                    "Referer": f"https://note.com/interests/{encoded_label}",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                }
                
                # Add XSRF token if available (optional)
                if self.xsrf_token:
                    headers["X-Xsrf-Token"] = self.xsrf_token
                
                response = self.session.get(api_url, headers=headers)
                
                if response.status_code == 429:
                    # Rate limit exceeded, wait longer
                    logger.warning(f"Rate limit exceeded, waiting 30 seconds...")
                    await asyncio.sleep(30)
                    continue
                elif response.status_code != 200:
                    logger.warning(f"API request failed: {response.status_code}")
                    if response.status_code >= 500:
                        # Server error, wait and retry
                        logger.info("Server error, waiting 10 seconds before retry...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        # Client error, stop trying
                        break
                
                data = response.json()
                
                # Check if last page
                is_last = data.get('data', {}).get('isLast', True)
                
                # Extract notes from sections
                sections = data.get('data', {}).get('sections', [])
                for section in sections:
                    notes = section.get('notes', [])
                    for note in notes:
                        article = self._parse_api_note(note, category)
                        if article:
                            articles.append(article)
                
                page_article_count = 0
                for section in sections:
                    page_article_count += len(section.get('notes', []))
                
                logger.info(f"Fetched {page_article_count} articles from page {page}")
                
                if is_last:
                    break
                
                # Rate limiting
                await asyncio.sleep(self.collection_settings.get("request_delay_seconds", 1.0))
                
            except Exception as e:
                logger.error(f"Error fetching API page {page}: {e}")
                break
        
        return articles
    
    def _parse_api_note(self, note: Dict[str, Any], category: str) -> Optional[Article]:
        """Parse note from API response.
        
        Args:
            note: Note data from API
            category: Article category
            
        Returns:
            Parsed article or None
        """
        try:
            # Extract basic fields
            note_id = str(note.get('id', ''))
            key = note.get('key', '')
            title = note.get('name', '')
            
            if not note_id or not title:
                return None
            
            # Build URL
            user_data = note.get('user', {})
            urlname = user_data.get('urlname', '')
            url = f"https://note.com/{urlname}/n/{key}"
            
            # Extract author
            author = user_data.get('nickname', 'Unknown')
            
            # Extract thumbnail
            thumbnail = note.get('eyecatch_url')
            
            # Extract publish date
            published_at = datetime.now(timezone.utc)  # Default to now
            publish_at_str = note.get('publish_at')
            if publish_at_str:
                try:
                    # Handle timezone offset format
                    publish_at_str = publish_at_str.replace('+09:00', '+0900')
                    published_at = datetime.strptime(publish_at_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                except:
                    try:
                        # Try without microseconds
                        published_at = datetime.strptime(publish_at_str[:19], '%Y-%m-%dT%H:%M:%S')
                    except:
                        logger.warning(f"Could not parse date: {publish_at_str}")
            
            # Fetch article detail to get content preview
            content_preview = ''
            if self.collection_settings.get("fetch_article_details", False):
                try:
                    detail = self._fetch_article_detail(urlname, key)
                    if detail:
                        content_preview = detail.get('content_preview', '')
                    else:
                        logger.debug(f"Could not fetch detail for {urlname}/n/{key}")
                except Exception as e:
                    logger.warning(f"Error fetching detail for {urlname}/n/{key}: {e}")
                    # Continue without content preview
            
            # Extract additional metadata
            note_data = NoteArticleData(
                note_type=note.get('type', 'TextNote'),
                like_count=note.get('like_count', 0),
                price=note.get('price', 0),
                can_read=note.get('can_read', True),
                is_liked=note.get('is_liked', False)
            )
            
            return Article(
                id=note_id,
                title=title,
                url=url,
                thumbnail=thumbnail,
                published_at=published_at,
                author=author,
                category=category,
                content_preview=content_preview,
                note_data=note_data
            )
            
        except Exception as e:
            logger.warning(f"Error parsing API note: {e}")
            return None
    
    async def _fetch_page_articles(self, url: str, category: str) -> List[Article]:
        """Fetch articles from a single page (fallback method).
        
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
                
                response = self.session.get(url)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status_code}")
                    if attempt == max_retries - 1:
                        return []
                    continue
                
                html = response.text
                
                # Extract JSON data from __INITIAL_STATE__
                if 'window.__INITIAL_STATE__' in html:
                    logger.debug(f"Found __INITIAL_STATE__ in {url}")
                    articles = self._parse_note_initial_state(html, category)
                    if articles:
                        logger.info(f"Extracted {len(articles)} articles from {url}")
                        return articles
                    else:
                        logger.warning(f"No articles parsed from __INITIAL_STATE__ in {url}")
                else:
                    logger.warning(f"No __INITIAL_STATE__ found in {url}")
                
                # Fallback to HTML parsing
                logger.info(f"Falling back to HTML parsing for {url}")
                return await self._parse_html_response(html, category)
                
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt == max_retries - 1:
                    return []
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    def _parse_note_initial_state(self, html: str, category: str) -> List[Article]:
        """Parse note's __INITIAL_STATE__ from HTML.
        
        Args:
            html: HTML content
            category: Article category
            
        Returns:
            List of parsed articles
        """
        articles = []
        
        try:
            # Extract JSON data from __INITIAL_STATE__
            start = html.find('window.__INITIAL_STATE__') + len('window.__INITIAL_STATE__ = ')
            end = html.find('</script>', start)
            json_str = html[start:end].rstrip(';').strip()
            
            data = json.loads(json_str)
            
            # Look for notes in different possible locations
            notes_data = None
            if 'notes' in data:
                notes_data = data['notes']
            elif 'topContents' in data:
                # Handle top page structure
                top_contents = data['topContents']
                if isinstance(top_contents, dict) and 'notes' in top_contents:
                    notes_data = top_contents['notes']
            elif 'searchResults' in data:
                # Handle search results
                search_results = data['searchResults']
                if 'contents' in search_results:
                    notes_data = {item['id']: item for item in search_results['contents']}
            
            if not notes_data:
                logger.warning(f"No notes data found in __INITIAL_STATE__ for category {category}")
                return articles
            
            # Parse notes data (can be dict or list)
            if isinstance(notes_data, dict):
                note_items = list(notes_data.values())
            else:
                note_items = notes_data
            
            for note_item in note_items:
                try:
                    article = self._parse_note_item(note_item, category)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse note item: {e}")
                    continue
            
            logger.info(f"Parsed {len(articles)} articles from __INITIAL_STATE__ for category {category}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse __INITIAL_STATE__ JSON: {e}")
        except Exception as e:
            logger.error(f"Error parsing __INITIAL_STATE__: {e}")
        
        return articles
    
    def _parse_note_item(self, item: Dict[str, Any], category: str) -> Optional[Article]:
        """Parse individual note item from JSON data.
        
        Args:
            item: Note item data
            category: Article category
            
        Returns:
            Parsed article or None
        """
        try:
            # Extract basic fields
            note_id = str(item.get('id', ''))
            title = item.get('name', '')
            if not note_id or not title:
                return None
            
            # Build URL
            url = f"https://note.com/{item.get('user', {}).get('urlname', '')}/n/{note_id}"
            
            # Extract author
            user_data = item.get('user', {})
            author = user_data.get('name', 'Unknown')
            
            # Extract thumbnail
            thumbnail = None
            if 'eyecatch' in item and item['eyecatch']:
                thumbnail = item['eyecatch']
            elif 'picture' in item and item['picture']:
                thumbnail = item['picture']
            
            # Extract publish date
            published_at = datetime.now(timezone.utc)  # Default to now
            if 'publishAt' in item:
                try:
                    published_at = datetime.fromisoformat(item['publishAt'].replace('Z', '+00:00'))
                except:
                    pass
            elif 'publish_at' in item:
                try:
                    published_at = datetime.fromisoformat(item['publish_at'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Extract content preview
            content_preview = ''
            if 'description' in item:
                content_preview = item['description'][:200]
            elif 'body' in item:
                content_preview = item['body'][:200]
            
            return Article(
                id=note_id,
                title=title,
                url=url,
                thumbnail=thumbnail,
                published_at=published_at,
                author=author,
                category=category,
                content_preview=content_preview
            )
            
        except Exception as e:
            logger.warning(f"Error parsing note item: {e}")
            return None
    
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
            published_at = datetime.now(timezone.utc)
            
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
        threshold_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)
        
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
        threshold_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)
        
        return [
            article for article in articles
            if article.published_at >= threshold_date
        ]
    
    def _fetch_article_detail(self, urlname: str, key: str) -> Optional[Dict[str, Any]]:
        """Fetch article detail from note page.
        
        Args:
            urlname: User's URL name
            key: Article key
            
        Returns:
            Article detail dictionary or None
        """
        try:
            article_url = f"https://note.com/{urlname}/n/{key}"
            
            # Add headers to mimic browser behavior
            headers = {
                **self.session.headers,
                "Referer": f"https://note.com/{urlname}",
            }
            
            response = self.session.get(article_url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch article detail: {response.status_code}")
                return None
            
            html = response.text
            
            # Extract article data from __INITIAL_STATE__
            if 'window.__INITIAL_STATE__' in html:
                detail = self._parse_article_detail_from_initial_state(html, key)
                if detail:
                    return detail
            
            # Try NUXT data if __INITIAL_STATE__ is not available
            if 'window.__NUXT__' in html:
                detail = self._parse_article_detail_from_nuxt(html, key)
                if detail:
                    return detail
            
            # Fallback to HTML parsing
            return self._parse_article_detail_from_html(html, article_url)
            
        except Exception as e:
            logger.error(f"Error fetching article detail for {urlname}/n/{key}: {e}")
            return None
    
    def _parse_article_detail_from_initial_state(self, html: str, key: str) -> Optional[Dict[str, Any]]:
        """Parse article detail from __INITIAL_STATE__.
        
        Args:
            html: HTML content
            key: Article key to find
            
        Returns:
            Article detail dictionary or None
        """
        try:
            # Extract JSON data from __INITIAL_STATE__
            start = html.find('window.__INITIAL_STATE__') + len('window.__INITIAL_STATE__ = ')
            end = html.find('</script>', start)
            json_str = html[start:end].rstrip(';').strip()
            
            data = json.loads(json_str)
            
            # Look for the specific note
            note = None
            
            # Try different possible locations
            if 'note' in data:
                note = data['note']
            elif 'notes' in data and key in data['notes']:
                note = data['notes'][key]
            elif 'currentNote' in data:
                note = data['currentNote']
            
            if not note:
                logger.warning(f"Could not find note with key {key} in __INITIAL_STATE__")
                return None
            
            # Extract article details
            detail = {
                'id': str(note.get('id', key)),
                'key': key,
                'title': note.get('name', ''),
                'thumbnail': note.get('eyecatch'),
                'author': note.get('user', {}).get('nickname', 'Unknown'),
                'type': note.get('type', 'TextNote'),
                'comment_count': note.get('commentCount', 0),
                'like_count': note.get('likeCount', 0),
                'price': note.get('price', 0),
                'can_read': note.get('canRead', True),
            }
            
            # Extract publish date
            published_at = datetime.now(timezone.utc)
            publish_at_str = note.get('publishAt') or note.get('publish_at')
            if publish_at_str:
                try:
                    published_at = datetime.fromisoformat(publish_at_str.replace('Z', '+00:00').replace('+09:00', '+0900'))
                except:
                    try:
                        # Parse as naive datetime and assume UTC
                        naive_dt = datetime.strptime(publish_at_str[:19], '%Y-%m-%dT%H:%M:%S')
                        published_at = naive_dt.replace(tzinfo=timezone.utc)
                    except:
                        pass
            
            detail['published_at'] = published_at
            
            # Extract content preview
            content_preview = ''
            if 'body' in note:
                # Remove HTML tags and get first 200 characters
                body_text = BeautifulSoup(note['body'], 'html.parser').get_text()
                content_preview = body_text[:200]
            elif 'description' in note:
                content_preview = note['description'][:200]
            
            detail['content_preview'] = content_preview
            
            return detail
            
        except Exception as e:
            logger.error(f"Error parsing article detail from __INITIAL_STATE__: {e}")
            return None
    
    def _parse_article_detail_from_nuxt(self, html: str, key: str) -> Optional[Dict[str, Any]]:
        """Parse article detail from __NUXT__ data.
        
        Args:
            html: HTML content
            key: Article key to find
            
        Returns:
            Article detail dictionary or None
        """
        try:
            # For now, NUXT parsing is complex, so we'll skip it
            # and rely on HTML parsing which works well
            logger.debug("NUXT parsing not implemented yet, falling back to HTML")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing article detail from __NUXT__: {e}")
            return None
    
    def _parse_article_detail_from_html(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse article detail from HTML (fallback method).
        
        Args:
            html: HTML content
            url: Article URL
            
        Returns:
            Article detail dictionary or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title - prefer og:title over title tag
            title = 'Unknown'
            og_title = soup.find('meta', {'property': 'og:title'})
            if og_title:
                title = og_title.get('content', 'Unknown')
                # Remove "｜作者名" suffix if present
                title = re.sub(r'｜[^｜]+$', '', title)
            else:
                title_element = soup.find('h1') or soup.find('title')
                if title_element:
                    title = title_element.get_text(strip=True)
                    # Remove "｜作者名" suffix if present
                    title = re.sub(r'｜[^｜]+$', '', title)
            
            # Extract author from various sources
            author = 'Unknown'
            
            # Method 1: From og:title suffix
            og_title = soup.find('meta', {'property': 'og:title'})
            if og_title:
                og_title_text = og_title.get('content', '')
                author_match = re.search(r'｜([^｜]+)$', og_title_text)
                if author_match:
                    author = author_match.group(1)
                    # Remove any remaining suffix like "|副業" etc.
                    author = re.sub(r'｜.+$', '', author)
            
            # Method 2: From URL path
            urlname = 'unknown'
            if author == 'Unknown':
                url_match = re.search(r'note\.com/([^/]+)/', url)
                if url_match:
                    urlname = url_match.group(1)
                    # Look for author name associated with this urlname in the page
                    # This is a heuristic approach
                    author = urlname  # Fallback to urlname
            
            # Method 3: Look for author in structured data or page content
            if author == 'Unknown' or author == urlname:
                # Look for JSON-LD structured data
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'author' in data:
                            author_data = data['author']
                            if isinstance(author_data, dict):
                                author = author_data.get('name', author)
                            elif isinstance(author_data, str):
                                author = author_data
                    except:
                        continue
            
            # Method 4: Look for author in meta tags
            if author == 'Unknown' or author == urlname:
                author_meta = soup.find('meta', {'name': 'author'}) or soup.find('meta', {'property': 'article:author'})
                if author_meta:
                    author = author_meta.get('content', author)
            
            # Extract thumbnail
            thumbnail = None
            og_image = soup.find('meta', {'property': 'og:image'})
            if og_image:
                thumbnail = og_image.get('content')
            
            # Extract published date
            published_at = datetime.now(timezone.utc)
            # Look for time elements or meta tags
            time_element = soup.find('time')
            if time_element:
                datetime_attr = time_element.get('datetime')
                if datetime_attr:
                    try:
                        published_at = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    except:
                        pass
            
            # Look for publication date in meta tags
            current_time = datetime.now(timezone.utc)
            if abs((published_at - current_time).total_seconds()) < 60:  # If still close to current time
                date_meta = soup.find('meta', {'property': 'article:published_time'})
                if date_meta:
                    try:
                        published_at = datetime.fromisoformat(date_meta.get('content', '').replace('Z', '+00:00'))
                    except:
                        pass
            
            # Extract content (both preview and full text)
            content_preview = ''
            content_full = ''
            
            # Look for main content area
            content_selectors = [
                'div.note-common-styles__textnote-body',
                'div[class*="textnote-body"]',
                'div[class*="content"]',
                'div[class*="article-body"]',
                'main',
                'article'
            ]
            
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    full_text = content_element.get_text(strip=True)
                    content_preview = full_text[:200]  # Preview for display
                    content_full = full_text  # Full text for AI evaluation
                    break
            
            # Fallback to meta description
            if not content_preview:
                description_meta = soup.find('meta', {'name': 'description'}) or soup.find('meta', {'property': 'og:description'})
                if description_meta:
                    content_preview = description_meta.get('content', '')[:200]
            
            # Extract key from URL
            key_match = re.search(r'/n/([a-f0-9]+)', url)
            key = key_match.group(1) if key_match else 'unknown'
            
            return {
                'id': key,
                'key': key,
                'title': title,
                'thumbnail': thumbnail,
                'author': author,
                'type': 'TextNote',
                'comment_count': 0,
                'like_count': 0,
                'price': 0,
                'can_read': True,
                'published_at': published_at,
                'content_preview': content_preview,
                'content_full': content_full,
            }
            
        except Exception as e:
            logger.error(f"Error parsing article detail from HTML: {e}")
            return None

    @log_execution_time
    async def collect_article_with_details(self, urlname: str = None, key: str = None) -> Optional[Article]:
        """Collect a single article with full details.
        
        Args:
            urlname: User's URL name (optional if full URL provided)
            key: Article key (optional if full URL provided)
            
        Returns:
            Article with full details or None
        """
        if not urlname or not key:
            logger.error("Both urlname and key are required")
            return None
        
        try:
            # Get session tokens if not already obtained
            if not self.client_code:
                base_url = f"https://note.com/{urlname}"
                if not self._get_session_tokens(base_url):
                    logger.error("Failed to get session tokens")
                    return None
            
            # Fetch article detail
            detail = self._fetch_article_detail(urlname, key)
            if not detail:
                logger.error(f"Failed to fetch article detail for {urlname}/n/{key}")
                return None
            
            # Build article URL
            url = f"https://note.com/{urlname}/n/{key}"
            
            # Create article object
            article = Article(
                id=str(detail.get('id', key)),  # Use detail ID if available, otherwise key
                title=detail.get('title', 'Unknown'),
                url=url,
                thumbnail=detail.get('thumbnail'),
                published_at=detail.get('published_at', datetime.now(timezone.utc)),
                author=detail.get('author', 'Unknown'),
                category='article',  # Default category
                content_preview=detail.get('content_preview', ''),
                note_data=NoteArticleData(
                    note_type=detail.get('type', 'TextNote'),
                    comment_count=detail.get('comment_count', 0)
                )
            )
            
            return article
            
        except Exception as e:
            logger.error(f"Error collecting article with details: {e}")
            return None


# Convenience functions for synchronous usage
def collect_article_list_sync() -> List[Dict[str, Any]]:
    """Collect article list synchronously.
    
    Returns:
        List of article references (key, urlname, etc.)
    """
    async def _collect():
        async with NoteScraper() as scraper:
            return await scraper.collect_article_list()
    
    return asyncio.run(_collect())


def collect_articles_sync() -> List[Article]:
    """Collect articles synchronously.
    
    Returns:
        List of collected articles
    """
    async def _collect():
        async with NoteScraper() as scraper:
            return await scraper.collect_articles()
    
    return asyncio.run(_collect())


def collect_article_detail_sync(urlname: str, key: str) -> Optional[Article]:
    """Collect a single article with details synchronously.
    
    Args:
        urlname: User's URL name
        key: Article key
        
    Returns:
        Article with full details or None
    """
    async def _collect():
        async with NoteScraper() as scraper:
            return await scraper.collect_article_with_details(urlname, key)
    
    return asyncio.run(_collect())