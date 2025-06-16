"""JSON generation service for GitHub Pages."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from backend.app.models.evaluation import ArticleWithEvaluation
from backend.app.repositories.article_repository import ArticleRepository
from backend.app.utils.logger import get_logger, log_execution_time
from config.config import config, JSON_DATA_DIR, OUTPUT_DIR

logger = get_logger(__name__)


class JSONGenerator:
    """Generator for JSON files used by GitHub Pages."""
    
    def __init__(self) -> None:
        """Initialize generator."""
        self.article_repo = ArticleRepository()
        self.output_dir = OUTPUT_DIR
        self.json_data_dir = JSON_DATA_DIR
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.json_data_dir.mkdir(parents=True, exist_ok=True)
    
    @log_execution_time
    def generate_all_json_files(self) -> bool:
        """Generate all JSON files for the website.
        
        Returns:
            True if all files generated successfully
        """
        try:
            logger.info("Starting JSON file generation")
            
            # Generate main files
            success = True
            success &= self.generate_articles_json()
            success &= self.generate_top5_json()
            success &= self.generate_meta_json()
            success &= self.generate_categories_json()
            success &= self.generate_statistics_json()
            
            # Archive today's data
            self.archive_daily_data()
            
            if success:
                logger.info("All JSON files generated successfully")
            else:
                logger.warning("Some JSON files failed to generate")
            
            return success
            
        except Exception as e:
            logger.error(f"Error generating JSON files: {e}")
            return False
    
    def generate_articles_json(self) -> bool:
        """Generate articles.json with all evaluated articles.
        
        Returns:
            True if generated successfully
        """
        try:
            # Get all articles with evaluations (recent 30 days)
            articles = self.article_repo.get_articles_with_evaluations(
                min_score=0, 
                days=30
            )
            
            # Remove duplicates by URL before converting to JSON
            unique_articles = {}
            for article in articles:
                url = str(article.url)
                # Keep the article with the highest score if duplicates exist
                if url not in unique_articles or article.total_score > unique_articles[url].total_score:
                    unique_articles[url] = article
            
            final_articles = list(unique_articles.values())
            logger.info(f"Removed {len(articles) - len(final_articles)} duplicate articles")
            
            # Convert to JSON format
            json_data = {
                "lastUpdated": datetime.now().isoformat(),
                "total": len(final_articles),
                "articles": [self._article_to_json(article) for article in final_articles]
            }
            
            # Save to both output and json data directories
            output_path = self.output_dir / "articles.json"
            data_path = self.json_data_dir / "articles.json"
            
            self._save_json_file(json_data, output_path)
            self._save_json_file(json_data, data_path)
            
            logger.info(f"Generated articles.json with {len(articles)} articles")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate articles.json: {e}")
            return False
    
    def generate_top5_json(self) -> bool:
        """Generate top5.json with highest-rated articles.
        
        Returns:
            True if generated successfully
        """
        try:
            # Get top 5 articles from today
            top_articles = self.article_repo.get_top_articles(limit=5, days=1)
            
            # If less than 5 from today, get from recent days
            if len(top_articles) < 5:
                top_articles = self.article_repo.get_top_articles(limit=5, days=7)
            
            # Remove duplicates by URL and keep highest-scored ones
            unique_articles = {}
            for article in top_articles:
                url = str(article.url)
                if url not in unique_articles or article.total_score > unique_articles[url].total_score:
                    unique_articles[url] = article
            
            final_top_articles = list(unique_articles.values())
            # Sort by score descending and take top 5
            final_top_articles.sort(key=lambda x: x.total_score, reverse=True)
            final_top_articles = final_top_articles[:5]
            
            json_data = {
                "lastUpdated": datetime.now().isoformat(),
                "period": "daily",
                "articles": [self._article_to_json(article) for article in final_top_articles]
            }
            
            # Save to both directories
            output_path = self.output_dir / "top5.json"
            data_path = self.json_data_dir / "top5.json"
            
            self._save_json_file(json_data, output_path)
            self._save_json_file(json_data, data_path)
            
            logger.info(f"Generated top5.json with {len(top_articles)} articles")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate top5.json: {e}")
            return False
    
    def generate_meta_json(self) -> bool:
        """Generate meta.json with system metadata.
        
        Returns:
            True if generated successfully
        """
        try:
            # Get statistics
            total_articles = self.article_repo.get_article_count()
            evaluated_articles = self.article_repo.get_evaluated_article_count()
            
            json_data = {
                "lastUpdated": datetime.now().isoformat(),
                "version": "1.0.0",
                "systemInfo": {
                    "totalArticles": total_articles,
                    "evaluatedArticles": evaluated_articles,
                    "websiteUrl": config.github_pages_url,
                    "githubRepo": config.github_repo_url,
                },
                "buildInfo": {
                    "buildTime": datetime.now().isoformat(),
                    "generator": "entertainment-column-system",
                }
            }
            
            # Save to both directories
            output_path = self.output_dir / "meta.json"
            data_path = self.json_data_dir / "meta.json"
            
            self._save_json_file(json_data, output_path)
            self._save_json_file(json_data, data_path)
            
            logger.info("Generated meta.json")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate meta.json: {e}")
            return False
    
    def generate_categories_json(self) -> bool:
        """Generate categories.json with articles grouped by category.
        
        Returns:
            True if generated successfully
        """
        try:
            categories = ["entertainment", "movie_drama", "music", "anime_game"]
            category_data = {}
            
            for category in categories:
                articles = self.article_repo.get_articles_by_category(category, limit=20)
                # Filter to only evaluated articles
                evaluated_articles = [
                    article for article in articles 
                    if article.is_evaluated
                ]
                
                category_data[category] = {
                    "name": self._get_category_display_name(category),
                    "count": len(evaluated_articles),
                    "articles": [self._simple_article_to_json(article) for article in evaluated_articles[:10]]
                }
            
            json_data = {
                "lastUpdated": datetime.now().isoformat(),
                "categories": category_data
            }
            
            # Save to both directories
            output_path = self.output_dir / "categories.json"
            data_path = self.json_data_dir / "categories.json"
            
            self._save_json_file(json_data, output_path)
            self._save_json_file(json_data, data_path)
            
            logger.info("Generated categories.json")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate categories.json: {e}")
            return False
    
    def generate_statistics_json(self) -> bool:
        """Generate statistics.json with evaluation statistics.
        
        Returns:
            True if generated successfully
        """
        try:
            from backend.app.repositories.evaluation_repository import EvaluationRepository
            eval_repo = EvaluationRepository()
            
            # Get statistics for different time periods
            daily_stats = eval_repo.get_evaluation_statistics(days=1)
            weekly_stats = eval_repo.get_evaluation_statistics(days=7)
            monthly_stats = eval_repo.get_evaluation_statistics(days=30)
            all_time_stats = eval_repo.get_evaluation_statistics()
            
            json_data = {
                "lastUpdated": datetime.now().isoformat(),
                "statistics": {
                    "daily": daily_stats,
                    "weekly": weekly_stats,
                    "monthly": monthly_stats,
                    "allTime": all_time_stats,
                }
            }
            
            # Save to both directories
            output_path = self.output_dir / "statistics.json"
            data_path = self.json_data_dir / "statistics.json"
            
            self._save_json_file(json_data, output_path)
            self._save_json_file(json_data, data_path)
            
            logger.info("Generated statistics.json")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate statistics.json: {e}")
            return False
    
    def archive_daily_data(self) -> None:
        """Archive today's data for historical tracking."""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            archive_dir = self.json_data_dir / "archives"
            archive_dir.mkdir(exist_ok=True)
            
            # Archive articles.json
            articles_path = self.json_data_dir / "articles.json"
            if articles_path.exists():
                archive_path = archive_dir / f"articles_{date_str}.json"
                archive_path.write_text(articles_path.read_text(), encoding='utf-8')
                logger.debug(f"Archived articles data to {archive_path}")
            
        except Exception as e:
            logger.warning(f"Failed to archive daily data: {e}")
    
    def _article_to_json(self, article: ArticleWithEvaluation) -> Dict[str, Any]:
        """Convert ArticleWithEvaluation to JSON format.
        
        Args:
            article: Article with evaluation data
            
        Returns:
            Dictionary in JSON format
        """
        json_data = {
            "id": article.id,
            "title": article.title,
            "url": article.url,
            "thumbnail": article.thumbnail,
            "author": article.author,
            "published_at": article.published_at.isoformat(),
            "category": article.category,
            "total_score": article.total_score,
            "scores": {
                "quality": article.quality_score,
                "originality": article.originality_score,
                "entertainment": article.entertainment_score
            },
            "ai_summary": article.ai_summary,
            "evaluated_at": article.evaluated_at.isoformat()
        }
        
        # Add retry evaluation metadata if applicable
        if hasattr(article, 'is_retry_evaluation') and article.is_retry_evaluation:
            evaluation_metadata = {
                "is_retry_evaluation": True,
                "retry_reason": getattr(article, 'retry_reason', 'unknown'),
                "original_evaluation_id": getattr(article, 'original_evaluation_id', None)
            }
            
            # Parse evaluation_metadata JSON if exists
            if hasattr(article, 'evaluation_metadata') and article.evaluation_metadata:
                try:
                    import json
                    parsed_metadata = json.loads(article.evaluation_metadata)
                    evaluation_metadata.update(parsed_metadata)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse evaluation_metadata for article {article.id}")
            
            json_data["evaluation_metadata"] = evaluation_metadata
        
        return json_data
    
    def _simple_article_to_json(self, article) -> Dict[str, Any]:
        """Convert Article to simple JSON format (for categories).
        
        Args:
            article: Article instance
            
        Returns:
            Dictionary in simple JSON format
        """
        return {
            "id": article.id,
            "title": article.title,
            "url": str(article.url),
            "author": article.author,
            "published_at": article.published_at.isoformat(),
            "thumbnail": article.thumbnail,
        }
    
    def _get_category_display_name(self, category: str) -> str:
        """Get display name for category.
        
        Args:
            category: Category key
            
        Returns:
            Display name
        """
        names = {
            "entertainment": "エンタメ総合",
            "movie_drama": "映画・ドラマ",
            "music": "音楽",
            "anime_game": "アニメ・ゲーム"
        }
        return names.get(category, category)
    
    def _save_json_file(self, data: Dict[str, Any], file_path: Path) -> None:
        """Save data to JSON file.
        
        Args:
            data: Data to save
            file_path: Path to save file
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, separators=(',', ': '))
        
        logger.debug(f"Saved JSON file: {file_path}")