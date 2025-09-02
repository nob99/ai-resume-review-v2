"""
File upload API endpoints for resume processing.
Implements secure file upload with comprehensive validation and rate limiting.
REFACTORED: Now uses Repository pattern and ORM instead of raw SQL.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form, Query

from app.core.rate_limiter import check_file_upload_rate_limit
from app.models.user import User
from app.models.upload import (
    FileUploadResponse, 
    FileValidationInfo,
    UploadListResponse,
    UploadStatusResponse,
    UploadDeleteResponse,
    UploadStats,
    UploadStatsResponse,
    ExperienceLevel,
    # Text extraction models
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionStatusResponse,
    AIReadyData
)
from app.api.auth import get_current_user
from app.services.upload_service import get_upload_service, UploadService, UploadServiceError

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/upload", tags=["File Upload"])


async def validate_upload_file(file: UploadFile) -> None:
    """
    Validate upload file.
    
    Args:
        file: FastAPI UploadFile object
        
    Raises:
        HTTPException: If file validation fails
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    try:
        # Read file content for validation
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Reset file pointer for service layer
        await file.seek(0)
        
    except Exception as e:
        logger.error(f"Error reading uploaded file {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file"
        )


@router.post("/resume", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    request: Request,
    file: UploadFile = File(..., description="Resume file (PDF, DOC, or DOCX)"),
    target_role: Optional[str] = Form(None, description="Target job role"),
    target_industry: Optional[str] = Form(None, description="Target industry"),
    experience_level: Optional[ExperienceLevel] = Form(None, description="Experience level"),
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Upload resume file for AI analysis.
    
    This endpoint accepts resume files and stores them securely for processing.
    
    **Features:**
    - Supports PDF, DOC, and DOCX files
    - Maximum file size: 30MB
    - Comprehensive validation (file type, size, content)
    - Rate limited: 30 uploads per hour
    - Secure UUID-based file storage
    - Integration with analysis pipeline
    
    **Process:**
    1. Rate limit check (30 uploads/hour)
    2. File validation (type, size, structure)
    3. Secure storage with UUID naming
    4. Database record creation (using ORM)
    5. Queue for text extraction
    
    Args:
        request: FastAPI request object
        file: Uploaded resume file
        target_role: Optional target job role for analysis
        target_industry: Optional target industry for analysis  
        experience_level: Optional experience level for tailored analysis
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        FileUploadResponse with upload details and validation info
        
    Raises:
        HTTPException: If upload fails or validation errors occur
        HTTP 400: File validation failed
        HTTP 429: Rate limit exceeded
        HTTP 413: File too large
        HTTP 500: Server error
    """
    logger.info(f"Resume upload requested by user {current_user.id}: {file.filename}")
    
    try:
        # Step 1: Rate limiting check
        await check_file_upload_rate_limit(request, current_user.id)
        
        # Step 2: Basic file validation
        await validate_upload_file(file)
        
        # Step 3: Use service layer for business logic
        upload_result = await upload_service.create_upload(
            file=file,
            user=current_user,
            target_role=target_role,
            target_industry=target_industry,
            experience_level=experience_level
        )
        
        logger.info(f"Upload completed successfully: {upload_result['id']}")
        
        # Step 4: Return structured response
        return FileUploadResponse(
            id=upload_result["id"],
            original_filename=upload_result["original_filename"],
            file_size_bytes=upload_result["file_size_bytes"],
            mime_type=upload_result["mime_type"],
            status=upload_result["status"],
            target_role=upload_result["target_role"],
            target_industry=upload_result["target_industry"],
            experience_level=upload_result["experience_level"],
            created_at=upload_result["created_at"],
            validation_info=FileValidationInfo(
                is_valid=True,
                file_type=upload_result["mime_type"],
                file_size_mb=round(upload_result["file_size_bytes"] / (1024 * 1024), 2),
                validation_details="File uploaded and validated successfully"
            ),
            message=upload_result["message"]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors, rate limits)
        raise
    except UploadServiceError as e:
        logger.error(f"Upload service error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed due to server error"
        )


@router.get("/list", response_model=UploadListResponse)
async def list_uploads(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[List[str]] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    List user's uploaded files with pagination and filtering.
    
    **Features:**
    - Paginated results (default: 20 per page)
    - Status filtering (pending, processing, completed, failed)
    - Ordered by upload date (newest first)
    - User isolation (only see own uploads)
    
    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        status: Optional status filter
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        UploadListResponse with uploads and pagination info
    """
    logger.info(f"Listing uploads for user {current_user.id}, page {page}")
    
    try:
        result = upload_service.list_uploads(
            user=current_user,
            page=page,
            per_page=per_page,
            status_filter=status
        )
        
        return UploadListResponse(
            uploads=[
                UploadStatusResponse(
                    id=upload["id"],
                    original_filename=upload["original_filename"],
                    file_size_bytes=upload["file_size_bytes"],
                    mime_type=upload["mime_type"],
                    status=upload["status"],
                    extraction_status=upload.get("extraction_status"),
                    target_role=upload.get("target_role"),
                    target_industry=upload.get("target_industry"),
                    experience_level=upload.get("experience_level"),
                    created_at=upload["created_at"],
                    updated_at=upload["updated_at"],
                    processing_started_at=upload.get("processing_started_at"),
                    processing_completed_at=upload.get("processing_completed_at"),
                    error_message=upload.get("error_message")
                ) for upload in result["uploads"]
            ],
            pagination=result["pagination"]
        )
        
    except Exception as e:
        logger.error(f"Error listing uploads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve uploads"
        )


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Get detailed status for a specific upload.
    
    **Features:**
    - Processing status tracking
    - Error information if failed
    - Timestamps for all stages
    - User ownership validation
    
    Args:
        upload_id: Upload UUID
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        UploadStatusResponse with detailed status
        
    Raises:
        HTTP 404: Upload not found or not owned by user
    """
    logger.info(f"Status check for upload {upload_id} by user {current_user.id}")
    
    try:
        upload = upload_service.get_upload(upload_id, current_user)
        
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return UploadStatusResponse(
            id=upload["id"],
            original_filename=upload["original_filename"],
            file_size_bytes=upload["file_size_bytes"],
            mime_type=upload["mime_type"],
            status=upload["status"],
            extraction_status=upload.get("extraction_status"),
            target_role=upload.get("target_role"),
            target_industry=upload.get("target_industry"),
            experience_level=upload.get("experience_level"),
            created_at=upload["created_at"],
            updated_at=upload["updated_at"],
            processing_started_at=upload.get("processing_started_at"),
            processing_completed_at=upload.get("processing_completed_at"),
            error_message=upload.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload status"
        )


@router.delete("/{upload_id}", response_model=UploadDeleteResponse)
async def delete_upload(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Delete an uploaded file and its analysis data.
    
    **Features:**
    - Removes file from storage
    - Deletes database record
    - User ownership validation
    - Complete cleanup
    
    Args:
        upload_id: Upload UUID
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        UploadDeleteResponse with success status
        
    Raises:
        HTTP 404: Upload not found or not owned by user
    """
    logger.info(f"Delete request for upload {upload_id} by user {current_user.id}")
    
    try:
        success = upload_service.delete_upload(upload_id, current_user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return UploadDeleteResponse(
            id=upload_id,
            message="Upload deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete upload"
        )


@router.get("/statistics", response_model=UploadStatsResponse)
async def get_upload_statistics(
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Get comprehensive upload statistics for the user.
    
    **Features:**
    - Total upload count
    - Status breakdown
    - File type statistics
    - Storage usage
    - Recent activity
    
    Args:
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        UploadStatsResponse with comprehensive statistics
    """
    logger.info(f"Statistics request for user {current_user.id}")
    
    try:
        stats = upload_service.get_user_statistics(current_user)
        
        return UploadStatsResponse(
            user_id=current_user.id,
            stats=UploadStats(
                total_uploads=stats["total_uploads"],
                successful_uploads=stats["status_breakdown"].get("completed", 0),
                failed_uploads=stats["status_breakdown"].get("failed", 0),
                pending_uploads=stats["status_breakdown"].get("pending", 0),
                processing_uploads=stats["status_breakdown"].get("processing", 0),
                total_storage_bytes=stats["total_storage_bytes"],
                total_storage_mb=round(stats["total_storage_bytes"] / (1024 * 1024), 2),
                file_type_breakdown=stats["file_type_breakdown"],
                recent_uploads_30_days=stats["recent_uploads_30_days"]
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting upload statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload statistics"
        )


# === TEXT EXTRACTION ENDPOINTS ===

@router.post("/{upload_id}/extract-text", response_model=TextExtractionResponse)
async def start_text_extraction(
    upload_id: UUID,
    request: TextExtractionRequest,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Start or restart text extraction for an uploaded file.
    
    **Features:**
    - Asynchronous text extraction
    - Progress tracking
    - Force re-extraction option
    - Multiple file format support
    
    Args:
        upload_id: Upload UUID
        request: Extraction configuration
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        TextExtractionResponse with job status
        
    Raises:
        HTTP 404: Upload not found
        HTTP 400: Invalid request
    """
    logger.info(f"Text extraction request for upload {upload_id} by user {current_user.id}")
    
    try:
        result = await upload_service.start_text_extraction(
            upload_id=upload_id,
            user=current_user,
            force_reextraction=request.force_reextraction
        )
        
        return TextExtractionResponse(
            upload_id=result["upload_id"],
            extraction_status=result["extraction_status"],
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting text extraction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start text extraction"
        )


@router.get("/{upload_id}/extraction-status", response_model=TextExtractionStatusResponse)
async def get_extraction_status(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Get text extraction status and results.
    
    **Features:**
    - Real-time status updates
    - Extracted text content
    - Processing metadata
    - Error information
    
    Args:
        upload_id: Upload UUID
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        TextExtractionStatusResponse with status and results
        
    Raises:
        HTTP 404: Upload not found
    """
    logger.info(f"Extraction status check for upload {upload_id} by user {current_user.id}")
    
    try:
        result = upload_service.get_extraction_result(upload_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return TextExtractionStatusResponse(
            upload_id=result["id"],
            extraction_status=result["extraction_status"],
            extracted_text=result.get("extracted_text"),
            processing_metadata=result.get("extraction_metadata"),
            error_message=result.get("error_message"),
            updated_at=result["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get extraction status"
        )


@router.get("/{upload_id}/ai-ready-data", response_model=AIReadyData)
async def get_ai_ready_data(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    upload_service: UploadService = Depends(get_upload_service)
):
    """
    Get AI-ready structured data from extracted resume.
    
    **Features:**
    - Structured resume sections
    - Clean text formatting
    - Metadata preservation
    - Ready for AI processing
    
    Args:
        upload_id: Upload UUID
        current_user: Authenticated user
        upload_service: Upload service instance
        
    Returns:
        AIReadyData with structured resume information
        
    Raises:
        HTTP 404: Upload not found or data not ready
        HTTP 400: Text extraction not completed
    """
    logger.info(f"AI-ready data request for upload {upload_id} by user {current_user.id}")
    
    try:
        result = upload_service.get_ai_ready_data(upload_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found or AI-ready data not available"
            )
        
        return AIReadyData(
            upload_id=result["upload_id"],
            structured_data=result["ai_ready_data"],
            extraction_metadata=result["extraction_metadata"],
            generated_at=result["generated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI-ready data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI-ready data"
        )


# Export router
__all__ = ["router"]