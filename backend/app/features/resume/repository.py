"""Resume repository for database operations - replaces FileUploadRepository."""

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
from database.models.resume import Resume, ResumeStatus


class ResumeRepository(BaseRepository[Resume]):
    """Repository for resume database operations - replaces FileUploadRepository."""
    
    def __init__(self, db: Session):
        """Initialize repository with database session."""
        super().__init__(db, Resume)
    
    async def create_resume(
        self,
        candidate_id: uuid.UUID,  # NEW: Required candidate relationship
        uploaded_by_user_id: uuid.UUID,
        original_filename: str,
        stored_filename: str,
        file_hash: str,
        file_size: int,
        mime_type: str,
        version_number: int = 1
    ) -> Resume:
        """Create a new resume record."""
        resume = Resume(
            candidate_id=candidate_id,  # NEW: Link to candidate
            uploaded_by_user_id=uploaded_by_user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            version_number=version_number,
            status=ResumeStatus.PENDING.value,
            uploaded_at=utc_now()
        )
        
        self.session.add(resume)
        await self.session.flush()  # Get ID without committing
        return resume
    
    async def update_status(
        self,
        resume_id: uuid.UUID,
        status: ResumeStatus,
        error_message: Optional[str] = None
    ) -> Optional[Resume]:
        """Update resume processing status."""
        resume = await self.get_by_id(resume_id)
        if not resume:
            return None
        
        resume.status = status.value
        
        if status == ResumeStatus.COMPLETED:
            resume.processed_at = utc_now()
        
        await self.session.flush()
        return resume
    
    async def update_extracted_content(
        self,
        resume_id: uuid.UUID,
        extracted_text: str,
        word_count: Optional[int] = None
    ) -> Optional[Resume]:
        """Update extracted text and word count."""
        resume = await self.get_by_id(resume_id)
        if not resume:
            return None
        
        resume.extracted_text = extracted_text
        resume.word_count = word_count or len(extracted_text.split())
        resume.status = ResumeStatus.COMPLETED.value
        resume.processed_at = utc_now()
        resume.progress = 100
        
        await self.session.flush()
        return resume
    
    async def get_by_candidate(
        self,
        candidate_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[Resume]:
        """Get resumes for a specific candidate."""
        query = (
            self.session.query(Resume)
            .filter(Resume.candidate_id == candidate_id)
            .order_by(desc(Resume.uploaded_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_by_user_and_candidate(
        self,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[Resume]:
        """Get resumes uploaded by a specific user for a specific candidate."""
        query = (
            self.session.query(Resume)
            .filter(
                and_(
                    Resume.uploaded_by_user_id == user_id,
                    Resume.candidate_id == candidate_id
                )
            )
            .order_by(desc(Resume.uploaded_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_latest_version_for_candidate(
        self,
        candidate_id: uuid.UUID
    ) -> Optional[Resume]:
        """Get the latest version resume for a candidate."""
        query = (
            self.session.query(Resume)
            .filter(Resume.candidate_id == candidate_id)
            .order_by(desc(Resume.version_number), desc(Resume.uploaded_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_next_version_number(
        self,
        candidate_id: uuid.UUID
    ) -> int:
        """Get the next version number for a candidate's resume."""
        query = (
            self.session.query(Resume.version_number)
            .filter(Resume.candidate_id == candidate_id)
            .order_by(desc(Resume.version_number))
            .limit(1)
        )
        result = await self.session.execute(query)
        latest_version = result.scalar_one_or_none()
        return (latest_version or 0) + 1
    
    async def check_duplicate_hash(
        self,
        candidate_id: uuid.UUID,
        file_hash: str
    ) -> Optional[Resume]:
        """Check if a resume with the same hash already exists for this candidate."""
        query = (
            self.session.query(Resume)
            .filter(
                and_(
                    Resume.candidate_id == candidate_id,
                    Resume.file_hash == file_hash
                )
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_candidate_resume_stats(self, candidate_id: uuid.UUID) -> dict:
        """Get resume statistics for a candidate."""
        query = self.session.query(Resume).filter(Resume.candidate_id == candidate_id)
        result = await self.session.execute(query)
        resumes = list(result.scalars().all())
        
        total_count = len(resumes)
        completed_count = sum(1 for r in resumes if r.status == ResumeStatus.COMPLETED.value)
        error_count = sum(1 for r in resumes if r.status == ResumeStatus.ERROR.value)
        total_size = sum(r.file_size for r in resumes)
        
        return {
            "total_resumes": total_count,
            "completed_resumes": completed_count,
            "failed_resumes": error_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "latest_version": max((r.version_number for r in resumes), default=0)
        }
    
    async def delete_old_resumes(
        self,
        candidate_id: uuid.UUID,
        keep_latest: int = 5
    ) -> int:
        """Delete old resume versions, keeping only the latest N versions."""
        query = (
            self.session.query(Resume)
            .filter(Resume.candidate_id == candidate_id)
            .order_by(desc(Resume.version_number), desc(Resume.uploaded_at))
            .offset(keep_latest)
        )
        result = await self.session.execute(query)
        old_resumes = list(result.scalars().all())
        
        count = len(old_resumes)
        for resume in old_resumes:
            await self.session.delete(resume)
        
        await self.session.flush()
        return count