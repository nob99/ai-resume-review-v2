"""Resume upload repository for database operations."""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, and_, select

from app.core.database import BaseRepository
from app.core.datetime_utils import utc_now
from database.models.resume import Resume, ResumeStatus


class ResumeUploadRepository(BaseRepository[Resume]):
    """Repository for resume upload database operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        super().__init__(session, Resume)

    async def get_latest_resume_for_candidate(self, candidate_id: uuid.UUID) -> Optional[Resume]:
        """Get the most recent resume for a candidate (by version number)."""
        query = select(Resume).where(
            Resume.candidate_id == candidate_id
        ).order_by(desc(Resume.version_number)).limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_resume(
        self,
        candidate_id: uuid.UUID,
        uploaded_by_user_id: uuid.UUID,
        original_filename: str,
        stored_filename: str,
        file_hash: str,
        file_size: int,
        mime_type: str,
        version_number: int,
        status: str = ResumeStatus.PENDING.value,
        extracted_text: Optional[str] = None
    ) -> Resume:
        """Create a new resume record. Just stores data as provided."""
        resume = Resume(
            candidate_id=candidate_id,
            uploaded_by_user_id=uploaded_by_user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            version_number=version_number,
            status=status,
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
        processed_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> Optional[Resume]:
        """Update file upload status and optionally set processed_at timestamp."""
        file_upload = await self.get_by_id(file_id)
        if not file_upload:
            return None

        file_upload.status = status

        # Set processed_at if provided (service decides when to set it)
        if processed_at is not None:
            file_upload.processed_at = processed_at

        # Note: error_message field not implemented in Resume model

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
    
