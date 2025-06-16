"""AI evaluation service using Groq Cloud."""

import asyncio
import json
import random
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
        
        # Track recent evaluations to detect duplicates
        self.recent_evaluations = []
        
        # Load retry evaluation config
        self.retry_evaluation_config = self.prompt_settings.get("retry_evaluation_prompt", {})
        
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
    
    async def evaluate_article_with_full_content(self, article: Article, full_content: str) -> Optional[Evaluation]:
        """Evaluate a single article with provided full content (streaming evaluation).
        
        Args:
            article: Article to evaluate (without full content)
            full_content: Full article content text
            
        Returns:
            Evaluation result or None if failed
        """
        try:
            # Apply rate limiting
            await rate_limiter.await_if_needed("groq")
            
            evaluation = await self._evaluate_single_article(article, full_content)
            
            if evaluation:
                rate_limiter.record_request("groq")
                logger.debug(f"Streaming evaluation completed for: {article.title}")
                return evaluation
            else:
                logger.warning(f"Streaming evaluation failed for: {article.title}")
                
        except Exception as e:
            logger.error(f"Error in streaming evaluation for {article.title}: {e}")
        
        return None
    
    async def _evaluate_single_article(self, article: Article, full_content: Optional[str] = None) -> Optional[Evaluation]:
        """Evaluate a single article with automatic retry for duplicate scores.
        
        Args:
            article: Article to evaluate
            full_content: Full content text (for streaming evaluation)
            
        Returns:
            Evaluation result or None if failed
        """
        try:
            # Prepare content for evaluation
            content_text = self._prepare_content_for_evaluation(article, full_content)
            
            # Generate evaluation prompt
            prompt = self._generate_evaluation_prompt(article, content_text)
            
            # Call Groq API
            ai_result = await self._call_groq_api(prompt, article.id)
            
            if ai_result:
                # Check for duplicate scores and retry if needed
                if self._check_for_duplicate_scores(ai_result):
                    logger.info(f"Duplicate score detected for {article.id}, attempting retry evaluation")
                    
                    retry_evaluation = await self._retry_evaluation_with_alternative_prompt(
                        article, content_text, ai_result
                    )
                    
                    if retry_evaluation:
                        return retry_evaluation
                    else:
                        logger.warning(f"Retry evaluation failed for {article.id}, using original result")
                
                return ai_result.to_evaluation(article.id)
            
        except Exception as e:
            logger.error(f"Error in single article evaluation: {e}")
        
        return None
    
    def _prepare_content_for_evaluation(self, article: Article, full_content: Optional[str] = None) -> str:
        """Prepare article content for evaluation.
        
        Args:
            article: Article to prepare
            full_content: Full content text (for streaming evaluation)
            
        Returns:
            Prepared content text
        """
        # Use provided full content for streaming evaluation, otherwise fallback to preview
        content = full_content or article.content_preview or ""
        
        # Clean up content
        if content:
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            # Remove excessive whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            # Limit length for API (keep reasonable limit for cost/performance)
            content = content[:4000]  # Increased to use more content for better evaluation
        
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
        
        # Format user prompt with article data including article ID and category
        user_prompt = user_prompt_template.format(
            article_id=article.id,
            title=article.title,
            author=article.author,
            category=article.category or "未分類",
            content_preview=content
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    async def _call_groq_api(self, messages: List[Dict[str, str]], expected_article_id: str) -> Optional[AIEvaluationResult]:
        """Call Groq API for evaluation.
        
        Args:
            messages: List of messages for the API
            expected_article_id: Expected article ID to validate against response
            
        Returns:
            AI evaluation result or None if failed
        """
        max_retries = self.prompt_settings.get("rate_limit", {}).get("max_retries", 3)
        retry_delay = self.prompt_settings.get("rate_limit", {}).get("retry_delay_seconds", 2.0)
        
        for attempt in range(max_retries):
            try:
                # Add slight randomization to temperature to prevent identical evaluations
                base_temperature = self.groq_settings.get("temperature", 0.3)
                # Vary temperature by ±0.05 to add diversity while maintaining consistency
                randomized_temperature = base_temperature + random.uniform(-0.05, 0.05)
                randomized_temperature = max(0.1, min(0.8, randomized_temperature))  # Keep within reasonable bounds
                
                # Make API call
                response = self.client.chat.completions.create(
                    model=self.groq_settings.get("model", "llama3-70b-8192"),
                    messages=messages,
                    temperature=randomized_temperature,
                    max_tokens=self.groq_settings.get("max_tokens", 1000),
                    top_p=self.groq_settings.get("top_p", 0.9),
                    frequency_penalty=self.groq_settings.get("frequency_penalty", 0.0),
                    presence_penalty=self.groq_settings.get("presence_penalty", 0.0),
                )
                
                # Parse response
                content = response.choices[0].message.content
                return self._parse_ai_response(content, expected_article_id)
                
            except Exception as e:
                logger.warning(f"Groq API call failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Groq API call failed after {max_retries} attempts")
        
        return None
    
    def _parse_ai_response(self, content: str, expected_article_id: str) -> Optional[AIEvaluationResult]:
        """Parse AI response content.
        
        Args:
            content: Response content from AI
            expected_article_id: Expected article ID to validate
            
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
            
            # Validate article ID first
            returned_article_id = data.get('article_id', '')
            if returned_article_id != expected_article_id:
                logger.warning(
                    f"Article ID mismatch: expected '{expected_article_id}', "
                    f"got '{returned_article_id}'. Using expected ID."
                )
                data['article_id'] = expected_article_id
            
            # Apply data validation and fallbacks
            data = self._validate_and_fix_response_data(data)
            
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
            logger.debug(f"Response content: {content}")
    
    def _validate_and_fix_response_data(self, data: dict) -> dict:
        """Validate and fix AI response data.
        
        Args:
            data: Raw response data from AI
            
        Returns:
            Validated and fixed data
        """
        # Ensure all required fields exist with default values
        if 'article_id' not in data:
            logger.warning("Missing article_id in AI response")
            data['article_id'] = None
        
        if 'quality_score' not in data:
            logger.warning("Missing quality_score, using default: 20")
            data['quality_score'] = 20
        
        if 'originality_score' not in data:
            logger.warning("Missing originality_score, using default: 15")
            data['originality_score'] = 15
        
        if 'entertainment_score' not in data:
            logger.warning("Missing entertainment_score, using default: 15")
            data['entertainment_score'] = 15
        
        if 'ai_summary' not in data:
            logger.warning("Missing ai_summary, using default")
            data['ai_summary'] = "AI評価の詳細が取得できませんでした。記事内容を確認してお楽しみください。"
        elif len(data['ai_summary']) < 10:
            logger.warning(f"AI summary too short ({len(data['ai_summary'])} chars), padding")
            data['ai_summary'] = data['ai_summary'] + "記事の詳細をご確認ください。"
        
        # Ensure ai_summary is within length limit (300 characters)
        if len(data['ai_summary']) > 300:
            logger.warning(f"AI summary too long ({len(data['ai_summary'])} chars), truncating to 300")
            data['ai_summary'] = data['ai_summary'][:297] + "..."
        
        # Calculate total_score
        data['total_score'] = data['quality_score'] + data['originality_score'] + data['entertainment_score']
        
        return data
    
    def _check_for_duplicate_scores(self, result: AIEvaluationResult) -> bool:
        """Check for duplicate scores and return True if retry is needed.
        
        Args:
            result: AI evaluation result to check
            
        Returns:
            True if duplicate scores detected and retry is needed
        """
        score_pattern = f"{result.quality_score}/{result.originality_score}/{result.entertainment_score}"
        
        # Add to recent evaluations (keep last 20)
        self.recent_evaluations.append({
            'article_id': result.article_id,
            'pattern': score_pattern,
            'total_score': result.total_score,
            'summary': result.ai_summary[:50] + "..." if len(result.ai_summary) > 50 else result.ai_summary
        })
        
        # Keep only last 20 evaluations
        if len(self.recent_evaluations) > 20:
            self.recent_evaluations = self.recent_evaluations[-20:]
        
        # Check for duplicates
        pattern_count = sum(1 for eval_data in self.recent_evaluations if eval_data['pattern'] == score_pattern)
        
        if pattern_count > 1:
            logger.warning(
                f"⚠️  DUPLICATE SCORE PATTERN DETECTED: {score_pattern} "
                f"(found {pattern_count} times in recent evaluations)"
            )
            
            # Log all articles with this pattern
            duplicates = [eval_data for eval_data in self.recent_evaluations if eval_data['pattern'] == score_pattern]
            for dup in duplicates:
                logger.warning(f"  - {dup['article_id']}: {dup['summary']}")
            
            # Trigger retry on second occurrence (pattern_count == 2)
            if pattern_count == 2:
                logger.info(f"🔄 Triggering retry evaluation for duplicate pattern: {score_pattern}")
                return True
            
            # If 3 or more identical patterns, this might indicate a system issue
            if pattern_count >= 3:
                logger.error(
                    f"❌ CRITICAL: {pattern_count} identical score patterns detected! "
                    f"This may indicate an AI model or system issue."
                )
        
        return False
    
    async def _retry_evaluation_with_alternative_prompt(self, article: Article, content_text: str, 
                                                       original_result: AIEvaluationResult) -> Optional[Evaluation]:
        """Retry evaluation with alternative prompt to avoid duplicate scores.
        
        Args:
            article: Article to re-evaluate
            content_text: Prepared content text
            original_result: Original evaluation result
            
        Returns:
            Retry evaluation result or None if failed
        """
        try:
            # Generate alternative prompt using retry config
            retry_prompt = self._generate_retry_evaluation_prompt(article, content_text)
            
            # Call Groq API with retry-specific settings
            retry_ai_result = await self._call_groq_api_with_retry_settings(retry_prompt, article.id)
            
            if retry_ai_result:
                # Create metadata for retry evaluation
                retry_metadata = {
                    "original_scores": {
                        "quality": original_result.quality_score,
                        "originality": original_result.originality_score,
                        "entertainment": original_result.entertainment_score,
                        "total": original_result.total_score
                    },
                    "retry_scores": {
                        "quality": retry_ai_result.quality_score,
                        "originality": retry_ai_result.originality_score,
                        "entertainment": retry_ai_result.entertainment_score,
                        "total": retry_ai_result.total_score
                    },
                    "score_pattern_original": f"{original_result.quality_score}/{original_result.originality_score}/{original_result.entertainment_score}",
                    "score_pattern_retry": f"{retry_ai_result.quality_score}/{retry_ai_result.originality_score}/{retry_ai_result.entertainment_score}"
                }
                
                retry_reason = f"Duplicate score pattern detected: {retry_metadata['score_pattern_original']}"
                
                logger.info(
                    f"✅ Retry evaluation completed for {article.id}: "
                    f"{retry_metadata['score_pattern_original']} → {retry_metadata['score_pattern_retry']}"
                )
                
                return retry_ai_result.to_evaluation(
                    article.id, 
                    is_retry=True,
                    retry_reason=retry_reason,
                    evaluation_metadata=retry_metadata
                )
            
        except Exception as e:
            logger.error(f"Error in retry evaluation: {e}")
        
        return None
    
    def _generate_retry_evaluation_prompt(self, article: Article, content: str) -> List[Dict[str, str]]:
        """Generate retry evaluation prompt with alternative approach.
        
        Args:
            article: Article to evaluate
            content: Prepared content text
            
        Returns:
            List of messages for the API
        """
        system_prompt = self.retry_evaluation_config.get("system_prompt", "")
        user_prompt_template = self.retry_evaluation_config.get("user_prompt_template", "")
        
        # Format user prompt with article data including category
        user_prompt = user_prompt_template.format(
            article_id=article.id,
            title=article.title,
            author=article.author,
            category=article.category or "未分類",
            content_preview=content
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    async def _call_groq_api_with_retry_settings(self, messages: List[Dict[str, str]], expected_article_id: str) -> Optional[AIEvaluationResult]:
        """Call Groq API with retry-specific settings for diversity.
        
        Args:
            messages: List of messages for the API
            expected_article_id: Expected article ID to validate against response
            
        Returns:
            AI evaluation result or None if failed
        """
        max_retries = self.prompt_settings.get("rate_limit", {}).get("max_retries", 3)
        retry_delay = self.prompt_settings.get("rate_limit", {}).get("retry_delay_seconds", 2.0)
        
        for attempt in range(max_retries):
            try:
                # Use higher temperature for retry to increase diversity
                base_temperature = self.groq_settings.get("temperature", 0.3)
                # Increase temperature significantly for retry (0.5-0.8 range)
                retry_temperature = base_temperature + random.uniform(0.2, 0.5)
                retry_temperature = max(0.5, min(0.8, retry_temperature))
                
                # Make API call with higher temperature
                response = self.client.chat.completions.create(
                    model=self.groq_settings.get("model", "llama3-70b-8192"),
                    messages=messages,
                    temperature=retry_temperature,
                    max_tokens=self.groq_settings.get("max_tokens", 1000),
                    top_p=self.groq_settings.get("top_p", 0.9),
                    frequency_penalty=self.groq_settings.get("frequency_penalty", 0.0),
                    presence_penalty=self.groq_settings.get("presence_penalty", 0.0),
                )
                
                # Parse response
                content = response.choices[0].message.content
                return self._parse_ai_response(content, expected_article_id)
                
            except Exception as e:
                logger.warning(f"Groq API retry call failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Groq API retry call failed after {max_retries} attempts")
        
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