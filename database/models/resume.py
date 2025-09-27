"""
Resume database model - replaces the old FileUpload model.

Contains the Resume model that represents uploaded resume files with candidate relationship.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from app.core.datetime_utils import utc_now


class ResumeStatus(str, Enum):
    """Resume processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class Resume(Base):
    """
    Resume model - replaces FileUpload in the new candidate-centric architecture.
    
    Key differences from old FileUpload:
    - Links to candidate (not just user)
    - Supports versioning (multiple resumes per candidate)
    - Simplified status tracking
    - Designed for section-level analysis
    """
    
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256 hash - allows duplicates for resume iterations
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    version_number = Column(Integer, default=1, nullable=False)  # Version tracking
    status = Column(String(20), default='pending')
    progress = Column(Integer, default=0)  # 0-100 processing progress
    extracted_text = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships  
    candidate = relationship("Candidate", back_populates="resumes")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")
    review_requests = relationship("ReviewRequest", back_populates="resume")
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate resume status."""
        allowed_statuses = ['pending', 'processing', 'completed', 'error']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return status
    
    @validates('progress')
    def validate_progress(self, key, progress):
        """Validate progress percentage."""
        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")
        return progress
    
    @validates('version_number')
    def validate_version_number(self, key, version_number):
        """Validate version number."""
        if version_number < 1:
            raise ValueError("Version number must be >= 1")
        return version_number
    
    @property
    def is_processed(self) -> bool:
        """Check if resume has been successfully processed."""
        return self.status == 'completed' and self.extracted_text is not None
    
    @property
    def file_extension(self) -> str:
        """Get file extension from original filename."""
        return self.original_filename.split('.')[-1].lower() if '.' in self.original_filename else ''
    
    def mark_completed(self, extracted_text: str, word_count: Optional[int] = None) -> None:
        """Mark resume as completed with extracted content."""
        self.status = 'completed'
        self.progress = 100
        self.extracted_text = extracted_text
        self.word_count = word_count or len(extracted_text.split())
        self.processed_at = utc_now()
    
    def mark_error(self, error_message: Optional[str] = None) -> None:
        """Mark resume processing as failed."""
        self.status = 'error'
        # Error message could be stored in a separate field if needed
    
    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, candidate_id={self.candidate_id}, filename='{self.original_filename}', version={self.version_number}, status='{self.status}')>"