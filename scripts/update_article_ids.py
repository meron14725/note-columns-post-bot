#!/usr/bin/env python3
"""Script to update article IDs to use key_urlname format."""

import sys
import sqlite3
import re
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_key_and_urlname_from_url(url: str) -> tuple:
    """Extract key and urlname from note URL.
    
    Args:
        url: Note article URL
        
    Returns:
        Tuple of (key, urlname) or (None, None) if extraction fails
    """
    # Pattern: https://note.com/{urlname}/n/{key}
    # Key can include letters and numbers, not just hex
    match = re.search(r'note\.com/([^/]+)/n/([a-zA-Z0-9]+)', url)
    if match:
        urlname = match.group(1)
        key = match.group(2)
        return key, urlname
    return None, None


def update_article_ids():
    """Update article IDs to use key_urlname format."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all articles with their current data
            cursor.execute("""
                SELECT id, url, title
                FROM articles
            """)
            
            articles = cursor.fetchall()
            logger.info(f"Found {len(articles)} articles to process")
            
            updated_count = 0
            
            for old_id, url, title in articles:
                # Extract key and urlname from URL
                key, urlname = extract_key_and_urlname_from_url(url)
                
                if not key or not urlname:
                    logger.warning(f"Could not extract key/urlname from URL: {url}")
                    continue
                
                # Generate new ID
                new_id = f"{key}_{urlname}"
                
                if old_id == new_id:
                    logger.debug(f"ID already correct for: {title}")
                    continue
                
                logger.info(f"Updating article ID: {old_id} -> {new_id} ({title})")
                
                # Check if new ID already exists
                cursor.execute("SELECT COUNT(*) FROM articles WHERE id = ?", (new_id,))
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"New ID {new_id} already exists, skipping {old_id}")
                    continue
                
                # Update evaluations table first (foreign key constraint)
                cursor.execute("""
                    UPDATE evaluations 
                    SET article_id = ? 
                    WHERE article_id = ?
                """, (new_id, old_id))
                
                # Update articles table
                cursor.execute("""
                    UPDATE articles 
                    SET id = ? 
                    WHERE id = ?
                """, (new_id, old_id))
                
                updated_count += 1
            
            conn.commit()
            logger.info(f"Updated {updated_count} article IDs")
            
            # Show sample of new IDs
            cursor.execute("SELECT id, url FROM articles LIMIT 5")
            samples = cursor.fetchall()
            logger.info("Sample of updated IDs:")
            for article_id, url in samples:
                logger.info(f"  {article_id} -> {url}")
            
    except Exception as e:
        logger.error(f"Error during ID update: {e}")
        raise


if __name__ == "__main__":
    update_article_ids()