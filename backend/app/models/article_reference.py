"""Article reference data model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArticleReference(BaseModel):
    """Article reference model for deduplication."""

    key: str = Field(..., description="Note article key")
    urlname: str = Field(..., description="Note article urlname")
    category: str = Field(..., description="Collection source category")
    title: Optional[str] = Field(None, description="Article title")
    author: Optional[str] = Field(None, description="Article author")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    collected_at: datetime = Field(
        default_factory=datetime.now, description="Collection timestamp"
    )
    is_processed: bool = Field(
        False, description="Whether article details have been processed"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @property
    def article_id(self) -> str:
        """Generate article ID from key and urlname."""
        return f"{self.urlname}_{self.key}"

    @property
    def article_url(self) -> str:
        """Generate article URL from urlname and key."""
        return f"https://note.com/{self.urlname}/n/{self.key}"
