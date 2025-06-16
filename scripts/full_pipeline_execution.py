#!/usr/bin/env python3
"""Complete pipeline execution: Scraping → Evaluation → Website Generation."""

import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Import modules using installed package structure

from backend.app.services.scraper import NoteScraper
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.services.json_generator import JSONGenerator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


class FullPipelineExecutor:
    """Complete pipeline executor."""
    
    def __init__(self):
        """Initialize executor."""
        self.article_repo = ArticleRepository()
        self.eval_repo = EvaluationRepository()
        self.json_generator = JSONGenerator()
        
    async def execute_full_pipeline(self):
        """Execute the complete pipeline."""
        try:
            logger.info("🚀 Starting Full Pipeline Execution")
            logger.info("=" * 60)
            
            # Step 1: Article Collection
            logger.info("📰 Step 1: Collecting articles from 5 categories...")
            articles = await self._collect_articles()
            if not articles:
                logger.error("❌ No articles collected. Pipeline terminated.")
                return False
            
            # Step 2: Save Articles to Database
            logger.info(f"\n💾 Step 2: Saving {len(articles)} articles to database...")
            saved_count = self._save_articles(articles)
            logger.info(f"✅ Saved {saved_count} articles to database")
            
            # Step 3: AI Evaluation
            logger.info(f"\n🤖 Step 3: AI evaluation of {saved_count} articles...")
            evaluations = await self._evaluate_articles(articles)
            if not evaluations:
                logger.error("❌ No evaluations completed. Pipeline terminated.")
                return False
            
            # Step 4: Save Evaluations
            logger.info(f"\n💾 Step 4: Saving {len(evaluations)} evaluations...")
            eval_saved_count = self._save_evaluations(evaluations)
            logger.info(f"✅ Saved {eval_saved_count} evaluations")
            
            # Step 5: Generate Website JSON
            logger.info(f"\n🌐 Step 5: Generating website JSON files...")
            json_success = self._generate_json_files()
            if not json_success:
                logger.error("❌ JSON generation failed. Pipeline terminated.")
                return False
            
            # Step 6: Pipeline Summary
            logger.info(f"\n📊 Step 6: Pipeline Summary")
            self._print_pipeline_summary()
            
            logger.info("\n🎉 Full Pipeline Execution Completed Successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _collect_articles(self):
        """Collect articles from all configured sources."""
        try:
            async with NoteScraper() as scraper:
                articles = await scraper.collect_articles()
                
                logger.info(f"📊 Collection Results:")
                logger.info(f"  Total articles collected: {len(articles)}")
                
                # Show breakdown by category
                category_counts = {}
                for article in articles:
                    category = article.category
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                for category, count in category_counts.items():
                    logger.info(f"  {category}: {count} articles")
                
                return articles
                
        except Exception as e:
            logger.error(f"Error during article collection: {e}")
            return []
    
    def _save_articles(self, articles):
        """Save articles to database."""
        saved_count = 0
        for article in articles:
            try:
                success = self.article_repo.save_article(article)
                if success:
                    saved_count += 1
                    logger.debug(f"Saved: {article.title[:50]}...")
                else:
                    logger.warning(f"Failed to save: {article.title[:50]}...")
            except Exception as e:
                logger.error(f"Error saving article {article.title[:50]}...: {e}")
        
        return saved_count
    
    async def _evaluate_articles(self, articles):
        """Evaluate articles using AI."""
        try:
            evaluator = ArticleEvaluator()
            evaluations = await evaluator.evaluate_articles(articles)
            
            logger.info(f"📊 Evaluation Results:")
            logger.info(f"  Total evaluations: {len(evaluations)}")
            
            if evaluations:
                # Show score statistics
                scores = [eval.total_score for eval in evaluations]
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                
                logger.info(f"  Average score: {avg_score:.1f}")
                logger.info(f"  Highest score: {max_score}")
                logger.info(f"  Lowest score: {min_score}")
                
                # Show score distribution
                score_ranges = {"90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "50-59": 0, "<50": 0}
                for score in scores:
                    if score >= 90:
                        score_ranges["90-100"] += 1
                    elif score >= 80:
                        score_ranges["80-89"] += 1
                    elif score >= 70:
                        score_ranges["70-79"] += 1
                    elif score >= 60:
                        score_ranges["60-69"] += 1
                    elif score >= 50:
                        score_ranges["50-59"] += 1
                    else:
                        score_ranges["<50"] += 1
                
                logger.info("  Score distribution:")
                for range_name, count in score_ranges.items():
                    if count > 0:
                        logger.info(f"    {range_name}: {count} articles")
            
            return evaluations
            
        except Exception as e:
            logger.error(f"Error during AI evaluation: {e}")
            return []
    
    def _save_evaluations(self, evaluations):
        """Save evaluations to database."""
        saved_count = 0
        for evaluation in evaluations:
            try:
                success = self.eval_repo.save_evaluation(evaluation)
                if success:
                    saved_count += 1
                    logger.debug(f"Saved evaluation for: {evaluation.article_id}")
                else:
                    logger.warning(f"Failed to save evaluation for: {evaluation.article_id}")
            except Exception as e:
                logger.error(f"Error saving evaluation for {evaluation.article_id}: {e}")
        
        return saved_count
    
    def _generate_json_files(self):
        """Generate all JSON files for the website."""
        try:
            success = self.json_generator.generate_all_json_files()
            
            if success:
                logger.info("✅ Generated all JSON files:")
                logger.info("  - articles.json")
                logger.info("  - top5.json") 
                logger.info("  - meta.json")
                logger.info("  - categories.json")
                logger.info("  - statistics.json")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating JSON files: {e}")
            return False
    
    def _print_pipeline_summary(self):
        """Print final pipeline summary."""
        try:
            # Get final database counts
            total_articles = self.article_repo.get_article_count()
            evaluated_articles = self.article_repo.get_evaluated_article_count()
            
            logger.info("=" * 60)
            logger.info("📈 FINAL PIPELINE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✅ Total articles in database: {total_articles}")
            logger.info(f"✅ Evaluated articles: {evaluated_articles}")
            logger.info(f"✅ Evaluation completion rate: {(evaluated_articles/total_articles*100):.1f}%" if total_articles > 0 else "N/A")
            
            # Get category breakdown
            categories = ["K-POP", "邦楽", "映画", "アニメ", "ゲーム"]
            logger.info("\n📊 Articles by category:")
            for category in categories:
                try:
                    category_articles = self.article_repo.get_articles_by_category(category, limit=1000)
                    evaluated_count = sum(1 for a in category_articles if a.is_evaluated)
                    logger.info(f"  {category}: {len(category_articles)} total, {evaluated_count} evaluated")
                except:
                    logger.info(f"  {category}: Error getting count")
            
            # Show time
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"\n🕒 Completed at: {current_time}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")


async def main():
    """Main execution function."""
    executor = FullPipelineExecutor()
    success = await executor.execute_full_pipeline()
    
    if success:
        logger.info("🎉 Pipeline completed successfully! Website is ready.")
        sys.exit(0)
    else:
        logger.error("❌ Pipeline failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Enable detailed logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    asyncio.run(main())