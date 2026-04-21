"""Tests for ArticleEvaluator focusing on non-deterministic behavior."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.services.evaluator import ArticleEvaluator


@pytest.fixture
def evaluator(mock_environment_variables):
    """Create an ArticleEvaluator with a mocked Groq client."""
    with patch("backend.app.services.evaluator.Groq") as mock_groq_cls:
        mock_groq_cls.return_value = MagicMock()
        ev = ArticleEvaluator(api_key="test_key")
        yield ev


@pytest.mark.anyio
async def test_call_groq_api_temperature_uses_random_uniform(
    evaluator, sample_article
):
    """_call_groq_api should pass base_temperature + random.uniform offset to the client."""
    base_temp = evaluator.groq_settings.get("temperature", 0.3)
    offset = 0.03
    expected_temperature = round(base_temp + offset, 10)

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"article_id": "test_article_123", '
                    '"quality_score": 30, "originality_score": 20, '
                    '"entertainment_score": 20, "total_score": 70, '
                    '"ai_summary": "テスト評価です。"}'
                )
            )
        )
    ]
    evaluator.client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "test"}]

    with patch(
        "backend.app.services.evaluator.random.uniform", return_value=offset
    ) as mock_uniform:
        await evaluator._call_groq_api(messages, sample_article.id)

    mock_uniform.assert_called_once_with(-0.05, 0.05)

    call_kwargs = evaluator.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == pytest.approx(expected_temperature)


@pytest.mark.anyio
async def test_call_groq_api_temperature_clamped_to_minimum(evaluator, sample_article):
    """Temperature must not drop below 0.1 even with a large negative offset."""
    evaluator.groq_settings["temperature"] = 0.1

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"article_id": "test_article_123", '
                    '"quality_score": 30, "originality_score": 20, '
                    '"entertainment_score": 20, "total_score": 70, '
                    '"ai_summary": "テスト評価です。"}'
                )
            )
        )
    ]
    evaluator.client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "test"}]

    with patch("backend.app.services.evaluator.random.uniform", return_value=-0.05):
        await evaluator._call_groq_api(messages, sample_article.id)

    call_kwargs = evaluator.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] >= 0.1


@pytest.mark.anyio
async def test_call_groq_api_temperature_clamped_to_maximum(evaluator, sample_article):
    """Temperature must not exceed 0.8 even with a large positive offset."""
    evaluator.groq_settings["temperature"] = 0.8

    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=(
                    '{"article_id": "test_article_123", '
                    '"quality_score": 30, "originality_score": 20, '
                    '"entertainment_score": 20, "total_score": 70, '
                    '"ai_summary": "テスト評価です。"}'
                )
            )
        )
    ]
    evaluator.client.chat.completions.create.return_value = mock_response

    messages = [{"role": "user", "content": "test"}]

    with patch("backend.app.services.evaluator.random.uniform", return_value=0.05):
        await evaluator._call_groq_api(messages, sample_article.id)

    call_kwargs = evaluator.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] <= 0.8
