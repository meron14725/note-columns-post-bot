"""Article data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class NoteArticleMetadata(BaseModel):
    """Note specific metadata."""
    
    note_type: str = Field(default="TextNote", description="Note type")
    like_count: int = Field(default=0, description="Number of likes")
    price: int = Field(default=0, description="Price in yen")
    can_read: bool = Field(default=True, description="Readability flag")
    is_liked: bool = Field(default=False, description="Liked status")
    comment_count: int = Field(default=0, description="Number of comments")


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
    is_excluded: bool = Field(False, description="Exclusion flag for quality control")
    exclusion_reason: Optional[str] = Field(None, description="Reason for exclusion (if excluded)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    note_data: Optional[NoteArticleMetadata] = Field(None, description="Note specific metadata")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class ArticleReference(BaseModel):
    """Article reference for list collection (key and urlname)."""
    
    id: str = Field(..., description="Note article ID")
    key: str = Field(..., description="Article key for URL")
    urlname: str = Field(..., description="User URL name")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    published_at: datetime = Field(..., description="Publication date")
    author: str = Field(..., description="Author name")
    category: str = Field(..., description="Article category")
    note_data: Optional[NoteArticleMetadata] = Field(None, description="Note metadata")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for scraper compatibility."""
        return {
            'id': self.id,
            'key': self.key,
            'urlname': self.urlname,
            'title': self.title,
            'url': self.url,
            'thumbnail': self.thumbnail,
            'published_at': self.published_at,
            'author': self.author,
            'category': self.category,
            'note_data': self.note_data
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
    note_data: Optional[NoteArticleMetadata] = None


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
    is_excluded: bool = False
    exclusion_reason: Optional[str] = None
    total_score: Optional[int] = None
    ai_summary: Optional[str] = None
    note_data: Optional[NoteArticleMetadata] = None
    
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
    """Note article data from API response (for backward compatibility)."""
    
    id: str
    name: str  # title in note API
    key: str   # URL key
    user: dict
    publishAt: Optional[str] = None
    publish_at: Optional[str] = None  # Alternative field name
    eyecatch: Optional[str] = None
    eyecatch_url: Optional[str] = None  # Alternative field name
    body: Optional[str] = None
    type: str = Field(default="TextNote")
    like_count: int = Field(default=0)
    price: int = Field(default=0)
    can_read: bool = Field(default=True)
    is_liked: bool = Field(default=False)
    
    def to_article(self, category: str) -> Article:
        """Convert to Article model.
        
        Args:
            category: Article category
            
        Returns:
            Article instance
        """
        # Parse publish date
        publish_date_str = self.publishAt or self.publish_at
        if publish_date_str:
            try:
                published_at = datetime.fromisoformat(
                    publish_date_str.replace('Z', '+00:00').replace('+09:00', '+0900')
                )
            except:
                published_at = datetime.now()
        else:
            published_at = datetime.now()
        
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
        
        # Get thumbnail
        thumbnail = self.eyecatch or self.eyecatch_url
        
        # Create metadata
        note_metadata = NoteArticleMetadata(
            note_type=self.type,
            like_count=self.like_count,
            price=self.price,
            can_read=self.can_read,
            is_liked=self.is_liked
        )
        
        return Article(
            id=str(self.id),
            title=self.name,
            url=article_url,
            thumbnail=thumbnail,
            published_at=published_at,
            author=self.user.get('nickname', 'Unknown'),
            content_preview=content_preview,
            category=category,
            note_data=note_metadata
        )
    
    def to_reference(self, category: str) -> ArticleReference:
        """Convert to ArticleReference for list collection.
        
        Args:
            category: Article category
            
        Returns:
            ArticleReference instance
        """
        # Parse publish date
        publish_date_str = self.publishAt or self.publish_at
        if publish_date_str:
            try:
                published_at = datetime.fromisoformat(
                    publish_date_str.replace('Z', '+00:00').replace('+09:00', '+0900')
                )
            except:
                published_at = datetime.now()
        else:
            published_at = datetime.now()
        
        # Construct URL
        user_key = self.user.get('urlname', '')
        article_url = f"https://note.com/{user_key}/n/{self.key}"
        
        # Get thumbnail
        thumbnail = self.eyecatch or self.eyecatch_url
        
        # Create metadata
        note_metadata = NoteArticleMetadata(
            note_type=self.type,
            like_count=self.like_count,
            price=self.price,
            can_read=self.can_read,
            is_liked=self.is_liked
        )
        
        return ArticleReference(
            id=str(self.id),
            key=self.key,
            urlname=user_key,
            title=self.name,
            url=article_url,
            thumbnail=thumbnail,
            published_at=published_at,
            author=self.user.get('nickname', 'Unknown'),
            category=category,
            note_data=note_metadata
        )