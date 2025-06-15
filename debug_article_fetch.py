#!/usr/bin/env python3
"""Debug article detail fetching."""

import asyncio
import sqlite3
from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)

async def test_article_fetch():
    """Test article detail fetching with real references."""
    
    # Get some article references from the database
    conn = sqlite3.connect('backend/database/entertainment_columns.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT key, urlname, category, title 
        FROM article_references 
        WHERE is_processed = FALSE 
        LIMIT 3
    ''')
    references = cursor.fetchall()
    conn.close()
    
    if not references:
        print("No unprocessed article references found")
        return
    
    print(f"Found {len(references)} unprocessed references to test:")
    for key, urlname, category, title in references:
        print(f"  {urlname}/n/{key} - {title[:50]}...")
    
    # Test with scraper (NoteScraper doesn't take config parameter)
    async with NoteScraper() as scraper:
        print(f"\nTesting article detail fetching...")
        
        for key, urlname, category, title in references:
            print(f"\n--- Testing {urlname}/n/{key} ---")
            try:
                # Test individual article fetching
                article = await scraper.collect_article_with_details(urlname=urlname, key=key)
                
                if article:
                    print(f"✓ Successfully fetched article:")
                    print(f"  ID: {article.id}")
                    print(f"  Title: {article.title}")
                    print(f"  Author: {article.author}")
                    print(f"  URL: {article.url}")
                    print(f"  Published: {article.published_at}")
                    print(f"  Content preview: {article.content_preview[:100]}...")
                else:
                    print("✗ Failed to fetch article details")
                    
            except Exception as e:
                print(f"✗ Error fetching article: {e}")
                logger.error(f"Error fetching {urlname}/n/{key}: {e}")

if __name__ == "__main__":
    asyncio.run(test_article_fetch())