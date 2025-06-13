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
from config.config import config, validate_required_env_vars, ensure_directories

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
            validate_required_env_vars()
            ensure_directories()
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
            # Step 1: Collect articles (2-phase process)
            articles = await self._collect_articles_two_phase()
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
    
    async def _collect_articles_two_phase(self) -> list:
        """Collect articles from note using 2-phase process.
        
        Phase 1: Collect article list (key, urlname) from all categories
        Phase 2: Fetch detailed content for each article
        
        Returns:
            List of collected articles with full details
        """
        logger.info("Step 1: Collecting articles (2-phase process)")
        
        try:
            async with NoteScraper() as scraper:
                # Phase 1: Collect article list from all categories
                logger.info("Phase 1: Collecting article list from all categories...")
                article_list = await scraper.collect_article_list()
                
                if not article_list:
                    logger.warning("No articles found in any category")
                    return []
                
                logger.info(f"Found {len(article_list)} articles across all categories")
                
                # Log article distribution by category
                category_counts = {}
                for ref in article_list:
                    category = ref.get('category', 'unknown')
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                for category, count in category_counts.items():
                    logger.info(f"  - {category}: {count} articles")
                
                # Check existing articles to avoid duplicates
                existing_ids = set()
                try:
                    existing_articles = self.article_repo.get_all_article_ids()
                    existing_ids = set(existing_articles)
                    logger.info(f"Found {len(existing_ids)} existing articles in database")
                except Exception as e:
                    logger.warning(f"Could not check existing articles: {e}")
                
                # Filter out existing articles
                new_article_refs = []
                for ref in article_list:
                    if ref['id'] not in existing_ids:
                        new_article_refs.append(ref)
                
                if not new_article_refs:
                    logger.info("All articles already exist in database")
                    return []
                
                logger.info(f"Found {len(new_article_refs)} new articles to fetch details")
                
                # Phase 2: Fetch detailed content for each new article
                logger.info("Phase 2: Fetching article details...")
                articles = []
                
                for i, ref in enumerate(new_article_refs):
                    try:
                        logger.info(f"[{i+1}/{len(new_article_refs)}] Fetching: {ref['title'][:50]}...")
                        
                        article = await scraper.collect_article_with_details(
                            urlname=ref['urlname'],
                            key=ref['key']
                        )
                        
                        if article:
                            # Preserve category from reference
                            article.category = ref.get('category', 'article')
                            articles.append(article)
                            logger.info(f"  ✓ Successfully fetched details (preview: {len(article.content_preview)} chars)")
                        else:
                            logger.warning(f"  ✗ Failed to fetch details for {ref['key']}")
                        
                        # Rate limiting between requests
                        delay = config.get_collection_settings().get("request_delay_seconds", 1.0)
                        await asyncio.sleep(delay)
                        
                        # Progress checkpoint every 10 articles
                        if (i + 1) % 10 == 0:
                            logger.info(f"Progress: {i+1}/{len(new_article_refs)} articles processed")
                        
                    except Exception as e:
                        logger.error(f"  ✗ Error fetching article {ref['key']}: {e}")
                        continue
                
                logger.info(f"Successfully collected {len(articles)} articles with full details")
                return articles
            
        except Exception as e:
            logger.error(f"Article collection failed: {e}")
            return []
    
    async def _collect_articles(self) -> list:
        """Legacy method - redirects to two-phase collection.
        
        Returns:
            List of collected articles
        """
        return await self._collect_articles_two_phase()
    
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