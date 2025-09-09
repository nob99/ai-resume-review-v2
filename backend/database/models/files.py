"""
File upload database models.

Contains FileUpload model for managing uploaded files and their processing status.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from . import Base
from app.core.datetime_utils import utc_now


class FileStatus(str, Enum):
    """File upload status enumeration."""
    PENDING = "pending"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class FileType(str, Enum):
    """Supported file types."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"


class FileUpload(Base):
    """File upload database model."""
    
    __tablename__ = "file_uploads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100))
    
    # Processing fields
    status = Column(String(50), default=FileStatus.PENDING)
    extracted_text = Column(Text)
    extraction_metadata = Column(JSON)  # word count, page count, etc.
    error_message = Column(Text)
    
    # Tracking fields
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    upload_started_at = Column(DateTime(timezone=True), default=utc_now)
    upload_completed_at = Column(DateTime(timezone=True))
    processing_time_ms = Column(Integer)
    
    # Relationships
    user = relationship("User", back_populates="file_uploads")
    analyses = relationship("ResumeAnalysis", back_populates="file_upload")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    
    def __repr__(self):
        return f"<FileUpload(id={self.id}, filename={self.filename}, status={self.status})>"