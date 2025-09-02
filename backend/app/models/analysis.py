"""
Analysis Request model for resume processing and text extraction.
Stores uploaded resume files and their processing status.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from app.core.datetime_utils import utc_now
from app.models.user import Base


class AnalysisStatus(str, Enum):
    """Status of analysis request processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionStatus(str, Enum):
    """Status of text extraction process."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AnalysisRequest(Base):
    """
    Analysis request model for resume processing.
    
    Stores uploaded resume files, their metadata, and processing status.
    Extended to support text extraction and structured processing.
    """
    
    __tablename__ = "analysis_requests"
    
    # Primary key and relationships
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    # file_hash = Column(String(64), nullable=True)  # SHA256 hash for integrity - Column doesn't exist in current DB
    
    # Analysis configuration
    target_role = Column(String(100), nullable=True)
    target_industry = Column(String(100), nullable=True)
    experience_level = Column(String(50), nullable=True)
    
    # Processing status
    status = Column(String(50), nullable=False, default=AnalysisStatus.PENDING.value)
    
    # Text extraction fields (NEW for UPLOAD-003) - COMMENTED OUT: columns don't exist in current DB
    # extraction_status = Column(String(50), nullable=False, default=ExtractionStatus.PENDING.value)
    # extracted_text = Column(Text, nullable=True)  # Raw extracted text
    # processed_text = Column(Text, nullable=True)  # Cleaned and structured text
    # extraction_metadata = Column(JSON, nullable=True)  # Processing metadata
    # ai_ready_data = Column(JSON, nullable=True)  # Structured data for AI processing
    
    # Processing metadata - COMMENTED OUT: columns don't exist in current DB
    # processing_started_at = Column(DateTime(timezone=True), nullable=True)
    # processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    # error_message = Column(Text, nullable=True)
    # error_details = Column(JSON, nullable=True)
    
    # Timestamps (matching actual database schema)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # This exists in DB
    
    # Results and analysis (for future AI processing) - COMMENTED OUT: columns don't exist in current DB
    # analysis_results = Column(JSON, nullable=True)
    # feedback_generated = Column(Boolean, nullable=False, default=False)
    
    # Relationship to user
    user = relationship("User", back_populates="analysis_requests")
    
    def __init__(
        self, 
        user_id: UUID,
        original_filename: str,
        file_path: str,
        file_size_bytes: int,
        mime_type: str,
        target_role: Optional[str] = None,
        target_industry: Optional[str] = None,
        experience_level: Optional[str] = None,
        **kwargs
    ):
        """Initialize analysis request."""
        super().__init__(**kwargs)
        
        self.user_id = user_id
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size_bytes = file_size_bytes
        self.mime_type = mime_type
        self.target_role = target_role
        self.target_industry = target_industry
        self.experience_level = experience_level
    
    def start_processing(self) -> None:
        """Mark request as processing started."""
        self.status = AnalysisStatus.PROCESSING.value
        # self.processing_started_at = utc_now()  # Column doesn't exist in current DB
    
    def complete_analysis(self) -> None:
        """Mark analysis as completed."""
        self.status = AnalysisStatus.COMPLETED.value
        self.completed_at = utc_now()  # Use the actual DB column
    
    def fail_analysis(self, error_message: str = None) -> None:
        """Mark analysis as failed."""
        self.status = AnalysisStatus.FAILED.value
        self.completed_at = utc_now()
        # self.error_message = error_message  # Column doesn't exist in current DB
    
    # All extraction-related methods commented out - fields don't exist in current DB
    # def start_extraction(self) -> None:
    # def complete_extraction(self, ...):
    # def fail_extraction(self, ...):
    # def is_extraction_complete(self) -> bool:
    
    def is_processing_complete(self) -> bool:
        """Check if processing is complete (success or failure)."""
        return self.status in [AnalysisStatus.COMPLETED.value, AnalysisStatus.FAILED.value]
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """
        Convert analysis request to dictionary (only actual DB fields).
        """
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "target_role": self.target_role,
            "target_industry": self.target_industry,
            "experience_level": self.experience_level,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        
        # All extraction/processing fields commented out - columns don't exist in current DB
        # if include_content:
        #     data.update({"extracted_text": self.extracted_text, ...})
        
        return data
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AnalysisRequest(id={self.id}, filename='{self.original_filename}', "
            f"status='{self.status}')>"
        )


# Pydantic models for API requests/responses

class TextExtractionResponse(BaseModel):
    """Response model for text extraction."""
    extraction_status: ExtractionStatus
    extracted_text: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class AnalysisRequestResponse(BaseModel):
    """Response model for analysis request."""
    id: UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    status: AnalysisStatus
    extraction_status: ExtractionStatus
    target_role: Optional[str] = None
    target_industry: Optional[str] = None
    experience_level: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    feedback_generated: bool
    processing_duration_seconds: Optional[float] = None
    
    class Config:
        from_attributes = True


class AnalysisRequestDetailResponse(AnalysisRequestResponse):
    """Detailed analysis request response with extracted content."""
    extracted_text: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    ai_ready_data: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class TextExtractionRequest(BaseModel):
    """Request to start text extraction for an uploaded file."""
    upload_id: UUID
    force_reextraction: bool = Field(default=False, description="Force re-extraction even if already completed")
    timeout_seconds: int = Field(default=30, ge=10, le=300, description="Extraction timeout in seconds")


class AIReadyDataResponse(BaseModel):
    """Response model for AI-ready structured data."""
    upload_id: UUID
    ai_ready_data: Dict[str, Any]
    extraction_metadata: Dict[str, Any]
    generated_at: datetime
    
    class Config:
        from_attributes = True