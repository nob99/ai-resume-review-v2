"""
Resume analysis database models.

Contains ResumeAnalysis model for storing AI analysis results.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from backend.app.core.datetime_utils import utc_now


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