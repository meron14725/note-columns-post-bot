#!/usr/bin/env python3
"""Test the automatic retry evaluation system."""

import sys
import asyncio
import logging
from pathlib import Path

# Import modules using installed package structure

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.models.article import Article
from backend.app.utils.logger import get_logger

# Enable detailed logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)


async def test_retry_system():
    """Test the retry evaluation system with articles designed to trigger duplicates."""
    try:
        # Create test articles that are likely to get similar scores
        similar_articles = [
            Article(
                id="test_retry_1",
                title="ゲーム音楽の基礎",
                url="https://note.com/test1",
                author="テストユーザー1",
                published_at="2025-06-15T10:00:00+09:00",
                category="ゲーム",
                content_preview="ゲーム音楽について基本的な内容を説明します。音楽の役割とその効果について。"
            ),
            Article(
                id="test_retry_2", 
                title="ゲーム音楽の効果",
                url="https://note.com/test2",
                author="テストユーザー2",
                published_at="2025-06-15T11:00:00+09:00",
                category="ゲーム",
                content_preview="ゲーム音楽がプレイヤーに与える影響について解説します。音楽の心理的効果を中心に。"
            ),
            Article(
                id="test_retry_3",
                title="ゲーム音楽の歴史",
                url="https://note.com/test3", 
                author="テストユーザー3",
                published_at="2025-06-15T12:00:00+09:00",
                category="ゲーム",
                content_preview="ゲーム音楽の発展について歴史的に振り返ります。初期から現代までの変遷を説明。"
            ),
            Article(
                id="test_retry_4",
                title="ゲーム音楽の技術",
                url="https://note.com/test4", 
                author="テストユーザー4",
                published_at="2025-06-15T13:00:00+09:00",
                category="ゲーム",
                content_preview="ゲーム音楽制作の技術的側面について解説します。制作手法と技術の進歩について。"
            )
        ]
        
        evaluator = ArticleEvaluator()
        
        logger.info(f"🧪 Testing retry evaluation system with {len(similar_articles)} similar articles")
        logger.info("Goal: Trigger duplicate detection and test automatic retry mechanism")
        
        results = []
        for i, article in enumerate(similar_articles, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"📝 EVALUATING ARTICLE {i}: {article.id}")
            logger.info(f"Title: {article.title}")
            logger.info(f"Content: {article.content_preview}")
            logger.info(f"{'='*80}")
            
            try:
                # Use the main evaluation method which includes retry logic
                evaluation = await evaluator._evaluate_single_article(article)
                
                if evaluation:
                    logger.info(f"\n✅ EVALUATION COMPLETED:")
                    logger.info(f"Article ID: {evaluation.article_id}")
                    logger.info(f"Scores: {evaluation.quality_score}/{evaluation.originality_score}/{evaluation.entertainment_score} = {evaluation.total_score}")
                    logger.info(f"Is Retry: {evaluation.is_retry_evaluation}")
                    if evaluation.is_retry_evaluation:
                        logger.info(f"Retry Reason: {evaluation.retry_reason}")
                        logger.info(f"🔄 RETRY EVALUATION TRIGGERED!")
                    logger.info(f"Summary: {evaluation.ai_summary[:100]}...")
                    
                    results.append({
                        'article_id': evaluation.article_id,
                        'pattern': f"{evaluation.quality_score}/{evaluation.originality_score}/{evaluation.entertainment_score}",
                        'total_score': evaluation.total_score,
                        'is_retry': evaluation.is_retry_evaluation,
                        'retry_reason': evaluation.retry_reason,
                        'summary': evaluation.ai_summary[:50] + "..." if len(evaluation.ai_summary) > 50 else evaluation.ai_summary
                    })
                else:
                    logger.error(f"❌ EVALUATION FAILED for {article.id}")
                
            except Exception as e:
                logger.error(f"❌ ERROR during evaluation of {article.id}: {e}")
            
            # Delay between evaluations
            logger.info("⏱️  Waiting 3 seconds before next evaluation...")
            await asyncio.sleep(3)
        
        # Analyze results
        logger.info(f"\n{'='*80}")
        logger.info("📊 RETRY SYSTEM TEST RESULTS")
        logger.info(f"{'='*80}")
        
        logger.info(f"Total evaluations: {len(results)}")
        retry_count = sum(1 for r in results if r['is_retry'])
        logger.info(f"Retry evaluations: {retry_count}")
        
        # Check for score patterns
        patterns = {}
        for result in results:
            pattern = result['pattern']
            if pattern in patterns:
                patterns[pattern].append(result)
            else:
                patterns[pattern] = [result]
        
        logger.info(f"\nScore pattern analysis:")
        duplicate_found = False
        for pattern, articles in patterns.items():
            logger.info(f"  Pattern {pattern}: {len(articles)} articles")
            if len(articles) > 1:
                duplicate_found = True
                logger.warning(f"    ⚠️  DUPLICATE PATTERN: {pattern}")
                for article in articles:
                    retry_status = "🔄 RETRY" if article['is_retry'] else "📝 ORIGINAL"
                    logger.info(f"      - {article['article_id']}: {retry_status}")
        
        # Final assessment
        logger.info(f"\n{'='*80}")
        logger.info("🎯 TEST ASSESSMENT")
        logger.info(f"{'='*80}")
        
        if retry_count > 0:
            logger.info(f"✅ SUCCESS: Retry system activated {retry_count} times")
            logger.info("✅ Automatic retry evaluation is working correctly")
        else:
            logger.info("ℹ️  INFO: No retry evaluations triggered (articles were sufficiently different)")
        
        if duplicate_found and retry_count == 0:
            logger.warning("⚠️  WARNING: Duplicates detected but no retries triggered - check detection logic")
        elif not duplicate_found:
            logger.info("✅ SUCCESS: All articles received unique scores")
        
        logger.info("\n📋 DETAILED RESULTS:")
        for result in results:
            retry_info = f" (RETRY: {result['retry_reason']})" if result['is_retry'] else ""
            logger.info(f"  {result['article_id']}: {result['pattern']} = {result['total_score']}{retry_info}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_retry_system())