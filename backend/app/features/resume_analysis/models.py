"""Resume analysis models and schemas."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict

from app.database.base import Base
from app.core.datetime_utils import utc_now


# Enums
class Industry(str, Enum):
    """Supported industries for analysis."""
    STRATEGY_TECH = "strategy_tech"
    MA_FINANCIAL = "ma_financial"
    CONSULTING = "consulting"
    SYSTEM_INTEGRATOR = "system_integrator"
    GENERAL = "general"


class AnalysisStatus(str, Enum):
    """Analysis processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class MarketTier(str, Enum):
    """Market tier classification."""
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    UNKNOWN = "unknown"


# SQLAlchemy Models
class ResumeAnalysis(Base):
    """Resume analysis database model."""
    
    __tablename__ = "resume_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # File and user references
    file_upload_id = Column(UUID(as_uuid=True), ForeignKey("file_uploads.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Analysis parameters
    industry = Column(String(50), nullable=False)
    status = Column(String(50), default=AnalysisStatus.PENDING)
    
    # Analysis results
    overall_score = Column(Float)
    market_tier = Column(String(20))
    
    # Detailed scores (stored as JSON)
    structure_scores = Column(JSON)
    appeal_scores = Column(JSON)
    confidence_metrics = Column(JSON)
    
    # Analysis content
    structure_feedback = Column(Text)
    appeal_feedback = Column(Text)
    analysis_summary = Column(Text)
    improvement_suggestions = Column(Text)
    
    # Metadata
    processing_time_seconds = Column(Float)
    error_message = Column(Text)
    retry_count = Column(Float, default=0)
    
    # AI model information
    ai_model_version = Column(String(100))
    ai_tokens_used = Column(Float)
    
    # Tracking
    analysis_started_at = Column(DateTime(timezone=True))
    analysis_completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    # Relationships
    file_upload = relationship("FileUpload", back_populates="analyses")
    user = relationship("User", back_populates="analyses")
    
    def __repr__(self):
        return f"<ResumeAnalysis(id={self.id}, industry={self.industry}, status={self.status})>"


# Pydantic Schemas
class AnalysisRequest(BaseModel):
    """Request to analyze a resume."""
    text: str = Field(..., min_length=100, max_length=50000)
    industry: Industry
    file_upload_id: Optional[str] = None
    analysis_options: Optional[Dict[str, Any]] = None


class ScoreDetails(BaseModel):
    """Detailed scores for analysis components."""
    overall: float = Field(..., ge=0, le=100)
    formatting: Optional[float] = Field(None, ge=0, le=100)
    content: Optional[float] = Field(None, ge=0, le=100)
    structure: Optional[float] = Field(None, ge=0, le=100)
    impact: Optional[float] = Field(None, ge=0, le=100)
    relevance: Optional[float] = Field(None, ge=0, le=100)


class ConfidenceMetrics(BaseModel):
    """AI confidence metrics."""
    overall_confidence: float = Field(..., ge=0, le=1)
    structure_confidence: Optional[float] = Field(None, ge=0, le=1)
    appeal_confidence: Optional[float] = Field(None, ge=0, le=1)
    data_quality_score: Optional[float] = Field(None, ge=0, le=1)


class FeedbackSection(BaseModel):
    """Feedback section with strengths and improvements."""
    strengths: List[str] = []
    improvements: List[str] = []
    specific_feedback: Optional[str] = None
    examples: Optional[List[str]] = None


class AnalysisResult(BaseModel):
    """Complete analysis result."""
    analysis_id: str
    overall_score: float = Field(..., ge=0, le=100)
    market_tier: MarketTier
    industry: Industry
    
    # Detailed scores
    structure_scores: Optional[ScoreDetails] = None
    appeal_scores: Optional[ScoreDetails] = None
    confidence_metrics: Optional[ConfidenceMetrics] = None
    
    # Feedback
    structure_feedback: Optional[FeedbackSection] = None
    appeal_feedback: Optional[FeedbackSection] = None
    analysis_summary: Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None
    
    # Metadata
    processing_time_seconds: Optional[float] = None
    ai_model_version: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    """API response for analysis."""
    success: bool = True
    analysis_id: str
    status: AnalysisStatus
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisSummary(BaseModel):
    """Summary view of an analysis for listings."""
    id: str
    file_name: Optional[str] = None
    industry: Industry
    overall_score: Optional[float] = None
    market_tier: Optional[MarketTier] = None
    status: AnalysisStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    """Response for listing analyses."""
    analyses: List[AnalysisSummary]
    total_count: int
    page: int = 1
    page_size: int = 10


class AnalysisStats(BaseModel):
    """Analysis statistics for a user."""
    total_analyses: int = 0
    completed_analyses: int = 0
    failed_analyses: int = 0
    average_score: Optional[float] = None
    industry_breakdown: Dict[Industry, int] = {}
    tier_breakdown: Dict[MarketTier, int] = {}


# Legacy compatibility schemas (for migration from old services)
class CompleteAnalysisResult(BaseModel):
    """Legacy format for compatibility with old service."""
    analysis_id: str
    overall_score: float
    market_tier: str = "unknown"
    summary: str = ""
    
    structure_analysis: Optional[Dict[str, Any]] = None
    appeal_analysis: Optional[Dict[str, Any]] = None
    confidence_metrics: Optional[Dict[str, Any]] = None
    
    processing_time_seconds: float = 0
    ai_model_version: Optional[str] = None
    
    @classmethod
    def from_analysis_result(cls, result: AnalysisResult) -> "CompleteAnalysisResult":
        """Convert new format to legacy format."""
        return cls(
            analysis_id=result.analysis_id,
            overall_score=result.overall_score,
            market_tier=result.market_tier.value if result.market_tier else "unknown",
            summary=result.analysis_summary or "",
            structure_analysis={
                "scores": result.structure_scores.dict() if result.structure_scores else {},
                "feedback": result.structure_feedback.dict() if result.structure_feedback else {},
                "metadata": {}
            },
            appeal_analysis={
                "scores": result.appeal_scores.dict() if result.appeal_scores else {},
                "feedback": result.appeal_feedback.dict() if result.appeal_feedback else {}
            },
            confidence_metrics=result.confidence_metrics.dict() if result.confidence_metrics else {},
            processing_time_seconds=result.processing_time_seconds or 0,
            ai_model_version=result.ai_model_version
        )