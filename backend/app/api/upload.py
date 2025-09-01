"""
File upload API endpoints for resume processing.
Implements secure file upload with comprehensive validation and rate limiting.
"""

import logging
from typing import List, Optional, Dict, Any
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
    UploadStatus,
    # Text extraction models
    TextExtractionRequest,
    TextExtractionResponse,
    TextExtractionResult,
    TextExtractionStatusResponse,
    UploadWithExtractionResponse,
    AIReadyData,
    BatchTextExtractionRequest,
    BatchTextExtractionResponse,
    ResumeSection
)
from app.api.auth import get_current_user
from app.database.connection import get_db
from app.core.datetime_utils import utc_now
from app.services.text_extraction_service import text_extraction_service, ExtractionStatus
from app.core.text_processor import text_processor
from app.core.file_validation import get_file_info
from app.core.background_processor import background_processor, JobPriority, JobStatus
from app.core.extraction_cache import extraction_cache
from pathlib import Path

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


# =============================================================================
# TEXT EXTRACTION ENDPOINTS (UPLOAD-003)
# =============================================================================

@router.post("/{upload_id}/extract-text", 
            response_model=TextExtractionResponse,
            summary="Extract text from uploaded resume",
            description="Start text extraction process for an uploaded file")
async def extract_text_from_upload(
    upload_id: UUID,
    extraction_request: Optional[TextExtractionRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TextExtractionResponse:
    """
    Extract text from an uploaded resume file.
    
    Performs comprehensive text extraction including:
    - Raw text extraction from PDF/DOCX/DOC files
    - Text cleaning and normalization
    - Section detection (Contact, Experience, Education, etc.)
    - AI-ready data formatting
    
    Args:
        upload_id: ID of the uploaded file
        extraction_request: Optional extraction parameters
        current_user: Authenticated user
        db: Database session
        
    Returns:
        TextExtractionResponse with extraction results
    """
    logger.info(f"Starting text extraction for upload {upload_id} by user {current_user.id}")
    
    try:
        # Get upload record with current extraction status
        query = """
            SELECT id, file_path, original_filename, mime_type, extraction_status, 
                   extracted_text, processed_text, extraction_metadata
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found or access denied"
            )
        
        upload_uuid, file_path, original_filename, mime_type, current_extraction_status, \
        existing_extracted_text, existing_processed_text, existing_metadata = row
        
        # Check if re-extraction is needed
        force_reextraction = extraction_request.force_reextraction if extraction_request else False
        
        if (current_extraction_status == ExtractionStatus.COMPLETED.value and 
            existing_extracted_text and not force_reextraction):
            # Return existing results
            logger.info(f"Text already extracted for upload {upload_id}, returning cached results")
            
            # Convert existing metadata to expected format
            sections = []
            if existing_metadata and "structure" in existing_metadata:
                for section_data in existing_metadata["structure"].get("sections", []):
                    sections.append(ResumeSection(
                        section_type=section_data.get("type", "other"),
                        title=section_data.get("title", ""),
                        content=section_data.get("content", ""),
                        line_start=section_data.get("position", {}).get("line_start", 0),
                        line_end=section_data.get("position", {}).get("line_end", 0),
                        confidence=section_data.get("confidence", 0.0)
                    ))
            
            extraction_result = TextExtractionResult(
                upload_id=upload_id,
                extraction_status=ExtractionStatus.COMPLETED,
                extracted_text=existing_extracted_text,
                processed_text=existing_processed_text,
                sections=sections,
                metadata=existing_metadata or {},
                word_count=len(existing_processed_text.split()) if existing_processed_text else 0,
                line_count=len(existing_processed_text.splitlines()) if existing_processed_text else 0
            )
            
            return TextExtractionResponse(
                message="Text extraction completed (cached)",
                extraction_result=extraction_result
            )
        
        # Update status to processing
        update_status_query = """
            UPDATE analysis_requests 
            SET extraction_status = %s, updated_at = %s
            WHERE id = %s
        """
        db.execute(update_status_query, (ExtractionStatus.PROCESSING.value, utc_now(), str(upload_id)))
        db.commit()
        
        # Get file info for extraction
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        # Check cache first for performance optimization
        cached_result = await extraction_cache.get(file_path_obj, mime_type)
        if cached_result and not force_reextraction:
            logger.info(f"Using cached extraction result for upload {upload_id}")
            extraction_result = cached_result
        else:
            # Get file validation info
            file_info = get_file_info(file_path_obj, original_filename)
            
            # Extract text using text extraction service
            timeout_seconds = extraction_request.timeout_seconds if extraction_request else 30
            extraction_result = await text_extraction_service.extract_text_from_file(
                file_path_obj, 
                file_info,
                timeout_seconds=timeout_seconds
            )
            
            # Cache successful results
            if extraction_result.is_success:
                await extraction_cache.store(file_path_obj, mime_type, extraction_result)
        
        if not extraction_result.is_success:
            # Update database with failure
            update_failure_query = """
                UPDATE analysis_requests 
                SET extraction_status = %s, error_message = %s, updated_at = %s
                WHERE id = %s
            """
            db.execute(update_failure_query, (
                extraction_result.status.value,
                extraction_result.error_message,
                utc_now(),
                str(upload_id)
            ))
            db.commit()
            
            return TextExtractionResponse(
                message="Text extraction failed",
                extraction_result=TextExtractionResult(
                    upload_id=upload_id,
                    extraction_status=extraction_result.status,
                    error_message=extraction_result.error_message,
                    processing_time_seconds=extraction_result.processing_time_seconds
                )
            )
        
        # Process extracted text
        processed_text_obj = text_processor.process_text(extraction_result.extracted_text)
        
        # Convert sections to API format
        api_sections = []
        for section in processed_text_obj.sections:
            api_sections.append(ResumeSection(
                section_type=section.section_type.value,
                title=section.title,
                content=section.content,
                line_start=section.line_start,
                line_end=section.line_end,
                confidence=section.confidence
            ))
        
        # Generate AI-ready data
        ai_ready_data = text_processor.get_ai_ready_format(processed_text_obj)
        
        # Combine metadata
        combined_metadata = {
            **extraction_result.metadata,
            **processed_text_obj.metadata,
            "processing_completed_at": utc_now().isoformat()
        }
        
        # Update database with results
        update_success_query = """
            UPDATE analysis_requests 
            SET extraction_status = %s, extracted_text = %s, processed_text = %s, 
                extraction_metadata = %s, ai_ready_data = %s, error_message = NULL, 
                updated_at = %s
            WHERE id = %s
        """
        db.execute(update_success_query, (
            ExtractionStatus.COMPLETED.value,
            extraction_result.extracted_text,
            processed_text_obj.cleaned_text,
            combined_metadata,
            ai_ready_data,
            utc_now(),
            str(upload_id)
        ))
        db.commit()
        
        # Create response
        final_result = TextExtractionResult(
            upload_id=upload_id,
            extraction_status=ExtractionStatus.COMPLETED,
            extracted_text=extraction_result.extracted_text,
            processed_text=processed_text_obj.cleaned_text,
            sections=api_sections,
            metadata=combined_metadata,
            processing_time_seconds=extraction_result.processing_time_seconds,
            word_count=processed_text_obj.word_count,
            line_count=processed_text_obj.line_count
        )
        
        logger.info(f"Text extraction completed for upload {upload_id}: "
                   f"{processed_text_obj.word_count} words, {len(api_sections)} sections")
        
        return TextExtractionResponse(
            message="Text extraction completed successfully",
            extraction_result=final_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text extraction failed for upload {upload_id}: {str(e)}")
        
        # Update database with error
        try:
            update_error_query = """
                UPDATE analysis_requests 
                SET extraction_status = %s, error_message = %s, updated_at = %s
                WHERE id = %s
            """
            db.execute(update_error_query, (
                ExtractionStatus.FAILED.value,
                f"Extraction error: {str(e)}",
                utc_now(),
                str(upload_id)
            ))
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update database with error status: {str(db_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text extraction failed"
        )


@router.get("/{upload_id}/extraction-status",
           response_model=TextExtractionStatusResponse,
           summary="Get text extraction status",
           description="Check the status of text extraction for an uploaded file")
async def get_extraction_status(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TextExtractionStatusResponse:
    """
    Get the current status of text extraction for an uploaded file.
    
    Args:
        upload_id: ID of the uploaded file
        current_user: Authenticated user
        db: Database session
        
    Returns:
        TextExtractionStatusResponse with extraction status details
    """
    try:
        query = """
            SELECT extraction_status, extracted_text, processed_text, extraction_metadata,
                   error_message, updated_at
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found or access denied"
            )
        
        extraction_status, extracted_text, processed_text, extraction_metadata, \
        error_message, updated_at = row
        
        # Calculate stats
        word_count = len(processed_text.split()) if processed_text else 0
        sections_detected = 0
        if extraction_metadata and "structure" in extraction_metadata:
            sections_detected = len(extraction_metadata["structure"].get("sections", []))
        
        return TextExtractionStatusResponse(
            upload_id=upload_id,
            extraction_status=ExtractionStatus(extraction_status),
            has_extracted_text=bool(extracted_text),
            has_processed_text=bool(processed_text),
            sections_detected=sections_detected,
            word_count=word_count,
            error_message=error_message,
            last_updated=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction status for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get extraction status"
        )


@router.get("/{upload_id}/ai-ready-data",
           response_model=AIReadyData,
           summary="Get AI-ready structured data",
           description="Get processed, structured data ready for AI analysis")
async def get_ai_ready_data(
    upload_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> AIReadyData:
    """
    Get AI-ready structured data for an uploaded resume.
    
    This endpoint returns the processed text in a format optimized for AI analysis,
    including structured sections, contact information, and quality assessments.
    
    Args:
        upload_id: ID of the uploaded file
        current_user: Authenticated user
        db: Database session
        
    Returns:
        AIReadyData with structured content for AI processing
    """
    try:
        query = """
            SELECT ai_ready_data, extraction_status, updated_at
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found or access denied"
            )
        
        ai_ready_data, extraction_status, updated_at = row
        
        if extraction_status != ExtractionStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Text extraction not completed. Status: {extraction_status}"
            )
        
        if not ai_ready_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI-ready data not available. Please run text extraction first."
            )
        
        # Convert database JSON to response format
        return AIReadyData(
            upload_id=upload_id,
            text_content=ai_ready_data.get("text_content", ""),
            structure=ai_ready_data.get("structure", {}),
            extraction_info=ai_ready_data.get("extraction_info", {}),
            contact_info=ai_ready_data.get("metadata", {}).get("contact_info", {}),
            quality_assessment=ai_ready_data.get("metadata", {}).get("extraction_quality", "unknown"),
            generated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI-ready data for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI-ready data"
        )


@router.post("/batch-extract-text",
            response_model=BatchTextExtractionResponse,
            summary="Batch extract text from multiple uploads",
            description="Start text extraction for multiple uploaded files")
async def batch_extract_text(
    batch_request: BatchTextExtractionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BatchTextExtractionResponse:
    """
    Extract text from multiple uploaded files in batch.
    
    Useful for processing multiple resumes at once. Each file is processed
    independently, and the response includes results for all files.
    
    Args:
        batch_request: Batch extraction request with upload IDs
        current_user: Authenticated user
        db: Database session
        
    Returns:
        BatchTextExtractionResponse with results for all files
    """
    logger.info(f"Starting batch text extraction for {len(batch_request.upload_ids)} files")
    
    results = []
    errors = []
    successfully_started = 0
    already_extracted = 0
    failed_to_start = 0
    
    for upload_id in batch_request.upload_ids:
        try:
            # Create individual extraction request
            individual_request = TextExtractionRequest(
                upload_id=upload_id,
                force_reextraction=batch_request.force_reextraction,
                timeout_seconds=batch_request.timeout_seconds
            )
            
            # Process individual extraction
            extraction_response = await extract_text_from_upload(
                upload_id=upload_id,
                extraction_request=individual_request,
                current_user=current_user,
                db=db
            )
            
            results.append(extraction_response.extraction_result)
            
            if "cached" in extraction_response.message:
                already_extracted += 1
            else:
                successfully_started += 1
                
        except HTTPException as http_error:
            failed_to_start += 1
            error_msg = f"Upload {upload_id}: {http_error.detail}"
            errors.append(error_msg)
            logger.warning(f"Batch extraction failed for {upload_id}: {http_error.detail}")
            
            # Add failed result
            results.append(TextExtractionResult(
                upload_id=upload_id,
                extraction_status=ExtractionStatus.FAILED,
                error_message=http_error.detail
            ))
            
        except Exception as e:
            failed_to_start += 1
            error_msg = f"Upload {upload_id}: Unexpected error - {str(e)}"
            errors.append(error_msg)
            logger.error(f"Unexpected error in batch extraction for {upload_id}: {str(e)}")
            
            results.append(TextExtractionResult(
                upload_id=upload_id,
                extraction_status=ExtractionStatus.FAILED,
                error_message=str(e)
            ))
    
    logger.info(f"Batch extraction completed: {successfully_started} started, "
               f"{already_extracted} cached, {failed_to_start} failed")
    
    return BatchTextExtractionResponse(
        total_requested=len(batch_request.upload_ids),
        successfully_started=successfully_started,
        already_extracted=already_extracted,
        failed_to_start=failed_to_start,
        results=results,
        errors=errors
    )


@router.post("/{upload_id}/extract-text-async",
            summary="Start background text extraction",
            description="Submit file for background text extraction processing")
async def extract_text_async(
    upload_id: UUID,
    priority: JobPriority = JobPriority.NORMAL,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submit file for background text extraction processing.
    
    This endpoint queues the file for processing and returns immediately.
    Use the job_id to check processing status.
    
    Args:
        upload_id: ID of uploaded file
        priority: Processing priority level
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Job submission details including job_id for tracking
    """
    try:
        # Get upload record
        query = """
            SELECT id, file_path, original_filename, mime_type, extraction_status
            FROM analysis_requests 
            WHERE id = %s AND user_id = %s
        """
        
        result = db.execute(query, (str(upload_id), str(current_user.id)))
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found or access denied"
            )
        
        upload_uuid, file_path, original_filename, mime_type, extraction_status = row
        
        # Check if file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk"
            )
        
        # Submit to background processor
        job_id = background_processor.submit_job(
            user_id=current_user.id,
            upload_id=upload_id,
            file_path=file_path,
            original_filename=original_filename,
            mime_type=mime_type,
            priority=priority,
            timeout_seconds=60  # Longer timeout for background processing
        )
        
        # Update database status
        update_query = """
            UPDATE analysis_requests 
            SET extraction_status = %s, updated_at = %s
            WHERE id = %s
        """
        db.execute(update_query, (ExtractionStatus.PROCESSING.value, utc_now(), str(upload_id)))
        db.commit()
        
        logger.info(f"Submitted background extraction job {job_id} for upload {upload_id}")
        
        return {
            "message": "Text extraction job submitted successfully",
            "job_id": str(job_id),
            "upload_id": str(upload_id),
            "priority": priority.value,
            "estimated_wait_time_seconds": background_processor.get_queue_stats()["queue_size"] * 10
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting background extraction for upload {upload_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit extraction job"
        )


@router.get("/processing-queue/status",
           summary="Get processing queue status",
           description="Get current status of background processing queue")
async def get_processing_queue_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current status of the background processing queue.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        Queue status and statistics
    """
    try:
        queue_stats = background_processor.get_queue_stats()
        cache_stats = extraction_cache.get_cache_stats()
        
        return {
            "queue_status": queue_stats,
            "cache_statistics": cache_stats,
            "system_health": {
                "background_processor_running": queue_stats["is_running"],
                "cache_hit_rate": cache_stats.get("hit_rate_percent", 0),
                "average_processing_time": queue_stats["stats"].get("average_processing_time", 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting processing queue status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue status"
        )


@router.get("/job/{job_id}/status",
           summary="Get background job status",
           description="Check status of background text extraction job")
async def get_job_status(
    job_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get status of a background processing job.
    
    Args:
        job_id: Background job ID
        current_user: Authenticated user
        
    Returns:
        Job status and details
    """
    try:
        job = background_processor.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify user has access to this job
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        job_dict = job.to_dict()
        
        # Add extraction result if available
        if job.extraction_result:
            job_dict["extraction_summary"] = {
                "status": job.extraction_result.status.value,
                "has_text": bool(job.extraction_result.extracted_text),
                "processing_time": job.extraction_result.processing_time_seconds,
                "error_message": job.extraction_result.error_message
            }
        
        return {
            "job": job_dict,
            "queue_position": None  # TODO: Calculate queue position for queued jobs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status"
        )


@router.delete("/job/{job_id}",
              summary="Cancel background job",
              description="Cancel a queued background processing job")
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a queued background processing job.
    
    Args:
        job_id: Background job ID to cancel
        current_user: Authenticated user
        
    Returns:
        Cancellation result
    """
    try:
        job = background_processor.get_job_status(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Verify user has access to this job
        if job.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this job"
            )
        
        # Can only cancel queued jobs
        if job.status != JobStatus.QUEUED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot cancel job with status: {job.status.value}"
            )
        
        success = background_processor.cancel_job(job_id)
        
        if success:
            logger.info(f"Cancelled background job {job_id} for user {current_user.id}")
            return {
                "message": "Job cancelled successfully",
                "job_id": str(job_id)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel job"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )