"""
Analysis Repository for AnalysisRequest model.
Provides specialized data access methods for resume upload and processing functionality.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError

from app.models.analysis import AnalysisRequest, AnalysisStatus, ExtractionStatus
from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.core.datetime_utils import utc_now


class AnalysisRepository(BaseRepository[AnalysisRequest]):
    """
    Repository for AnalysisRequest model.
    
    Provides specialized methods for:
    - User-scoped queries (security isolation)
    - Status-based filtering and updates
    - File processing operations
    - Statistical aggregations
    """
    
    def __init__(self, db: Session):
        """Initialize with AnalysisRequest model."""
        super().__init__(AnalysisRequest, db)
    
    def create_analysis_request(
        self,
        user_id: UUID,
        original_filename: str,
        file_path: str,
        file_size_bytes: int,
        mime_type: str,
        target_role: Optional[str] = None,
        target_industry: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> AnalysisRequest:
        """
        Create a new analysis request.
        
        Args:
            user_id: User who owns this request
            original_filename: Original filename from upload
            file_path: Server-side file storage path
            file_size_bytes: File size in bytes
            mime_type: MIME type of the file
            target_role: Target role for analysis
            target_industry: Target industry for analysis  
            experience_level: Experience level for analysis
            
        Returns:
            Created AnalysisRequest object
            
        Raises:
            IntegrityError: If user doesn't exist or constraints violated
        """
        analysis_request = AnalysisRequest(
            user_id=user_id,
            original_filename=original_filename,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            target_role=target_role,
            target_industry=target_industry,
            experience_level=experience_level
        )
        
        return self.create(analysis_request)
    
    def get_by_id_and_user(self, id: UUID, user_id: UUID) -> Optional[AnalysisRequest]:
        """
        Get analysis request by ID, ensuring user ownership.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            
        Returns:
            AnalysisRequest if found and owned by user, None otherwise
        """
        return self.db.query(AnalysisRequest).filter(
            and_(
                AnalysisRequest.id == id,
                AnalysisRequest.user_id == user_id
            )
        ).first()
    
    def list_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[List[str]] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[AnalysisRequest]:
        """
        List analysis requests for a specific user.
        
        Args:
            user_id: User ID to filter by
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            status_filter: List of statuses to include
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            List of analysis requests
        """
        query = self.db.query(AnalysisRequest).filter(
            AnalysisRequest.user_id == user_id
        )
        
        # Apply status filter
        if status_filter:
            query = query.filter(AnalysisRequest.status.in_(status_filter))
        
        # Apply ordering
        if hasattr(AnalysisRequest, order_by):
            order_field = getattr(AnalysisRequest, order_by)
            if order_desc:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
        
        return query.offset(skip).limit(limit).all()
    
    def count_by_user(
        self,
        user_id: UUID,
        status_filter: Optional[List[str]] = None
    ) -> int:
        """
        Count analysis requests for a user.
        
        Args:
            user_id: User ID to filter by
            status_filter: List of statuses to include
            
        Returns:
            Number of matching requests
        """
        query = self.db.query(func.count(AnalysisRequest.id)).filter(
            AnalysisRequest.user_id == user_id
        )
        
        if status_filter:
            query = query.filter(AnalysisRequest.status.in_(status_filter))
        
        return query.scalar()
    
    def get_user_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive statistics for user's analysis requests.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with various statistics
        """
        # Total count and status breakdown
        status_stats = self.db.query(
            AnalysisRequest.status,
            func.count(AnalysisRequest.id)
        ).filter(
            AnalysisRequest.user_id == user_id
        ).group_by(AnalysisRequest.status).all()
        
        # File type statistics
        type_stats = self.db.query(
            AnalysisRequest.mime_type,
            func.count(AnalysisRequest.id)
        ).filter(
            AnalysisRequest.user_id == user_id
        ).group_by(AnalysisRequest.mime_type).all()
        
        # Recent activity (last 30 days)
        from datetime import timedelta
        thirty_days_ago = utc_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
        
        recent_count = self.db.query(func.count(AnalysisRequest.id)).filter(
            and_(
                AnalysisRequest.user_id == user_id,
                AnalysisRequest.created_at >= thirty_days_ago
            )
        ).scalar()
        
        # Total file size
        total_size = self.db.query(
            func.sum(AnalysisRequest.file_size_bytes)
        ).filter(
            AnalysisRequest.user_id == user_id
        ).scalar() or 0
        
        return {
            "total_uploads": sum(count for _, count in status_stats),
            "status_breakdown": {status: count for status, count in status_stats},
            "file_type_breakdown": {mime_type: count for mime_type, count in type_stats},
            "recent_uploads_30_days": recent_count,
            "total_storage_bytes": total_size
        }
    
    def update_status(
        self,
        id: UUID,
        user_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[AnalysisRequest]:
        """
        Update analysis request status.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            status: New status
            error_message: Optional error message
            error_details: Optional error details
            
        Returns:
            Updated AnalysisRequest if found, None otherwise
        """
        analysis_request = self.get_by_id_and_user(id, user_id)
        if not analysis_request:
            return None
        
        update_data = {
            "status": status,
            "error_message": error_message,
            "error_details": error_details
        }
        
        # Set completion timestamp for terminal states
        if status in [AnalysisStatus.COMPLETED.value, AnalysisStatus.FAILED.value]:
            update_data["processing_completed_at"] = utc_now()
        elif status == AnalysisStatus.PROCESSING.value:
            update_data["processing_started_at"] = utc_now()
        
        return self.update(analysis_request, update_data)
    
    def update_extraction_status(
        self,
        id: UUID,
        user_id: UUID,
        extraction_status: str,
        extracted_text: Optional[str] = None,
        processed_text: Optional[str] = None,
        extraction_metadata: Optional[Dict[str, Any]] = None,
        ai_ready_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[AnalysisRequest]:
        """
        Update text extraction status and data.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            extraction_status: New extraction status
            extracted_text: Raw extracted text
            processed_text: Processed/cleaned text
            extraction_metadata: Processing metadata
            ai_ready_data: Structured data for AI processing
            error_message: Optional error message
            error_details: Optional error details
            
        Returns:
            Updated AnalysisRequest if found, None otherwise
        """
        analysis_request = self.get_by_id_and_user(id, user_id)
        if not analysis_request:
            return None
        
        update_data = {
            "extraction_status": extraction_status,
            "extracted_text": extracted_text,
            "processed_text": processed_text,
            "extraction_metadata": extraction_metadata,
            "ai_ready_data": ai_ready_data,
            "error_message": error_message,
            "error_details": error_details
        }
        
        # Remove None values to avoid overwriting existing data
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        return self.update(analysis_request, update_data)
    
    def delete_by_id_and_user(self, id: UUID, user_id: UUID) -> bool:
        """
        Delete analysis request by ID, ensuring user ownership.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            
        Returns:
            True if deleted, False if not found
        """
        analysis_request = self.get_by_id_and_user(id, user_id)
        if not analysis_request:
            return False
        
        try:
            self.db.delete(analysis_request)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_pending_extractions(self, limit: int = 50) -> List[AnalysisRequest]:
        """
        Get analysis requests pending text extraction.
        
        Args:
            limit: Maximum number of requests to return
            
        Returns:
            List of analysis requests ready for extraction
        """
        return self.db.query(AnalysisRequest).filter(
            AnalysisRequest.extraction_status == ExtractionStatus.PENDING.value
        ).order_by(asc(AnalysisRequest.created_at)).limit(limit).all()
    
    def get_by_file_path(self, file_path: str) -> Optional[AnalysisRequest]:
        """
        Get analysis request by file path.
        
        Args:
            file_path: Server-side file path
            
        Returns:
            AnalysisRequest if found, None otherwise
        """
        return self.db.query(AnalysisRequest).filter(
            AnalysisRequest.file_path == file_path
        ).first()
    
    def get_extraction_result(self, id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get extraction results for an analysis request.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            
        Returns:
            Dictionary with extraction data if found, None otherwise
        """
        analysis_request = self.get_by_id_and_user(id, user_id)
        if not analysis_request:
            return None
        
        return {
            "id": analysis_request.id,
            "extraction_status": analysis_request.extraction_status,
            "extracted_text": analysis_request.extracted_text,
            "processed_text": analysis_request.processed_text,
            "extraction_metadata": analysis_request.extraction_metadata,
            "ai_ready_data": analysis_request.ai_ready_data,
            "error_message": analysis_request.error_message,
            "error_details": analysis_request.error_details,
            "updated_at": analysis_request.updated_at
        }
    
    def get_ai_ready_data(self, id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get AI-ready structured data for an analysis request.
        
        Args:
            id: Analysis request ID
            user_id: User ID (for security)
            
        Returns:
            AI-ready data if available, None otherwise
        """
        analysis_request = self.get_by_id_and_user(id, user_id)
        if not analysis_request or not analysis_request.ai_ready_data:
            return None
        
        return {
            "upload_id": analysis_request.id,
            "ai_ready_data": analysis_request.ai_ready_data,
            "extraction_metadata": analysis_request.extraction_metadata or {},
            "generated_at": analysis_request.updated_at
        }