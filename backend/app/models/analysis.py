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

# Re-use Base from user model to ensure same declarative base
# Base = declarative_base()  # Already imported from user.py


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
    file_hash = Column(String(64), nullable=True)  # SHA256 hash for integrity
    
    # Analysis configuration
    target_role = Column(String(100), nullable=True)
    target_industry = Column(String(100), nullable=True)
    experience_level = Column(String(50), nullable=True)
    
    # Processing status
    status = Column(String(50), nullable=False, default=AnalysisStatus.PENDING.value)
    
    # Text extraction fields (NEW for UPLOAD-003)
    extraction_status = Column(String(50), nullable=False, default=ExtractionStatus.PENDING.value)
    extracted_text = Column(Text, nullable=True)  # Raw extracted text
    processed_text = Column(Text, nullable=True)  # Cleaned and structured text
    extraction_metadata = Column(JSON, nullable=True)  # Processing metadata
    ai_ready_data = Column(JSON, nullable=True)  # Structured data for AI processing
    
    # Processing metadata
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    
    # Results and analysis (for future AI processing)
    analysis_results = Column(JSON, nullable=True)
    feedback_generated = Column(Boolean, nullable=False, default=False)
    
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
        file_hash: Optional[str] = None,
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
        self.file_hash = file_hash
    
    def start_processing(self) -> None:
        """Mark request as processing started."""
        self.status = AnalysisStatus.PROCESSING.value
        self.processing_started_at = utc_now()
    
    def start_extraction(self) -> None:
        """Mark text extraction as started."""
        self.extraction_status = ExtractionStatus.PROCESSING.value
        if not self.processing_started_at:
            self.processing_started_at = utc_now()
    
    def complete_extraction(
        self, 
        extracted_text: str, 
        processed_text: str, 
        extraction_metadata: Dict[str, Any],
        ai_ready_data: Dict[str, Any]
    ) -> None:
        """Mark text extraction as completed."""
        self.extraction_status = ExtractionStatus.COMPLETED.value
        self.extracted_text = extracted_text
        self.processed_text = processed_text
        self.extraction_metadata = extraction_metadata
        self.ai_ready_data = ai_ready_data
        self.error_message = None
        self.error_details = None
    
    def fail_extraction(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark text extraction as failed."""
        self.extraction_status = ExtractionStatus.FAILED.value
        self.error_message = error_message
        self.error_details = error_details
    
    def complete_analysis(self, analysis_results: Dict[str, Any]) -> None:
        """Mark analysis as completed."""
        self.status = AnalysisStatus.COMPLETED.value
        self.processing_completed_at = utc_now()
        self.analysis_results = analysis_results
        self.feedback_generated = True
    
    def fail_analysis(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark analysis as failed."""
        self.status = AnalysisStatus.FAILED.value
        self.processing_completed_at = utc_now()
        self.error_message = error_message
        self.error_details = error_details
    
    def is_processing_complete(self) -> bool:
        """Check if processing is complete (success or failure)."""
        return self.status in [AnalysisStatus.COMPLETED.value, AnalysisStatus.FAILED.value]
    
    def is_extraction_complete(self) -> bool:
        """Check if text extraction is complete (success or failure)."""
        return self.extraction_status in [
            ExtractionStatus.COMPLETED.value, 
            ExtractionStatus.FAILED.value,
            ExtractionStatus.TIMEOUT.value
        ]
    
    def get_processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """
        Convert analysis request to dictionary.
        
        Args:
            include_content: Whether to include extracted text content
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
            "extraction_status": self.extraction_status,
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "error_message": self.error_message,
            "feedback_generated": self.feedback_generated,
            "processing_duration_seconds": self.get_processing_duration()
        }
        
        if include_content:
            data.update({
                "extracted_text": self.extracted_text,
                "processed_text": self.processed_text,
                "extraction_metadata": self.extraction_metadata,
                "ai_ready_data": self.ai_ready_data,
                "analysis_results": self.analysis_results,
                "error_details": self.error_details
            })
        
        return data
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<AnalysisRequest(id={self.id}, filename='{self.original_filename}', "
            f"status='{self.status}', extraction_status='{self.extraction_status}')>"
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