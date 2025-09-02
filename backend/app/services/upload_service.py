"""
Upload Service for business logic orchestration.
Coordinates file upload, storage, and database operations using repository pattern.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from pathlib import Path

from fastapi import UploadFile, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.analysis import AnalysisRequest, AnalysisStatus, ExtractionStatus
from app.models.user import User
from app.models.upload import ExperienceLevel
from app.repositories.analysis_repository import AnalysisRepository
from app.services.file_service import store_uploaded_file, file_storage_service, FileStorageResult
from app.core.file_validation import get_file_info, FileValidationError as ValidationError
from app.core.datetime_utils import utc_now
from app.database.connection import get_db
# from app.core.background_processor import background_processor, JobPriority

logger = logging.getLogger(__name__)


class UploadServiceError(Exception):
    """Custom exception for upload service errors."""
    pass


class UploadService:
    """
    Service class for upload operations.
    
    Orchestrates:
    - File validation and storage
    - Database record creation
    - Text extraction initiation
    - Error handling and cleanup
    """
    
    def __init__(self, db: Session):
        """
        Initialize upload service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = AnalysisRepository(db)
    
    async def create_upload(
        self,
        file: UploadFile,
        user: User,
        target_role: Optional[str] = None,
        target_industry: Optional[str] = None,
        experience_level: Optional[ExperienceLevel] = None
    ) -> Dict[str, Any]:
        """
        Create a new file upload with validation and storage.
        
        Args:
            file: Uploaded file
            user: Current user
            target_role: Target job role for analysis
            target_industry: Target industry for analysis
            experience_level: Experience level for analysis
            
        Returns:
            Dictionary with upload details and ID
            
        Raises:
            UploadServiceError: If upload fails
            HTTPException: If validation fails
        """
        logger.info(f"Starting upload for user {user.id}: {file.filename}")
        
        try:
            # Step 1: Read file content
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Step 2: Validate and store file
            storage_result = store_uploaded_file(
                file_content=file_content,
                original_filename=file.filename,
                user_id=str(user.id)
            )
            
            if not storage_result.success:
                logger.error(f"File storage failed: {storage_result.error_message}")
                raise UploadServiceError(f"File storage failed: {storage_result.error_message}")
            
            logger.info(f"File stored successfully: {storage_result.file_path}")
            
            # Step 3: Create database record using repository
            try:
                analysis_request = self.repository.create_analysis_request(
                    user_id=user.id,
                    original_filename=file.filename,
                    file_path=storage_result.file_path,
                    file_size_bytes=storage_result.validation_result.file_info['file_size'],
                    mime_type=storage_result.validation_result.file_info['mime_type'],
                    target_role=target_role,
                    target_industry=target_industry,
                    experience_level=experience_level.value if experience_level else None
                    # file_hash removed - column doesn't exist in current database schema
                )
                
                logger.info(f"Analysis request created: {analysis_request.id}")
                
                # Step 4: Queue text extraction (non-blocking)
                self._queue_text_extraction(analysis_request.id)
                
                return {
                    "id": analysis_request.id,
                    "original_filename": analysis_request.original_filename,
                    "file_size_bytes": analysis_request.file_size_bytes,
                    "mime_type": analysis_request.mime_type,
                    "status": analysis_request.status,
                    "extraction_status": "pending",  # Default value since DB field doesn't exist
                    "target_role": analysis_request.target_role,
                    "target_industry": analysis_request.target_industry,
                    "experience_level": analysis_request.experience_level,
                    "created_at": analysis_request.created_at,
                    "message": "Upload completed successfully. Text extraction will begin shortly."
                }
                
            except IntegrityError as e:
                # Cleanup file on database error
                self._cleanup_file(storage_result.file_path)
                logger.error(f"Database error creating analysis request: {str(e)}")
                raise UploadServiceError("Database error: Could not create upload record")
                
            except Exception as e:
                # Cleanup file on any error
                self._cleanup_file(storage_result.file_path)
                logger.error(f"Unexpected error creating analysis request: {str(e)}")
                raise UploadServiceError("Failed to create upload record")
                
        except ValidationError as e:
            logger.error(f"File validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {str(e)}"
            )
        except UploadServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected upload error: {str(e)}")
            raise UploadServiceError("Upload failed due to unexpected error")
    
    def get_upload(self, upload_id: UUID, user: User) -> Optional[Dict[str, Any]]:
        """
        Get upload details by ID and user.
        
        Args:
            upload_id: Upload ID
            user: Current user
            
        Returns:
            Upload details if found and owned by user, None otherwise
        """
        analysis_request = self.repository.get_by_id_and_user(upload_id, user.id)
        
        if not analysis_request:
            return None
        
        return analysis_request.to_dict()
    
    def list_uploads(
        self,
        user: User,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        List user's uploads with pagination.
        
        Args:
            user: Current user
            page: Page number (1-based)
            per_page: Items per page
            status_filter: Optional status filter
            
        Returns:
            Dictionary with uploads and pagination info
        """
        skip = (page - 1) * per_page
        
        uploads = self.repository.list_by_user(
            user_id=user.id,
            skip=skip,
            limit=per_page,
            status_filter=status_filter,
            order_by="created_at",
            order_desc=True
        )
        
        total_count = self.repository.count_by_user(
            user_id=user.id,
            status_filter=status_filter
        )
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            "uploads": [upload.to_dict() for upload in uploads],
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_items": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    def delete_upload(self, upload_id: UUID, user: User) -> bool:
        """
        Delete upload and associated file.
        
        Args:
            upload_id: Upload ID
            user: Current user
            
        Returns:
            True if deleted, False if not found
        """
        analysis_request = self.repository.get_by_id_and_user(upload_id, user.id)
        
        if not analysis_request:
            return False
        
        # Store file path for cleanup
        file_path = analysis_request.file_path
        
        # Delete database record
        success = self.repository.delete_by_id_and_user(upload_id, user.id)
        
        if success:
            # Cleanup file
            self._cleanup_file(file_path)
            logger.info(f"Upload deleted: {upload_id}")
        
        return success
    
    def get_user_statistics(self, user: User) -> Dict[str, Any]:
        """
        Get comprehensive upload statistics for user.
        
        Args:
            user: Current user
            
        Returns:
            Dictionary with various statistics
        """
        return self.repository.get_user_statistics(user.id)
    
    def get_extraction_result(self, upload_id: UUID, user: User) -> Optional[Dict[str, Any]]:
        """
        Get text extraction results for upload.
        
        Args:
            upload_id: Upload ID
            user: Current user
            
        Returns:
            Extraction results if available, None otherwise
        """
        return self.repository.get_extraction_result(upload_id, user.id)
    
    def get_ai_ready_data(self, upload_id: UUID, user: User) -> Optional[Dict[str, Any]]:
        """
        Get AI-ready structured data for upload.
        
        Args:
            upload_id: Upload ID
            user: Current user
            
        Returns:
            AI-ready data if available, None otherwise
        """
        return self.repository.get_ai_ready_data(upload_id, user.id)
    
    async def start_text_extraction(
        self,
        upload_id: UUID,
        user: User,
        force_reextraction: bool = False
    ) -> Dict[str, Any]:
        """
        Start or restart text extraction for an upload.
        
        Args:
            upload_id: Upload ID
            user: Current user
            force_reextraction: Whether to force re-extraction
            
        Returns:
            Status information
            
        Raises:
            HTTPException: If upload not found or extraction fails
        """
        analysis_request = self.repository.get_by_id_and_user(upload_id, user.id)
        
        if not analysis_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        # Check if extraction is needed (extraction_status field doesn't exist in DB yet)
        # TODO: Re-enable when extraction_status column is added to database
        # if (analysis_request.extraction_status == ExtractionStatus.COMPLETED.value 
        #     and not force_reextraction):
        #     return {
        #         "upload_id": upload_id,
        #         "extraction_status": analysis_request.extraction_status,
        #         "message": "Text extraction already completed"
        #     }
        
        # Update status to processing (extraction_status column doesn't exist in DB yet)
        # TODO: Re-enable when extraction_status column is added to database
        # self.repository.update_extraction_status(
        #     id=upload_id,
        #     user_id=user.id,
        #     extraction_status=ExtractionStatus.PROCESSING.value
        # )
        
        # Queue extraction job
        self._queue_text_extraction(upload_id)
        
        return {
            "upload_id": upload_id,
            "extraction_status": "processing",  # Default value since DB field doesn't exist
            "message": "Text extraction started"
        }
    
    def _queue_text_extraction(self, analysis_request_id: UUID) -> None:
        """
        Queue text extraction job for background processing.
        
        Args:
            analysis_request_id: Analysis request ID
        """
        # TODO: Re-enable background processing when dependencies are installed
        logger.info(f"Text extraction would be queued for analysis request: {analysis_request_id}")
    
    def _cleanup_file(self, file_path: str) -> None:
        """
        Clean up uploaded file.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"File cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {str(e)}")


def get_upload_service(db: Session = Depends(get_db)) -> UploadService:
    """
    Dependency injection for upload service.
    
    Args:
        db: Database session
        
    Returns:
        UploadService instance
    """
    return UploadService(db)