#!/usr/bin/env python3
"""Script to restore test data with corrected IDs."""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.models.article import Article
from backend.app.models.evaluation import Evaluation
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_key_and_urlname_from_url(url: str) -> tuple:
    """Extract key and urlname from note URL."""
    import re
    match = re.search(r'note\.com/([^/]+)/n/([a-zA-Z0-9]+)', url)
    if match:
        urlname = match.group(1)
        key = match.group(2)
        return key, urlname
    return None, None


def restore_test_data():
    """Restore test data from archive with corrected IDs."""
    try:
        # Load archive data
        archive_path = project_root / "docs/data/archives/articles_20250615.json"
        with open(archive_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        article_repo = ArticleRepository()
        eval_repo = EvaluationRepository()
        
        logger.info(f"Restoring {len(data['articles'])} articles from archive")
        
        # Track unique articles by URL
        unique_articles = {}
        
        for item in data['articles']:
            url = item['url']
            
            # Skip duplicates, keep the one with highest score
            if url in unique_articles:
                if item['total_score'] > unique_articles[url]['total_score']:
                    unique_articles[url] = item
                continue
            else:
                unique_articles[url] = item
        
        logger.info(f"Processing {len(unique_articles)} unique articles")
        
        for item in unique_articles.values():
            # Generate correct ID
            key, urlname = extract_key_and_urlname_from_url(item['url'])
            if not key or not urlname:
                logger.warning(f"Could not extract key/urlname from URL: {item['url']}")
                continue
            
            correct_id = f"{key}_{urlname}"
            
            # Create Article object
            article = Article(
                id=correct_id,
                title=item['title'],
                url=item['url'],
                thumbnail=item.get('thumbnail'),
                published_at=datetime.fromisoformat(item['published_at'].replace('+09:00', '+00:00')),
                author=item['author'],
                category=item['category'],
                content_preview='',
                is_evaluated=True
            )
            
            # Save article
            success = article_repo.save_article(article)
            if not success:
                logger.error(f"Failed to save article: {correct_id}")
                continue
            
            # Create Evaluation object
            evaluation = Evaluation(
                article_id=correct_id,
                quality_score=item['scores']['quality'],
                originality_score=item['scores']['originality'],
                entertainment_score=item['scores']['entertainment'],
                total_score=item['total_score'],
                ai_summary=item['ai_summary'],
                evaluated_at=datetime.fromisoformat(item['evaluated_at'])
            )
            
            # Save evaluation
            eval_success = eval_repo.save_evaluation(evaluation)
            if not eval_success:
                logger.error(f"Failed to save evaluation for: {correct_id}")
                continue
            
            logger.info(f"Restored article with correct ID: {correct_id}")
        
        logger.info("Data restoration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during data restoration: {e}")
        raise


if __name__ == "__main__":
    restore_test_data()