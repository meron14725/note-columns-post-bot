"""Article reference repository for database operations."""

from datetime import datetime
from typing import Optional

from backend.app.models.article_reference import ArticleReference
from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


class ArticleReferenceRepository:
    """Repository for article reference database operations."""

    def __init__(self) -> None:
        """Initialize repository."""
        self.db = db_manager

    def save_references(self, references: list[ArticleReference]) -> int:
        """Save multiple article references to database.

        Args:
            references: List of article references to save

        Returns:
            Number of references saved successfully
        """
        if not references:
            return 0

        saved_count = 0

        query = """
            INSERT OR REPLACE INTO article_references
            (key, urlname, category, title, author, thumbnail, published_at, collected_at, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        for ref in references:
            try:
                params = (
                    ref.key,
                    ref.urlname,
                    ref.category,
                    ref.title,
                    ref.author,
                    ref.thumbnail,
                    ref.published_at.isoformat() if ref.published_at else None,
                    ref.collected_at.isoformat(),
                    ref.is_processed,
                )

                self.db.execute_insert(query, params)
                saved_count += 1
                logger.debug(f"Saved article reference: {ref.key}/{ref.urlname}")

            except Exception as e:
                logger.error(
                    f"Failed to save article reference {ref.key}/{ref.urlname}: {e}"
                )

        logger.info(f"Saved {saved_count}/{len(references)} article references")
        return saved_count

    def get_existing_keys_urlnames(self) -> set[tuple[str, str]]:
        """Get all existing (key, urlname) combinations.

        Returns:
            Set of (key, urlname) tuples
        """
        try:
            query = "SELECT key, urlname FROM article_references"
            rows = self.db.execute_query(query)
            return {(row["key"], row["urlname"]) for row in rows}
        except Exception as e:
            logger.error(f"Failed to get existing key/urlname combinations: {e}")
            return set()

    def get_unprocessed_references(
        self, limit: Optional[int] = None
    ) -> list[ArticleReference]:
        """Get unprocessed article references.

        Args:
            limit: Maximum number of references to return

        Returns:
            List of unprocessed article references
        """
        try:
            query = """
                SELECT key, urlname, category, title, author, thumbnail, published_at, collected_at, is_processed
                FROM article_references
                WHERE is_processed = FALSE
                ORDER BY collected_at ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            rows = self.db.execute_query(query)
            references = []

            for row in rows:
                ref = ArticleReference(
                    key=row["key"],
                    urlname=row["urlname"],
                    category=row["category"],
                    title=row["title"],
                    author=row["author"],
                    thumbnail=row["thumbnail"],
                    published_at=(
                        datetime.fromisoformat(row["published_at"])
                        if row["published_at"]
                        else None
                    ),
                    collected_at=datetime.fromisoformat(row["collected_at"]),
                    is_processed=bool(row["is_processed"]),
                )
                references.append(ref)

            return references

        except Exception as e:
            logger.error(f"Failed to get unprocessed references: {e}")
            return []

    def mark_as_processed(self, key: str, urlname: str) -> bool:
        """Mark an article reference as processed.

        Args:
            key: Article key
            urlname: Article urlname

        Returns:
            True if marked successfully, False otherwise
        """
        try:
            query = """
                UPDATE article_references
                SET is_processed = TRUE
                WHERE key = ? AND urlname = ?
            """

            self.db.execute_update(query, (key, urlname))
            logger.debug(f"Marked as processed: {key}/{urlname}")
            return True

        except Exception as e:
            logger.error(f"Failed to mark as processed {key}/{urlname}: {e}")
            return False

    def get_reference_counts_by_category(self) -> dict[str, int]:
        """Get reference counts by category.

        Returns:
            Dictionary of category -> count
        """
        try:
            query = """
                SELECT category, COUNT(*) as count
                FROM article_references
                GROUP BY category
                ORDER BY count DESC
            """

            rows = self.db.execute_query(query)
            return {row["category"]: row["count"] for row in rows}

        except Exception as e:
            logger.error(f"Failed to get reference counts by category: {e}")
            return {}

    def get_total_reference_count(self) -> int:
        """Get total number of article references.

        Returns:
            Total count of references
        """
        try:
            query = "SELECT COUNT(*) as count FROM article_references"
            result = self.db.execute_query(query)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get total reference count: {e}")
            return 0
