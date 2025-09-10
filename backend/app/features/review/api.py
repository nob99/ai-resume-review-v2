"""
API endpoints for review feature.
Handles HTTP requests for resume review operations.
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from .service import ReviewService
from .schemas import (
    CreateReviewRequest, ReviewRequestResponse, ReviewResultResponse,
    ReviewListResponse, TaskSubmissionResponse, AIConnectionTestResponse,
    ErrorResponse, ParsedAIResponse
)
from app.features.auth.api import get_current_user
from infrastructure.persistence.postgres.connection import get_async_session as get_db
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.auth import User

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/reviews", tags=["reviews"])


# Dependency to get review service
async def get_review_service(session: AsyncSession = Depends(get_db)) -> ReviewService:
    """Get ReviewService instance with database session."""
    return ReviewService(session)


@router.post(
    "/request",
    response_model=ReviewRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Review Request",
    description="Create a new review request for a resume analysis"
)
async def create_review_request(
    request: CreateReviewRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> ReviewRequestResponse:
    """
    Create a new review request and optionally start processing.
    
    - **resume_id**: ID of the resume to analyze
    - **target_industry**: Industry to target in the analysis
    - **target_role**: Optional specific role to target
    - **experience_level**: Optional experience level context
    - **review_type**: Type of review (comprehensive, quick_scan, ats_check)
    """
    try:
        # Create the review request
        review_data = await review_service.create_review_request(
            resume_id=request.resume_id,
            requested_by_user_id=current_user.id,
            target_industry=request.target_industry,
            target_role=request.target_role,
            experience_level=request.experience_level.value if request.experience_level else None,
            review_type=request.review_type.value
        )
        
        logger.info(f"Created review request {review_data['id']} for user {current_user.id}")
        
        return ReviewRequestResponse(**review_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_review_request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review request"
        )


@router.post(
    "/{review_request_id}/process",
    response_model=TaskSubmissionResponse,
    summary="Submit Review for Processing",
    description="Submit a review request for background AI processing"
)
async def submit_review_for_processing(
    review_request_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> TaskSubmissionResponse:
    """
    Submit a review request for background processing.
    
    - **review_request_id**: ID of the review request to process
    
    The review will be processed asynchronously using AI agents.
    Use GET /reviews/{id} to check processing status.
    """
    try:
        # Verify access to the review request first
        await review_service.get_review_request(review_request_id, current_user.id)
        
        # Submit for processing
        result = await review_service.submit_for_processing(
            review_request_id=review_request_id,
            background_tasks=background_tasks
        )
        
        logger.info(f"Submitted review {review_request_id} for processing by user {current_user.id}")
        
        return TaskSubmissionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting review for processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit review for processing"
        )


@router.get(
    "/{review_request_id}",
    response_model=ReviewRequestResponse,
    summary="Get Review Request",
    description="Get review request details and processing status"
)
async def get_review_request(
    review_request_id: UUID,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> ReviewRequestResponse:
    """
    Get review request details including processing status.
    
    - **review_request_id**: ID of the review request
    
    Returns current status: pending, processing, completed, or failed.
    """
    try:
        review_data = await review_service.get_review_request(
            review_request_id=review_request_id,
            user_id=current_user.id
        )
        
        return ReviewRequestResponse(**review_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting review request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get review request"
        )


@router.get(
    "/{review_request_id}/results",
    response_model=ReviewResultResponse,
    summary="Get Review Results",
    description="Get complete review results with raw AI response"
)
async def get_review_results(
    review_request_id: UUID,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> ReviewResultResponse:
    """
    Get complete review results including raw AI response.
    
    - **review_request_id**: ID of the review request
    
    Returns the complete AI analysis results in raw JSON format for frontend processing.
    Only available when review status is 'completed'.
    """
    try:
        result_data = await review_service.get_review_results(
            review_request_id=review_request_id,
            user_id=current_user.id
        )
        
        return ReviewResultResponse(**result_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting review results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get review results"
        )


@router.get(
    "/{review_request_id}/results/parsed",
    response_model=ParsedAIResponse,
    summary="Get Parsed Review Results",
    description="Get review results with structured AI response parsing"
)
async def get_parsed_review_results(
    review_request_id: UUID,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> ParsedAIResponse:
    """
    Get review results with structured parsing of AI response.
    
    - **review_request_id**: ID of the review request
    
    Returns AI analysis results with structured schema validation for easier consumption.
    """
    try:
        result_data = await review_service.get_review_results(
            review_request_id=review_request_id,
            user_id=current_user.id
        )
        
        # Parse raw AI response into structured format
        raw_ai_response = result_data.get("raw_ai_response", {})
        if not raw_ai_response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No AI response data available"
            )
        
        return ParsedAIResponse.from_raw_response(raw_ai_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parsed review results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse review results"
        )


@router.get(
    "/user/my-reviews",
    response_model=List[ReviewListResponse],
    summary="Get My Reviews",
    description="Get all review requests for the current user"
)
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> List[ReviewListResponse]:
    """
    Get all review requests for the current user.
    
    Returns a list of all review requests created by the current user,
    including basic result summaries where available.
    """
    try:
        reviews = await review_service.get_user_reviews(current_user.id)
        return [ReviewListResponse(**review) for review in reviews]
        
    except Exception as e:
        logger.error(f"Error getting user reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user reviews"
        )


@router.get(
    "/resume/{resume_id}/reviews",
    response_model=List[ReviewListResponse],
    summary="Get Resume Reviews",
    description="Get all review requests for a specific resume"
)
async def get_resume_reviews(
    resume_id: UUID,
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> List[ReviewListResponse]:
    """
    Get all review requests for a specific resume.
    
    - **resume_id**: ID of the resume
    
    Returns all review requests for the specified resume that the current user has access to.
    """
    try:
        reviews = await review_service.get_resume_reviews(
            resume_id=resume_id,
            user_id=current_user.id
        )
        return [ReviewListResponse(**review) for review in reviews]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get resume reviews"
        )


@router.get(
    "/admin/test-ai-connection",
    response_model=AIConnectionTestResponse,
    summary="Test AI Connection",
    description="Test connection to AI analysis service (Admin only)"
)
async def test_ai_connection(
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service)
) -> AIConnectionTestResponse:
    """
    Test connection to AI analysis service.
    
    This endpoint tests the connection to the AI orchestrator and validates
    that the analysis pipeline is working correctly.
    
    **Note**: This is an admin endpoint for system monitoring.
    """
    try:
        # TODO: Add admin role check when role system is implemented
        # For now, any authenticated user can test the connection
        
        test_result = await review_service.test_ai_connection()
        
        logger.info(f"AI connection test performed by user {current_user.id}")
        
        return AIConnectionTestResponse(**test_result)
        
    except Exception as e:
        logger.error(f"Error testing AI connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test AI connection"
        )


# Health check endpoint
@router.get(
    "/health",
    summary="Health Check",
    description="Check review service health status"
)
async def health_check():
    """
    Health check endpoint for the review service.
    
    Returns basic health status information.
    """
    return {
        "status": "healthy",
        "service": "review",
        "version": "1.0.0",
        "features": [
            "review_requests",
            "ai_integration", 
            "background_processing",
            "raw_json_storage"
        ]
    }


# Error handlers
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return ErrorResponse(
        success=False,
        error=exc.detail,
        request_id=getattr(request.state, 'request_id', None)
    )


@router.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """Handle validation errors."""
    return ErrorResponse(
        success=False,
        error="Validation error",
        details=[{
            "type": "validation_error",
            "message": str(exc)
        }]
    )