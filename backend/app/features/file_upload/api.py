"""File upload API endpoints."""

import uuid
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.connection import get_db
from app.features.auth.api import get_current_user
from database.models.auth import User
from app.core.rate_limiter import rate_limiter, RateLimitExceeded

from .service import FileUploadService
from .schemas import (
    UploadedFileV2,
    FileUploadResponse,
    FileUploadListResponse
)
from database.models.files import FileStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Dependency injection
def get_file_upload_service(db: Session = Depends(get_db)) -> FileUploadService:
    """Get file upload service instance."""
    return FileUploadService(db)


@router.post(
    "/upload",
    response_model=UploadedFileV2,
    summary="Upload a single file",
    description="Upload a resume file (PDF, DOC, DOCX, TXT) for processing"
)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> UploadedFileV2:
    """
    Upload a single resume file.
    
    - Validates file type and size
    - Extracts text content
    - Returns upload status with extracted text
    """
    
    try:
        # Apply rate limiting
        await rate_limiter.check_rate_limit(
            key=f"upload:{current_user.id}",
            max_requests=10,
            window_seconds=60
        )
        
        logger.info(f"User {current_user.id} uploading file: {file.filename}")
        
        # Process upload
        result = await service.process_upload(
            file=file,
            user_id=current_user.id
        )
        
        logger.info(f"File upload successful: {result.id}")
        return result
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Too many upload requests. Please wait before uploading more files."
        )
    except ValueError as e:
        logger.warning(f"File validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.post(
    "/batch",
    response_model=List[UploadedFileV2],
    summary="Upload multiple files",
    description="Upload multiple resume files at once"
)
async def upload_files_batch(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> List[UploadedFileV2]:
    """
    Upload multiple resume files.
    
    - Processes files concurrently
    - Returns status for each file
    - Maximum 5 files per request
    """
    
    if len(files) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 files can be uploaded at once"
        )
    
    try:
        # Apply rate limiting
        await rate_limiter.check_rate_limit(
            key=f"batch_upload:{current_user.id}",
            max_requests=2,
            window_seconds=60
        )
        
        results = []
        errors = []
        
        for file in files:
            try:
                result = await service.process_upload(
                    file=file,
                    user_id=current_user.id
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to upload {file.filename}: {str(e)}")
                errors.append({"file": file.filename, "error": str(e)})
        
        if errors and not results:
            raise HTTPException(
                status_code=400,
                detail={"message": "All files failed to upload", "errors": errors}
            )
        
        return results
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Too many batch upload requests. Please wait."
        )


@router.get(
    "/{file_id}",
    response_model=FileUploadResponse,
    summary="Get upload details",
    description="Get details of a specific file upload"
)
async def get_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> FileUploadResponse:
    """Get details of a specific upload."""
    
    upload = await service.get_upload(file_id, current_user.id)
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return upload


@router.get(
    "/",
    response_model=FileUploadListResponse,
    summary="List user uploads",
    description="Get list of user's file uploads with pagination"
)
async def list_uploads(
    status: Optional[FileStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> FileUploadListResponse:
    """List user's file uploads with optional filtering."""
    
    offset = (page - 1) * page_size
    
    uploads = await service.get_user_uploads(
        user_id=current_user.id,
        status=status,
        limit=page_size,
        offset=offset
    )
    
    # Get total count for pagination
    stats = await service.get_upload_stats(current_user.id)
    
    return FileUploadListResponse(
        uploads=uploads,
        total_count=stats["total_uploads"],
        page=page,
        page_size=page_size
    )


@router.delete(
    "/{file_id}/cancel",
    summary="Cancel upload",
    description="Cancel an ongoing file upload"
)
async def cancel_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> JSONResponse:
    """Cancel an ongoing upload."""
    
    success = await service.cancel_upload(file_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Unable to cancel upload. It may be already completed or not found."
        )
    
    return JSONResponse(
        content={"message": "Upload cancelled successfully"},
        status_code=200
    )


@router.get(
    "/stats/summary",
    summary="Get upload statistics",
    description="Get user's upload statistics"
)
async def get_upload_stats(
    current_user: User = Depends(get_current_user),
    service: FileUploadService = Depends(get_file_upload_service)
) -> dict:
    """Get upload statistics for the current user."""
    
    return await service.get_upload_stats(current_user.id)