"""Resume feature schemas for API requests and responses."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class ResumeUploadRequest(BaseModel):
    """Request schema for uploading a resume to a candidate."""
    candidate_id: uuid.UUID = Field(..., description="ID of the candidate this resume belongs to")


class ResumeInfo(BaseModel):
    """Basic resume information schema."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    version_number: int
    status: str
    progress: int = Field(ge=0, le=100)
    word_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ResumeContent(BaseModel):
    """Resume with extracted content."""
    id: uuid.UUID
    candidate_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    version_number: int
    status: str
    progress: int
    extracted_text: Optional[str] = None
    word_count: Optional[int] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    """Response schema for resume upload."""
    success: bool
    message: str
    resume: Optional[ResumeInfo] = None
    error: Optional[str] = None


class ResumeListResponse(BaseModel):
    """Response schema for listing resumes."""
    resumes: List[ResumeInfo]
    total_count: int
    candidate_id: uuid.UUID


class ResumeStats(BaseModel):
    """Resume statistics for a candidate."""
    candidate_id: uuid.UUID
    total_resumes: int
    completed_resumes: int
    failed_resumes: int
    total_size_bytes: int
    total_size_mb: float
    latest_version: int


class ResumeStatsResponse(BaseModel):
    """Response schema for resume statistics."""
    stats: ResumeStats


class ResumeVersionInfo(BaseModel):
    """Information about resume versions."""
    version_number: int
    uploaded_at: datetime
    file_size: int
    status: str
    word_count: Optional[int] = None


class ResumeVersionHistory(BaseModel):
    """Complete version history for a candidate's resumes."""
    candidate_id: uuid.UUID
    versions: List[ResumeVersionInfo]
    total_versions: int
    
    
# Request/Response schemas for candidate context
class CandidateResumeRequest(BaseModel):
    """Base request with candidate context."""
    candidate_id: uuid.UUID
    
    
class CandidateResumeListRequest(CandidateResumeRequest):
    """Request to list resumes for a candidate."""
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    
    
class ProcessingStatus(BaseModel):
    """Resume processing status information."""
    resume_id: uuid.UUID
    status: str
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# Error response schemas
class ResumeErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    resume_id: Optional[uuid.UUID] = None


# File validation schemas
class FileValidationError(BaseModel):
    """File validation error details."""
    field: str
    message: str
    received: Optional[str] = None
    expected: Optional[str] = None


class ResumeValidationResponse(BaseModel):
    """Resume validation response."""
    valid: bool
    errors: List[FileValidationError] = []
    warnings: List[str] = []