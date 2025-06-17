"""Twitter/X posting service."""

from datetime import datetime, timedelta
from typing import Any, Optional

import tweepy

from backend.app.models.evaluation import ArticleWithEvaluation
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.utils.logger import get_logger, log_execution_time
from backend.app.utils.rate_limiter import rate_limiter
from config.config import config, get_posting_schedule

logger = get_logger(__name__)


class TwitterBot:
    """Twitter/X posting bot."""

    def __init__(self) -> None:
        """Initialize Twitter bot."""
        self.config = config
        self.posting_config = get_posting_schedule()
        self.article_repo = ArticleRepository()

        # Initialize Twitter API
        self.api = self._initialize_twitter_api()

    def _initialize_twitter_api(self) -> Optional[tweepy.API]:
        """Initialize Twitter API client.

        Returns:
            Twitter API client or None if credentials not available
        """
        if not self.config.has_twitter_credentials:
            logger.warning("Twitter credentials not available")
            return None

        try:
            # Twitter API v1.1 for posting
            auth = tweepy.OAuthHandler(
                self.config.twitter_credentials["api_key"],
                self.config.twitter_credentials["api_secret"],
            )
            auth.set_access_token(
                self.config.twitter_credentials["access_token"],
                self.config.twitter_credentials["access_token_secret"],
            )

            api = tweepy.API(auth, wait_on_rate_limit=True)

            # Verify credentials
            api.verify_credentials()
            logger.info("Twitter API initialized successfully")
            return api

        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
            return None

    @log_execution_time
    async def post_scheduled_content(self) -> bool:
        """Post scheduled content based on current time.

        Returns:
            True if posting was successful
        """
        if not self.api:
            logger.error("Twitter API not available")
            return False

        current_time = datetime.now()

        # Check if we should post now
        post_config = self._get_current_post_config(current_time)
        if not post_config:
            logger.info("No scheduled post for current time")
            return True

        logger.info(f"Creating scheduled post: {post_config['post_type']}")

        try:
            # Get articles for the post
            articles = await self._get_articles_for_post(post_config)

            if not articles:
                logger.warning("No articles available for posting")
                return False

            # Create and post tweet
            tweet_content = self._create_tweet_content(articles, post_config)
            success = await self._post_tweet(tweet_content)

            if success:
                logger.info(f"Successfully posted {post_config['post_type']}")
            else:
                logger.error(f"Failed to post {post_config['post_type']}")

            return success

        except Exception as e:
            logger.error(f"Error in scheduled posting: {e}")
            return False

    def _get_current_post_config(
        self, current_time: datetime
    ) -> Optional[dict[str, Any]]:
        """Get post configuration for current time.

        Args:
            current_time: Current datetime

        Returns:
            Post configuration or None if no match
        """
        daily_posts = self.posting_config.get("daily_posts", [])
        current_time.strftime("%H:%M")

        for post_config in daily_posts:
            post_time = post_config.get("time", "")

            # Allow some tolerance (±5 minutes)
            post_datetime = datetime.strptime(post_time, "%H:%M").time()
            current_datetime = current_time.time()

            time_diff = abs(
                datetime.combine(datetime.today(), current_datetime)
                - datetime.combine(datetime.today(), post_datetime)
            )

            if time_diff <= timedelta(minutes=5):
                return post_config

        return None

    async def _get_articles_for_post(
        self, post_config: dict[str, Any]
    ) -> list[ArticleWithEvaluation]:
        """Get articles for the post based on configuration.

        Args:
            post_config: Post configuration

        Returns:
            List of articles for the post
        """
        post_type = post_config.get("post_type", "")
        selection_criteria = self.posting_config.get("selection_criteria", {}).get(
            post_type, {}
        )

        min_score = selection_criteria.get("min_score", 70)
        max_articles = selection_criteria.get("max_articles", 5)

        # Get top articles from today, fallback to recent days if needed
        articles = self.article_repo.get_articles_with_evaluations(
            min_score=min_score, limit=max_articles, days=1
        )

        # If not enough articles from today, get from recent days
        if len(articles) < max_articles:
            articles = self.article_repo.get_articles_with_evaluations(
                min_score=min_score, limit=max_articles, days=3
            )

        return articles[:max_articles]

    def _create_tweet_content(
        self, articles: list[ArticleWithEvaluation], post_config: dict[str, Any]
    ) -> str:
        """Create tweet content from articles.

        Args:
            articles: List of articles
            post_config: Post configuration

        Returns:
            Tweet content
        """
        template = self.posting_config.get("post_template", {})
        twitter_settings = self.posting_config.get("twitter_settings", {})

        # Start with header
        header = template.get("header", "").format(
            title=post_config.get("title", "今日のエンタメコラム TOP5")
        )

        # Add articles
        article_content = ""
        for i, article in enumerate(articles, 1):
            article_text = template.get("article_format", "").format(
                rank=i,
                title=article.title[:30] + ("..." if len(article.title) > 30 else ""),
                total_score=article.total_score,
                author=article.author,
                url=article.url,
            )
            article_content += article_text

        # Add footer
        footer = template.get("footer", "").format(
            website_url=self.config.github_pages_url or ""
        )

        # Combine all parts
        full_content = header + article_content + footer

        # Ensure within Twitter length limit
        max_length = twitter_settings.get("max_tweet_length", 280)
        if len(full_content) > max_length:
            # Truncate gracefully
            full_content = self._truncate_tweet(full_content, max_length)

        return full_content

    def _truncate_tweet(self, content: str, max_length: int) -> str:
        """Truncate tweet content while preserving structure.

        Args:
            content: Original content
            max_length: Maximum length

        Returns:
            Truncated content
        """
        if len(content) <= max_length:
            return content

        # Find a good truncation point
        truncated = content[: max_length - 3]

        # Try to truncate at a line break
        last_newline = truncated.rfind("\n")
        if last_newline > max_length * 0.7:  # If newline is not too early
            truncated = truncated[:last_newline]

        return truncated + "..."

    async def _post_tweet(self, content: str) -> bool:
        """Post tweet content.

        Args:
            content: Tweet content

        Returns:
            True if posted successfully
        """
        if not self.api:
            logger.error("Twitter API not available")
            return False

        try:
            # Apply rate limiting
            await rate_limiter.await_if_needed("twitter")

            # Post tweet
            tweet = self.api.update_status(content)
            rate_limiter.record_request("twitter")

            # Log success
            logger.info(f"Tweet posted successfully: {tweet.id}")

            # Save to database for tracking
            await self._save_tweet_record(tweet.id, content, "posted")

            return True

        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            await self._save_tweet_record(None, content, "failed", str(e))
            return False

    async def _save_tweet_record(
        self,
        tweet_id: Optional[str],
        content: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Save tweet record to database.

        Args:
            tweet_id: Twitter tweet ID
            content: Tweet content
            status: Status (posted/failed)
            error_message: Error message if failed
        """
        try:
            from backend.app.utils.database import db_manager

            query = """
                INSERT INTO twitter_posts
                (tweet_id, content, posted_at, status, error_message)
                VALUES (?, ?, ?, ?, ?)
            """

            params = (
                tweet_id,
                content,
                datetime.now().isoformat() if status == "posted" else None,
                status,
                error_message,
            )

            db_manager.execute_insert(query, params)

        except Exception as e:
            logger.warning(f"Failed to save tweet record: {e}")

    async def post_custom_content(self, content: str) -> bool:
        """Post custom content.

        Args:
            content: Custom tweet content

        Returns:
            True if posted successfully
        """
        return await self._post_tweet(content)

    def get_posting_schedule(self) -> list[dict[str, Any]]:
        """Get posting schedule.

        Returns:
            List of scheduled posts
        """
        return self.posting_config.get("daily_posts", [])

    def get_recent_tweets(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent tweet records from database.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of recent tweet records
        """
        try:
            from backend.app.utils.database import db_manager

            query = """
                SELECT * FROM twitter_posts
                ORDER BY created_at DESC
                LIMIT ?
            """

            results = db_manager.execute_query(query, (limit,))
            return results

        except Exception as e:
            logger.error(f"Failed to get recent tweets: {e}")
            return []


# Convenience function for scheduled posting
async def run_scheduled_posting() -> bool:
    """Run scheduled posting check.

    Returns:
        True if posting was successful or not needed
    """
    bot = TwitterBot()
    return await bot.post_scheduled_content()
