"""Article data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    """Article model representing a note article."""
    
    id: str = Field(..., description="Note article ID")
    title: str = Field(..., description="Article title")
    url: HttpUrl = Field(..., description="Article URL")
    thumbnail: Optional[str] = Field(None, description="Thumbnail image URL")
    published_at: datetime = Field(..., description="Publication date")
    author: str = Field(..., description="Author name")
    content_preview: Optional[str] = Field(None, description="Article preview text")
    category: str = Field(..., description="Article category")
    collected_at: datetime = Field(default_factory=datetime.now, description="Collection timestamp")
    is_evaluated: bool = Field(False, description="Evaluation status flag")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class ArticleCreateRequest(BaseModel):
    """Article creation request model."""
    
    id: str
    title: str
    url: str
    thumbnail: Optional[str] = None
    published_at: datetime
    author: str
    content_preview: Optional[str] = None
    category: str


class ArticleResponse(BaseModel):
    """Article response model for API."""
    
    id: str
    title: str
    url: str
    thumbnail: Optional[str]
    published_at: datetime
    author: str
    content_preview: Optional[str]
    category: str
    collected_at: datetime
    is_evaluated: bool
    total_score: Optional[int] = None
    ai_summary: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class NoteApiResponse(BaseModel):
    """Note API response model."""
    
    data: dict
    status: int = 200
    message: str = "success"


class NoteArticleData(BaseModel):
    """Note article data from API response."""
    
    id: str
    name: str  # title in note API
    key: str   # URL key
    user: dict
    publishAt: str
    eyecatch: Optional[str] = None
    body: Optional[str] = None
    
    def to_article(self, category: str) -> Article:
        """Convert to Article model.
        
        Args:
            category: Article category
            
        Returns:
            Article instance
        """
        # Parse publish date
        published_at = datetime.fromisoformat(
            self.publishAt.replace('Z', '+00:00')
        )
        
        # Extract content preview (first 200 characters of body)
        content_preview = None
        if self.body:
            # Remove HTML tags and get preview
            import re
            clean_body = re.sub('<[^<]+?>', '', self.body)
            content_preview = clean_body[:200].strip()
        
        # Construct URL
        user_key = self.user.get('urlname', '')
        article_url = f"https://note.com/{user_key}/n/{self.key}"
        
        return Article(
            id=self.id,
            title=self.name,
            url=article_url,
            thumbnail=self.eyecatch,
            published_at=published_at,
            author=self.user.get('nickname', 'Unknown'),
            content_preview=content_preview,
            category=category,
        )