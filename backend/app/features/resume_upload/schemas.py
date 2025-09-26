"""Resume upload Pydantic schemas for API requests/responses."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


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
    candidate_id: Optional[str] = None  # Added for candidate association
    filename: Optional[str] = None  # Added for compatibility
    file: FileInfo
    status: str  # Changed from FileStatus to str for flexibility
    progress: int = 0
    progressInfo: Optional[ProgressInfo] = None
    extracted_text: Optional[str] = None  # Support both naming conventions
    extractedText: Optional[str] = None  # Keep for backward compatibility
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