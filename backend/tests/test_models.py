"""Test data models."""

from datetime import datetime


def test_article_model():
    """Test Article model creation and validation."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.models.article import Article

    article = Article(
        id="test123",
        title="Test Article",
        url="https://note.com/test/n/test123",
        published_at=datetime.now(),
        author="Test Author",
        category="entertainment",
    )

    assert article.id == "test123"
    assert article.title == "Test Article"
    assert article.author == "Test Author"
    assert article.category == "entertainment"
    assert article.is_evaluated is False


def test_evaluation_model():
    """Test Evaluation model creation and validation."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.models.evaluation import Evaluation

    evaluation = Evaluation(
        article_id="test123",
        quality_score=35,
        originality_score=25,
        entertainment_score=28,
        total_score=88,
        ai_summary="This is a test summary.",
    )

    assert evaluation.article_id == "test123"
    assert evaluation.quality_score == 35
    assert evaluation.originality_score == 25
    assert evaluation.entertainment_score == 28
    assert evaluation.total_score == 88
    assert evaluation.ai_summary == "This is a test summary."


def test_evaluation_score_validation():
    """Test evaluation score range validation."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.models.evaluation import Evaluation

    # Test valid scores
    evaluation = Evaluation(
        article_id="test123",
        quality_score=40,  # Max for quality
        originality_score=30,  # Max for originality
        entertainment_score=30,  # Max for entertainment
        total_score=100,
        ai_summary="Test summary",
    )

    assert evaluation.quality_score == 40
    assert evaluation.originality_score == 30
    assert evaluation.entertainment_score == 30
    assert evaluation.total_score == 100


def test_ai_evaluation_result():
    """Test AI evaluation result model."""
    import sys
    from pathlib import Path

    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from backend.app.models.evaluation import AIEvaluationResult

    result = AIEvaluationResult(
        quality_score=38,
        originality_score=27,
        entertainment_score=29,
        total_score=94,
        ai_summary="This article demonstrates excellent writing quality with unique insights.",
        evaluation_reason="High scores across all criteria.",
    )

    assert result.total_score == 94
    assert len(result.ai_summary) >= 50  # Minimum length check

    # Test conversion to Evaluation
    evaluation = result.to_evaluation("test456")
    assert evaluation.article_id == "test456"
    assert evaluation.total_score == 94
