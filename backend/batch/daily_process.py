"""Daily batch processing script."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.services.scraper import NoteScraper
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.services.json_generator import JSONGenerator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.utils.logger import setup_logger, get_logger, log_execution_time
from backend.app.utils.database import db_manager
from config.config import config

logger = setup_logger("daily_batch", console=True)


class DailyBatchProcessor:
    """Main daily batch processor."""
    
    def __init__(self) -> None:
        """Initialize processor."""
        self.article_repo = ArticleRepository()
        self.evaluation_repo = EvaluationRepository()
        self.json_generator = JSONGenerator()
        
        # Validate configuration
        try:
            config.validate_required_env_vars()
            config.ensure_directories()
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    @log_execution_time
    async def run_daily_batch(self) -> bool:
        """Run the complete daily batch process.
        
        Returns:
            True if batch completed successfully
        """
        logger.info("Starting daily batch process")
        
        try:
            # Step 1: Collect articles
            articles = await self._collect_articles()
            if not articles:
                logger.warning("No new articles collected")
                return False
            
            # Step 2: Save articles to database
            saved_count = self._save_articles(articles)
            logger.info(f"Saved {saved_count} articles to database")
            
            # Step 3: Evaluate unevaluated articles
            evaluations = await self._evaluate_articles()
            if evaluations:
                eval_count = self._save_evaluations(evaluations)
                logger.info(f"Completed {eval_count} evaluations")
            
            # Step 4: Generate JSON files
            json_success = self._generate_json_files()
            if not json_success:
                logger.error("Failed to generate JSON files")
                return False
            
            # Step 5: Log completion statistics
            self._log_completion_stats()
            
            logger.info("Daily batch process completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Daily batch process failed: {e}")
            return False
    
    async def _collect_articles(self) -> list:
        """Collect articles from note.
        
        Returns:
            List of collected articles
        """
        logger.info("Step 1: Collecting articles")
        
        try:
            async with NoteScraper() as scraper:
                articles = await scraper.collect_articles()
            
            logger.info(f"Collected {len(articles)} articles from note")
            return articles
            
        except Exception as e:
            logger.error(f"Article collection failed: {e}")
            return []
    
    def _save_articles(self, articles: list) -> int:
        """Save articles to database.
        
        Args:
            articles: List of articles to save
            
        Returns:
            Number of articles saved
        """
        logger.info("Step 2: Saving articles to database")
        
        try:
            saved_count = self.article_repo.save_articles(articles)
            return saved_count
            
        except Exception as e:
            logger.error(f"Failed to save articles: {e}")
            return 0
    
    async def _evaluate_articles(self) -> list:
        """Evaluate unevaluated articles.
        
        Returns:
            List of evaluations
        """
        logger.info("Step 3: Evaluating articles with AI")
        
        try:
            # Get unevaluated articles
            unevaluated = self.article_repo.get_unevaluated_articles(limit=100)
            
            if not unevaluated:
                logger.info("No articles to evaluate")
                return []
            
            logger.info(f"Found {len(unevaluated)} articles to evaluate")
            
            # Evaluate with AI
            evaluator = ArticleEvaluator()
            evaluations = await evaluator.evaluate_articles(unevaluated)
            
            return evaluations
            
        except Exception as e:
            logger.error(f"Article evaluation failed: {e}")
            return []
    
    def _save_evaluations(self, evaluations: list) -> int:
        """Save evaluations to database and mark articles as evaluated.
        
        Args:
            evaluations: List of evaluations to save
            
        Returns:
            Number of evaluations saved
        """
        logger.info("Saving evaluations to database")
        
        try:
            # Save evaluations
            saved_count = self.evaluation_repo.save_evaluations(evaluations)
            
            # Mark articles as evaluated
            for evaluation in evaluations:
                self.article_repo.mark_as_evaluated(evaluation.article_id)
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Failed to save evaluations: {e}")
            return 0
    
    def _generate_json_files(self) -> bool:
        """Generate JSON files for GitHub Pages.
        
        Returns:
            True if generation successful
        """
        logger.info("Step 4: Generating JSON files")
        
        try:
            success = self.json_generator.generate_all_json_files()
            return success
            
        except Exception as e:
            logger.error(f"JSON generation failed: {e}")
            return False
    
    def _log_completion_stats(self) -> None:
        """Log completion statistics."""
        try:
            # Get database stats
            stats = db_manager.get_database_stats()
            
            # Get evaluation stats
            eval_stats = self.evaluation_repo.get_evaluation_statistics(days=1)
            
            logger.info("=== Daily Batch Completion Statistics ===")
            logger.info(f"Total articles in database: {stats.get('articles_count', 0)}")
            logger.info(f"Total evaluations: {stats.get('evaluations_count', 0)}")
            logger.info(f"Articles evaluated today: {eval_stats.get('total', 0)}")
            
            if eval_stats.get('total', 0) > 0:
                logger.info(f"Average score today: {eval_stats.get('average_total_score', 0):.1f}")
                logger.info(f"High quality articles today: {eval_stats.get('high_quality_count', 0)}")
            
            logger.info("==========================================")
            
        except Exception as e:
            logger.warning(f"Failed to log completion stats: {e}")


async def main():
    """Main function."""
    processor = DailyBatchProcessor()
    
    try:
        success = await processor.run_daily_batch()
        
        if success:
            logger.info("Daily batch completed successfully")
            sys.exit(0)
        else:
            logger.error("Daily batch failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Daily batch interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in daily batch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())