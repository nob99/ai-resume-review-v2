"""File upload repository for database operations."""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from infrastructure.persistence.postgres.base import BaseRepository
from app.core.datetime_utils import utc_now
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.files import FileUpload, FileStatus


class FileUploadRepository(BaseRepository[FileUpload]):
    """Repository for file upload database operations."""
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        super().__init__(FileUpload, db)
    
    async def create_upload(
        self,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        user_id: uuid.UUID,
        mime_type: Optional[str] = None
    ) -> FileUpload:
        """Create a new file upload record."""
        file_upload = FileUpload(
            filename=filename,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            mime_type=mime_type,
            user_id=user_id,
            status=FileStatus.PENDING,
            upload_started_at=utc_now()
        )
        
        self.db.add(file_upload)
        self.db.commit()
        self.db.refresh(file_upload)
        
        return file_upload
    
    async def update_status(
        self,
        file_id: uuid.UUID,
        status: FileStatus,
        error_message: Optional[str] = None
    ) -> Optional[FileUpload]:
        """Update file upload status."""
        file_upload = self.get(file_id)
        if not file_upload:
            return None
        
        file_upload.status = status
        file_upload.updated_at = utc_now()
        
        if error_message:
            file_upload.error_message = error_message
        
        if status == FileStatus.COMPLETED:
            file_upload.upload_completed_at = utc_now()
            if file_upload.upload_started_at:
                delta = file_upload.upload_completed_at - file_upload.upload_started_at
                file_upload.processing_time_ms = int(delta.total_seconds() * 1000)
        
        self.db.commit()
        self.db.refresh(file_upload)
        
        return file_upload
    
    async def update_extracted_text(
        self,
        file_id: uuid.UUID,
        extracted_text: str,
        extraction_metadata: Optional[dict] = None
    ) -> Optional[FileUpload]:
        """Update extracted text and metadata."""
        file_upload = self.get(file_id)
        if not file_upload:
            return None
        
        file_upload.extracted_text = extracted_text
        file_upload.extraction_metadata = extraction_metadata
        file_upload.updated_at = utc_now()
        
        self.db.commit()
        self.db.refresh(file_upload)
        
        return file_upload
    
    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[FileStatus] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[FileUpload]:
        """Get file uploads by user."""
        query = self.db.query(FileUpload).filter(FileUpload.user_id == user_id)
        
        if status:
            query = query.filter(FileUpload.status == status)
        
        return query.order_by(desc(FileUpload.created_at)).limit(limit).offset(offset).all()
    
    async def get_recent_uploads(
        self,
        user_id: uuid.UUID,
        hours: int = 24,
        limit: int = 10
    ) -> List[FileUpload]:
        """Get recent uploads within specified hours."""
        from datetime import timedelta
        
        cutoff_time = utc_now() - timedelta(hours=hours)
        
        return self.db.query(FileUpload).filter(
            and_(
                FileUpload.user_id == user_id,
                FileUpload.created_at >= cutoff_time
            )
        ).order_by(desc(FileUpload.created_at)).limit(limit).all()
    
    async def delete_old_uploads(
        self,
        days: int = 30,
        status: Optional[FileStatus] = None
    ) -> int:
        """Delete old uploads older than specified days."""
        from datetime import timedelta
        
        cutoff_time = utc_now() - timedelta(days=days)
        
        query = self.db.query(FileUpload).filter(FileUpload.created_at < cutoff_time)
        
        if status:
            query = query.filter(FileUpload.status == status)
        
        count = query.count()
        query.delete()
        self.db.commit()
        
        return count
    
    async def get_upload_stats(self, user_id: uuid.UUID) -> dict:
        """Get upload statistics for a user."""
        uploads = self.db.query(FileUpload).filter(FileUpload.user_id == user_id).all()
        
        total_count = len(uploads)
        completed_count = sum(1 for u in uploads if u.status == FileStatus.COMPLETED)
        error_count = sum(1 for u in uploads if u.status == FileStatus.ERROR)
        total_size = sum(u.file_size for u in uploads)
        
        return {
            "total_uploads": total_count,
            "completed_uploads": completed_count,
            "failed_uploads": error_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    async def mark_cancelled(self, file_id: uuid.UUID) -> Optional[FileUpload]:
        """Mark an upload as cancelled."""
        return await self.update_status(file_id, FileStatus.CANCELLED)
    
    async def get_pending_uploads(self, user_id: uuid.UUID) -> List[FileUpload]:
        """Get all pending uploads for a user."""
        return self.db.query(FileUpload).filter(
            and_(
                FileUpload.user_id == user_id,
                FileUpload.status.in_([
                    FileStatus.PENDING,
                    FileStatus.UPLOADING,
                    FileStatus.VALIDATING,
                    FileStatus.EXTRACTING
                ])
            )
        ).all()