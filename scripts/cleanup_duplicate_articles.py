#!/usr/bin/env python3
"""Script to clean up duplicate articles in the database."""

import sys
import sqlite3
from pathlib import Path

# Import modules using installed package structure

from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def cleanup_duplicate_articles():
    """Clean up duplicate articles by URL, keeping only the best one."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Find duplicate URLs
            cursor.execute("""
                SELECT url, COUNT(*) as count
                FROM articles 
                GROUP BY url 
                HAVING COUNT(*) > 1
            """)
            
            duplicates = cursor.fetchall()
            logger.info(f"Found {len(duplicates)} URLs with duplicates")
            
            removed_count = 0
            
            for url, count in duplicates:
                logger.info(f"Processing URL with {count} duplicates: {url}")
                
                # Get all articles for this URL
                cursor.execute("""
                    SELECT id, title, author, is_evaluated, created_at
                    FROM articles 
                    WHERE url = ?
                    ORDER BY is_evaluated DESC, created_at DESC
                """, (url,))
                
                articles = cursor.fetchall()
                
                if not articles:
                    continue
                
                # Keep the first one (evaluated and most recent)
                keep_id = articles[0][0]
                logger.info(f"Keeping article ID: {keep_id}")
                
                # Remove the rest
                for article in articles[1:]:
                    article_id = article[0]
                    logger.info(f"Removing duplicate article ID: {article_id}")
                    
                    # Remove from evaluations first (foreign key constraint)
                    cursor.execute("DELETE FROM evaluations WHERE article_id = ?", (article_id,))
                    
                    # Remove from articles
                    cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
                    
                    removed_count += 1
            
            conn.commit()
            logger.info(f"Cleanup completed. Removed {removed_count} duplicate articles")
            
            # Show final statistics
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT url) FROM articles")
            unique_urls = cursor.fetchone()[0]
            
            logger.info(f"Final statistics: {total_articles} total articles, {unique_urls} unique URLs")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise


if __name__ == "__main__":
    cleanup_duplicate_articles()