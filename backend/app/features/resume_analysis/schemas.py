"""Resume analysis Pydantic schemas for API requests/responses."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field, ConfigDict

# Import enums from database models to avoid duplication
from database.models.analysis import Industry, AnalysisStatus, MarketTier


class AnalysisDepth(str, Enum):
    """Analysis depth/complexity levels."""
    QUICK = "quick"        # Basic scoring, fast turnaround
    STANDARD = "standard"  # Full analysis with detailed feedback
    DEEP = "deep"         # Comprehensive analysis with section-level insights


# Pydantic Schemas
class AnalysisRequest(BaseModel):
    """Request to analyze an uploaded resume."""
    industry: Industry


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
    """Complete analysis result with granular scoring."""
    analysis_id: str
    overall_score: int = Field(..., ge=0, le=100)
    ats_score: int = Field(..., ge=0, le=100)
    content_score: int = Field(..., ge=0, le=100)
    formatting_score: int = Field(..., ge=0, le=100)
    industry: str

    # Executive summary and detailed breakdown
    executive_summary: Optional[str] = None
    detailed_scores: Optional[Dict[str, Any]] = None

    # Legacy fields for backward compatibility
    market_tier: Optional[MarketTier] = None
    structure_scores: Optional[ScoreDetails] = None
    appeal_scores: Optional[ScoreDetails] = None
    confidence_metrics: Optional[ConfidenceMetrics] = None
    structure_feedback: Optional[FeedbackSection] = None
    appeal_feedback: Optional[FeedbackSection] = None
    improvement_suggestions: Optional[List[str]] = None

    # Metadata
    processing_time_ms: Optional[int] = None
    ai_model_used: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    """API response for analysis request."""
    analysis_id: str
    status: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    """API response for analysis status check."""
    analysis_id: str
    status: str
    requested_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisSummary(BaseModel):
    """Summary view of an analysis for listings."""
    id: str
    file_name: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_id: Optional[str] = None
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
            summary=result.executive_summary or "",
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
            processing_time_seconds=(result.processing_time_ms or 0) / 1000,  # Convert ms to seconds
            ai_model_version=result.ai_model_used
        )