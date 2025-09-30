"""Resume analysis repository for database operations using two-table architecture."""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import desc, and_, func, select

from app.core.database import BaseRepository
from app.core.datetime_utils import utc_now
from database.models import ReviewRequest, ReviewResult, ReviewFeedbackItem


class ReviewRequestRepository(BaseRepository[ReviewRequest]):
    """Repository for review requests (Schema v1.1)"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewRequest)

    async def create_review_request(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        target_industry: str,
        review_type: str = "comprehensive"
    ) -> ReviewRequest:
        """Create a new review request"""
        request = ReviewRequest(
            resume_id=resume_id,
            requested_by_user_id=user_id,
            target_industry=target_industry,
            review_type=review_type,
            status="pending",
            requested_at=utc_now()
        )

        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def update_status(
        self,
        request_id: uuid.UUID,
        status: str,
        completed_at: Optional[datetime] = None
    ) -> ReviewRequest:
        """Update request status"""
        request = await self.get_by_id(request_id)
        if not request:
            raise ValueError(f"Review request {request_id} not found")

        request.status = status
        if completed_at:
            request.completed_at = completed_at
        elif status == "completed":
            request.completed_at = utc_now()

        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get_by_resume_and_user(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ReviewRequest]:
        """Get recent request for resume by user"""
        query = select(ReviewRequest).where(
            and_(
                ReviewRequest.resume_id == resume_id,
                ReviewRequest.requested_by_user_id == user_id
            )
        ).order_by(desc(ReviewRequest.requested_at))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[ReviewRequest]:
        """Get requests by user with optional filtering"""
        query = select(ReviewRequest).where(ReviewRequest.requested_by_user_id == user_id)

        if status:
            query = query.where(ReviewRequest.status == status)

        if industry:
            query = query.where(ReviewRequest.target_industry == industry)

        if candidate_id:
            # Join with resumes table to filter by candidate_id
            from database.models import Resume
            query = query.join(Resume, ReviewRequest.resume_id == Resume.id)
            query = query.where(Resume.candidate_id == candidate_id)

        query = query.order_by(desc(ReviewRequest.requested_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_pending_requests(self, user_id: uuid.UUID) -> List[ReviewRequest]:
        """Get all pending/processing requests for a user"""
        query = select(ReviewRequest).where(
            and_(
                ReviewRequest.requested_by_user_id == user_id,
                ReviewRequest.status.in_(["pending", "processing"])
            )
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None
    ) -> int:
        """Count total requests by user with optional filtering"""
        query = select(func.count(ReviewRequest.id)).where(ReviewRequest.requested_by_user_id == user_id)

        if status:
            query = query.where(ReviewRequest.status == status)

        if industry:
            query = query.where(ReviewRequest.target_industry == industry)

        if candidate_id:
            # Join with resumes table to filter by candidate_id
            from database.models import Resume
            query = query.join(Resume, ReviewRequest.resume_id == Resume.id)
            query = query.where(Resume.candidate_id == candidate_id)

        result = await self.session.execute(query)
        return result.scalar() or 0


class ReviewResultRepository(BaseRepository[ReviewResult]):
    """Repository for review results (Schema v1.1)"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewResult)

    async def save_analysis_results(
        self,
        request_id: uuid.UUID,
        overall_score: int,
        ats_score: int,
        content_score: int,
        formatting_score: int,
        executive_summary: str,
        detailed_scores: dict,
        ai_model_used: str,
        processing_time_ms: int
    ) -> ReviewResult:
        """Save analysis results with granular scoring"""
        result = ReviewResult(
            review_request_id=request_id,
            overall_score=overall_score,
            ats_score=ats_score,
            content_score=content_score,
            formatting_score=formatting_score,
            executive_summary=executive_summary,
            detailed_scores=detailed_scores,
            ai_model_used=ai_model_used,
            processing_time_ms=processing_time_ms,
            created_at=utc_now()
        )

        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_by_request_id(self, request_id: uuid.UUID) -> Optional[ReviewResult]:
        """Get result by request ID"""
        query = select(ReviewResult).where(ReviewResult.review_request_id == request_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_feedback(self, request_id: uuid.UUID) -> Optional[ReviewResult]:
        """Get result with feedback items"""
        query = select(ReviewResult).options(
            selectinload(ReviewResult.feedback_items)
        ).where(ReviewResult.review_request_id == request_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class AnalysisRepository:
    """Updated repository using two-table architecture"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.request_repo = ReviewRequestRepository(session)
        self.result_repo = ReviewResultRepository(session)

    async def create_analysis(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        target_industry: str,
        review_type: str = "comprehensive"
    ) -> ReviewRequest:
        """Create analysis request (Step 1 of 2)"""
        return await self.request_repo.create_review_request(
            user_id=user_id,
            resume_id=resume_id,
            target_industry=target_industry,
            review_type=review_type
        )

    async def save_results(
        self,
        request_id: uuid.UUID,
        overall_score: int,
        ats_score: int,
        content_score: int,
        formatting_score: int,
        executive_summary: str,
        detailed_scores: dict,
        ai_model_used: str,
        processing_time_ms: int
    ) -> ReviewResult:
        """Save analysis results with granular scoring (Step 2 of 2)"""
        # Save results
        result = await self.result_repo.save_analysis_results(
            request_id=request_id,
            overall_score=overall_score,
            ats_score=ats_score,
            content_score=content_score,
            formatting_score=formatting_score,
            executive_summary=executive_summary,
            detailed_scores=detailed_scores,
            ai_model_used=ai_model_used,
            processing_time_ms=processing_time_ms
        )

        # Update request status
        await self.request_repo.update_status(
            request_id=request_id,
            status="completed",
            completed_at=utc_now()
        )

        return result

    async def get_analysis_with_results(self, request_id: uuid.UUID) -> Optional[Tuple[ReviewRequest, Optional[ReviewResult]]]:
        """Get complete analysis data"""
        request = await self.request_repo.get_by_id(request_id)
        if not request:
            return None

        result = await self.result_repo.get_by_request_id(request_id)
        return (request, result)

    async def update_request_status(
        self,
        request_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None
    ) -> ReviewRequest:
        """Update request status with optional error message"""
        request = await self.request_repo.update_status(request_id, status)

        # For now, we don't have an error field in ReviewRequest
        # This could be added to detailed_scores or handled differently
        if error_message and status == "failed":
            # We could store error in a result record or handle it differently
            pass

        return request

    async def get_user_analyses(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[ReviewRequest]:
        """Get user's analysis requests"""
        return await self.request_repo.get_by_user(
            user_id=user_id,
            status=status,
            industry=industry,
            candidate_id=candidate_id,
            limit=limit,
            offset=offset
        )

    async def count_user_analyses(
        self,
        user_id: uuid.UUID,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        candidate_id: Optional[uuid.UUID] = None
    ) -> int:
        """Count user's analysis requests"""
        return await self.request_repo.count_by_user(
            user_id=user_id,
            status=status,
            industry=industry,
            candidate_id=candidate_id
        )

    async def get_recent_analyses(
        self,
        user_id: uuid.UUID,
        hours: int = 24,
        limit: int = 10
    ) -> List[ReviewRequest]:
        """Get recent analyses within specified hours"""
        cutoff_time = utc_now() - timedelta(hours=hours)

        query = select(ReviewRequest).where(
            and_(
                ReviewRequest.requested_by_user_id == user_id,
                ReviewRequest.requested_at >= cutoff_time
            )
        ).order_by(desc(ReviewRequest.requested_at)).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_stats(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get analysis statistics for a user"""
        # Get all requests for user
        requests = await self.request_repo.get_by_user(user_id, limit=1000)

        total_count = len(requests)
        completed_count = sum(1 for r in requests if r.status == "completed")
        failed_count = sum(1 for r in requests if r.status == "failed")

        # Get results for completed requests
        completed_request_ids = [r.id for r in requests if r.status == "completed"]

        average_score = None
        industry_breakdown = {}
        score_breakdown = {}

        if completed_request_ids:
            # Get results for completed requests
            query = select(ReviewResult).where(
                ReviewResult.review_request_id.in_(completed_request_ids)
            )
            result = await self.session.execute(query)
            results = result.scalars().all()

            # Calculate average score
            scores = [r.overall_score for r in results if r.overall_score is not None]
            if scores:
                average_score = sum(scores) / len(scores)

            # Score breakdown
            for score in scores:
                range_key = f"{score//10*10}-{score//10*10+9}"
                score_breakdown[range_key] = score_breakdown.get(range_key, 0) + 1

        # Industry breakdown
        for request in requests:
            industry = request.target_industry
            industry_breakdown[industry] = industry_breakdown.get(industry, 0) + 1

        return {
            "total_analyses": total_count,
            "completed_analyses": completed_count,
            "failed_analyses": failed_count,
            "average_score": round(average_score, 2) if average_score else None,
            "industry_breakdown": industry_breakdown,
            "score_breakdown": score_breakdown
        }

    async def get_pending_analyses(self, user_id: uuid.UUID) -> List[ReviewRequest]:
        """Get all pending analyses for a user"""
        return await self.request_repo.get_pending_requests(user_id)