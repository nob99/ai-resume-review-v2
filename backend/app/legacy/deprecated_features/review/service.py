"""
Review Service - Business logic orchestrator for the review feature.
Coordinates repositories, AI integration, and background tasks.
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import ReviewRequestRepository, ReviewResultRepository, ReviewFeedbackRepository
from .ai_integration import AIIntegrationService
from .background_tasks import ReviewTaskManager
from app.core.datetime_utils import utc_now
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.resume import Resume

# Configure logging
logger = logging.getLogger(__name__)


class ReviewService:
    """Service class for managing review operations and business logic."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the review service.
        
        Args:
            session: Database session for operations
        """
        self.session = session
        self.request_repo = ReviewRequestRepository(session)
        self.result_repo = ReviewResultRepository(session)
        self.feedback_repo = ReviewFeedbackRepository(session)
        self.ai_service = AIIntegrationService()
        self.task_manager = ReviewTaskManager()
    
    async def create_review_request(
        self,
        resume_id: UUID,
        requested_by_user_id: UUID,
        target_industry: str,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None,
        review_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Create a new review request and validate inputs.
        
        Args:
            resume_id: ID of the resume to review
            requested_by_user_id: ID of the user requesting the review
            target_industry: Target industry for the review
            target_role: Optional target role
            experience_level: Optional experience level
            review_type: Type of review to perform
            
        Returns:
            Dict with created review request details
        """
        try:
            # Validate resume exists
            resume = await self._get_resume_by_id(resume_id)
            if not resume:
                raise HTTPException(status_code=404, detail="Resume not found")
            
            if not resume.extracted_text or not resume.extracted_text.strip():
                raise HTTPException(status_code=400, detail="Resume has no extractable text")
            
            # Create the review request
            review_request = await self.request_repo.create_review_request(
                resume_id=resume_id,
                requested_by_user_id=requested_by_user_id,
                target_role=target_role,
                target_industry=target_industry,
                experience_level=experience_level,
                review_type=review_type
            )
            
            await self.session.commit()
            
            logger.info(f"Created review request {review_request.id} for resume {resume_id}")
            
            return {
                "id": review_request.id,
                "resume_id": review_request.resume_id,
                "requested_by_user_id": review_request.requested_by_user_id,
                "target_role": review_request.target_role,
                "target_industry": review_request.target_industry,
                "experience_level": review_request.experience_level,
                "review_type": review_request.review_type,
                "status": review_request.status,
                "requested_at": review_request.requested_at,
                "completed_at": review_request.completed_at
            }
            
        except HTTPException:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating review request: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create review request")
    
    async def submit_for_processing(
        self,
        review_request_id: UUID,
        background_tasks: BackgroundTasks
    ) -> Dict[str, Any]:
        """
        Submit a review request for background processing.
        
        Args:
            review_request_id: ID of the review request to process
            background_tasks: FastAPI BackgroundTasks instance
            
        Returns:
            Dict with submission status
        """
        try:
            # Get the review request
            review_request = await self.request_repo.get_by_id(review_request_id)
            if not review_request:
                raise HTTPException(status_code=404, detail="Review request not found")
            
            if review_request.status != "pending":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Review request is already {review_request.status}"
                )
            
            # Get the resume
            resume = await self._get_resume_by_id(review_request.resume_id)
            if not resume or not resume.extracted_text:
                raise HTTPException(status_code=400, detail="Resume text not available")
            
            # Submit for background processing
            result = await self.task_manager.submit_review_for_processing(
                background_tasks=background_tasks,
                review_request_id=review_request_id,
                resume_id=review_request.resume_id,
                industry=review_request.target_industry,
                target_role=review_request.target_role,
                experience_level=review_request.experience_level
            )
            
            if result["success"]:
                logger.info(f"Successfully submitted review request {review_request_id} for processing")
            else:
                logger.error(f"Failed to submit review request {review_request_id}: {result.get('error')}")
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting review for processing: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to submit review for processing")
    
    async def get_review_request(self, review_request_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Get review request details with authorization check.
        
        Args:
            review_request_id: ID of the review request
            user_id: ID of the requesting user
            
        Returns:
            Dict with review request details
        """
        try:
            review_request = await self.request_repo.get_by_id(review_request_id)
            if not review_request:
                raise HTTPException(status_code=404, detail="Review request not found")
            
            # Authorization check - user must be the one who requested it
            if review_request.requested_by_user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Get processing status
            status_info = await self.task_manager.get_task_status(review_request_id)
            
            return {
                "id": review_request.id,
                "resume_id": review_request.resume_id,
                "requested_by_user_id": review_request.requested_by_user_id,
                "target_role": review_request.target_role,
                "target_industry": review_request.target_industry,
                "experience_level": review_request.experience_level,
                "review_type": review_request.review_type,
                "status": review_request.status,
                "requested_at": review_request.requested_at,
                "completed_at": review_request.completed_at,
                "processing_info": status_info
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting review request: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get review request")
    
    async def get_review_results(
        self, 
        review_request_id: UUID, 
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get review results with raw AI response for frontend consumption.
        
        Args:
            review_request_id: ID of the review request
            user_id: ID of the requesting user
            
        Returns:
            Dict with complete review results including raw AI response
        """
        try:
            # Verify access to review request
            review_request = await self.request_repo.get_by_id(review_request_id)
            if not review_request:
                raise HTTPException(status_code=404, detail="Review request not found")
            
            if review_request.requested_by_user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Get review result
            review_result = await self.result_repo.get_by_review_request_id(review_request_id)
            if not review_result:
                if review_request.status == "pending":
                    raise HTTPException(status_code=202, detail="Review is pending processing")
                elif review_request.status == "processing":
                    raise HTTPException(status_code=202, detail="Review is currently being processed")
                elif review_request.status == "failed":
                    raise HTTPException(status_code=500, detail="Review processing failed")
                else:
                    raise HTTPException(status_code=404, detail="Review results not found")
            
            # Return complete review data with raw AI response
            result_data = await self.result_repo.get_review_with_raw_response(review_result.id)
            
            logger.info(f"Retrieved review results for request {review_request_id}")
            
            return result_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting review results: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get review results")
    
    async def get_user_reviews(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all review requests for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of review request dictionaries
        """
        try:
            review_requests = await self.request_repo.get_by_user_id(user_id)
            
            results = []
            for request in review_requests:
                # Get basic result info if available
                review_result = await self.result_repo.get_by_review_request_id(request.id)
                
                result_summary = None
                if review_result:
                    result_summary = {
                        "overall_score": review_result.overall_score,
                        "processing_time_ms": review_result.processing_time_ms,
                        "ai_model_used": review_result.ai_model_used,
                        "created_at": review_result.created_at
                    }
                
                results.append({
                    "id": request.id,
                    "resume_id": request.resume_id,
                    "target_role": request.target_role,
                    "target_industry": request.target_industry,
                    "experience_level": request.experience_level,
                    "review_type": request.review_type,
                    "status": request.status,
                    "requested_at": request.requested_at,
                    "completed_at": request.completed_at,
                    "result_summary": result_summary
                })
            
            logger.info(f"Retrieved {len(results)} review requests for user {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error getting user reviews: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get user reviews")
    
    async def get_resume_reviews(self, resume_id: UUID, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all review requests for a specific resume.
        
        Args:
            resume_id: ID of the resume
            user_id: ID of the requesting user (for authorization)
            
        Returns:
            List of review request dictionaries
        """
        try:
            # Verify user has access to this resume
            resume = await self._get_resume_by_id(resume_id)
            if not resume:
                raise HTTPException(status_code=404, detail="Resume not found")
            
            # TODO: Add proper authorization check for resume access
            # For now, we'll get reviews and filter by user
            
            review_requests = await self.request_repo.get_by_resume_id(resume_id)
            
            # Filter by user access
            user_requests = [req for req in review_requests if req.requested_by_user_id == user_id]
            
            results = []
            for request in user_requests:
                review_result = await self.result_repo.get_by_review_request_id(request.id)
                
                result_summary = None
                if review_result:
                    result_summary = {
                        "overall_score": review_result.overall_score,
                        "executive_summary": review_result.executive_summary,
                        "processing_time_ms": review_result.processing_time_ms,
                        "created_at": review_result.created_at
                    }
                
                results.append({
                    "id": request.id,
                    "target_role": request.target_role,
                    "target_industry": request.target_industry,
                    "experience_level": request.experience_level,
                    "review_type": request.review_type,
                    "status": request.status,
                    "requested_at": request.requested_at,
                    "completed_at": request.completed_at,
                    "result_summary": result_summary
                })
            
            logger.info(f"Retrieved {len(results)} review requests for resume {resume_id}")
            return results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting resume reviews: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get resume reviews")
    
    async def test_ai_connection(self) -> Dict[str, Any]:
        """
        Test AI service connection and functionality.
        
        Returns:
            Dict with test results
        """
        try:
            test_result = await self.ai_service.test_connection()
            logger.info("AI connection test completed")
            return test_result
            
        except Exception as e:
            logger.error(f"Error testing AI connection: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "AI connection test failed"
            }
    
    async def _get_resume_by_id(self, resume_id: UUID) -> Optional[Resume]:
        """
        Get resume by ID from database.
        
        Args:
            resume_id: ID of the resume
            
        Returns:
            Resume instance if found, None otherwise
        """
        try:
            from sqlalchemy import select
            query = select(Resume).where(Resume.id == resume_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching resume {resume_id}: {str(e)}")
            return None