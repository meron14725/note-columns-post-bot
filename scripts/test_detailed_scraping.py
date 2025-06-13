#!/usr/bin/env python
"""詳細なスクレイピングテスト用スクリプト"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import setup_logger

logger = setup_logger("detailed_test", console=True)


async def test_detailed_scraping():
    """詳細なスクレイピングテストを実行"""
    
    logger.info("=== 詳細スクレイピングテスト開始 ===")
    
    async with NoteScraper() as scraper:
        # Step 1: 記事リスト収集
        logger.info("Step 1: 記事リスト収集")
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.error("記事リストが取得できませんでした")
            return
        
        logger.info(f"取得した記事数: {len(article_list)}")
        
        # 各記事の基本情報を表示
        for i, ref in enumerate(article_list):
            logger.info(f"\n--- 記事 {i+1} (基本情報) ---")
            logger.info(f"ID: {ref['id']}")
            logger.info(f"Key: {ref['key']}")
            logger.info(f"Title: {ref['title']}")
            logger.info(f"Author: {ref['author']}")
            logger.info(f"URL: {ref['url']}")
            logger.info(f"Urlname: {ref['urlname']}")
            logger.info(f"Category: {ref['category']}")
            logger.info(f"Published: {ref['published_at']}")
            logger.info(f"Thumbnail: {ref.get('thumbnail', 'なし')}")
            
            if ref.get('note_data'):
                note_data = ref['note_data']
                logger.info(f"Note Type: {note_data.note_type}")
                logger.info(f"Like Count: {note_data.like_count}")
                logger.info(f"Price: {note_data.price}")
                logger.info(f"Can Read: {note_data.can_read}")
        
        # Step 2: 各記事の詳細情報取得
        logger.info(f"\n=== Step 2: 詳細情報取得 ===")
        
        for i, ref in enumerate(article_list):
            logger.info(f"\n--- 記事 {i+1} 詳細取得中 ---")
            logger.info(f"取得対象: {ref['title']}")
            
            try:
                # 詳細情報を取得
                article = await scraper.collect_article_with_details(
                    urlname=ref['urlname'],
                    key=ref['key']
                )
                
                if article:
                    logger.info("✅ 詳細取得成功")
                    logger.info(f"詳細タイトル: {article.title}")
                    logger.info(f"詳細著者: {article.author}")
                    logger.info(f"詳細公開日: {article.published_at}")
                    logger.info(f"詳細カテゴリ: {article.category}")
                    logger.info(f"サムネイル: {article.thumbnail or 'なし'}")
                    logger.info(f"コンテンツプレビュー長: {len(article.content_preview)} 文字")
                    
                    if len(article.content_preview) > 0:
                        logger.info(f"コンテンツ冒頭: {article.content_preview[:100]}...")
                    
                    if article.note_data:
                        logger.info(f"いいね数: {article.note_data.like_count}")
                        logger.info(f"コメント数: {article.note_data.comment_count}")
                        logger.info(f"記事タイプ: {article.note_data.note_type}")
                    
                    # 基本情報との比較
                    logger.info("\n--- 基本情報vs詳細情報の比較 ---")
                    logger.info(f"タイトル一致: {ref['title'] == article.title}")
                    logger.info(f"著者一致: {ref['author'] == article.author}")
                    logger.info(f"URL一致: {ref['url'] == article.url}")
                    
                else:
                    logger.error("❌ 詳細取得失敗")
                    
            except Exception as e:
                logger.error(f"❌ 詳細取得エラー: {e}")
                
            # レート制限対応
            await asyncio.sleep(1)
        
        logger.info(f"\n=== 詳細スクレイピングテスト完了 ===")


if __name__ == "__main__":
    asyncio.run(test_detailed_scraping())