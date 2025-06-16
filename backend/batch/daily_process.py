"""Daily batch processing script."""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add project root to Python path for config imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.app.services.scraper import NoteScraper
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.services.json_generator import JSONGenerator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.models.article import Article, NoteArticleMetadata
from backend.app.utils.logger import setup_logger, log_execution_time
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
        """Run the complete daily batch process with streaming evaluation.
        
        Returns:
            True if batch completed successfully
        """
        logger.info("Starting daily batch process (streaming evaluation)")
        
        try:
            # Step 1: Streaming collection and evaluation (articles → evaluate → save evaluation → discard full content)
            evaluations_count = await self._collect_and_evaluate_streaming()
            if evaluations_count == 0:
                logger.warning("No new articles processed or evaluated")
                return False
            
            logger.info(f"Completed streaming evaluation: {evaluations_count} articles")
            
            # Step 2: Generate JSON files
            json_success = self._generate_json_files()
            if not json_success:
                logger.error("Failed to generate JSON files")
                return False
            
            # Step 3: Log completion statistics
            self._log_completion_stats()
            
            logger.info("Daily batch process completed successfully (streaming evaluation)")
            return True
            
        except Exception as e:
            logger.error(f"Daily batch process failed: {e}")
            return False
    
    async def _collect_and_evaluate_streaming(self) -> int:
        """Collect articles and evaluate them in streaming fashion (no full content storage).
        
        Returns:
            Number of successful evaluations
        """
        logger.info("Step 1: Streaming collection and evaluation")
        
        try:
            evaluations_count = 0
            
            async with NoteScraper() as scraper:
                # Phase 1: Collect article list from all categories
                logger.info("Phase 1: Collecting article list from all categories...")
                article_list = await scraper.collect_article_list()
                
                if not article_list:
                    logger.warning("No articles found in any category")
                    return 0
                
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
                    return 0
                
                logger.info(f"Found {len(new_article_refs)} new articles for streaming processing")
                
                # Phase 2: Streaming processing (collect details → evaluate → save → discard)
                logger.info("Phase 2: Streaming processing...")
                evaluator = ArticleEvaluator()
                
                for i, ref in enumerate(new_article_refs):
                    try:
                        logger.info(f"[{i+1}/{len(new_article_refs)}] Processing: {ref['title'][:50]}...")
                        
                        # Get session tokens if not already obtained
                        if not scraper.client_code:
                            base_url = f"https://note.com/{ref['urlname']}"
                            if not scraper._get_session_tokens(base_url):
                                logger.warning(f"  ✗ Failed to get session tokens for {ref['urlname']}")
                                continue
                        
                        # Fetch article details (raw data)
                        article_detail = scraper._fetch_article_detail(ref['urlname'], ref['key'])
                        
                        if not article_detail:
                            logger.warning(f"  ✗ Failed to fetch details for {ref['key']}")
                            continue
                        
                        # Extract full content from raw detail
                        full_content = article_detail.get('content_full', '') or article_detail.get('content_preview', '')
                        
                        # Build article URL
                        url = f"https://note.com/{ref['urlname']}/n/{ref['key']}"
                        
                        # Create article object for DB storage (without full content)
                        article_for_db = Article(
                            id=str(article_detail.get('id', ref['key'])),
                            title=article_detail.get('title', ref['title']),
                            url=url,
                            thumbnail=article_detail.get('thumbnail', ref.get('thumbnail')),
                            published_at=article_detail.get('published_at', ref['published_at']),
                            author=article_detail.get('author', ref['author']),
                            content_preview=article_detail.get('content_preview', ''),
                            category=ref.get('category', 'article'),
                            note_data=NoteArticleMetadata(
                                note_type=article_detail.get('type', 'TextNote'),
                                comment_count=article_detail.get('comment_count', 0),
                                like_count=article_detail.get('like_count', 0),
                                price=article_detail.get('price', 0),
                                can_read=article_detail.get('can_read', True)
                            )
                        )
                        
                        # Save article to DB (preview only)
                        saved_count = self.article_repo.save_articles([article_for_db])
                        
                        if saved_count > 0:
                            logger.info(f"  ✓ Saved article to DB (preview: {len(article_for_db.content_preview or '')} chars)")
                            
                            # Evaluate with full content
                            logger.info(f"  🤖 Evaluating with full content ({len(full_content)} chars)...")
                            evaluation = await evaluator.evaluate_article_with_full_content(article_for_db, full_content)
                            
                            if evaluation:
                                # Save evaluation
                                eval_saved = self.evaluation_repo.save_evaluations([evaluation])
                                if eval_saved > 0:
                                    # Mark article as evaluated
                                    self.article_repo.mark_as_evaluated(article_for_db.id)
                                    evaluations_count += 1
                                    logger.info(f"  ✅ Evaluation completed (score: {evaluation.total_score}/100)")
                                else:
                                    logger.warning(f"  ✗ Failed to save evaluation")
                            else:
                                logger.warning(f"  ✗ Evaluation failed")
                        else:
                            logger.warning(f"  ✗ Failed to save article to DB")
                        
                        # Discard full content from memory
                        del full_content
                        
                        # Rate limiting between requests
                        delay = config.get_collection_settings().get("request_delay_seconds", 1.0)
                        await asyncio.sleep(delay)
                        
                        # Progress checkpoint every 10 articles
                        if (i + 1) % 10 == 0:
                            logger.info(f"Progress: {i+1}/{len(new_article_refs)} articles processed, {evaluations_count} evaluations completed")
                        
                    except Exception as e:
                        logger.error(f"  ✗ Error processing article {ref['key']}: {e}")
                        continue
                
                logger.info(f"Streaming processing completed: {evaluations_count} articles evaluated successfully")
                return evaluations_count
            
        except Exception as e:
            logger.error(f"Streaming collection and evaluation failed: {e}")
            return 0
    
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