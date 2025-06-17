"""Article repository for database operations."""

from datetime import datetime, timedelta
from typing import Any, Optional

from backend.app.models.article import Article
from backend.app.models.evaluation import ArticleWithEvaluation
from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


class ArticleRepository:
    """Repository for article database operations."""

    def __init__(self) -> None:
        """Initialize repository."""
        self.db = db_manager

    def save_article(self, article: Article) -> bool:
        """Save a single article to database.

        Args:
            article: Article to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            query = """
                INSERT OR REPLACE INTO articles
                (id, title, url, thumbnail, published_at, author, content_preview,
                 category, collected_at, is_evaluated, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                article.id,
                article.title,
                str(article.url),
                article.thumbnail,
                article.published_at.isoformat(),
                article.author,
                article.content_preview,
                article.category,
                article.collected_at.isoformat(),
                article.is_evaluated,
                article.created_at.isoformat(),
                article.updated_at.isoformat(),
            )

            self.db.execute_insert(query, params)
            logger.debug(f"Saved article: {article.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to save article {article.title}: {e}")
            return False

    def save_articles(self, articles: list[Article]) -> int:
        """Save multiple articles to database.

        Args:
            articles: List of articles to save

        Returns:
            Number of articles saved successfully
        """
        if not articles:
            return 0

        saved_count = 0

        query = """
            INSERT OR REPLACE INTO articles
            (id, title, url, thumbnail, published_at, author, content_preview,
             category, collected_at, is_evaluated, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        param_list = []
        for article in articles:
            params = (
                article.id,
                article.title,
                str(article.url),
                article.thumbnail,
                article.published_at.isoformat(),
                article.author,
                article.content_preview,
                article.category,
                article.collected_at.isoformat(),
                article.is_evaluated,
                article.created_at.isoformat(),
                article.updated_at.isoformat(),
            )
            param_list.append(params)

        try:
            saved_count = self.db.execute_many(query, param_list)
            logger.info(f"Saved {saved_count} articles to database")
        except Exception as e:
            logger.error(f"Failed to save articles in batch: {e}")
            # Try saving individually
            for article in articles:
                if self.save_article(article):
                    saved_count += 1

        return saved_count

    def get_article_by_id(self, article_id: str) -> Optional[Article]:
        """Get article by ID.

        Args:
            article_id: Article ID

        Returns:
            Article if found, None otherwise
        """
        query = "SELECT * FROM articles WHERE id = ?"
        results = self.db.execute_query(query, (article_id,))

        if results:
            return self._row_to_article(results[0])
        return None

    def get_unevaluated_articles(self, limit: Optional[int] = None) -> list[Article]:
        """Get articles that haven't been evaluated.

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of unevaluated articles
        """
        query = """
            SELECT * FROM articles
            WHERE is_evaluated = FALSE
            ORDER BY published_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query)
        return [self._row_to_article(row) for row in results]

    def get_recent_articles(
        self, days: int = 7, limit: Optional[int] = None
    ) -> list[Article]:
        """Get articles from recent days.

        Args:
            days: Number of recent days
            limit: Maximum number of articles to return

        Returns:
            List of recent articles
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        query = """
            SELECT * FROM articles
            WHERE published_at >= ?
            ORDER BY published_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query, (cutoff_date.isoformat(),))
        return [self._row_to_article(row) for row in results]

    def get_articles_by_category(
        self, category: str, limit: Optional[int] = None
    ) -> list[Article]:
        """Get articles by category.

        Args:
            category: Article category
            limit: Maximum number of articles to return

        Returns:
            List of articles in the category
        """
        query = """
            SELECT * FROM articles
            WHERE category = ?
            ORDER BY published_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query, (category,))
        return [self._row_to_article(row) for row in results]

    def mark_as_evaluated(self, article_id: str) -> bool:
        """Mark article as evaluated.

        Args:
            article_id: Article ID

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE articles
            SET is_evaluated = TRUE, updated_at = ?
            WHERE id = ?
        """

        try:
            affected_rows = self.db.execute_update(
                query, (datetime.now().isoformat(), article_id)
            )
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Failed to mark article {article_id} as evaluated: {e}")
            return False

    def get_articles_with_evaluations(
        self,
        min_score: int = 0,
        limit: Optional[int] = None,
        days: Optional[int] = None,
    ) -> list[ArticleWithEvaluation]:
        """Get articles with their evaluations.

        Args:
            min_score: Minimum total score
            limit: Maximum number of articles to return
            days: Only articles from recent days

        Returns:
            List of articles with evaluations
        """
        query = """
            SELECT
                a.id, a.title, a.url, a.thumbnail, a.published_at,
                a.author, a.content_preview, a.category, a.collected_at,
                e.quality_score, e.originality_score, e.entertainment_score,
                e.total_score, e.ai_summary, e.evaluated_at
            FROM articles a
            INNER JOIN evaluations e ON a.id = e.article_id
            WHERE e.total_score >= ?
        """

        params = [min_score]

        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            query += " AND a.published_at >= ?"
            params.append(cutoff_date.isoformat())

        query += " ORDER BY e.total_score DESC, a.published_at DESC"

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query, tuple(params))
        return [self._row_to_article_with_evaluation(row) for row in results]

    def get_top_articles(
        self, limit: int = 10, days: Optional[int] = None
    ) -> list[ArticleWithEvaluation]:
        """Get top-rated articles.

        Args:
            limit: Number of top articles to return
            days: Only articles from recent days

        Returns:
            List of top-rated articles
        """
        return self.get_articles_with_evaluations(min_score=0, limit=limit, days=days)

    def get_article_count(self) -> int:
        """Get total number of articles.

        Returns:
            Total article count
        """
        query = "SELECT COUNT(*) as count FROM articles"
        result = self.db.execute_query(query)
        return result[0]["count"] if result else 0

    def get_evaluated_article_count(self) -> int:
        """Get number of evaluated articles.

        Returns:
            Evaluated article count
        """
        query = "SELECT COUNT(*) as count FROM articles WHERE is_evaluated = TRUE"
        result = self.db.execute_query(query)
        return result[0]["count"] if result else 0

    def _row_to_article(self, row: dict[str, Any]) -> Article:
        """Convert database row to Article model.

        Args:
            row: Database row

        Returns:
            Article instance
        """
        return Article(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            thumbnail=row["thumbnail"],
            published_at=datetime.fromisoformat(row["published_at"]),
            author=row["author"],
            content_preview=row["content_preview"],
            category=row["category"],
            collected_at=datetime.fromisoformat(row["collected_at"]),
            is_evaluated=bool(row["is_evaluated"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_article_with_evaluation(
        self, row: dict[str, Any]
    ) -> ArticleWithEvaluation:
        """Convert database row to ArticleWithEvaluation model.

        Args:
            row: Database row with article and evaluation data

        Returns:
            ArticleWithEvaluation instance
        """
        return ArticleWithEvaluation(
            id=row["id"],
            title=row["title"],
            url=row["url"],
            thumbnail=row["thumbnail"],
            published_at=datetime.fromisoformat(row["published_at"]),
            author=row["author"],
            content_preview=row["content_preview"],
            category=row["category"],
            collected_at=datetime.fromisoformat(row["collected_at"]),
            quality_score=row["quality_score"],
            originality_score=row["originality_score"],
            entertainment_score=row["entertainment_score"],
            total_score=row["total_score"],
            ai_summary=row["ai_summary"],
            evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
        )

    def get_all_article_ids(self) -> list[str]:
        """Get all article IDs from database.

        Returns:
            List of article IDs
        """
        query = "SELECT id FROM articles"

        try:
            results = self.db.execute_query(query)
            return [row["id"] for row in results] if results else []
        except Exception as e:
            logger.error(f"Failed to get article IDs: {e}")
            return []

    def get_articles_by_ids(self, article_ids: list[str]) -> list[Article]:
        """Get multiple articles by their IDs.

        Args:
            article_ids: List of article IDs

        Returns:
            List of articles
        """
        if not article_ids:
            return []

        placeholders = ",".join(["?" for _ in article_ids])
        query = f"SELECT * FROM articles WHERE id IN ({placeholders})"

        try:
            results = self.db.execute_query(query, tuple(article_ids))
            return [self._row_to_article(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get articles by IDs: {e}")
            return []

    def article_exists(self, article_id: str) -> bool:
        """Check if article exists in database.

        Args:
            article_id: Article ID to check

        Returns:
            True if article exists, False otherwise
        """
        query = "SELECT COUNT(*) as count FROM articles WHERE id = ?"

        try:
            result = self.db.execute_query(query, (article_id,))
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error(f"Failed to check article existence: {e}")
            return False
