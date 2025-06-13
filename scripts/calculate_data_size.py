#!/usr/bin/env python
"""データサイズ計算"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import setup_logger

logger = setup_logger("data_size_calc", console=True)


async def calculate_data_sizes():
    """データサイズ計算"""
    logger.info("=== データサイズ計算 ===")
    
    async with NoteScraper() as scraper:
        article_list = await scraper.collect_article_list()
        
        if not article_list:
            logger.error("記事リストが取得できませんでした")
            return
        
        # 複数記事でサンプリング
        sample_sizes = []
        preview_sizes = []
        
        for i, ref in enumerate(article_list[:2]):  # 最初の2記事でテスト
            logger.info(f"\nサンプル {i+1}: {ref['title']}")
            
            article = await scraper.collect_article_with_details(
                urlname=ref['urlname'],
                key=ref['key']
            )
            
            if article:
                preview_size = len(article.content_preview.encode('utf-8'))
                full_size = len(article.content_full.encode('utf-8'))
                
                sample_sizes.append(full_size)
                preview_sizes.append(preview_size)
                
                logger.info(f"  プレビュー: {preview_size:,} bytes")
                logger.info(f"  全文: {full_size:,} bytes")
                logger.info(f"  倍率: {full_size/preview_size:.1f}x")
        
        if sample_sizes:
            avg_full_size = sum(sample_sizes) / len(sample_sizes)
            avg_preview_size = sum(preview_sizes) / len(preview_sizes)
            
            logger.info(f"\n=== 統計情報 ===")
            logger.info(f"平均プレビューサイズ: {avg_preview_size:,.0f} bytes")
            logger.info(f"平均全文サイズ: {avg_full_size:,.0f} bytes")
            logger.info(f"平均倍率: {avg_full_size/avg_preview_size:.1f}x")
            
            # 運用規模での計算
            daily_articles = 100
            yearly_days = 365
            
            # 現在の方式（プレビューのみ）
            current_daily = avg_preview_size * daily_articles
            current_yearly = current_daily * yearly_days
            
            # 全文保存方式
            full_daily = avg_full_size * daily_articles
            full_yearly = full_daily * yearly_days
            
            logger.info(f"\n=== 運用規模でのデータ量 ===")
            logger.info(f"日次（100記事）:")
            logger.info(f"  現在方式: {current_daily:,} bytes ({current_daily/1024/1024:.1f} MB)")
            logger.info(f"  全文保存: {full_daily:,} bytes ({full_daily/1024/1024:.1f} MB)")
            logger.info(f"  差分: {full_daily - current_daily:,} bytes ({(full_daily - current_daily)/1024/1024:.1f} MB)")
            
            logger.info(f"\n年間（365日）:")
            logger.info(f"  現在方式: {current_yearly:,} bytes ({current_yearly/1024/1024/1024:.2f} GB)")
            logger.info(f"  全文保存: {full_yearly:,} bytes ({full_yearly/1024/1024/1024:.2f} GB)")
            logger.info(f"  差分: {full_yearly - current_yearly:,} bytes ({(full_yearly - current_yearly)/1024/1024/1024:.2f} GB)")
            
            # SQLiteファイルサイズ推定（インデックス等を考慮して1.5倍）
            sqlite_factor = 1.5
            full_yearly_sqlite = full_yearly * sqlite_factor
            
            logger.info(f"\nSQLiteファイルサイズ推定:")
            logger.info(f"  全文保存: {full_yearly_sqlite/1024/1024/1024:.2f} GB")
            
            if full_yearly_sqlite > 1024*1024*1024:  # 1GB以上
                logger.warning("⚠️ SQLiteファイルが1GB以上になる可能性があります")
            
            if full_yearly_sqlite > 5*1024*1024*1024:  # 5GB以上
                logger.error("❌ SQLiteファイルが5GB以上になり、パフォーマンス問題が発生する可能性があります")


if __name__ == "__main__":
    asyncio.run(calculate_data_sizes())