"""Resume upload repository for database operations."""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, select

from infrastructure.persistence.postgres.base import BaseRepository
from app.core.datetime_utils import utc_now
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.resume import Resume, ResumeStatus


class ResumeUploadRepository(BaseRepository[Resume]):
    """Repository for resume upload database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        super().__init__(session, Resume)
    
    async def create_resume(
        self,
        candidate_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        original_filename: str,
        stored_filename: str,
        file_hash: str,
        file_size: int,
        mime_type: str,
        extracted_text: Optional[str] = None
    ) -> Resume:
        """Create a new resume record with proper fields."""
        # Get the latest version number for this candidate
        query = select(Resume).where(Resume.candidate_id == candidate_id).order_by(desc(Resume.version_number))
        result = await self.session.execute(query)
        existing_resumes = result.scalar_one_or_none()

        version_number = 1
        if existing_resumes:
            version_number = existing_resumes.version_number + 1

        resume = Resume(
            candidate_id=candidate_id,
            uploaded_by_user_id=uploaded_by_user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            version_number=version_number,
            status=ResumeStatus.PENDING.value,
            extracted_text=extracted_text
        )

        self.session.add(resume)
        await self.session.commit()
        await self.session.refresh(resume)

        return resume

    async def create_upload(
        self,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        user_id: uuid.UUID,
        mime_type: Optional[str] = None
    ) -> Resume:
        """Legacy method - kept for compatibility but should not be used."""
        # This method has wrong field mappings, use create_resume instead
        raise NotImplementedError("Use create_resume method instead")
        
        self.session.add(file_upload)
        await self.session.commit()
        await self.session.refresh(file_upload)
        
        return file_upload
    
    async def update_status(
        self,
        file_id: uuid.UUID,
        status: ResumeStatus,
        error_message: Optional[str] = None
    ) -> Optional[Resume]:
        """Update file upload status."""
        file_upload = await self.get_by_id(file_id)
        if not file_upload:
            return None
        
        file_upload.status = status
        file_upload.updated_at = utc_now()
        
        if error_message:
            file_upload.error_message = error_message
        
        if status == ResumeStatus.COMPLETED:
            file_upload.upload_completed_at = utc_now()
            if file_upload.upload_started_at:
                delta = file_upload.upload_completed_at - file_upload.upload_started_at
                file_upload.processing_time_ms = int(delta.total_seconds() * 1000)

        await self.session.commit()
        await self.session.refresh(file_upload)
        
        return file_upload
    
    async def update_extracted_text(
        self,
        file_id: uuid.UUID,
        extracted_text: str,
        extraction_metadata: Optional[dict] = None
    ) -> Optional[Resume]:
        """Update extracted text and metadata."""
        file_upload = await self.get_by_id(file_id)
        if not file_upload:
            return None
        
        file_upload.extracted_text = extracted_text
        file_upload.extraction_metadata = extraction_metadata
        file_upload.updated_at = utc_now()
        
        await self.session.commit()
        await self.session.refresh(file_upload)
        
        return file_upload
    
    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[ResumeStatus] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Resume]:
        """Get file uploads by user."""
        query = select(Resume).where(Resume.uploaded_by_user_id == user_id)

        if status:
            query = query.where(Resume.status == status)

        query = query.order_by(desc(Resume.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_uploads(
        self,
        user_id: uuid.UUID,
        hours: int = 24,
        limit: int = 10
    ) -> List[Resume]:
        """Get recent uploads within specified hours."""
        from datetime import timedelta
        
        cutoff_time = utc_now() - timedelta(hours=hours)
        
        query = select(Resume).where(
            and_(
                Resume.uploaded_by_user_id == user_id,
                Resume.created_at >= cutoff_time
            )
        ).order_by(desc(Resume.created_at)).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def delete_old_uploads(
        self,
        days: int = 30,
        status: Optional[ResumeStatus] = None
    ) -> int:
        """Delete old uploads older than specified days."""
        from datetime import timedelta
        
        cutoff_time = utc_now() - timedelta(days=days)
        
        from sqlalchemy import delete, func

        # First get count
        count_query = select(func.count()).select_from(Resume).where(Resume.created_at < cutoff_time)
        if status:
            count_query = count_query.where(Resume.status == status)

        count_result = await self.session.execute(count_query)
        count = count_result.scalar()

        # Then delete
        delete_query = delete(Resume).where(Resume.created_at < cutoff_time)
        if status:
            delete_query = delete_query.where(Resume.status == status)

        await self.session.execute(delete_query)
        await self.session.commit()
        
        return count
    
    async def get_upload_stats(self, user_id: uuid.UUID) -> dict:
        """Get upload statistics for a user."""
        query = select(Resume).where(Resume.uploaded_by_user_id == user_id)
        result = await self.session.execute(query)
        uploads = list(result.scalars().all())
        
        total_count = len(uploads)
        completed_count = sum(1 for u in uploads if u.status == ResumeStatus.COMPLETED)
        error_count = sum(1 for u in uploads if u.status == ResumeStatus.ERROR)
        total_size = sum(u.file_size for u in uploads)
        
        return {
            "total_uploads": total_count,
            "completed_uploads": completed_count,
            "failed_uploads": error_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    async def mark_cancelled(self, file_id: uuid.UUID) -> Optional[Resume]:
        """Mark an upload as cancelled."""
        return await self.update_status(file_id, ResumeStatus.CANCELLED)
    
    async def get_pending_uploads(self, user_id: uuid.UUID) -> List[Resume]:
        """Get all pending uploads for a user."""
        query = select(Resume).where(
            and_(
                Resume.uploaded_by_user_id == user_id,
                Resume.status.in_([
                    ResumeStatus.PENDING,
                    ResumeStatus.UPLOADING,
                    ResumeStatus.VALIDATING,
                    ResumeStatus.EXTRACTING
                ])
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())