#!/usr/bin/env python
"""ストリーミング評価方式のテスト"""

import asyncio
import sys
from pathlib import Path

# Import modules using installed package structure

from backend.app.services.scraper import NoteScraper
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.utils.logger import setup_logger

logger = setup_logger("streaming_eval_test", console=True)


async def test_streaming_evaluation():
    """ストリーミング評価方式のテスト"""
    
    logger.info("=== ストリーミング評価方式テスト ===")
    
    async with NoteScraper() as scraper:
        # Step 1: 記事リスト取得
        logger.info("Step 1: 記事リスト収集")
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.error("記事リストが取得できませんでした")
            return
        
        logger.info(f"取得した記事数: {len(article_list)}")
        
        # Step 2: ストリーミング評価（記事詳細取得→即評価→破棄）
        logger.info("\nStep 2: ストリーミング評価開始")
        
        evaluator = ArticleEvaluator()
        total_articles = len(article_list)
        
        for i, ref in enumerate(article_list):
            logger.info(f"\n--- 記事 {i+1}/{total_articles} ---")
            logger.info(f"処理中: {ref['title']}")
            
            try:
                # 記事詳細取得（全文含む）
                logger.info("📄 詳細取得中...")
                article = await scraper.collect_article_with_details(
                    urlname=ref['urlname'],
                    key=ref['key']
                )
                
                if not article:
                    logger.error("❌ 詳細取得失敗")
                    continue
                
                logger.info(f"✅ 詳細取得成功（全文: {len(article.content_full)} 文字）")
                
                # AI評価実行
                logger.info("🤖 AI評価中...")
                evaluation = await evaluator._evaluate_single_article(article)
                
                if evaluation:
                    logger.info(f"✅ AI評価成功")
                    logger.info(f"   総合スコア: {evaluation.total_score}/100")
                    logger.info(f"   文章の質: {evaluation.quality_score}/40")
                    logger.info(f"   独自性: {evaluation.originality_score}/30")
                    logger.info(f"   エンタメ性: {evaluation.entertainment_score}/30")
                    logger.info(f"   AI要約: {evaluation.ai_summary[:100]}...")
                else:
                    logger.error("❌ AI評価失敗")
                
                # 記事オブジェクトを破棄（メモリ節約）
                del article
                logger.info("🗑️ 記事データ破棄（メモリ節約）")
                
                # レート制限
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ エラー: {e}")
                continue
        
        logger.info(f"\n=== ストリーミング評価完了 ===")
        logger.info("メリット:")
        logger.info("- DB容量圧迫なし（全文保存しない）")
        logger.info("- メモリ使用量最小化")
        logger.info("- リアルタイム評価")


async def compare_data_sizes():
    """データサイズ比較"""
    logger.info("\n=== データサイズ比較 ===")
    
    async with NoteScraper() as scraper:
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            return
        
        ref = article_list[0]
        article = await scraper.collect_article_with_details(
            urlname=ref['urlname'],
            key=ref['key']
        )
        
        if article:
            preview_size = len(article.content_preview.encode('utf-8'))
            full_size = len(article.content_full.encode('utf-8'))
            
            logger.info(f"1記事のデータサイズ:")
            logger.info(f"  プレビュー: {preview_size:,} bytes")
            logger.info(f"  全文: {full_size:,} bytes")
            logger.info(f"  差分: {full_size - preview_size:,} bytes")
            
            # 年間推定
            daily_articles = 100
            yearly_preview = preview_size * daily_articles * 365
            yearly_full = full_size * daily_articles * 365
            
            logger.info(f"\n年間推定（100記事/日）:")
            logger.info(f"  プレビューのみ: {yearly_preview:,} bytes ({yearly_preview/1024/1024:.1f} MB)")
            logger.info(f"  全文保存: {yearly_full:,} bytes ({yearly_full/1024/1024:.1f} MB)")
            logger.info(f"  差分: {yearly_full - yearly_preview:,} bytes ({(yearly_full - yearly_preview)/1024/1024:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(test_streaming_evaluation())
    asyncio.run(compare_data_sizes())