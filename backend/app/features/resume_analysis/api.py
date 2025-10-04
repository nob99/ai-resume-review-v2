"""Resume analysis API endpoints."""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.dependencies import get_current_user
from database.models.auth import User
from app.core.rate_limiter import rate_limiter, RateLimitExceeded, RateLimitType

from .service import AnalysisService, AnalysisValidationException, AnalysisException
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisResult,
    AnalysisListResponse,
    AnalysisSummary,
    AnalysisStats
)
from database.models.analysis import AnalysisStatus, Industry

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Dependency injection
def get_analysis_service(db: AsyncSession = Depends(get_async_session)) -> AnalysisService:
    """Get analysis service instance."""
    return AnalysisService(db)


@router.post(
    "/resumes/{resume_id}/analyze",
    response_model=AnalysisResponse,
    summary="Request resume analysis",
    description="Request AI analysis for an uploaded resume, returns job ID for polling"
)
async def request_resume_analysis(
    resume_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisResponse:
    """
    Request analysis for an uploaded resume.

    - References uploaded resume by ID (no copy/paste needed!)
    - Validates user access to the resume via candidate permissions
    - Queues analysis job for background processing
    - Returns analysis job ID for polling results
    - Supports different analysis depths and focus areas
    """
    
    try:
        # Apply rate limiting
        is_allowed, rate_info = await rate_limiter.check_rate_limit(
            limit_type=RateLimitType.ANALYSIS,
            identifier=str(current_user.id)
        )

        if not is_allowed:
            raise RateLimitExceeded("Too many analysis requests. Please wait before analyzing more resumes.")
        
        logger.info(f"User {current_user.id} requesting analysis for resume {resume_id}, industry: {request.industry}")

        # Request analysis (async processing with background tasks)
        result = await service.request_analysis(
            resume_id=resume_id,
            user_id=current_user.id,
            industry=request.industry,
            background_tasks=background_tasks
        )

        logger.info(f"Analysis queued: {result.analysis_id}")
        return result
        
    except RateLimitExceeded:
        raise HTTPException(
            status_code=429,
            detail="Too many analysis requests. Please wait before analyzing more resumes."
        )
    except AnalysisValidationException as e:
        logger.warning(f"Analysis validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except AnalysisException as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Resume analysis failed. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get(
    "/analysis/{analysis_id}/status",
    response_model=AnalysisStatusResponse,
    summary="Get analysis status",
    description="Poll analysis status and get results when ready"
)
async def get_analysis_status(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisStatusResponse:
    """
    Poll analysis status and get results when complete.

    Use this endpoint to check if analysis is done and retrieve results.
    Frontend should poll this every 2-3 seconds until status is 'completed'.
    """

    status_result = await service.get_analysis_status(analysis_id, current_user.id)
    if not status_result:
        raise HTTPException(status_code=404, detail="Analysis not found or not accessible")

    # === DATA SIZE CHECKPOINT 10: API RESPONSE TO FRONTEND (STATUS) ===
    if status_result.status == "completed" and status_result.result:
        logger.info(f"=== CHECKPOINT 10: API RESPONSE TO FRONTEND (STATUS) ===")
        logger.info(f"Analysis ID: {analysis_id}")
        logger.info(f"User ID: {current_user.id}")
        logger.info(f"Status: {status_result.status}")

        # Check if result has detailed_scores
        result_dict = status_result.result.dict() if hasattr(status_result.result, 'dict') else status_result.result
        if isinstance(result_dict, dict):
            detailed_scores = result_dict.get('detailed_scores', {})
            if detailed_scores:
                structure_feedback = detailed_scores.get("structure_analysis", {}).get("feedback", {})
                structure_total = sum(len(v) if isinstance(v, list) else 0 for v in structure_feedback.values())
                logger.info(f"Structure feedback items in API response: {structure_total}")
                for key, value in structure_feedback.items():
                    if isinstance(value, list):
                        logger.info(f"  - structure.{key}: {len(value)} items")

                appeal_feedback = detailed_scores.get("appeal_analysis", {}).get("feedback", {})
                appeal_total = sum(len(v) if isinstance(v, list) else 0 for v in appeal_feedback.values())
                logger.info(f"Appeal feedback items in API response: {appeal_total}")
                for key, value in appeal_feedback.items():
                    if isinstance(value, list):
                        logger.info(f"  - appeal.{key}: {len(value)} items")

                logger.info(f"Total feedback items in API response: {structure_total + appeal_total}")
        logger.info(f"=== END CHECKPOINT 10 ===")

    return status_result


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResult,
    summary="Get analysis result",
    description="Get detailed results of a completed analysis"
)
async def get_analysis_result(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisResult:
    """Get detailed analysis results by ID (only for completed analyses)."""

    result = await service.get_analysis_result(analysis_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found or not accessible")

    # === DATA SIZE CHECKPOINT 11: API RESPONSE TO FRONTEND (GET RESULT) ===
    logger.info(f"=== CHECKPOINT 11: API RESPONSE TO FRONTEND (GET RESULT) ===")
    logger.info(f"Analysis ID: {analysis_id}")
    logger.info(f"User ID: {current_user.id}")

    result_dict = result.dict() if hasattr(result, 'dict') else result
    if isinstance(result_dict, dict):
        detailed_scores = result_dict.get('detailed_scores', {})
        if detailed_scores:
            structure_feedback = detailed_scores.get("structure_analysis", {}).get("feedback", {})
            structure_total = sum(len(v) if isinstance(v, list) else 0 for v in structure_feedback.values())
            logger.info(f"Structure feedback items in API response: {structure_total}")
            for key, value in structure_feedback.items():
                if isinstance(value, list):
                    logger.info(f"  - structure.{key}: {len(value)} items")

            appeal_feedback = detailed_scores.get("appeal_analysis", {}).get("feedback", {})
            appeal_total = sum(len(v) if isinstance(v, list) else 0 for v in appeal_feedback.values())
            logger.info(f"Appeal feedback items in API response: {appeal_total}")
            for key, value in appeal_feedback.items():
                if isinstance(value, list):
                    logger.info(f"  - appeal.{key}: {len(value)} items")

            logger.info(f"Total feedback items in API response: {structure_total + appeal_total}")
            import json
            logger.info(f"Total API response JSON length: {len(json.dumps(result_dict))} chars")
    logger.info(f"=== END CHECKPOINT 11 ===")

    return result


@router.get(
    "/resumes/{resume_id}/analyses",
    response_model=AnalysisListResponse,
    summary="List resume analyses",
    description="Get all analyses performed on a specific resume"
)
async def get_resume_analysis_history(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisListResponse:
    """Get analysis history for a specific resume."""

    analyses = await service.get_resume_analyses(resume_id, current_user.id)
    return AnalysisListResponse(
        analyses=analyses,
        total_count=len(analyses)
    )


@router.get(
    "/",
    response_model=AnalysisListResponse,
    summary="List user analyses",
    description="Get paginated list of user's analysis history"
)
async def list_analyses(
    status: Optional[AnalysisStatus] = Query(None, description="Filter by status"),
    industry: Optional[Industry] = Query(None, description="Filter by industry"),
    candidate_id: Optional[uuid.UUID] = Query(None, description="Filter by candidate"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisListResponse:
    """List user's analyses with optional filtering and pagination."""

    offset = (page - 1) * page_size

    result = await service.list_user_analyses(
        user_id=current_user.id,
        limit=page_size,
        offset=offset,
        status=status,
        industry=industry,
        candidate_id=candidate_id
    )

    return AnalysisListResponse(
        analyses=result["analyses"],
        total_count=result["total_count"],
        page=page,
        page_size=page_size
    )


@router.delete(
    "/{analysis_id}/cancel",
    summary="Cancel analysis",
    description="Cancel an ongoing analysis"
)
async def cancel_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> JSONResponse:
    """Cancel an ongoing analysis."""
    
    success = await service.cancel_analysis(analysis_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Unable to cancel analysis. It may be already completed or not found."
        )
    
    return JSONResponse(
        content={"message": "Analysis cancelled successfully"},
        status_code=200
    )


@router.get(
    "/stats/summary",
    response_model=AnalysisStats,
    summary="Get analysis statistics",
    description="Get user's analysis statistics and breakdown"
)
async def get_analysis_stats(
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisStats:
    """Get comprehensive analysis statistics for the current user."""
    
    return await service.get_user_stats(current_user.id)


@router.get(
    "/config/limits",
    summary="Get analysis limits",
    description="Get analysis configuration and limits"
)
async def get_analysis_limits(
    service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Get analysis configuration limits and supported options."""
    
    return {
        **service.get_analysis_limits(),
        "supported_industries": [industry.value for industry in service.get_supported_industries()],
        "rate_limits": {
            "analyses_per_5_minutes": 5,
            "max_concurrent_analyses": 2
        }
    }


# Health check endpoint specific to analysis
@router.get(
    "/health",
    summary="Analysis service health",
    description="Check health of analysis service and AI components"
)
async def analysis_health(
    service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """Check health of analysis service and dependencies."""
    
    try:
        # Check AI orchestrator health
        # This would ideally call a health check method on the AI orchestrator
        ai_status = "healthy"  # Placeholder
        
        return {
            "status": "healthy",
            "ai_orchestrator": ai_status,
            "supported_industries": len(service.get_supported_industries()),
            "timestamp": str(uuid.uuid4())  # Would use actual timestamp
        }
        
    except Exception as e:
        logger.error(f"Analysis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(uuid.uuid4())
        }


# Utility endpoint for testing (development only)
@router.post(
    "/test/validate",
    summary="Validate analysis request",
    description="Validate analysis request without running analysis (testing only)"
)
async def validate_request(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> dict:
    """
    Validate an analysis request without running the analysis.
    Useful for frontend validation and testing.
    """

    try:
        # Validate industry support
        if request.industry not in service.get_supported_industries():
            raise AnalysisValidationException("Unsupported industry")

        return {
            "valid": True,
            "message": "Request is valid",
            "industry": request.industry.value
        }

    except AnalysisValidationException as e:
        return {
            "valid": False,
            "message": str(e),
            "industry": request.industry.value,
            "analysis_depth": request.analysis_depth.value
        }