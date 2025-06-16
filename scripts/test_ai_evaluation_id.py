#!/usr/bin/env python3
"""Test script for AI evaluation ID validation system."""

import sys
import asyncio
from pathlib import Path

# Import modules using installed package structure

from backend.app.models.article import Article
from backend.app.services.evaluator import ArticleEvaluator
from backend.app.utils.logger import get_logger
from datetime import datetime
import logging

# Set up logging to see output
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


def create_test_article() -> Article:
    """Create a test article with proper ID format."""
    return Article(
        id="n49df3e21aa0c_shiro160",  # key_urlname format
        title="【厳選】ボカロ系曲+歌ってみた+α紹介【236曲目】",
        url="https://note.com/shiro160/n/n49df3e21aa0c",
        thumbnail="https://assets.st-note.com/production/uploads/images/196129972/rectangle_large_type_2_a390cdf62a0bd66f8fcbaa2f62c7158f.png",
        published_at=datetime.now(),
        author="shiro",
        category="邦楽",
        content_preview="今回は最新のボカロ楽曲を中心に、歌ってみた動画やオリジナル楽曲まで幅広く紹介します。特に注目の楽曲は..."
    )


async def test_ai_evaluation_with_id():
    """Test AI evaluation with ID validation."""
    try:
        # Create test article
        article = create_test_article()
        logger.info(f"Testing AI evaluation for article ID: {article.id}")
        
        # Initialize evaluator
        evaluator = ArticleEvaluator()
        
        # Test evaluation
        evaluation = await evaluator._evaluate_single_article(article)
        
        if evaluation:
            logger.info("✅ AI evaluation successful!")
            logger.info(f"Article ID: {evaluation.article_id}")
            logger.info(f"Quality Score: {evaluation.quality_score}")
            logger.info(f"Originality Score: {evaluation.originality_score}")
            logger.info(f"Entertainment Score: {evaluation.entertainment_score}")
            logger.info(f"Total Score: {evaluation.total_score}")
            logger.info(f"AI Summary: {evaluation.ai_summary[:100]}...")
            
            # Verify ID matches
            if evaluation.article_id == article.id:
                logger.info("✅ Article ID validation passed!")
            else:
                logger.warning(f"❌ Article ID mismatch! Expected: {article.id}, Got: {evaluation.article_id}")
        else:
            logger.error("❌ AI evaluation failed!")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


async def test_prompt_generation():
    """Test prompt generation with article ID."""
    try:
        article = create_test_article()
        evaluator = ArticleEvaluator()
        
        # Test content preparation
        content = evaluator._prepare_content_for_evaluation(article)
        logger.info(f"Prepared content length: {len(content)}")
        
        # Test prompt generation
        messages = evaluator._generate_evaluation_prompt(article, content)
        
        logger.info("Generated prompt:")
        for message in messages:
            logger.info(f"Role: {message['role']}")
            if message['role'] == 'user' and 'article_id' in message['content']:
                logger.info("✅ Article ID found in prompt!")
            logger.info(f"Content preview: {message['content'][:200]}...")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"Error during prompt test: {e}")


if __name__ == "__main__":
    async def main():
        logger.info("🧪 Testing AI Evaluation ID Validation System")
        logger.info("=" * 50)
        
        logger.info("1. Testing prompt generation...")
        await test_prompt_generation()
        
        logger.info("\n2. Testing AI evaluation...")
        await test_ai_evaluation_with_id()
        
        logger.info("\n✅ Tests completed!")
    
    asyncio.run(main())