#!/usr/bin/env python3
"""Batch AI evaluation with improved rate limiting."""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


class BatchEvaluator:
    """Batch AI evaluator with optimized rate limiting."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.article_repo = ArticleRepository()
        self.eval_repo = EvaluationRepository()
        self.evaluator = ArticleEvaluator()
    
    async def evaluate_batch(self, batch_size: int = 10):
        """Evaluate articles in small batches."""
        try:
            # Get unevaluated articles
            unevaluated_articles = self.article_repo.get_unevaluated_articles()
            total_articles = len(unevaluated_articles)
            
            if total_articles == 0:
                logger.info("✅ All articles are already evaluated!")
                return True
            
            logger.info(f"🤖 Starting batch evaluation of {total_articles} articles")
            logger.info(f"Batch size: {batch_size}")
            
            completed = 0
            failed = 0
            
            # Process in batches
            for i in range(0, total_articles, batch_size):
                batch = unevaluated_articles[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_articles + batch_size - 1) // batch_size
                
                logger.info(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")
                
                batch_completed = 0
                for article in batch:
                    try:
                        # Add extra delay between requests
                        if batch_completed > 0:
                            await asyncio.sleep(2.0)  # 2 second delay between requests
                        
                        evaluation = await self.evaluator._evaluate_single_article(article)
                        
                        if evaluation:
                            success = self.eval_repo.save_evaluation(evaluation)
                            if success:
                                # Mark article as evaluated
                                article.is_evaluated = True
                                self.article_repo.save_article(article)
                                
                                completed += 1
                                batch_completed += 1
                                logger.info(f"✅ Evaluated ({completed}/{total_articles}): {article.title[:50]}... [Score: {evaluation.total_score}]")
                            else:
                                failed += 1
                                logger.error(f"❌ Failed to save evaluation for: {article.title[:50]}...")
                        else:
                            failed += 1
                            logger.warning(f"⚠️ Evaluation failed for: {article.title[:50]}...")
                            
                    except Exception as e:
                        failed += 1
                        logger.error(f"❌ Error evaluating {article.title[:50]}...: {e}")
                
                # Longer delay between batches
                if i + batch_size < total_articles:
                    logger.info(f"⏳ Waiting 10 seconds before next batch...")
                    await asyncio.sleep(10.0)
            
            logger.info(f"\n📊 Batch Evaluation Complete!")
            logger.info(f"✅ Successfully evaluated: {completed}")
            logger.info(f"❌ Failed evaluations: {failed}")
            logger.info(f"📈 Success rate: {(completed/(completed+failed)*100):.1f}%" if (completed+failed) > 0 else "N/A")
            
            return completed > 0
            
        except Exception as e:
            logger.error(f"Error in batch evaluation: {e}")
            return False
    
    def print_current_status(self):
        """Print current evaluation status."""
        try:
            total_articles = self.article_repo.get_article_count()
            evaluated_articles = self.article_repo.get_evaluated_article_count()
            
            logger.info("=" * 50)
            logger.info("📊 CURRENT STATUS")
            logger.info("=" * 50)
            logger.info(f"Total articles: {total_articles}")
            logger.info(f"Evaluated articles: {evaluated_articles}")
            logger.info(f"Remaining: {total_articles - evaluated_articles}")
            logger.info(f"Progress: {(evaluated_articles/total_articles*100):.1f}%" if total_articles > 0 else "N/A")
            
            # Category breakdown
            categories = ["K-POP", "邦楽", "映画", "アニメ", "ゲーム"]
            logger.info("\n📋 By category:")
            for category in categories:
                try:
                    category_articles = self.article_repo.get_articles_by_category(category, limit=1000)
                    evaluated_count = sum(1 for a in category_articles if a.is_evaluated)
                    logger.info(f"  {category}: {evaluated_count}/{len(category_articles)}")
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")


async def main():
    """Main execution function."""
    evaluator = BatchEvaluator()
    
    # Print current status
    evaluator.print_current_status()
    
    # Run batch evaluation
    success = await evaluator.evaluate_batch(batch_size=5)  # Small batches for rate limiting
    
    if success:
        logger.info("\n🎉 Batch evaluation completed!")
        evaluator.print_current_status()
    else:
        logger.error("\n❌ Batch evaluation failed!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    asyncio.run(main())