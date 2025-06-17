"""Test configuration and fixtures for pytest."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.app.models.article import Article, NoteArticleMetadata
from backend.app.models.evaluation import Evaluation


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_article():
    """Create a sample article for testing."""
    return Article(
        id="test_article_123",
        title="テストエンタメ記事のタイトル",
        url="https://note.com/test_user/n/test_article_123",
        thumbnail="https://example.com/thumbnail.jpg",
        published_at=datetime.now(timezone.utc),
        author="テストユーザー",
        category="entertainment",
        content_preview="これはテスト用のエンタメ記事です。内容はサンプルテキストです。",
        note_data=NoteArticleMetadata(
            note_type="TextNote",
            like_count=10,
            comment_count=5,
            price=0,
            can_read=True,
            is_liked=False
        )
    )


@pytest.fixture
def sample_evaluation():
    """Create a sample evaluation for testing."""
    return Evaluation(
        id=1,
        article_id="test_article_123",
        quality_score=35,
        originality_score=25,
        entertainment_score=20,
        total_score=80,
        ai_summary="この記事は質の高いエンタメコンテンツです。",
        evaluated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_articles_list():
    """Create a list of sample articles for testing."""
    articles = []
    for i in range(5):
        article = Article(
            id=f"test_article_{i}",
            title=f"テスト記事 {i+1}",
            url=f"https://note.com/user{i}/n/test_article_{i}",
            thumbnail=f"https://example.com/thumbnail{i}.jpg",
            published_at=datetime.now(timezone.utc),
            author=f"テストユーザー{i+1}",
            category="entertainment",
            content_preview=f"これはテスト記事{i+1}の内容です。",
            note_data=NoteArticleMetadata(
                note_type="TextNote",
                like_count=i * 2,
                comment_count=i,
                price=0,
                can_read=True,
                is_liked=False
            )
        )
        articles.append(article)
    return articles


@pytest.fixture
def mock_groq_client():
    """Create a mock Groq client for testing."""
    mock_client = MagicMock()
    
    # Default successful response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"article_id": "test", "quality_score": 30, "originality_score": 20, "entertainment_score": 20, "total_score": 70, "ai_summary": "テスト評価です。"}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session for testing."""
    mock_session = MagicMock()
    
    # Default successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '<html><head><title>Test</title></head><body>Test content</body></html>'
    mock_response.json.return_value = {
        "data": {
            "sections": [
                {
                    "notes": [
                        {
                            "id": "test_note",
                            "key": "test_key",
                            "name": "テスト記事",
                            "price": 0,
                            "can_read": True,
                            "user": {"urlname": "test_user", "nickname": "テストユーザー"},
                            "publish_at": "2024-01-01T00:00:00.000Z",
                            "eyecatch_url": "https://example.com/image.jpg"
                        }
                    ]
                }
            ],
            "isLast": True
        }
    }
    mock_session.get.return_value = mock_response
    
    return mock_session


@pytest.fixture
def test_config():
    """Create test configuration."""
    return {
        "collection_urls": [
            {
                "name": "テストカテゴリ",
                "url": "https://note.com/interests/test",
                "category": "test"
            }
        ],
        "collection_settings": {
            "request_delay_seconds": 0.1,
            "old_article_threshold_days": 1,
            "max_retries": 2,
            "stop_after_old_articles": True,
            "fetch_article_details": False
        },
        "rate_limit": {
            "groq": {
                "requests_per_minute": 30,
                "max_retries": 3,
                "retry_delay_seconds": 2.0
            }
        }
    }


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        db_path = temp_file.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    env_vars = {
        "GROQ_API_KEY": "test_groq_api_key",
        "TWITTER_BEARER_TOKEN": "test_twitter_bearer_token",
        "TWITTER_API_KEY": "test_twitter_api_key",
        "TWITTER_API_SECRET": "test_twitter_api_secret",
        "TWITTER_ACCESS_TOKEN": "test_twitter_access_token",
        "TWITTER_ACCESS_TOKEN_SECRET": "test_twitter_access_token_secret",
        "DRY_RUN": "false"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def sample_groq_responses():
    """Sample Groq API responses for testing."""
    return {
        "valid_response": '{"article_id": "test_123", "quality_score": 35, "originality_score": 25, "entertainment_score": 20, "total_score": 80, "ai_summary": "この記事は高品質なエンタメコンテンツです。"}',
        "invalid_json": "This is not valid JSON",
        "missing_fields": '{"article_id": "test_123"}',
        "out_of_range_scores": '{"article_id": "test_123", "quality_score": 50, "originality_score": 40, "entertainment_score": 35, "total_score": 125, "ai_summary": "テスト"}',
        "empty_summary": '{"article_id": "test_123", "quality_score": 30, "originality_score": 20, "entertainment_score": 20, "total_score": 70, "ai_summary": ""}'
    }


@pytest.fixture
def sample_note_api_responses():
    """Sample note.com API responses for testing."""
    return {
        "valid_response": {
            "data": {
                "sections": [
                    {
                        "notes": [
                            {
                                "id": "note_123",
                                "key": "abc123def",
                                "name": "テストエンタメ記事",
                                "price": 0,
                                "can_read": True,
                                "user": {
                                    "urlname": "test_user",
                                    "nickname": "テストユーザー"
                                },
                                "publish_at": "2024-01-01T12:00:00.000+09:00",
                                "eyecatch_url": "https://example.com/image.jpg",
                                "like_count": 10,
                                "type": "TextNote"
                            }
                        ]
                    }
                ],
                "isLast": False
            }
        },
        "empty_response": {
            "data": {
                "sections": [],
                "isLast": True
            }
        },
        "paid_article_response": {
            "data": {
                "sections": [
                    {
                        "notes": [
                            {
                                "id": "paid_note_123",
                                "key": "paid123def",
                                "name": "有料記事テスト",
                                "price": 500,
                                "can_read": False,
                                "user": {
                                    "urlname": "paid_user",
                                    "nickname": "有料ユーザー"
                                }
                            }
                        ]
                    }
                ],
                "isLast": True
            }
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Ensure test directory exists
    test_dir = Path("backend/tests")
    test_dir.mkdir(exist_ok=True)
    
    # Set test environment variables
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    
    yield
    
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter for testing."""
    mock_limiter = MagicMock()
    mock_limiter.await_if_needed = MagicMock(return_value=asyncio.sleep(0))
    mock_limiter.record_request = MagicMock()
    return mock_limiter