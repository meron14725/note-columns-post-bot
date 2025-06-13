"""AI evaluation service using Groq Cloud."""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional

import httpx
from groq import Groq

from backend.app.models.article import Article
from backend.app.models.evaluation import Evaluation, AIEvaluationResult
from backend.app.utils.logger import get_logger, log_execution_time
from backend.app.utils.rate_limiter import rate_limiter
from config.config import config, get_prompt_settings

logger = get_logger(__name__)


class ArticleEvaluator:
    """AI-powered article evaluator using Groq Cloud."""
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize evaluator.
        
        Args:
            api_key: Groq API key (uses config if not provided)
        """
        self.api_key = api_key or config.groq_api_key
        if not self.api_key:
            raise ValueError("Groq API key is required")
        
        self.client = Groq(api_key=self.api_key)
        self.prompt_settings = get_prompt_settings()
        self.evaluation_config = self.prompt_settings.get("evaluation_prompt", {})
        self.groq_settings = self.prompt_settings.get("groq_settings", {})
        
    @log_execution_time
    async def evaluate_articles(self, articles: List[Article]) -> List[Evaluation]:
        """Evaluate multiple articles.
        
        Args:
            articles: List of articles to evaluate
            
        Returns:
            List of evaluations
        """
        evaluations = []
        total_articles = len(articles)
        
        logger.info(f"Starting evaluation of {total_articles} articles")
        
        for i, article in enumerate(articles, 1):
            try:
                # Apply rate limiting
                await rate_limiter.await_if_needed("groq")
                
                evaluation = await self._evaluate_single_article(article)
                if evaluation:
                    evaluations.append(evaluation)
                    logger.debug(f"Evaluated article {i}/{total_articles}: {article.title}")
                else:
                    logger.warning(f"Failed to evaluate article {i}/{total_articles}: {article.title}")
                
                rate_limiter.record_request("groq")
                
                # Small delay between requests
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error evaluating article {article.title}: {e}")
                continue
        
        logger.info(f"Completed evaluation: {len(evaluations)}/{total_articles} articles successfully evaluated")
        return evaluations
    
    async def _evaluate_single_article(self, article: Article) -> Optional[Evaluation]:
        """Evaluate a single article.
        
        Args:
            article: Article to evaluate
            
        Returns:
            Evaluation result or None if failed
        """
        try:
            # Prepare content for evaluation
            content_text = self._prepare_content_for_evaluation(article)
            
            # Generate evaluation prompt
            prompt = self._generate_evaluation_prompt(article, content_text)
            
            # Call Groq API
            ai_result = await self._call_groq_api(prompt)
            
            if ai_result:
                return ai_result.to_evaluation(article.id)
            
        except Exception as e:
            logger.error(f"Error in single article evaluation: {e}")
        
        return None
    
    def _prepare_content_for_evaluation(self, article: Article) -> str:
        """Prepare article content for evaluation.
        
        Args:
            article: Article to prepare
            
        Returns:
            Prepared content text
        """
        # Use full content if available, otherwise fallback to preview
        content = getattr(article, 'content_full', None) or article.content_preview or ""
        
        # Clean up content
        if content:
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Remove excessive whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            # Limit length for API (keep reasonable limit for cost/performance)
            content = content[:3000]  # Increased from 500 to 3000 for better evaluation
        
        # If no content, use just the title
        if not content:
            content = f"タイトルのみ: {article.title}"
        
        return content
    
    def _generate_evaluation_prompt(self, article: Article, content: str) -> List[Dict[str, str]]:
        """Generate evaluation prompt for Groq API.
        
        Args:
            article: Article to evaluate
            content: Prepared content text
            
        Returns:
            List of messages for the API
        """
        system_prompt = self.evaluation_config.get("system_prompt", "")
        user_prompt_template = self.evaluation_config.get("user_prompt_template", "")
        
        # Format user prompt with article data
        user_prompt = user_prompt_template.format(
            title=article.title,
            author=article.author,
            content_preview=content
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    async def _call_groq_api(self, messages: List[Dict[str, str]]) -> Optional[AIEvaluationResult]:
        """Call Groq API for evaluation.
        
        Args:
            messages: List of messages for the API
            
        Returns:
            AI evaluation result or None if failed
        """
        max_retries = self.prompt_settings.get("rate_limit", {}).get("max_retries", 3)
        retry_delay = self.prompt_settings.get("rate_limit", {}).get("retry_delay_seconds", 2.0)
        
        for attempt in range(max_retries):
            try:
                # Make API call
                response = self.client.chat.completions.create(
                    model=self.groq_settings.get("model", "llama3-70b-8192"),
                    messages=messages,
                    temperature=self.groq_settings.get("temperature", 0.3),
                    max_tokens=self.groq_settings.get("max_tokens", 1000),
                    top_p=self.groq_settings.get("top_p", 0.9),
                    frequency_penalty=self.groq_settings.get("frequency_penalty", 0.0),
                    presence_penalty=self.groq_settings.get("presence_penalty", 0.0),
                )
                
                # Parse response
                content = response.choices[0].message.content
                return self._parse_ai_response(content)
                
            except Exception as e:
                logger.warning(f"Groq API call failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Groq API call failed after {max_retries} attempts")
        
        return None
    
    def _parse_ai_response(self, content: str) -> Optional[AIEvaluationResult]:
        """Parse AI response content.
        
        Args:
            content: Response content from AI
            
        Returns:
            Parsed evaluation result or None if failed
        """
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in AI response")
                return None
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Validate and create result
            result = AIEvaluationResult(**data)
            
            # Validate score ranges
            if not (0 <= result.quality_score <= 40):
                logger.warning(f"Quality score out of range: {result.quality_score}")
                result.quality_score = max(0, min(40, result.quality_score))
            
            if not (0 <= result.originality_score <= 30):
                logger.warning(f"Originality score out of range: {result.originality_score}")
                result.originality_score = max(0, min(30, result.originality_score))
            
            if not (0 <= result.entertainment_score <= 30):
                logger.warning(f"Entertainment score out of range: {result.entertainment_score}")
                result.entertainment_score = max(0, min(30, result.entertainment_score))
            
            # Recalculate total score
            result.total_score = result.quality_score + result.originality_score + result.entertainment_score
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI response: {e}")
            logger.debug(f"Response content: {content}")
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
        
        return None
    
    def get_evaluation_stats(self, evaluations: List[Evaluation]) -> Dict[str, Any]:
        """Generate evaluation statistics.
        
        Args:
            evaluations: List of evaluations
            
        Returns:
            Dictionary with statistics
        """
        if not evaluations:
            return {"total": 0}
        
        total_scores = [e.total_score for e in evaluations]
        quality_scores = [e.quality_score for e in evaluations]
        originality_scores = [e.originality_score for e in evaluations]
        entertainment_scores = [e.entertainment_score for e in evaluations]
        
        return {
            "total": len(evaluations),
            "average_total_score": sum(total_scores) / len(total_scores),
            "max_total_score": max(total_scores),
            "min_total_score": min(total_scores),
            "average_quality_score": sum(quality_scores) / len(quality_scores),
            "average_originality_score": sum(originality_scores) / len(originality_scores),
            "average_entertainment_score": sum(entertainment_scores) / len(entertainment_scores),
            "high_quality_articles": len([s for s in total_scores if s >= 80]),
            "medium_quality_articles": len([s for s in total_scores if 60 <= s < 80]),
            "low_quality_articles": len([s for s in total_scores if s < 60]),
        }


# Convenience function for synchronous usage
def evaluate_articles_sync(articles: List[Article]) -> List[Evaluation]:
    """Evaluate articles synchronously.
    
    Args:
        articles: List of articles to evaluate
        
    Returns:
        List of evaluations
    """
    async def _evaluate():
        evaluator = ArticleEvaluator()
        return await evaluator.evaluate_articles(articles)
    
    return asyncio.run(_evaluate())