"""Resume analysis API endpoints."""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.connection import get_db
from app.features.auth.api import get_current_user
from database.models.auth import User
from app.core.rate_limiter import rate_limiter, RateLimitExceeded

from .service import AnalysisService, AnalysisValidationException, AnalysisException
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
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
def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    """Get analysis service instance."""
    return AnalysisService(db)


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze resume",
    description="Analyze a resume text for a specific industry using AI agents"
)
async def analyze_resume(
    background_tasks: BackgroundTasks,
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisResponse:
    """
    Analyze a resume for industry-specific feedback.
    
    - Validates input text and industry
    - Uses specialized AI agents for analysis
    - Returns detailed scores and feedback
    - Stores results for future reference
    """
    
    try:
        # Apply rate limiting
        await rate_limiter.check_rate_limit(
            key=f"analysis:{current_user.id}",
            max_requests=5,
            window_seconds=300  # 5 analyses per 5 minutes
        )
        
        logger.info(f"User {current_user.id} starting analysis for industry: {request.industry}")
        
        # Process analysis
        result = await service.analyze_resume(
            request=request,
            user_id=current_user.id
        )
        
        logger.info(f"Analysis completed: {result.analysis_id}")
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
    "/{analysis_id}",
    response_model=AnalysisResult,
    summary="Get analysis result",
    description="Get detailed results of a specific analysis"
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisResult:
    """Get detailed analysis results by ID."""
    
    result = await service.get_analysis_result(analysis_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found or not accessible")
    
    return result


@router.get(
    "/",
    response_model=AnalysisListResponse,
    summary="List user analyses",
    description="Get paginated list of user's analysis history"
)
async def list_analyses(
    status: Optional[AnalysisStatus] = Query(None, description="Filter by status"),
    industry: Optional[Industry] = Query(None, description="Filter by industry"),
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
        industry=industry
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
        # This would call internal validation without running analysis
        # For now, just return basic validation
        
        if len(request.text) < 100:
            raise AnalysisValidationException("Text too short")
        
        if len(request.text) > 50000:
            raise AnalysisValidationException("Text too long")
        
        if request.industry not in service.get_supported_industries():
            raise AnalysisValidationException("Unsupported industry")
        
        return {
            "valid": True,
            "message": "Request is valid",
            "text_length": len(request.text),
            "industry": request.industry.value
        }
        
    except AnalysisValidationException as e:
        return {
            "valid": False,
            "message": str(e),
            "text_length": len(request.text),
            "industry": request.industry.value
        }