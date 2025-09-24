"""
Background task infrastructure for review processing.
Handles asynchronous resume analysis with AI agents.
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from .repository import ReviewRequestRepository, ReviewResultRepository
from .ai_integration import AIIntegrationService
from app.core.datetime_utils import utc_now
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from infrastructure.persistence.postgres.connection import get_async_session

# Configure logging
logger = logging.getLogger(__name__)


class ReviewBackgroundTaskService:
    """Service for managing background review processing tasks."""
    
    def __init__(self):
        """Initialize the background task service."""
        self.ai_service = AIIntegrationService()
    
    async def process_review_async(
        self,
        review_request_id: UUID,
        resume_text: str,
        industry: str,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> None:
        """
        Process a review request asynchronously in the background.
        
        Args:
            review_request_id: ID of the review request to process
            resume_text: Resume text to analyze
            industry: Target industry for analysis
            target_role: Optional target role
            experience_level: Optional experience level
        """
        logger.info(f"Starting background review processing for request {review_request_id}")
        
        # Get database session
        async with get_db_session() as session:
            try:
                # Initialize repositories
                request_repo = ReviewRequestRepository(session)
                result_repo = ReviewResultRepository(session)
                
                # Update request status to processing
                await request_repo.update_request_status(review_request_id, "processing")
                await session.commit()
                
                logger.info(f"Updated request {review_request_id} status to processing")
                
                # Call AI service for analysis
                raw_ai_response = await self.ai_service.analyze_resume(
                    resume_text=resume_text,
                    industry=industry,
                    review_request_id=review_request_id,
                    target_role=target_role,
                    experience_level=experience_level
                )
                
                logger.info(f"AI analysis completed for request {review_request_id}")
                
                # Extract essential fields
                essential_fields = self.ai_service.extract_essential_fields(raw_ai_response)
                
                # Create review result with raw AI response
                review_result = await result_repo.create_review_result(
                    review_request_id=review_request_id,
                    raw_ai_response=raw_ai_response,
                    overall_score=essential_fields["overall_score"],
                    executive_summary=essential_fields["executive_summary"],
                    ai_model_used=essential_fields["ai_model_used"],
                    processing_time_ms=essential_fields["processing_time_ms"]
                )
                
                # Update request status to completed
                await request_repo.update_request_status(review_request_id, "completed")
                
                # Commit all changes
                await session.commit()
                
                logger.info(f"Successfully completed review processing for request {review_request_id}, "
                           f"result ID: {review_result.id}")
                
            except Exception as e:
                logger.error(f"Error processing review request {review_request_id}: {str(e)}", exc_info=True)
                
                try:
                    # Update request status to failed
                    await request_repo.update_request_status(review_request_id, "failed")
                    await session.commit()
                    logger.info(f"Marked request {review_request_id} as failed")
                except Exception as commit_error:
                    logger.error(f"Failed to mark request {review_request_id} as failed: {str(commit_error)}")
                    await session.rollback()
    
    def schedule_review_processing(
        self,
        background_tasks: BackgroundTasks,
        review_request_id: UUID,
        resume_text: str,
        industry: str,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> None:
        """
        Schedule a review for background processing.
        
        Args:
            background_tasks: FastAPI BackgroundTasks instance
            review_request_id: ID of the review request
            resume_text: Resume text to analyze
            industry: Target industry
            target_role: Optional target role
            experience_level: Optional experience level
        """
        logger.info(f"Scheduling background processing for review request {review_request_id}")
        
        background_tasks.add_task(
            self.process_review_async,
            review_request_id=review_request_id,
            resume_text=resume_text,
            industry=industry,
            target_role=target_role,
            experience_level=experience_level
        )
    
    async def get_processing_status(self, review_request_id: UUID) -> Dict[str, Any]:
        """
        Get the current processing status of a review request.
        
        Args:
            review_request_id: ID of the review request
            
        Returns:
            Dict with processing status information
        """
        async with get_db_session() as session:
            try:
                request_repo = ReviewRequestRepository(session)
                result_repo = ReviewResultRepository(session)
                
                # Get the review request
                review_request = await request_repo.get_by_id(review_request_id)
                if not review_request:
                    return {
                        "found": False,
                        "error": "Review request not found"
                    }
                
                # Check if there's a result
                review_result = await result_repo.get_by_review_request_id(review_request_id)
                
                status_info = {
                    "found": True,
                    "request_id": review_request.id,
                    "status": review_request.status,
                    "requested_at": review_request.requested_at,
                    "completed_at": review_request.completed_at,
                    "has_result": review_result is not None
                }
                
                if review_result:
                    status_info.update({
                        "result_id": review_result.id,
                        "overall_score": review_result.overall_score,
                        "processing_time_ms": review_result.processing_time_ms,
                        "ai_model_used": review_result.ai_model_used
                    })
                
                return status_info
                
            except Exception as e:
                logger.error(f"Error getting status for review request {review_request_id}: {str(e)}")
                return {
                    "found": False,
                    "error": str(e)
                }


class ReviewTaskManager:
    """Manager for review processing tasks with error handling and monitoring."""
    
    def __init__(self):
        """Initialize the task manager."""
        self.task_service = ReviewBackgroundTaskService()
    
    async def submit_review_for_processing(
        self,
        background_tasks: BackgroundTasks,
        review_request_id: UUID,
        resume_id: UUID,
        industry: str,
        target_role: Optional[str] = None,
        experience_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a review request for background processing.
        
        Args:
            background_tasks: FastAPI BackgroundTasks instance
            review_request_id: ID of the review request
            resume_id: ID of the resume to process
            industry: Target industry
            target_role: Optional target role
            experience_level: Optional experience level
            
        Returns:
            Dict with submission status
        """
        try:
            # Get database session to fetch resume text
            async with get_db_session() as session:
                # TODO: Import and use Resume model to get extracted_text
                # For now, we'll need to add this import when Resume model is available
                # from database.models.resume import Resume
                # resume = await session.get(Resume, resume_id)
                # resume_text = resume.extracted_text if resume else ""
                
                # Placeholder for resume text fetching
                # In actual implementation, this will fetch from Resume model
                resume_text = "Placeholder resume text - will be fetched from Resume model"
                
                # Schedule the background task
                self.task_service.schedule_review_processing(
                    background_tasks=background_tasks,
                    review_request_id=review_request_id,
                    resume_text=resume_text,
                    industry=industry,
                    target_role=target_role,
                    experience_level=experience_level
                )
                
                logger.info(f"Successfully submitted review request {review_request_id} for processing")
                
                return {
                    "success": True,
                    "review_request_id": review_request_id,
                    "status": "submitted_for_processing",
                    "message": "Review has been queued for background processing"
                }
                
        except Exception as e:
            logger.error(f"Error submitting review {review_request_id} for processing: {str(e)}")
            return {
                "success": False,
                "review_request_id": review_request_id,
                "error": str(e),
                "message": "Failed to submit review for processing"
            }
    
    async def get_task_status(self, review_request_id: UUID) -> Dict[str, Any]:
        """
        Get the status of a background task.
        
        Args:
            review_request_id: ID of the review request
            
        Returns:
            Dict with task status information
        """
        return await self.task_service.get_processing_status(review_request_id)


# Database session helper
async def get_db_session():
    """
    Get async database session for background tasks.
    
    Returns:
        Async context manager for database session
    """
    # Import here to avoid circular imports
    from infrastructure.persistence.postgres.connection import get_async_session
    
    # Create an async session
    session = get_async_session()
    
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Global instances for use in API routes
review_task_service = ReviewBackgroundTaskService()
review_task_manager = ReviewTaskManager()