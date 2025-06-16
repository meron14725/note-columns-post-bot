#!/usr/bin/env python3
"""Debug AI evaluation responses."""

import sys
import asyncio
from pathlib import Path

# Import modules using installed package structure

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.utils.logger import get_logger
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = get_logger(__name__)


async def debug_duplicate_scores():
    """Debug why multiple articles get the same scores."""
    try:
        # Get articles with duplicate scores
        repo = ArticleRepository()
        
        # Get the specific articles that have score 20/12/15
        articles = repo.get_articles_by_category("ゲーム", limit=20)
        problem_articles = []
        
        for article in articles:
            if not article.is_evaluated and len(problem_articles) < 5:  # Get first 5 unevaluated
                problem_articles.append(article)
        
        if not problem_articles:
            logger.info("No unevaluated articles found for testing")
            return
        
        evaluator = ArticleEvaluator()
        
        logger.info(f"🔍 Testing AI evaluation for {len(problem_articles)} articles")
        
        for i, article in enumerate(problem_articles, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 TESTING ARTICLE {i}: {article.id}")
            logger.info(f"Title: {article.title}")
            logger.info(f"Category: {article.category}")
            logger.info(f"{'='*60}")
            
            # Test prompt generation
            content = evaluator._prepare_content_for_evaluation(article)
            messages = evaluator._generate_evaluation_prompt(article, content)
            
            logger.info(f"📤 PROMPT SENT TO AI:")
            for message in messages:
                if message['role'] == 'user':
                    logger.info(message['content'])
                    break
            
            # Test AI evaluation
            logger.info(f"\n🤖 CALLING AI...")
            
            try:
                # Call AI directly and capture response
                response = evaluator.client.chat.completions.create(
                    model=evaluator.groq_settings.get("model", "llama3-70b-8192"),
                    messages=messages,
                    temperature=evaluator.groq_settings.get("temperature", 0.3),
                    max_tokens=evaluator.groq_settings.get("max_tokens", 1000),
                )
                
                raw_response = response.choices[0].message.content
                logger.info(f"📥 RAW AI RESPONSE:")
                logger.info(raw_response)
                
                # Test parsing
                parsed_result = evaluator._parse_ai_response(raw_response, article.id)
                
                if parsed_result:
                    logger.info(f"\n✅ PARSED RESULT:")
                    logger.info(f"Article ID: {parsed_result.article_id}")
                    logger.info(f"Quality: {parsed_result.quality_score}")
                    logger.info(f"Originality: {parsed_result.originality_score}")
                    logger.info(f"Entertainment: {parsed_result.entertainment_score}")
                    logger.info(f"Total: {parsed_result.total_score}")
                    logger.info(f"Summary: {parsed_result.ai_summary[:100]}...")
                else:
                    logger.error("❌ FAILED TO PARSE RESPONSE")
                
            except Exception as e:
                logger.error(f"❌ AI CALL FAILED: {e}")
            
            # Delay between requests
            await asyncio.sleep(5)
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_duplicate_scores())