"""
Review database models - replaces the old AnalysisRequest/AnalysisResult models.

Contains ReviewRequest, ReviewResult, and ReviewFeedbackItem models for the new review workflow.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from app.core.datetime_utils import utc_now


class ReviewStatus(str, Enum):
    """Review request status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperienceLevel(str, Enum):
    """Experience level enumeration."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"


class ReviewType(str, Enum):
    """Review type enumeration."""
    COMPREHENSIVE = "comprehensive"
    QUICK_SCAN = "quick_scan"
    ATS_CHECK = "ats_check"


class FeedbackType(str, Enum):
    """Feedback type enumeration."""
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    SUGGESTION = "suggestion"
    ERROR = "error"


class FeedbackCategory(str, Enum):
    """Feedback category enumeration."""
    CONTENT = "content"
    FORMATTING = "formatting"
    KEYWORDS = "keywords"
    GRAMMAR = "grammar"


class ReviewRequest(Base):
    """
    Review Request model - replaces AnalysisRequest.
    
    Represents a request to analyze a resume with AI agents.
    """
    
    __tablename__ = "review_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey('resumes.id'), nullable=False)
    requested_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    target_role = Column(String(255), nullable=True)
    target_industry = Column(String(100), nullable=True)
    experience_level = Column(String(20), nullable=True)
    review_type = Column(String(20), default='comprehensive')
    status = Column(String(20), default='pending')
    requested_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    resume = relationship("Resume", back_populates="review_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    review_result = relationship("ReviewResult", back_populates="review_request", uselist=False)
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate review status."""
        allowed_statuses = ['pending', 'processing', 'completed', 'failed']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return status
    
    @validates('review_type')
    def validate_review_type(self, key, review_type):
        """Validate review type."""
        allowed_types = ['comprehensive', 'quick_scan', 'ats_check']
        if review_type not in allowed_types:
            raise ValueError(f"Review type must be one of: {', '.join(allowed_types)}")
        return review_type
    
    @validates('experience_level')
    def validate_experience_level(self, key, experience_level):
        """Validate experience level."""
        if experience_level is not None:
            allowed_levels = ['entry', 'mid', 'senior', 'executive']
            if experience_level not in allowed_levels:
                raise ValueError(f"Experience level must be one of: {', '.join(allowed_levels)}")
        return experience_level
    
    @property
    def is_completed(self) -> bool:
        """Check if review is completed."""
        return self.status == 'completed' and self.completed_at is not None
    
    def mark_completed(self) -> None:
        """Mark review as completed."""
        self.status = 'completed'
        self.completed_at = utc_now()
    
    def mark_failed(self) -> None:
        """Mark review as failed."""
        self.status = 'failed'
        self.completed_at = utc_now()
    
    def __repr__(self) -> str:
        return f"<ReviewRequest(id={self.id}, resume_id={self.resume_id}, type='{self.review_type}', status='{self.status}')>"


class ReviewResult(Base):
    """
    Review Result model - replaces AnalysisResult.
    
    Stores the results of AI analysis with detailed scoring and feedback.
    """
    
    __tablename__ = "review_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_request_id = Column(UUID(as_uuid=True), ForeignKey('review_requests.id'), nullable=False)
    overall_score = Column(Integer, nullable=True)  # 0-100
    ats_score = Column(Integer, nullable=True)  # 0-100
    content_score = Column(Integer, nullable=True)  # 0-100
    formatting_score = Column(Integer, nullable=True)  # 0-100
    executive_summary = Column(Text, nullable=True)
    detailed_scores = Column(JSON, nullable=True)  # JSON object with detailed breakdowns
    raw_ai_response = Column(JSONB, nullable=True, doc="Complete raw AI response JSON for flexible frontend processing")
    ai_model_used = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    # Relationships
    review_request = relationship("ReviewRequest", back_populates="review_result")
    feedback_items = relationship("ReviewFeedbackItem", back_populates="review_result", cascade="all, delete-orphan")
    
    @validates('overall_score', 'ats_score', 'content_score', 'formatting_score')
    def validate_scores(self, key, score):
        """Validate score values."""
        if score is not None and (score < 0 or score > 100):
            raise ValueError(f"{key} must be between 0 and 100")
        return score
    
    @property
    def has_feedback(self) -> bool:
        """Check if result has feedback items."""
        return len(self.feedback_items) > 0
    
    def __repr__(self) -> str:
        return f"<ReviewResult(id={self.id}, overall_score={self.overall_score}, feedback_count={len(self.feedback_items)})>"


class ReviewFeedbackItem(Base):
    """
    Review Feedback Item model - provides section-level feedback.
    
    Links specific feedback to resume sections for precise highlighting and improvement suggestions.
    """
    
    __tablename__ = "review_feedback_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_result_id = Column(UUID(as_uuid=True), ForeignKey('review_results.id'), nullable=False)
    resume_section_id = Column(UUID(as_uuid=True), ForeignKey('resume_sections.id'), nullable=True)  # Optional - some feedback is general
    feedback_type = Column(String(20), nullable=False)  # strength, weakness, suggestion, error
    category = Column(String(20), nullable=False)  # content, formatting, keywords, grammar
    feedback_text = Column(Text, nullable=False)
    severity_level = Column(Integer, default=3)  # 1-5 (1=minor, 5=critical)
    original_text = Column(Text, nullable=True)  # Text being referenced
    suggested_text = Column(Text, nullable=True)  # Suggested improvement
    confidence_score = Column(Integer, nullable=True)  # 0-100 AI confidence
    
    # Relationships
    review_result = relationship("ReviewResult", back_populates="feedback_items")
    resume_section = relationship("ResumeSection", back_populates="feedback_items")
    
    @validates('feedback_type')
    def validate_feedback_type(self, key, feedback_type):
        """Validate feedback type."""
        allowed_types = ['strength', 'weakness', 'suggestion', 'error']
        if feedback_type not in allowed_types:
            raise ValueError(f"Feedback type must be one of: {', '.join(allowed_types)}")
        return feedback_type
    
    @validates('category')
    def validate_category(self, key, category):
        """Validate feedback category."""
        allowed_categories = ['content', 'formatting', 'keywords', 'grammar']
        if category not in allowed_categories:
            raise ValueError(f"Category must be one of: {', '.join(allowed_categories)}")
        return category
    
    @validates('severity_level')
    def validate_severity_level(self, key, severity_level):
        """Validate severity level."""
        if severity_level < 1 or severity_level > 5:
            raise ValueError("Severity level must be between 1 and 5")
        return severity_level
    
    @validates('confidence_score')
    def validate_confidence_score(self, key, confidence_score):
        """Validate confidence score."""
        if confidence_score is not None and (confidence_score < 0 or confidence_score > 100):
            raise ValueError("Confidence score must be between 0 and 100")
        return confidence_score
    
    @property
    def is_critical(self) -> bool:
        """Check if feedback is critical (severity 4 or 5)."""
        return self.severity_level >= 4
    
    def __repr__(self) -> str:
        return f"<ReviewFeedbackItem(type='{self.feedback_type}', category='{self.category}', severity={self.severity_level})>"