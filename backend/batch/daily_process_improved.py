"""Improved daily batch processing with article reference deduplication."""

import argparse
import asyncio
import sys
from typing import Optional


from backend.app.models.article import Article, NoteArticleMetadata
from backend.app.models.article_reference import ArticleReference
from backend.app.repositories.article_reference_repository import (
    ArticleReferenceRepository,
)
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.repositories.evaluation_repository import EvaluationRepository
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.services.json_generator import JSONGenerator
from backend.app.services.scraper import NoteScraper
from backend.app.utils.logger import get_logger, log_execution_time, setup_logger
from config.config import ensure_directories, validate_required_env_vars

logger = get_logger(__name__)


class ImprovedDailyBatchProcessor:
    """Improved daily batch processor with article reference deduplication."""

    def __init__(
        self, target_categories: Optional[list[str]] = None, limit: Optional[int] = None
    ) -> None:
        """Initialize processor.

        Args:
            target_categories: List of categories to process (None for all)
            limit: Maximum number of articles to process (None for unlimited)
        """
        self.article_repo = ArticleRepository()
        self.evaluation_repo = EvaluationRepository()
        self.article_ref_repo = ArticleReferenceRepository()
        self.json_generator = JSONGenerator()
        self.target_categories = target_categories
        self.limit = limit

        logger.info(
            f"Initialized processor (categories: {target_categories}, limit: {limit})"
        )

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
            True if successful, False otherwise
        """
        logger.info("Starting improved daily batch process")

        try:
            # Step 1: Collect article references and evaluate new articles
            evaluated_count = await self._collect_and_evaluate_with_references()

            if evaluated_count == 0:
                logger.info("No new articles to process")
                return True

            # Step 2: Generate JSON files for website
            logger.info("Step 2: Generating JSON files for website")
            json_success = self._generate_json_files()

            if not json_success:
                logger.error("JSON generation failed")
                return False

            logger.info(
                f"Daily batch completed successfully: {evaluated_count} articles evaluated"
            )
            return True

        except Exception as e:
            logger.error(f"Daily batch failed: {e}")
            return False

    async def _collect_and_evaluate_with_references(self) -> int:
        """Collect article references and evaluate new articles.

        Returns:
            Number of evaluations completed
        """
        logger.info(
            "Step 1: Improved collection and evaluation with reference deduplication"
        )

        try:
            evaluations_count = 0

            async with NoteScraper() as scraper:
                # Phase 1: Collect article references from all categories
                logger.info(
                    "Phase 1: Collecting article references from all categories..."
                )
                article_list = await scraper.collect_article_list()

                if not article_list:
                    logger.warning("No articles found in any category")
                    return 0

                logger.info(
                    f"Found {len(article_list)} article references across all categories"
                )

                # Log article distribution by category
                category_counts = {}
                for ref in article_list:
                    category = ref.get("category", "unknown")
                    category_counts[category] = category_counts.get(category, 0) + 1

                for category, count in category_counts.items():
                    logger.info(f"  - {category}: {count} articles")

                # Convert to ArticleReference objects
                article_references = []
                for ref in article_list:
                    try:
                        article_ref = ArticleReference(
                            key=ref["key"],
                            urlname=ref["urlname"],
                            category=ref["category"],
                            title=ref.get("title"),
                            author=ref.get("author"),
                            thumbnail=ref.get("thumbnail"),
                            published_at=ref.get("published_at"),
                        )
                        article_references.append(article_ref)
                    except Exception as e:
                        logger.warning(
                            f"Failed to create ArticleReference for {ref.get('key', 'unknown')}: {e}"
                        )
                        continue

                # Save article references to database (with automatic deduplication)
                saved_refs = self.article_ref_repo.save_references(article_references)
                logger.info(f"Saved {saved_refs} article references to database")

                # Get unprocessed references for detailed processing
                unprocessed_refs = self.article_ref_repo.get_unprocessed_references()

                # Filter by target categories if specified
                if self.target_categories:
                    original_count = len(unprocessed_refs)
                    unprocessed_refs = [
                        ref
                        for ref in unprocessed_refs
                        if ref.category in self.target_categories
                    ]
                    logger.info(
                        f"Filtered from {original_count} to {len(unprocessed_refs)} references for categories: {self.target_categories}"
                    )

                # Apply limit if specified
                if self.limit and len(unprocessed_refs) > self.limit:
                    unprocessed_refs = unprocessed_refs[: self.limit]
                    logger.info(f"Limited to {self.limit} references for processing")

                if not unprocessed_refs:
                    logger.info("No article references to process after filtering")
                    return 0

                logger.info(
                    f"Found {len(unprocessed_refs)} article references for processing"
                )

                # Phase 2: Process unprocessed references (fetch details → evaluate → save)
                logger.info("Phase 2: Processing unprocessed article references...")
                evaluator = ArticleEvaluator()

                for i, ref in enumerate(unprocessed_refs):
                    try:
                        logger.info(
                            f"[{i + 1}/{len(unprocessed_refs)}] Processing: {ref.title[:50]}..."
                        )

                        # Get session tokens if not already obtained
                        if not scraper.client_code:
                            base_url = f"https://note.com/{ref.urlname}"
                            if not scraper._get_session_tokens(base_url):
                                logger.warning(
                                    f"  ✗ Failed to get session tokens for {ref.urlname}"
                                )
                                continue

                        # Fetch article details (raw data)
                        article_detail = scraper._fetch_article_detail(
                            ref.urlname, ref.key
                        )

                        if not article_detail:
                            logger.warning(f"  ✗ Failed to fetch details for {ref.key}")
                            continue

                        # Extract full content from raw detail
                        full_content = article_detail.get(
                            "content_full", ""
                        ) or article_detail.get("content_preview", "")

                        # Create article object for DB storage (without full content)
                        article_for_db = Article(
                            id=ref.article_id,  # Use consistent ID generation
                            title=article_detail.get("title", ref.title),
                            url=ref.article_url,
                            thumbnail=article_detail.get("thumbnail", ref.thumbnail),
                            published_at=article_detail.get(
                                "published_at", ref.published_at
                            ),
                            author=article_detail.get("author", ref.author),
                            content_preview=article_detail.get("content_preview", ""),
                            category=ref.category,
                            note_data=NoteArticleMetadata(
                                note_type=article_detail.get("type", "TextNote"),
                                comment_count=article_detail.get("comment_count", 0),
                                like_count=article_detail.get("like_count", 0),
                                price=article_detail.get("price", 0),
                                can_read=article_detail.get("can_read", True),
                            ),
                        )

                        # Save article to DB (preview only)
                        saved_count = self.article_repo.save_articles([article_for_db])

                        if saved_count > 0:
                            logger.info(
                                f"  ✓ Saved article to DB (preview: {len(article_for_db.content_preview or '')} chars)"
                            )

                            # Evaluate with full content
                            logger.info(
                                f"  🤖 Evaluating with full content ({len(full_content)} chars)..."
                            )
                            evaluation = (
                                await evaluator.evaluate_article_with_full_content(
                                    article_for_db, full_content
                                )
                            )

                            if evaluation:
                                # Save evaluation
                                eval_saved = self.evaluation_repo.save_evaluations(
                                    [evaluation]
                                )
                                if eval_saved > 0:
                                    # Mark article as evaluated and reference as processed
                                    self.article_repo.mark_as_evaluated(
                                        article_for_db.id
                                    )
                                    self.article_ref_repo.mark_as_processed(
                                        ref.key, ref.urlname
                                    )
                                    evaluations_count += 1
                                    logger.info(
                                        f"  ✅ Evaluation completed (score: {evaluation.total_score}/100)"
                                    )
                                else:
                                    logger.warning("  ✗ Failed to save evaluation")
                            else:
                                logger.warning("  ✗ Evaluation failed")
                        else:
                            logger.warning("  ✗ Failed to save article to DB")

                        # Discard full content from memory
                        del full_content

                        # Progress logging every 10 articles
                        if (i + 1) % 10 == 0:
                            logger.info(
                                f"Progress: {i + 1}/{len(unprocessed_refs)} articles processed, {evaluations_count} evaluations completed"
                            )

                    except Exception as e:
                        logger.error(
                            f"Failed to process article reference {ref.key}/{ref.urlname}: {e}"
                        )
                        continue

                logger.info(
                    f"Streaming processing completed: {evaluations_count} articles evaluated successfully"
                )
                return evaluations_count

        except Exception as e:
            logger.error(f"Collection and evaluation failed: {e}")
            return 0

    def _generate_json_files(self) -> bool:
        """Generate JSON files for website.

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.json_generator.generate_all_json_files()
            if success:
                logger.info("JSON files generated successfully")
            else:
                logger.error("JSON file generation failed")
            return success
        except Exception as e:
            logger.error(f"JSON file generation failed: {e}")
            return False


async def main():
    """Main entry point for improved daily batch processing."""
    # Setup logging
    setup_logger()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Improved daily batch processing")
    parser.add_argument(
        "--json-only", action="store_true", help="Generate JSON files only"
    )
    parser.add_argument(
        "--categories", nargs="*", help="Process specific categories only"
    )
    parser.add_argument("--limit", type=int, help="Limit number of articles to process")

    args = parser.parse_args()

    try:
        processor = ImprovedDailyBatchProcessor(
            target_categories=args.categories, limit=args.limit
        )

        # Check operation mode
        if args.json_only:
            logger.info("Running JSON generation only")
            success = processor._generate_json_files()
        else:
            logger.info("Running full daily batch process")
            success = await processor.run_daily_batch()

        if success:
            logger.info("Process completed successfully")
            sys.exit(0)
        else:
            logger.error("Process failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Process failed with exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
