"""
Repository for review feature - handles ReviewRequest and ReviewResult data access.
Implements storage for raw AI responses with JSONB support.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.persistence.postgres.base import BaseRepository
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.review import ReviewRequest, ReviewResult, ReviewFeedbackItem
from app.core.datetime_utils import utc_now


class ReviewRequestRepository(BaseRepository[ReviewRequest]):
    """Repository for ReviewRequest model operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewRequest)
    
    async def create_review_request(
        self,
        resume_id: UUID,
        requested_by_user_id: UUID,
        target_role: Optional[str] = None,
        target_industry: Optional[str] = None,
        experience_level: Optional[str] = None,
        review_type: str = "comprehensive"
    ) -> ReviewRequest:
        """
        Create a new review request.
        
        Args:
            resume_id: ID of the resume to review
            requested_by_user_id: ID of the user requesting the review
            target_role: Optional target role for the review
            target_industry: Optional target industry
            experience_level: Optional experience level
            review_type: Type of review (comprehensive, quick_scan, ats_check)
            
        Returns:
            Created ReviewRequest instance
        """
        review_request = ReviewRequest(
            resume_id=resume_id,
            requested_by_user_id=requested_by_user_id,
            target_role=target_role,
            target_industry=target_industry,
            experience_level=experience_level,
            review_type=review_type,
            status="pending",
            requested_at=utc_now()
        )
        
        self.session.add(review_request)
        await self.session.flush()
        return review_request
    
    async def update_request_status(self, id: UUID, status: str) -> Optional[ReviewRequest]:
        """
        Update the status of a review request.
        
        Args:
            id: Review request ID
            status: New status (pending, processing, completed, failed)
            
        Returns:
            Updated ReviewRequest if found, None otherwise
        """
        review_request = await self.get_by_id(id)
        if review_request:
            review_request.status = status
            if status in ["completed", "failed"]:
                review_request.completed_at = utc_now()
            await self.session.flush()
        return review_request
    
    async def get_by_resume_id(self, resume_id: UUID) -> List[ReviewRequest]:
        """
        Get all review requests for a specific resume.
        
        Args:
            resume_id: Resume ID
            
        Returns:
            List of ReviewRequest instances
        """
        query = select(ReviewRequest).where(ReviewRequest.resume_id == resume_id)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_user_id(self, user_id: UUID) -> List[ReviewRequest]:
        """
        Get all review requests created by a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of ReviewRequest instances
        """
        query = select(ReviewRequest).where(ReviewRequest.requested_by_user_id == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_pending_requests(self) -> List[ReviewRequest]:
        """
        Get all pending review requests for processing.
        
        Returns:
            List of pending ReviewRequest instances
        """
        query = select(ReviewRequest).where(ReviewRequest.status == "pending")
        result = await self.session.execute(query)
        return result.scalars().all()


class ReviewResultRepository(BaseRepository[ReviewResult]):
    """Repository for ReviewResult model operations with raw AI response support."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewResult)
    
    async def create_review_result(
        self,
        review_request_id: UUID,
        raw_ai_response: Dict[str, Any],
        overall_score: Optional[int] = None,
        executive_summary: Optional[str] = None,
        ai_model_used: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> ReviewResult:
        """
        Create a new review result with raw AI response.
        
        Args:
            review_request_id: ID of the review request
            raw_ai_response: Complete raw AI response JSON
            overall_score: Optional overall score (0-100)
            executive_summary: Optional executive summary
            ai_model_used: AI model identifier
            processing_time_ms: Processing time in milliseconds
            
        Returns:
            Created ReviewResult instance
        """
        # Extract essential fields from raw AI response if not provided
        if overall_score is None and raw_ai_response:
            overall_score = raw_ai_response.get("overall_score")
        
        if executive_summary is None and raw_ai_response:
            executive_summary = raw_ai_response.get("summary")
        
        review_result = ReviewResult(
            review_request_id=review_request_id,
            raw_ai_response=raw_ai_response,
            overall_score=overall_score,
            executive_summary=executive_summary,
            ai_model_used=ai_model_used,
            processing_time_ms=processing_time_ms,
            created_at=utc_now()
        )
        
        self.session.add(review_result)
        await self.session.flush()
        return review_result
    
    async def get_by_review_request_id(self, review_request_id: UUID) -> Optional[ReviewResult]:
        """
        Get review result by review request ID.
        
        Args:
            review_request_id: Review request ID
            
        Returns:
            ReviewResult if found, None otherwise
        """
        query = select(ReviewResult).where(ReviewResult.review_request_id == review_request_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_review_with_raw_response(self, id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get review result with raw AI response for frontend consumption.
        
        Args:
            id: ReviewResult ID
            
        Returns:
            Dict with review data including raw AI response, None if not found
        """
        review_result = await self.get_by_id(id)
        if not review_result:
            return None
        
        return {
            "id": review_result.id,
            "review_request_id": review_result.review_request_id,
            "overall_score": review_result.overall_score,
            "executive_summary": review_result.executive_summary,
            "raw_ai_response": review_result.raw_ai_response,
            "ai_model_used": review_result.ai_model_used,
            "processing_time_ms": review_result.processing_time_ms,
            "created_at": review_result.created_at
        }
    
    async def update_raw_ai_response(
        self, 
        id: UUID, 
        raw_ai_response: Dict[str, Any]
    ) -> Optional[ReviewResult]:
        """
        Update the raw AI response for an existing review result.
        
        Args:
            id: ReviewResult ID
            raw_ai_response: Updated raw AI response JSON
            
        Returns:
            Updated ReviewResult if found, None otherwise
        """
        review_result = await self.get_by_id(id)
        if review_result:
            review_result.raw_ai_response = raw_ai_response
            # Update extracted fields if they exist in the new response
            if "overall_score" in raw_ai_response:
                review_result.overall_score = raw_ai_response["overall_score"]
            if "summary" in raw_ai_response:
                review_result.executive_summary = raw_ai_response["summary"]
            await self.session.flush()
        return review_result


class ReviewFeedbackRepository(BaseRepository[ReviewFeedbackItem]):
    """Repository for ReviewFeedbackItem model operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ReviewFeedbackItem)
    
    async def create_feedback_item(
        self,
        review_result_id: UUID,
        feedback_type: str,
        category: str,
        feedback_text: str,
        severity_level: int = 3,
        resume_section_id: Optional[UUID] = None,
        original_text: Optional[str] = None,
        suggested_text: Optional[str] = None,
        confidence_score: Optional[int] = None
    ) -> ReviewFeedbackItem:
        """
        Create a new review feedback item.
        
        Args:
            review_result_id: ID of the review result
            feedback_type: Type of feedback (strength, weakness, suggestion, error)
            category: Category (content, formatting, keywords, grammar)
            feedback_text: The feedback text
            severity_level: Severity level (1-5)
            resume_section_id: Optional resume section ID
            original_text: Optional original text being referenced
            suggested_text: Optional suggested improvement
            confidence_score: Optional AI confidence score (0-100)
            
        Returns:
            Created ReviewFeedbackItem instance
        """
        feedback_item = ReviewFeedbackItem(
            review_result_id=review_result_id,
            resume_section_id=resume_section_id,
            feedback_type=feedback_type,
            category=category,
            feedback_text=feedback_text,
            severity_level=severity_level,
            original_text=original_text,
            suggested_text=suggested_text,
            confidence_score=confidence_score
        )
        
        self.session.add(feedback_item)
        await self.session.flush()
        return feedback_item
    
    async def get_by_review_result_id(self, review_result_id: UUID) -> List[ReviewFeedbackItem]:
        """
        Get all feedback items for a review result.
        
        Args:
            review_result_id: Review result ID
            
        Returns:
            List of ReviewFeedbackItem instances
        """
        query = select(ReviewFeedbackItem).where(
            ReviewFeedbackItem.review_result_id == review_result_id
        )
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_critical_feedback(self, review_result_id: UUID) -> List[ReviewFeedbackItem]:
        """
        Get critical feedback items (severity 4 or 5) for a review result.
        
        Args:
            review_result_id: Review result ID
            
        Returns:
            List of critical ReviewFeedbackItem instances
        """
        query = select(ReviewFeedbackItem).where(
            and_(
                ReviewFeedbackItem.review_result_id == review_result_id,
                ReviewFeedbackItem.severity_level >= 4
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()