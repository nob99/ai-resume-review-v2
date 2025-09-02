"""
Upload-related Pydantic models for API requests and responses.
Defines data structures for file upload operations and text extraction.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# Define SectionType locally to avoid import issues
class SectionType(str, Enum):
    """Resume section types."""
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"


class UploadStatus(str, Enum):
    """Status of file upload/analysis."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperienceLevel(str, Enum):
    """Experience level options for resume analysis."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"


class FileUploadRequest(BaseModel):
    """Request model for file upload with analysis parameters."""
    target_role: Optional[str] = Field(
        None, 
        max_length=255,
        description="Target job role for analysis"
    )
    target_industry: Optional[str] = Field(
        None,
        max_length=255, 
        description="Target industry for analysis"
    )
    experience_level: Optional[ExperienceLevel] = Field(
        None,
        description="Experience level for tailored analysis"
    )


class FileValidationInfo(BaseModel):
    """File validation information."""
    is_valid: bool = Field(description="Whether file passed validation")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="Detected MIME type")
    file_extension: str = Field(description="File extension")
    file_hash: str = Field(description="SHA256 hash of file content")


class FileUploadResponse(BaseModel):
    """Response model for successful file upload."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="Unique analysis request ID")
    original_filename: str = Field(description="Original filename")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(description="File MIME type")
    status: UploadStatus = Field(description="Current processing status")
    target_role: Optional[str] = Field(description="Target job role")
    target_industry: Optional[str] = Field(description="Target industry")
    experience_level: Optional[ExperienceLevel] = Field(description="Experience level")
    created_at: datetime = Field(description="Upload timestamp")
    validation_info: FileValidationInfo = Field(description="File validation details")


class FileUploadError(BaseModel):
    """Error response for failed file upload."""
    error: str = Field(description="Error type")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    validation_errors: Optional[List[str]] = Field(default=None, description="File validation errors")


class UploadListResponse(BaseModel):
    """Response model for listing user's uploads."""
    uploads: List[FileUploadResponse] = Field(description="List of user uploads")
    total: int = Field(description="Total number of uploads")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    has_more: bool = Field(description="Whether more pages exist")


class UploadStatusResponse(BaseModel):
    """Response model for upload status check."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(description="Analysis request ID")
    status: UploadStatus = Field(description="Current status")
    original_filename: str = Field(description="Original filename")
    created_at: datetime = Field(description="Upload timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    progress_info: Optional[Dict[str, Any]] = Field(None, description="Processing progress info")


class UploadDeleteResponse(BaseModel):
    """Response model for upload deletion."""
    success: bool = Field(description="Whether deletion was successful")
    message: str = Field(description="Success or error message")
    id: UUID = Field(description="ID of deleted upload")


# Request/Response models for batch operations
class BulkDeleteRequest(BaseModel):
    """Request model for bulk deletion of uploads."""
    upload_ids: List[UUID] = Field(
        description="List of upload IDs to delete",
        min_length=1,
        max_length=50
    )


class BulkDeleteResponse(BaseModel):
    """Response model for bulk deletion."""
    total_requested: int = Field(description="Number of uploads requested for deletion")
    deleted: int = Field(description="Number of uploads successfully deleted")
    failed: int = Field(description="Number of uploads that failed to delete")
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of errors for failed deletions"
    )


# Statistics and analytics models
class UploadStats(BaseModel):
    """Statistics about user uploads."""
    total_uploads: int = Field(description="Total number of uploads")
    pending_uploads: int = Field(description="Number of pending uploads")
    completed_uploads: int = Field(description="Number of completed uploads")
    failed_uploads: int = Field(description="Number of failed uploads")
    total_storage_bytes: int = Field(description="Total storage used in bytes")
    most_recent_upload: Optional[datetime] = Field(None, description="Timestamp of most recent upload")
    file_type_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown by file type"
    )


class UploadStatsResponse(BaseModel):
    """Response model for upload statistics."""
    stats: UploadStats = Field(description="User upload statistics")
    rate_limit_info: Dict[str, Any] = Field(description="Current rate limit status")


# Admin-only models
class AdminUploadListResponse(BaseModel):
    """Admin response model for listing all uploads."""
    uploads: List[FileUploadResponse] = Field(description="List of all uploads")
    total: int = Field(description="Total number of uploads")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    has_more: bool = Field(description="Whether more pages exist")
    storage_stats: Dict[str, Any] = Field(description="System storage statistics")


class AdminStorageStats(BaseModel):
    """Admin model for system storage statistics."""
    total_files: int = Field(description="Total number of files")
    total_size_bytes: int = Field(description="Total storage used in bytes")
    files_by_status: Dict[str, int] = Field(description="File count by status")
    files_by_type: Dict[str, int] = Field(description="File count by type")
    average_file_size: float = Field(description="Average file size in bytes")
    oldest_file: Optional[datetime] = Field(None, description="Timestamp of oldest file")
    newest_file: Optional[datetime] = Field(None, description="Timestamp of newest file")
    files_to_cleanup: int = Field(description="Number of files eligible for cleanup")


# Text Extraction Models for UPLOAD-003

class TextExtractionRequest(BaseModel):
    """Request to extract text from uploaded file."""
    upload_id: UUID = Field(description="ID of uploaded file")
    force_reextraction: bool = Field(
        default=False, 
        description="Force re-extraction even if already completed"
    )
    timeout_seconds: int = Field(
        default=30, 
        ge=10, 
        le=300, 
        description="Maximum processing time in seconds"
    )


class ResumeSection(BaseModel):
    """Detected section in resume text."""
    section_type: str = Field(description="Type of section (contact, experience, etc.)")
    title: str = Field(description="Section title/header")
    content: str = Field(description="Section content")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    confidence: float = Field(description="Detection confidence score")


class TextExtractionResult(BaseModel):
    """Result of text extraction operation."""
    upload_id: UUID = Field(description="Upload ID")
    extraction_status: Optional[str] = Field(None, description="Extraction status")
    extracted_text: Optional[str] = Field(None, description="Raw extracted text")
    processed_text: Optional[str] = Field(None, description="Cleaned and processed text")
    sections: List[ResumeSection] = Field(default_factory=list, description="Detected resume sections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    word_count: int = Field(default=0, description="Number of words extracted")
    line_count: int = Field(default=0, description="Number of lines extracted")


class AIReadyData(BaseModel):
    """AI-ready structured data for resume analysis."""
    upload_id: UUID = Field(description="Upload ID")
    text_content: str = Field(description="Cleaned text content")
    structure: Dict[str, Any] = Field(description="Structured sections and metadata")
    extraction_info: Dict[str, Any] = Field(description="Extraction statistics and info")
    contact_info: Dict[str, List[str]] = Field(description="Extracted contact information")
    quality_assessment: str = Field(description="Text quality assessment (poor/fair/good)")
    generated_at: datetime = Field(description="When this data was generated")


class TextExtractionResponse(BaseModel):
    """Response for text extraction endpoint."""
    message: str = Field(description="Success message")
    extraction_result: TextExtractionResult = Field(description="Extraction results")


class TextExtractionStatusResponse(BaseModel):
    """Response for checking text extraction status."""
    upload_id: UUID = Field(description="Upload ID")
    extraction_status: str = Field(description="Current extraction status")
    has_extracted_text: bool = Field(description="Whether text has been extracted")
    has_processed_text: bool = Field(description="Whether text has been processed")
    sections_detected: int = Field(default=0, description="Number of sections detected")
    word_count: int = Field(default=0, description="Number of words extracted")
    error_message: Optional[str] = Field(None, description="Error message if applicable")
    last_updated: datetime = Field(description="Last update timestamp")


class UploadWithExtractionResponse(BaseModel):
    """Extended upload response including extraction status."""
    # Base upload fields
    id: UUID = Field(description="Upload ID")
    original_filename: str = Field(description="Original filename")
    file_size_bytes: int = Field(description="File size in bytes")
    mime_type: str = Field(description="File MIME type")
    status: UploadStatus = Field(description="Upload processing status")
    
    # Analysis parameters
    target_role: Optional[str] = Field(None, description="Target job role")
    target_industry: Optional[str] = Field(None, description="Target industry")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Experience level")
    
    # Extraction fields
    extraction_status: Optional[str] = Field(None, description="Text extraction status")
    has_extracted_text: bool = Field(description="Whether text extraction is complete")
    word_count: int = Field(default=0, description="Number of words extracted")
    sections_detected: int = Field(default=0, description="Number of resume sections detected")
    text_quality: Optional[str] = Field(None, description="Text quality assessment")
    
    # Timestamps
    created_at: datetime = Field(description="Upload creation time")
    updated_at: datetime = Field(description="Last update time")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if applicable")


class BatchTextExtractionRequest(BaseModel):
    """Request to extract text from multiple uploads."""
    upload_ids: List[UUID] = Field(description="List of upload IDs to process")
    force_reextraction: bool = Field(
        default=False, 
        description="Force re-extraction for all files"
    )
    timeout_seconds: int = Field(
        default=30, 
        ge=10, 
        le=300, 
        description="Timeout per file"
    )


class BatchTextExtractionResponse(BaseModel):
    """Response for batch text extraction."""
    total_requested: int = Field(description="Total files requested for extraction")
    successfully_started: int = Field(description="Files that started extraction")
    already_extracted: int = Field(description="Files already extracted (skipped)")
    failed_to_start: int = Field(description="Files that failed to start")
    results: List[TextExtractionResult] = Field(description="Individual extraction results")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")