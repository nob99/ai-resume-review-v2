"""
Upload-related Pydantic models for API requests and responses.
Defines data structures for file upload operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


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