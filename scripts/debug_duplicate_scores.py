#!/usr/bin/env python3
"""Debug duplicate AI evaluation scores issue."""

import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.evaluator import ArticleEvaluator
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.models.article import Article
from backend.app.utils.logger import get_logger

# Enable detailed logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)


async def test_duplicate_scores():
    """Test AI evaluation to see if it produces duplicate scores."""
    try:
        # Create test articles with different content
        test_articles = [
            Article(
                id="test_1",
                title="ゲーム音楽の魅力について語る",
                url="https://note.com/test1",
                author="テストユーザー1",
                published_at="2025-06-15T10:00:00+09:00",
                category="ゲーム",
                content_preview="ゲーム音楽は私たちの心に深く響く要素の一つです。RPGの美しいオーケストラから、アクションゲームのテンポの良いBGMまで、多様な音楽がゲーム体験を豊かにしています。"
            ),
            Article(
                id="test_2", 
                title="インディーゲーム開発の現状",
                url="https://note.com/test2",
                author="テストユーザー2",
                published_at="2025-06-15T11:00:00+09:00",
                category="ゲーム",
                content_preview="近年、インディーゲーム市場は急速に拡大しています。小規模なチームでも創造性豊かなゲームを制作し、世界中のプレイヤーに届けることが可能になりました。"
            ),
            Article(
                id="test_3",
                title="レトロゲームの魅力再発見",
                url="https://note.com/test3", 
                author="テストユーザー3",
                published_at="2025-06-15T12:00:00+09:00",
                category="ゲーム",
                content_preview="ファミコンやスーパーファミコン時代のゲームには、現代のゲームにはない独特の魅力があります。限られた技術的制約の中で生み出された創意工夫は今も色褪せません。"
            )
        ]
        
        evaluator = ArticleEvaluator()
        
        logger.info(f"🔍 Testing AI evaluation with {len(test_articles)} different articles")
        
        results = []
        for i, article in enumerate(test_articles, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"📝 TESTING ARTICLE {i}: {article.id}")
            logger.info(f"Title: {article.title}")
            logger.info(f"Content: {article.content_preview[:100]}...")
            logger.info(f"{'='*60}")
            
            # Prepare content and generate prompt
            content = evaluator._prepare_content_for_evaluation(article)
            messages = evaluator._generate_evaluation_prompt(article, content)
            
            logger.info(f"📤 CALLING AI...")
            
            try:
                # Call AI directly
                response = evaluator.client.chat.completions.create(
                    model=evaluator.groq_settings.get("model", "llama3-70b-8192"),
                    messages=messages,
                    temperature=evaluator.groq_settings.get("temperature", 0.3),
                    max_tokens=evaluator.groq_settings.get("max_tokens", 1000),
                )
                
                raw_response = response.choices[0].message.content
                logger.info(f"📥 RAW AI RESPONSE:")
                logger.info(raw_response)
                
                # Parse response
                parsed_result = evaluator._parse_ai_response(raw_response, article.id)
                
                if parsed_result:
                    logger.info(f"\n✅ PARSED RESULT:")
                    logger.info(f"Article ID: {parsed_result.article_id}")
                    logger.info(f"Quality: {parsed_result.quality_score}")
                    logger.info(f"Originality: {parsed_result.originality_score}")
                    logger.info(f"Entertainment: {parsed_result.entertainment_score}")
                    logger.info(f"Total: {parsed_result.total_score}")
                    logger.info(f"Summary: {parsed_result.ai_summary}")
                    
                    results.append({
                        'article_id': parsed_result.article_id,
                        'scores': f"{parsed_result.quality_score}/{parsed_result.originality_score}/{parsed_result.entertainment_score}",
                        'total': parsed_result.total_score,
                        'summary': parsed_result.ai_summary
                    })
                else:
                    logger.error("❌ FAILED TO PARSE RESPONSE")
                
            except Exception as e:
                logger.error(f"❌ AI CALL FAILED: {e}")
            
            # Delay between requests to avoid rate limiting
            await asyncio.sleep(3)
        
        # Analyze results
        logger.info(f"\n{'='*80}")
        logger.info("📊 RESULTS ANALYSIS")
        logger.info(f"{'='*80}")
        
        score_patterns = {}
        for result in results:
            pattern = result['scores']
            if pattern in score_patterns:
                score_patterns[pattern].append(result)
            else:
                score_patterns[pattern] = [result]
        
        logger.info(f"Score patterns found:")
        for pattern, articles in score_patterns.items():
            logger.info(f"  {pattern}: {len(articles)} articles")
            if len(articles) > 1:
                logger.warning(f"  ⚠️  DUPLICATE PATTERN DETECTED: {pattern}")
                for article in articles:
                    logger.info(f"    - {article['article_id']}: {article['summary'][:60]}...")
        
        if len(set(r['scores'] for r in results)) == len(results):
            logger.info("✅ All articles received unique scores - no duplicates detected")
        else:
            logger.warning("⚠️  Some articles received identical scores!")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_duplicate_scores())