"""Resume upload repository for database operations."""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, select

from infrastructure.persistence.postgres.base import BaseRepository
from app.core.datetime_utils import utc_now
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
        query = select(Resume).where(Resume.candidate_id == candidate_id).order_by(desc(Resume.version_number)).limit(1)
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
        
        # Note: error_message field not implemented in Resume model
        
        if status == ResumeStatus.COMPLETED:
            file_upload.processed_at = utc_now()

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
    
    async def get_upload_stats(self, user_id: uuid.UUID) -> dict:
        """Get upload statistics for a user using SQL aggregation."""
        from sqlalchemy import func, case

        query = select(
            func.count(Resume.id).label('total'),
            func.sum(
                case((Resume.status == ResumeStatus.COMPLETED.value, 1), else_=0)
            ).label('completed'),
            func.sum(
                case((Resume.status == ResumeStatus.ERROR.value, 1), else_=0)
            ).label('failed'),
            func.coalesce(func.sum(Resume.file_size), 0).label('total_size')
        ).where(Resume.uploaded_by_user_id == user_id)

        result = await self.session.execute(query)
        stats = result.one()

        total_size_bytes = stats.total_size or 0

        return {
            "total_uploads": stats.total or 0,
            "completed_uploads": stats.completed or 0,
            "failed_uploads": stats.failed or 0,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2)
        }
    
    async def mark_cancelled(self, file_id: uuid.UUID) -> Optional[Resume]:
        """Mark an upload as cancelled."""
        return await self.update_status(file_id, ResumeStatus.CANCELLED)
    
