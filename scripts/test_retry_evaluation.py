#!/usr/bin/env python3
"""Test script for retry evaluation system."""

import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.models.article import Article
from backend.app.utils.logger import get_logger
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


def create_test_articles():
    """Create test articles with same content to trigger duplicate scores."""
    test_articles = []
    
    # Create multiple similar articles to trigger duplicate detection
    for i in range(3):
        article = Article(
            id=f"test_article_{i}",
            title=f"テストゲーム記事 {i}: 新しいゲームの魅力について",
            url=f"https://note.com/test/n/test_article_{i}",
            thumbnail="https://example.com/thumb.jpg",
            published_at="2025-06-15T10:00:00+09:00",
            author=f"テストユーザー{i}",
            content_preview="このゲームは非常に面白く、プレイヤーを魅了する要素が満載です。グラフィックも美しく、ストーリーも充実しています。",
            category="ゲーム",
            collected_at="2025-06-15T10:00:00+09:00",
            is_evaluated=False
        )
        test_articles.append(article)
    
    return test_articles


async def test_retry_evaluation_system():
    """Test the automatic retry evaluation system."""
    try:
        logger.info("🧪 Starting retry evaluation system test")
        
        # Create test articles
        test_articles = create_test_articles()
        logger.info(f"Created {len(test_articles)} test articles")
        
        # Initialize evaluator
        evaluator = ArticleEvaluator()
        
        # Test each article and monitor for duplicate detection
        results = []
        
        for i, article in enumerate(test_articles, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 Testing Article {i}: {article.id}")
            logger.info(f"Title: {article.title}")
            logger.info(f"{'='*60}")
            
            # Evaluate the article
            evaluation = await evaluator._evaluate_single_article(article)
            
            if evaluation:
                results.append(evaluation)
                
                score_pattern = f"{evaluation.quality_score}/{evaluation.originality_score}/{evaluation.entertainment_score}"
                
                logger.info(f"✅ Evaluation completed:")
                logger.info(f"   Score Pattern: {score_pattern}")
                logger.info(f"   Total Score: {evaluation.total_score}")
                logger.info(f"   Is Retry: {evaluation.is_retry_evaluation}")
                
                if evaluation.is_retry_evaluation:
                    logger.info(f"   Retry Reason: {evaluation.retry_reason}")
                    if evaluation.evaluation_metadata:
                        original_pattern = evaluation.evaluation_metadata.get('score_pattern_original', 'N/A')
                        retry_pattern = evaluation.evaluation_metadata.get('score_pattern_retry', 'N/A')
                        logger.info(f"   Original → Retry: {original_pattern} → {retry_pattern}")
                
                logger.info(f"   Summary: {evaluation.ai_summary[:100]}...")
            else:
                logger.error(f"❌ Failed to evaluate article {article.id}")
            
            # Small delay between evaluations
            await asyncio.sleep(2)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total articles tested: {len(test_articles)}")
        logger.info(f"Successful evaluations: {len(results)}")
        
        # Check for duplicate patterns
        patterns = {}
        retry_count = 0
        
        for result in results:
            pattern = f"{result.quality_score}/{result.originality_score}/{result.entertainment_score}"
            if pattern in patterns:
                patterns[pattern] += 1
            else:
                patterns[pattern] = 1
            
            if result.is_retry_evaluation:
                retry_count += 1
        
        logger.info(f"Retry evaluations triggered: {retry_count}")
        logger.info(f"Unique score patterns: {len(patterns)}")
        
        # Log patterns
        for pattern, count in patterns.items():
            status = "🔁 DUPLICATE" if count > 1 else "✅ UNIQUE"
            logger.info(f"   {pattern}: {count} occurrences {status}")
        
        # Test success criteria
        success = True
        if retry_count == 0:
            logger.warning("⚠️  No retry evaluations were triggered - this may indicate the system is not working as expected")
            success = False
        
        if len(patterns) == 1 and len(results) > 1:
            logger.error("❌ All evaluations have the same pattern - retry system may not be working")
            success = False
        
        if success:
            logger.info("✅ Retry evaluation system test PASSED")
        else:
            logger.error("❌ Retry evaluation system test FAILED")
        
        return success
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_duplicate_detection_logic():
    """Test the duplicate detection logic specifically."""
    logger.info("\n🧪 Testing duplicate detection logic")
    
    evaluator = ArticleEvaluator()
    
    # Mock evaluation results with same pattern
    from backend.app.models.evaluation import AIEvaluationResult
    
    # Create identical results to test detection
    result1 = AIEvaluationResult(
        article_id="test1",
        quality_score=20,
        originality_score=12,
        entertainment_score=15,
        total_score=47,
        ai_summary="Test summary 1 with sufficient length to pass validation requirements."
    )
    
    result2 = AIEvaluationResult(
        article_id="test2", 
        quality_score=20,
        originality_score=12,
        entertainment_score=15,
        total_score=47,
        ai_summary="Test summary 2 with sufficient length to pass validation requirements."
    )
    
    # Test detection
    logger.info("Testing first identical result...")
    should_retry_1 = evaluator._check_for_duplicate_scores(result1)
    logger.info(f"Should retry: {should_retry_1} (expected: False)")
    
    logger.info("Testing second identical result...")
    should_retry_2 = evaluator._check_for_duplicate_scores(result2)
    logger.info(f"Should retry: {should_retry_2} (expected: True)")
    
    success = not should_retry_1 and should_retry_2
    if success:
        logger.info("✅ Duplicate detection logic test PASSED")
    else:
        logger.error("❌ Duplicate detection logic test FAILED")
    
    return success


if __name__ == "__main__":
    async def main():
        logger.info("🚀 Starting retry evaluation system tests")
        
        # Test duplicate detection logic
        detection_success = await test_duplicate_detection_logic()
        
        # Test full retry system
        system_success = await test_retry_evaluation_system()
        
        # Overall result
        overall_success = detection_success and system_success
        
        if overall_success:
            logger.info("\n🎉 ALL TESTS PASSED! Retry evaluation system is working correctly.")
        else:
            logger.error("\n💥 SOME TESTS FAILED! Please check the retry evaluation system.")
        
        return overall_success
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
