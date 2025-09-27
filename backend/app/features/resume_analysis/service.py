"""Resume analysis service - minimal version for two-table workflow."""

import logging
import uuid
from typing import Optional, Dict, Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.datetime_utils import utc_now

# Import AI orchestrator from the isolated ai_agents module
from ai_agents.orchestrator import ResumeAnalysisOrchestrator

from .repository import AnalysisRepository
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models import ReviewRequest, ReviewResult, ReviewFeedbackItem

# Import resume upload service for integration
from app.features.resume_upload.service import ResumeUploadService
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    Industry
)

logger = logging.getLogger(__name__)


class AnalysisException(Exception):
    """Custom exception for analysis-related errors."""
    pass


class AnalysisValidationException(AnalysisException):
    """Exception for input validation errors."""
    pass


class AnalysisService:
    """
    Minimal business logic service for resume analysis using two-table workflow.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the analysis service."""
        self.db = db
        self.repository = AnalysisRepository(db)
        self.settings = get_settings()

        # Initialize resume upload service for integration
        self.resume_service = ResumeUploadService(db)

        # Initialize AI orchestrator from isolated module
        self.ai_orchestrator = ResumeAnalysisOrchestrator()

        logger.info("AnalysisService initialized successfully")

    async def request_analysis(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        industry: Industry
    ) -> AnalysisResponse:
        """
        Request analysis for an uploaded resume using two-table workflow.
        """

        try:
            logger.info(f"User {user_id} requesting analysis for resume {resume_id}, industry: {industry.value}")

            # Step 1: Get resume text
            resume = await self.resume_service.get_upload(resume_id, user_id)
            if not resume or not resume.extracted_text:
                raise ValueError("Resume text not available")

            # Step 2: Create review request
            review_request = await self.repository.create_analysis(
                user_id=user_id,
                resume_id=resume_id,
                target_industry=industry.value,
                review_type="comprehensive"
            )

            # Step 3: Queue background analysis job
            await self._queue_analysis_job(
                request_id=review_request.id,
                resume_text=resume.extracted_text,
                industry=industry
            )

            return AnalysisResponse(
                analysis_id=str(review_request.id),
                status=review_request.status,
                message="Analysis request created successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error requesting analysis: {str(e)}")
            raise AnalysisException(f"Failed to request analysis: {str(e)}")

    async def get_analysis_status(self, request_id: uuid.UUID, user_id: uuid.UUID) -> AnalysisStatusResponse:
        """Get analysis status with access control"""
        # TODO: Implement access control - verify user owns this analysis request
        # Should check: request.requested_by_user_id == user_id

        analysis_data = await self.repository.get_analysis_with_results(request_id)
        if not analysis_data:
            raise ValueError("Analysis not found")

        request, result = analysis_data

        return AnalysisStatusResponse(
            analysis_id=str(request.id),
            status=request.status,
            requested_at=request.requested_at,
            completed_at=request.completed_at,
            result=self._build_result_response(request, result) if result else None
        )

    def _build_result_response(self, request: ReviewRequest, result: ReviewResult) -> Dict[str, Any]:
        """Build API response combining request + result data with granular scoring"""
        return {
            "analysis_id": str(request.id),
            "overall_score": result.overall_score,
            "ats_score": result.ats_score,
            "content_score": result.content_score,
            "formatting_score": result.formatting_score,
            "industry": request.target_industry,
            "executive_summary": result.executive_summary,
            "detailed_scores": result.detailed_scores,
            "ai_model_used": result.ai_model_used,
            "processing_time_ms": result.processing_time_ms,
            "completed_at": request.completed_at
        }

    async def _queue_analysis_job(
        self,
        request_id: uuid.UUID,
        resume_text: str,
        industry: Industry
    ):
        """Queue background analysis job for two-table workflow."""
        # TODO: Implement actual background job queueing
        logger.info(f"Queuing analysis job {request_id} for industry {industry.value}")
        # For now, just log - in production this would use Celery/RQ/etc.

    def get_supported_industries(self) -> list[Industry]:
        """Get list of supported industries."""
        return [
            Industry.STRATEGY_TECH,
            Industry.MA_FINANCIAL,
            Industry.CONSULTING,
            Industry.SYSTEM_INTEGRATOR,
            Industry.GENERAL
        ]