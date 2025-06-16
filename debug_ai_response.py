#!/usr/bin/env python3
"""Debug AI response to understand JSON parsing issues."""

import sys
import asyncio
from pathlib import Path

# Add the parent directory to sys.path for imports
sys.path.append(str(Path(__file__).parent))

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.models.article import Article, NoteArticleMetadata
from backend.app.utils.logger import setup_logger, get_logger
from config.config import validate_required_env_vars

logger = get_logger(__name__)

async def debug_ai_response():
    """Debug AI response to understand JSON parsing issues."""
    setup_logger()
    
    try:
        validate_required_env_vars()
        
        # Create a test article
        from datetime import datetime
        test_article = Article(
            id="debug_test_001",
            title="K-POP徒然日記　知らない言葉とルッキズムについてダラダラと書いてみた",
            url="https://note.com/noraalphaz/n/n50ad83a5f3bb",
            author="のらあるふぁず",
            category="K-POP",
            published_at=datetime.now(),
            content_preview="K-POPファンにとって重要な問題について語るこの記事では、ルッキズムという概念について詳しく解説しています。筆者の個人的な体験を交えながら、K-POP業界におけるルッキズムの現状と問題点を分析。特に、ファンがアーティストの外見に対して抱く感情や評価について考察し、音楽そのものの価値を重視することの大切さを訴えています。",
            note_data=NoteArticleMetadata()
        )
        
        # Test evaluation
        evaluator = ArticleEvaluator()
        
        # Generate prompt
        content = evaluator._prepare_content_for_evaluation(test_article)
        messages = evaluator._generate_evaluation_prompt(test_article, content)
        
        print("Generated prompt:")
        for message in messages:
            print(f"Role: {message['role']}")
            print(f"Content: {message['content']}")
            print("-" * 80)
        
        # Call API and get raw response
        try:
            response = evaluator.client.chat.completions.create(
                model=evaluator.groq_settings.get("model", "llama3-70b-8192"),
                messages=messages,
                temperature=evaluator.groq_settings.get("temperature", 0.7),
                max_tokens=evaluator.groq_settings.get("max_tokens", 1000),
                top_p=evaluator.groq_settings.get("top_p", 0.9),
                frequency_penalty=evaluator.groq_settings.get("frequency_penalty", 0.3),
                presence_penalty=evaluator.groq_settings.get("presence_penalty", 0.2),
            )
            
            raw_content = response.choices[0].message.content
            print("Raw AI Response:")
            print(raw_content)
            print("-" * 80)
            
            # Try to parse
            parsed_result = evaluator._parse_ai_response(raw_content, test_article.id)
            if parsed_result:
                print("Successfully parsed:")
                print(f"Quality Score: {parsed_result.quality_score}")
                print(f"Originality Score: {parsed_result.originality_score}")
                print(f"Entertainment Score: {parsed_result.entertainment_score}")
                print(f"Total Score: {parsed_result.total_score}")
                print(f"Summary: {parsed_result.ai_summary}")
            else:
                print("Failed to parse response")
                
        except Exception as e:
            logger.error(f"API call failed: {e}")
            
    except Exception as e:
        logger.error(f"Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_ai_response())