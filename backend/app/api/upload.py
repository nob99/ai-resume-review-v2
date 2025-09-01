"""
File upload API endpoints for resume processing.
Implements secure file upload with comprehensive validation and rate limiting.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.rate_limiter import check_file_upload_rate_limit
from app.services.file_service import store_uploaded_file, file_storage_service
from app.models.user import User
from app.models.upload import (
    FileUploadRequest,
    FileUploadResponse, 
    FileUploadError,
    FileValidationInfo,
    UploadListResponse,
    UploadStatusResponse,
    UploadDeleteResponse,
    UploadStats,
    UploadStatsResponse,
    ExperienceLevel,
    UploadStatus
)
from app.api.auth import get_current_user
from app.database.connection import get_db
from app.core.datetime_utils import utc_now

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/upload", tags=["File Upload"])


async def validate_upload_file(file: UploadFile) -> bytes:
    """
    Validate and read upload file content.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        File content bytes
        
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
        # Read file content
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Reset file pointer for potential re-reading
        await file.seek(0)
        
        return file_content
        
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
    db: Session = Depends(get_db)
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
    4. Database record creation
    5. Queue for AI analysis (future sprint)
    
    Args:
        request: FastAPI request object
        file: Uploaded resume file
        target_role: Optional target job role for analysis
        target_industry: Optional target industry for analysis  
        experience_level: Optional experience level for tailored analysis
        current_user: Authenticated user
        db: Database session
        
    Returns:
        FileUploadResponse with upload details and validation info
        
    Raises:
        HTTPException: If upload fails, validation fails, or rate limit exceeded
    """
    try:
        # 1. Check rate limiting
        logger.info(f"Processing file upload for user {current_user.email}: {file.filename}")
        await check_file_upload_rate_limit(request, str(current_user.id))
        
        # 2. Validate and read file content
        file_content = await validate_upload_file(file)
        
        logger.debug(f"File read successfully: {file.filename} ({len(file_content)} bytes)")
        
        # 3. Store file with validation
        storage_result = store_uploaded_file(
            file_content=file_content,
            original_filename=file.filename,
            user_id=str(current_user.id)
        )
        
        if not storage_result.success:
            logger.warning(f"File storage failed for {file.filename}: {storage_result.error_message}")
            
            # Return detailed validation errors if available
            if storage_result.validation_result and not storage_result.validation_result.is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "FILE_VALIDATION_FAILED",
                        "message": "File validation failed",
                        "validation_errors": storage_result.validation_result.errors
                    }
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=storage_result.error_message or "File storage failed"
            )
        
        # 4. Create database record
        # Note: Using raw SQL approach as shown in existing patterns
        # The analysis_requests table already exists from migration
        
        current_time = utc_now()
        
        try:
            # Create analysis request record
            insert_query = """
                INSERT INTO analysis_requests (
                    id, user_id, original_filename, file_path, file_size_bytes, 
                    mime_type, status, target_role, target_industry, experience_level,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id, created_at;
            """
            
            validation_result = storage_result.validation_result
            
            result = db.execute(insert_query, (
                str(current_user.id),
                file.filename,
                storage_result.file_path,
                validation_result.file_info['file_size'],
                validation_result.file_info['mime_type'],
                UploadStatus.PENDING.value,
                target_role,
                target_industry, 
                experience_level.value if experience_level else None,
                current_time,
                current_time
            ))
            
            row = result.fetchone()
            if not row:
                raise Exception("Failed to create analysis request record")
                
            request_id, created_at = row
            db.commit()
            
            logger.info(f"Analysis request created: {request_id} for user {current_user.email}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error creating analysis request: {str(e)}")
            
            # Clean up stored file on database error
            try:
                if storage_result.file_path:
                    file_storage_service.delete_file(storage_result.file_path)
            except:
                pass  # Don't fail the request on cleanup error
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create analysis request"
            )
        
        # 5. Build response
        validation_info = FileValidationInfo(
            is_valid=validation_result.is_valid,
            errors=validation_result.errors,
            warnings=validation_result.warnings,
            file_size=validation_result.file_info['file_size'],
            mime_type=validation_result.file_info['mime_type'],
            file_extension=validation_result.file_info['file_extension'],
            file_hash=validation_result.file_info['file_hash']
        )
        
        response = FileUploadResponse(
            id=request_id,
            original_filename=file.filename,
            file_size=validation_result.file_info['file_size'],
            mime_type=validation_result.file_info['mime_type'],
            status=UploadStatus.PENDING,
            target_role=target_role,
            target_industry=target_industry,
            experience_level=experience_level,
            created_at=created_at,
            validation_info=validation_info
        )
        
        logger.info(f"File upload completed successfully: {request_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed"
        )


@router.get("/list", response_model=UploadListResponse)
async def list_user_uploads(
    page: int = 1,
    per_page: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's uploaded files with pagination.
    
    Args:
        page: Page number (1-based)
        per_page: Items per page (max 100)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        UploadListResponse with paginated uploads
    """
    try:
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20
        
        offset = (page - 1) * per_page
        
        # Get total count
        count_query = """
            SELECT COUNT(*) FROM analysis_requests 
            WHERE user_id = %s
        """
        total_result = db.execute(count_query, (str(current_user.id),))
        total = total_result.scalar()
        
        # Get paginated results
        list_query = """
            SELECT id, original_filename, file_size_bytes, mime_type, status,
                   target_role, target_industry, experience_level, created_at, updated_at
            FROM analysis_requests 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """
        
        result = db.execute(list_query, (str(current_user.id), per_page, offset))
        
        uploads = []
        for row in result:
            upload = FileUploadResponse(
                id=row[0],
                original_filename=row[1],
                file_size=row[2],
                mime_type=row[3],
                status=UploadStatus(row[4]),
                target_role=row[5],
                target_industry=row[6],
                experience_level=ExperienceLevel(row[7]) if row[7] else None,
                created_at=row[8],
                validation_info=FileValidationInfo(
                    is_valid=True,  # Assume valid if stored
                    errors=[],
                    warnings=[],
                    file_size=row[2],
                    mime_type=row[3],
                    file_extension="",  # Would need to store this separately
                    file_hash=""  # Would need to store this separately
                )
            )
            uploads.append(upload)
        
        has_more = (offset + per_page) < total
        
        return UploadListResponse(
            uploads=uploads,
            total=total,
            page=page,
            per_page=per_page,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error listing uploads for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list uploads"
        )


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status of a specific upload.
    
    Args:
        upload_id: Upload ID to check
        current_user: Authenticated user
        db: Database session
        
    Returns:
        UploadStatusResponse with current status
    """
    try:
        # Get upload record
        query = """
            SELECT id, status, original_filename, created_at, updated_at, completed_at
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return UploadStatusResponse(
            id=row[0],
            status=UploadStatus(row[1]),
            original_filename=row[2],
            created_at=row[3],
            updated_at=row[4],
            completed_at=row[5],
            error_message=None,  # Would need additional field in DB
            progress_info=None   # Would need additional field in DB
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting upload status {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload status"
        )


@router.delete("/{upload_id}", response_model=UploadDeleteResponse)
async def delete_upload(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an uploaded file and its analysis.
    
    Args:
        upload_id: Upload ID to delete
        current_user: Authenticated user
        db: Database session
        
    Returns:
        UploadDeleteResponse with deletion status
    """
    try:
        # Get upload record including file path
        query = """
            SELECT id, file_path, original_filename
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        _, file_path, original_filename = row
        
        # Delete from database first
        delete_query = """
            DELETE FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        db.execute(delete_query, (str(upload_id), str(current_user.id)))
        db.commit()
        
        # Delete file from storage
        file_deleted = False
        if file_path:
            file_deleted = file_storage_service.delete_file(file_path)
            if not file_deleted:
                logger.warning(f"Failed to delete file {file_path} for upload {upload_id}")
        
        logger.info(f"Upload deleted: {upload_id} ({original_filename}) for user {current_user.email}")
        
        return UploadDeleteResponse(
            success=True,
            message=f"Upload '{original_filename}' deleted successfully",
            id=upload_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete upload"
        )


@router.get("/stats", response_model=UploadStatsResponse)
async def get_upload_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upload statistics for current user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        UploadStatsResponse with user statistics
    """
    try:
        # Get basic stats
        stats_query = """
            SELECT 
                COUNT(*) as total_uploads,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_uploads,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_uploads,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_uploads,
                COALESCE(SUM(file_size_bytes), 0) as total_storage_bytes,
                MAX(created_at) as most_recent_upload
            FROM analysis_requests 
            WHERE user_id = %s
        """
        
        result = db.execute(stats_query, (str(current_user.id),))
        row = result.fetchone()
        
        if row:
            total, pending, completed, failed, storage_bytes, recent = row
        else:
            total = pending = completed = failed = storage_bytes = 0
            recent = None
        
        # Get file type breakdown
        type_query = """
            SELECT mime_type, COUNT(*) 
            FROM analysis_requests 
            WHERE user_id = %s 
            GROUP BY mime_type
        """
        
        type_result = db.execute(type_query, (str(current_user.id),))
        file_type_breakdown = dict(type_result.fetchall())
        
        stats = UploadStats(
            total_uploads=total,
            pending_uploads=pending,
            completed_uploads=completed,
            failed_uploads=failed,
            total_storage_bytes=storage_bytes,
            most_recent_upload=recent,
            file_type_breakdown=file_type_breakdown
        )
        
        # Get rate limit info (placeholder for now)
        rate_limit_info = {
            "uploads_allowed_per_hour": 30,
            "uploads_remaining": 30,  # Would need to check actual rate limiter
            "reset_time": None
        }
        
        return UploadStatsResponse(
            stats=stats,
            rate_limit_info=rate_limit_info
        )
        
    except Exception as e:
        logger.error(f"Error getting upload stats for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upload statistics"
        )