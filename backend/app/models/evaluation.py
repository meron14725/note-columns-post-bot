"""Evaluation data models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Evaluation(BaseModel):
    """Evaluation model for article scores."""
    
    id: Optional[int] = Field(None, description="Evaluation ID")
    article_id: str = Field(..., description="Article ID")
    quality_score: int = Field(..., ge=0, le=40, description="Writing quality score (0-40)")
    originality_score: int = Field(..., ge=0, le=30, description="Originality score (0-30)")
    entertainment_score: int = Field(..., ge=0, le=30, description="Entertainment score (0-30)")
    total_score: int = Field(..., ge=0, le=100, description="Total score (0-100)")
    ai_summary: str = Field(..., description="AI-generated summary")
    evaluated_at: datetime = Field(default_factory=datetime.now, description="Evaluation timestamp")
    created_at: datetime = Field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate total score matches sum of individual scores."""
        calculated_total = self.quality_score + self.originality_score + self.entertainment_score
        if self.total_score != calculated_total:
            self.total_score = calculated_total
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class EvaluationRequest(BaseModel):
    """Evaluation request model."""
    
    article_id: str
    quality_score: int = Field(..., ge=0, le=40)
    originality_score: int = Field(..., ge=0, le=30)
    entertainment_score: int = Field(..., ge=0, le=30)
    ai_summary: str


class EvaluationResponse(BaseModel):
    """Evaluation response model."""
    
    quality_score: int
    originality_score: int
    entertainment_score: int
    total_score: int
    ai_summary: str
    evaluation_reason: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True


class AIEvaluationResult(BaseModel):
    """AI evaluation result from Groq API."""
    
    article_id: Optional[str] = Field(None, description="Article ID returned by AI")
    quality_score: int = Field(..., ge=0, le=40)
    originality_score: int = Field(..., ge=0, le=30)
    entertainment_score: int = Field(..., ge=0, le=30)
    total_score: int = Field(..., ge=0, le=100)
    ai_summary: str = Field(..., min_length=10, max_length=300)
    evaluation_reason: Optional[str] = None
    
    def to_evaluation(self, article_id: str) -> Evaluation:
        """Convert to Evaluation model.
        
        Args:
            article_id: Article ID
            
        Returns:
            Evaluation instance
        """
        return Evaluation(
            article_id=article_id,
            quality_score=self.quality_score,
            originality_score=self.originality_score,
            entertainment_score=self.entertainment_score,
            total_score=self.total_score,
            ai_summary=self.ai_summary,
        )


class ArticleWithEvaluation(BaseModel):
    """Combined article and evaluation model."""
    
    # Article fields
    id: str
    title: str
    url: str
    thumbnail: Optional[str]
    published_at: datetime
    author: str
    content_preview: Optional[str]
    category: str
    collected_at: datetime
    
    # Evaluation fields
    quality_score: int
    originality_score: int
    entertainment_score: int
    total_score: int
    ai_summary: str
    evaluated_at: datetime
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }