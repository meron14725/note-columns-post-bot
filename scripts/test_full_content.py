#!/usr/bin/env python
"""記事の全文取得テスト"""

import asyncio
import sys
from pathlib import Path

# Import modules using installed package structure

from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import setup_logger

logger = setup_logger("full_content_test", console=True)


async def test_full_content_extraction():
    """記事の全文取得テスト"""
    
    logger.info("=== 記事全文取得テスト ===")
    
    async with NoteScraper() as scraper:
        # 記事リスト取得
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.error("記事リストが取得できませんでした")
            return
        
        # 最初の記事で全文取得テスト
        ref = article_list[0]
        logger.info(f"テスト対象記事: {ref['title']}")
        logger.info(f"URL: {ref['url']}")
        
        # 詳細取得（現在の実装）
        article = await scraper.collect_article_with_details(
            urlname=ref['urlname'],
            key=ref['key']
        )
        
        if article:
            logger.info(f"現在のコンテンツプレビュー長: {len(article.content_preview)} 文字")
            logger.info(f"プレビュー: {article.content_preview}")
            
            # HTMLを直接解析して全文を取得してみる
            logger.info("\n=== 全文取得試行 ===")
            article_url = f"https://note.com/{ref['urlname']}/n/{ref['key']}"
            
            response = scraper.session.get(article_url)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # より詳細なセレクターで全文を探す
                content_selectors = [
                    'div.note-common-styles__textnote-body',
                    'div[class*="textnote-body"]',
                    'div[class*="note-common-styles"]',
                    'div[class*="content"]',
                    'div[class*="article"]',
                    'main div',
                    'article div'
                ]
                
                logger.info("全文取得を試行中...")
                
                for i, selector in enumerate(content_selectors):
                    elements = soup.select(selector)
                    logger.info(f"セレクター {i+1} '{selector}': {len(elements)}個の要素")
                    
                    for j, element in enumerate(elements[:3]):  # 最初の3つを確認
                        text = element.get_text(strip=True)
                        if len(text) > 500:  # 500文字以上なら本文候補
                            logger.info(f"  要素 {j+1}: {len(text)} 文字")
                            logger.info(f"  冒頭: {text[:200]}...")
                            logger.info(f"  末尾: ...{text[-100:]}")
                            
                            # これが本文と思われる場合
                            if len(text) > 1000:
                                logger.info(f"✅ 本文候補発見！全長: {len(text)} 文字")
                                return text
                
                # クラス名を確認
                logger.info("\n=== ページ内のdivクラス一覧 ===")
                divs = soup.find_all('div', class_=True)
                class_names = set()
                for div in divs:
                    classes = div.get('class', [])
                    for cls in classes:
                        if any(keyword in cls.lower() for keyword in ['content', 'body', 'text', 'article', 'note']):
                            class_names.add(cls)
                
                for cls in sorted(class_names):
                    logger.info(f"  クラス: {cls}")
            
        else:
            logger.error("記事詳細取得に失敗")


if __name__ == "__main__":
    asyncio.run(test_full_content_extraction())