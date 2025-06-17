"""Evaluation repository for database operations."""

from datetime import datetime, timedelta
from typing import Any, Optional

from backend.app.models.evaluation import Evaluation
from backend.app.utils.database import db_manager
from backend.app.utils.logger import get_logger

logger = get_logger(__name__)


class EvaluationRepository:
    """Repository for evaluation database operations."""

    def __init__(self) -> None:
        """Initialize repository."""
        self.db = db_manager

    def save_evaluation(self, evaluation: Evaluation) -> bool:
        """Save a single evaluation to database.

        Args:
            evaluation: Evaluation to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            query = """
                INSERT INTO evaluations
                (article_id, quality_score, originality_score, entertainment_score,
                 total_score, ai_summary, evaluated_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                evaluation.article_id,
                evaluation.quality_score,
                evaluation.originality_score,
                evaluation.entertainment_score,
                evaluation.total_score,
                evaluation.ai_summary,
                evaluation.evaluated_at.isoformat(),
                evaluation.created_at.isoformat(),
            )

            self.db.execute_insert(query, params)
            logger.debug(f"Saved evaluation for article: {evaluation.article_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to save evaluation for article {evaluation.article_id}: {e}"
            )
            return False

    def save_evaluations(self, evaluations: list[Evaluation]) -> int:
        """Save multiple evaluations to database.

        Args:
            evaluations: List of evaluations to save

        Returns:
            Number of evaluations saved successfully
        """
        if not evaluations:
            return 0

        saved_count = 0

        query = """
            INSERT INTO evaluations
            (article_id, quality_score, originality_score, entertainment_score,
             total_score, ai_summary, evaluated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        param_list = []
        for evaluation in evaluations:
            params = (
                evaluation.article_id,
                evaluation.quality_score,
                evaluation.originality_score,
                evaluation.entertainment_score,
                evaluation.total_score,
                evaluation.ai_summary,
                evaluation.evaluated_at.isoformat(),
                evaluation.created_at.isoformat(),
            )
            param_list.append(params)

        try:
            saved_count = self.db.execute_many(query, param_list)
            logger.info(f"Saved {saved_count} evaluations to database")
        except Exception as e:
            logger.error(f"Failed to save evaluations in batch: {e}")
            # Try saving individually
            for evaluation in evaluations:
                if self.save_evaluation(evaluation):
                    saved_count += 1

        return saved_count

    def get_evaluation_by_article_id(self, article_id: str) -> Optional[Evaluation]:
        """Get evaluation by article ID.

        Args:
            article_id: Article ID

        Returns:
            Evaluation if found, None otherwise
        """
        query = "SELECT * FROM evaluations WHERE article_id = ?"
        results = self.db.execute_query(query, (article_id,))

        if results:
            return self._row_to_evaluation(results[0])
        return None

    def get_evaluations_by_score_range(
        self, min_score: int = 0, max_score: int = 100, limit: Optional[int] = None
    ) -> list[Evaluation]:
        """Get evaluations within score range.

        Args:
            min_score: Minimum total score
            max_score: Maximum total score
            limit: Maximum number of evaluations to return

        Returns:
            List of evaluations within score range
        """
        query = """
            SELECT * FROM evaluations
            WHERE total_score >= ? AND total_score <= ?
            ORDER BY total_score DESC, evaluated_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query, (min_score, max_score))
        return [self._row_to_evaluation(row) for row in results]

    def get_recent_evaluations(
        self, days: int = 7, limit: Optional[int] = None
    ) -> list[Evaluation]:
        """Get evaluations from recent days.

        Args:
            days: Number of recent days
            limit: Maximum number of evaluations to return

        Returns:
            List of recent evaluations
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        query = """
            SELECT * FROM evaluations
            WHERE evaluated_at >= ?
            ORDER BY evaluated_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        results = self.db.execute_query(query, (cutoff_date.isoformat(),))
        return [self._row_to_evaluation(row) for row in results]

    def get_top_evaluations(self, limit: int = 10) -> list[Evaluation]:
        """Get top-rated evaluations.

        Args:
            limit: Number of top evaluations to return

        Returns:
            List of top-rated evaluations
        """
        query = """
            SELECT * FROM evaluations
            ORDER BY total_score DESC, evaluated_at DESC
            LIMIT ?
        """

        results = self.db.execute_query(query, (limit,))
        return [self._row_to_evaluation(row) for row in results]

    def get_evaluation_statistics(self, days: Optional[int] = None) -> dict[str, Any]:
        """Get evaluation statistics.

        Args:
            days: Only include evaluations from recent days

        Returns:
            Dictionary with evaluation statistics
        """
        base_query = "SELECT * FROM evaluations"
        params = []

        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            base_query += " WHERE evaluated_at >= ?"
            params.append(cutoff_date.isoformat())

        results = self.db.execute_query(base_query, tuple(params))

        if not results:
            return {"total": 0}

        total_scores = [row["total_score"] for row in results]
        quality_scores = [row["quality_score"] for row in results]
        originality_scores = [row["originality_score"] for row in results]
        entertainment_scores = [row["entertainment_score"] for row in results]

        return {
            "total": len(results),
            "average_total_score": sum(total_scores) / len(total_scores),
            "max_total_score": max(total_scores),
            "min_total_score": min(total_scores),
            "average_quality_score": sum(quality_scores) / len(quality_scores),
            "average_originality_score": sum(originality_scores)
            / len(originality_scores),
            "average_entertainment_score": sum(entertainment_scores)
            / len(entertainment_scores),
            "high_quality_count": len([s for s in total_scores if s >= 80]),
            "medium_quality_count": len([s for s in total_scores if 60 <= s < 80]),
            "low_quality_count": len([s for s in total_scores if s < 60]),
            "excellent_quality": len([s for s in quality_scores if s >= 35]),
            "excellent_originality": len([s for s in originality_scores if s >= 25]),
            "excellent_entertainment": len(
                [s for s in entertainment_scores if s >= 25]
            ),
        }

    def get_evaluation_count(self) -> int:
        """Get total number of evaluations.

        Returns:
            Total evaluation count
        """
        query = "SELECT COUNT(*) as count FROM evaluations"
        result = self.db.execute_query(query)
        return result[0]["count"] if result else 0

    def delete_evaluation(self, article_id: str) -> bool:
        """Delete evaluation by article ID.

        Args:
            article_id: Article ID

        Returns:
            True if deleted successfully
        """
        try:
            query = "DELETE FROM evaluations WHERE article_id = ?"
            affected_rows = self.db.execute_update(query, (article_id,))

            if affected_rows > 0:
                logger.info(f"Deleted evaluation for article: {article_id}")
                return True
            else:
                logger.warning(
                    f"No evaluation found to delete for article: {article_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to delete evaluation for article {article_id}: {e}")
            return False

    def _row_to_evaluation(self, row: dict[str, Any]) -> Evaluation:
        """Convert database row to Evaluation model.

        Args:
            row: Database row

        Returns:
            Evaluation instance
        """
        return Evaluation(
            id=row["id"],
            article_id=row["article_id"],
            quality_score=row["quality_score"],
            originality_score=row["originality_score"],
            entertainment_score=row["entertainment_score"],
            total_score=row["total_score"],
            ai_summary=row["ai_summary"],
            evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
