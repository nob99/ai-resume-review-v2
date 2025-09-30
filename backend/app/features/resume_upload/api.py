"""Resume upload API endpoints with candidate association."""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from database.models.auth import User
from app.core.rate_limiter import rate_limiter, RateLimitExceeded, RateLimitType

from .service import ResumeUploadService
from .schemas import (
    UploadedFileV2,
    FileUploadResponse,
    FileUploadListResponse
)
from database.models.resume import ResumeStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Dependency injection
async def get_resume_upload_service(session: AsyncSession = Depends(get_async_session)) -> ResumeUploadService:
    """Get resume upload service instance."""
    return ResumeUploadService(session)


async def get_resume_upload_repository(session: AsyncSession = Depends(get_async_session)):
    """Get resume upload repository instance."""
    from .repository import ResumeUploadRepository
    return ResumeUploadRepository(session)


@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=UploadedFileV2,
    summary="Upload resume for candidate",
    description="Upload a resume file (PDF, DOC, DOCX, TXT) for a specific candidate"
)
async def upload_resume(
    candidate_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: ResumeUploadService = Depends(get_resume_upload_service)
) -> UploadedFileV2:
    """
    Upload a resume for a specific candidate.

    - Links resume to candidate
    - Validates file type and size
    - Extracts text content
    - Manages version history
    - Returns upload status with extracted text
    """

    try:
        # Apply rate limiting
        is_allowed, rate_info = await rate_limiter.check_rate_limit(
            limit_type=RateLimitType.FILE_UPLOAD,
            identifier=str(current_user.id)
        )
        if not is_allowed:
            raise RateLimitExceeded("Upload rate limit exceeded")

        logger.info(f"User {current_user.id} uploading resume for candidate {candidate_id}: {file.filename}")

        # Process upload with candidate association
        result = await service.upload_resume(
            candidate_id=candidate_id,
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



# NOTE: Batch upload endpoint removed during refactoring
# Reason: Requires candidate_id for proper domain modeling (version management)
# Use POST /candidates/{candidate_id}/resumes for individual uploads
# TODO: Implement proper batch upload with candidate associations if needed


@router.get(
    "/{file_id}",
    response_model=FileUploadResponse,
    summary="Get upload details",
    description="Get details of a specific file upload"
)
async def get_upload(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repository = Depends(get_resume_upload_repository)
) -> FileUploadResponse:
    """Get details of a specific upload."""

    upload = await repository.get_by_id(file_id)
    if not upload or upload.uploaded_by_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Upload not found")

    return FileUploadResponse.model_validate(upload)


@router.get(
    "/",
    response_model=FileUploadListResponse,
    summary="List user uploads",
    description="Get list of user's file uploads with pagination"
)
async def list_uploads(
    status: Optional[ResumeStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    repository = Depends(get_resume_upload_repository)
) -> FileUploadListResponse:
    """List user's file uploads with optional filtering."""

    offset = (page - 1) * page_size

    # Get uploads from repository
    uploads = await repository.get_by_user(
        user_id=current_user.id,
        status=status,
        limit=page_size,
        offset=offset
    )

    # Get total count for pagination
    stats = await repository.get_upload_stats(current_user.id)

    return FileUploadListResponse(
        uploads=[FileUploadResponse.model_validate(u) for u in uploads],
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
    service: ResumeUploadService = Depends(get_resume_upload_service)
) -> JSONResponse:
    """Cancel an ongoing upload."""

    try:
        await service.cancel_upload(
            file_id=file_id,
            user_id=current_user.id
        )

        return JSONResponse(
            content={"message": "Upload cancelled successfully"},
            status_code=200
        )

    except ValueError as e:
        # Business rule violation (not found, not owned, or invalid state)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.get(
    "/stats/summary",
    summary="Get upload statistics",
    description="Get user's upload statistics"
)
async def get_upload_stats(
    current_user: User = Depends(get_current_user),
    repository = Depends(get_resume_upload_repository)
) -> dict:
    """Get upload statistics for the current user."""

    return await repository.get_upload_stats(current_user.id)