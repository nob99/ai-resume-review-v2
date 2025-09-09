"""File upload models and schemas for AI Resume Review Platform."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict

from app.database.base import Base
from app.core.datetime_utils import utc_now


# Enums
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


# SQLAlchemy Models
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


# Pydantic Schemas
class FileInfo(BaseModel):
    """File information schema."""
    name: str
    size: int
    type: str
    lastModified: int


class ProgressInfo(BaseModel):
    """Upload progress information."""
    fileId: str
    fileName: str
    stage: str
    percentage: float = 0
    bytesUploaded: int = 0
    totalBytes: int
    timeElapsed: int = 0
    estimatedTimeRemaining: int = 0
    speed: float = 0
    retryCount: int = 0
    maxRetries: int = 3


class CancellationToken(BaseModel):
    """Cancellation token for upload."""
    fileId: str
    timestamp: int


class UploadedFileV2(BaseModel):
    """Frontend-compatible uploaded file schema."""
    id: str
    file: FileInfo
    status: FileStatus
    progress: int = 0
    progressInfo: Optional[ProgressInfo] = None
    extractedText: Optional[str] = None
    error: Optional[str] = None
    startTime: Optional[int] = None
    endTime: Optional[int] = None
    cancellationToken: Optional[CancellationToken] = None
    
    model_config = ConfigDict(from_attributes=True)


class FileUploadRequest(BaseModel):
    """File upload request schema."""
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: FileType
    file_size: int = Field(..., gt=0, le=10485760)  # Max 10MB
    mime_type: Optional[str] = None


class FileUploadResponse(BaseModel):
    """File upload response schema."""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: FileStatus
    extracted_text: Optional[str] = None
    extraction_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    processing_time_ms: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_orm(cls, db_obj: FileUpload) -> "FileUploadResponse":
        """Create response from database object."""
        return cls(
            id=str(db_obj.id),
            filename=db_obj.filename,
            file_type=db_obj.file_type,
            file_size=db_obj.file_size,
            status=db_obj.status,
            extracted_text=db_obj.extracted_text,
            extraction_metadata=db_obj.extraction_metadata,
            created_at=db_obj.created_at,
            processing_time_ms=db_obj.processing_time_ms
        )


class FileUploadListResponse(BaseModel):
    """List of file uploads response."""
    uploads: list[FileUploadResponse]
    total_count: int
    page: int = 1
    page_size: int = 10


class FileValidationError(BaseModel):
    """File validation error details."""
    field: str
    message: str
    code: str