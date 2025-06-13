#!/usr/bin/env python
"""Test script for Note scraper."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import setup_logger

# ロガーセットアップ
logger = setup_logger("test_scraper", console=True)


async def test_article_list_collection():
    """記事リストの収集をテスト"""
    logger.info("=== Testing Article List Collection ===")
    
    async with NoteScraper() as scraper:
        # 記事リストを収集
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.warning("No articles found")
            return
        
        logger.info(f"Found {len(article_list)} articles")
        
        # カテゴリ別に集計
        categories = {}
        for ref in article_list:
            category = ref.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        logger.info("Articles by category:")
        for category, count in categories.items():
            logger.info(f"  - {category}: {count}")
        
        # 最初の5件を表示
        logger.info("\nFirst 5 articles:")
        for i, ref in enumerate(article_list[:5]):
            logger.info(f"{i+1}. {ref['title']}")
            logger.info(f"   URL: {ref['url']}")
            logger.info(f"   Key: {ref['key']}")
            logger.info(f"   Author: {ref['author']}")
            logger.info("")


async def test_article_detail_fetch():
    """単一記事の詳細取得をテスト"""
    logger.info("=== Testing Article Detail Fetch ===")
    
    async with NoteScraper() as scraper:
        # まず記事リストを取得
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.warning("No articles found")
            return
        
        # 最初の記事の詳細を取得
        ref = article_list[0]
        logger.info(f"Fetching details for: {ref['title']}")
        
        article = await scraper.collect_article_with_details(
            urlname=ref['urlname'],
            key=ref['key']
        )
        
        if article:
            logger.info(f"Successfully fetched article:")
            logger.info(f"  Title: {article.title}")
            logger.info(f"  Author: {article.author}")
            logger.info(f"  Published: {article.published_at}")
            logger.info(f"  Category: {article.category}")
            logger.info(f"  Preview length: {len(article.content_preview)} chars")
            if article.note_data:
                logger.info(f"  Like count: {article.note_data.like_count}")
                logger.info(f"  Comment count: {article.note_data.comment_count}")
        else:
            logger.error("Failed to fetch article details")


async def test_full_process():
    """完全な処理をテスト（記事リスト→詳細取得）"""
    logger.info("=== Testing Full Process ===")
    
    async with NoteScraper() as scraper:
        # Step 1: 記事リストを収集
        logger.info("Step 1: Collecting article list...")
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.warning("No articles found")
            return
        
        logger.info(f"Found {len(article_list)} articles")
        
        # Step 2: 最初の3件の詳細を取得
        logger.info("\nStep 2: Fetching details for first 3 articles...")
        articles_with_details = []
        
        for i, ref in enumerate(article_list[:3]):
            logger.info(f"\n[{i+1}/3] Fetching: {ref['title']}")
            
            article = await scraper.collect_article_with_details(
                urlname=ref['urlname'],
                key=ref['key']
            )
            
            if article:
                articles_with_details.append(article)
                logger.info(f"  ✓ Success - Preview: {article.content_preview[:100]}...")
            else:
                logger.error(f"  ✗ Failed to fetch details")
            
            # レート制限
            await asyncio.sleep(1)
        
        logger.info(f"\nSuccessfully fetched {len(articles_with_details)}/{3} articles")


async def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Note scraper")
    parser.add_argument(
        "--test", 
        choices=["list", "detail", "full"], 
        default="list",
        help="Test type to run"
    )
    
    args = parser.parse_args()
    
    try:
        if args.test == "list":
            await test_article_list_collection()
        elif args.test == "detail":
            await test_article_detail_fetch()
        elif args.test == "full":
            await test_full_process()
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())