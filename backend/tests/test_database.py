"""Test database operations."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name

    # Ensure the file is removed after test
    yield temp_db_path

    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


def test_database_initialization(temp_db):
    """Test database initialization."""
    import sys

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.utils.database import DatabaseManager

    db_manager = DatabaseManager(temp_db)

    # Test that tables are created
    assert db_manager.table_exists("articles")
    assert db_manager.table_exists("evaluations")
    assert db_manager.table_exists("twitter_posts")
    assert db_manager.table_exists("system_logs")


def test_database_stats(temp_db):
    """Test database statistics retrieval."""
    import sys

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.utils.database import DatabaseManager

    db_manager = DatabaseManager(temp_db)
    stats = db_manager.get_database_stats()

    assert isinstance(stats, dict)
    assert "articles_count" in stats
    assert "evaluations_count" in stats
    assert stats["articles_count"] == 0  # New database should be empty


def test_article_repository(temp_db):
    """Test article repository operations."""
    import sys
    from datetime import datetime

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.models.article import Article
    from backend.app.repositories.article_repository import ArticleRepository
    from backend.app.utils.database import DatabaseManager

    # Initialize database
    db_manager = DatabaseManager(temp_db)
    repo = ArticleRepository()
    repo.db = db_manager

    # Test empty database
    assert repo.get_article_count() == 0

    # Create test article
    test_article = Article(
        id="test123",
        title="Test Article",
        url="https://note.com/test/n/test123",
        published_at=datetime.now(),
        author="Test Author",
        category="entertainment",
    )

    # Test saving article
    success = repo.save_article(test_article)
    assert success

    # Test retrieving article
    assert repo.get_article_count() == 1
    retrieved = repo.get_article_by_id("test123")
    assert retrieved is not None
    assert retrieved.title == "Test Article"
