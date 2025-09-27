"""Resume analysis service - migrated from services/analysis_service.py."""

import logging
import uuid
from typing import Optional, List, Dict, Any

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
    AnalysisResult,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisSummary,
    AnalysisStats,
    ScoreDetails,
    ConfidenceMetrics,
    FeedbackSection,
    AnalysisDepth,
    AnalysisStatus,
    MarketTier,
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
    Main business logic service for resume analysis.
    
    Migrated from services/analysis_service.py with clean architecture:
    - Business logic: validation, rate limiting, tracking
    - AI delegation: uses isolated ai_agents module
    - Data persistence: uses repository pattern
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
        
        # Configuration (migrated from old service)
        self.config = {
            "max_file_size_bytes": 10 * 1024 * 1024,  # 10MB
            "min_resume_length": 100,
            "max_resume_length": 50000,
            "supported_industries": [
                Industry.STRATEGY_TECH,
                Industry.MA_FINANCIAL,
                Industry.CONSULTING,
                Industry.SYSTEM_INTEGRATOR,
                Industry.GENERAL
            ],
            "analysis_timeout_seconds": 300  # 5 minutes
        }
        
        logger.info("AnalysisService initialized successfully")

    async def request_analysis(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        industry: Industry,
        analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    ) -> AnalysisResponse:
        """
        Request analysis for an uploaded resume using two-table workflow.

        Args:
            resume_id: ID of uploaded resume to analyze
            user_id: User requesting the analysis
            industry: Target industry for analysis
            analysis_depth: Complexity level (quick/standard/deep)

        Returns:
            AnalysisResponse: Analysis request ID and status

        Raises:
            HTTPException: If resume not found or access denied
            AnalysisValidationException: When input validation fails
        """

        try:
            logger.info(f"User {user_id} requesting {analysis_depth.value} analysis for resume {resume_id}")

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
                industry=industry,
                analysis_depth=analysis_depth
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

    async def _get_resume_text(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """Get resume text via resume_upload service with access validation."""
        try:
            # This will validate user access to the resume via candidate permissions
            resume = await self.resume_service.get_upload(resume_id, user_id)
            if not resume:
                raise HTTPException(status_code=404, detail="Resume not found or access denied")

            # Get the extracted text from the resume
            # TODO: Update this once resume_service provides get_resume_text method
            if hasattr(resume, 'extracted_text') and resume.extracted_text:
                return resume.extracted_text
            else:
                raise AnalysisValidationException("Resume text not available - may still be processing")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting resume text: {str(e)}")
            raise AnalysisException(f"Failed to get resume text: {str(e)}")

    async def _check_recent_analysis(
        self,
        resume_id: uuid.UUID,
        industry: Industry,
        max_age_hours: int = 24
    ) -> Optional[AnalysisResponse]:
        """Check for recent analysis to avoid duplicates."""
        # TODO: Implement caching logic
        return None

    async def _queue_analysis_job(
        self,
        request_id: uuid.UUID,
        resume_text: str,
        industry: Industry,
        analysis_depth: AnalysisDepth
    ):
        """Queue background analysis job for two-table workflow."""
        # TODO: Implement actual background job queueing
        logger.info(f"Queuing analysis job {request_id} for {analysis_depth.value} analysis")
        # For now, just log - in production this would use Celery/RQ/etc.

    def _estimate_completion_time(self, analysis_depth: AnalysisDepth) -> int:
        """Estimate completion time based on analysis depth."""
        time_map = {
            AnalysisDepth.QUICK: 15,      # 15 seconds
            AnalysisDepth.STANDARD: 45,   # 45 seconds
            AnalysisDepth.DEEP: 120       # 2 minutes
        }
        return time_map.get(analysis_depth, 45)

    async def get_analysis_status(self, request_id: uuid.UUID) -> AnalysisStatusResponse:
        """Get analysis status"""
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

    async def get_resume_analyses(
        self,
        resume_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[AnalysisSummary]:
        """Get all analyses for a specific resume."""
        try:
            # TODO: Add proper resume access validation via candidate service
            # For now, get analyses by resume_id
            analyses = await self.repository.get_by_resume_id(resume_id, user_id)

            summaries = []
            for analysis in analyses:
                summary = AnalysisSummary(
                    id=str(analysis.id),
                    resume_id=str(analysis.resume_id) if hasattr(analysis, 'resume_id') else None,
                    industry=Industry(analysis.industry),
                    overall_score=analysis.overall_score,
                    market_tier=MarketTier(analysis.market_tier) if analysis.market_tier else None,
                    status=AnalysisStatus(analysis.status),
                    requested_at=analysis.requested_at,
                    completed_at=analysis.completed_at
                )
                summaries.append(summary)

            return summaries

        except Exception as e:
            logger.error(f"Error getting resume analyses: {str(e)}")
            return []

    async def get_analysis_result(
        self,
        analysis_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[AnalysisResult]:
        """Get analysis results by ID."""
        analysis = await self.repository.get_analysis_with_file(analysis_id, user_id)
        if not analysis:
            return None
        
        if analysis.status != AnalysisStatus.COMPLETED:
            return None
        
        return self._convert_to_analysis_result(analysis)
    
    async def list_user_analyses(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0,
        status: Optional[AnalysisStatus] = None,
        industry: Optional[Industry] = None
    ) -> Dict[str, Any]:
        """List analysis history for a user."""
        analyses = await self.repository.get_by_user(
            user_id=user_id,
            status=status,
            industry=industry,
            limit=limit,
            offset=offset,
            include_file_info=True
        )
        
        # Get total count for pagination
        stats = await self.repository.get_user_stats(user_id)
        
        summaries = []
        for analysis in analyses:
            summary = AnalysisSummary(
                id=str(analysis.id),
                file_name=analysis.file_upload.original_filename if analysis.file_upload else None,
                industry=Industry(analysis.industry),
                overall_score=analysis.overall_score,
                market_tier=MarketTier(analysis.market_tier) if analysis.market_tier else None,
                status=AnalysisStatus(analysis.status),
                created_at=analysis.created_at
            )
            summaries.append(summary)
        
        return {
            "analyses": summaries,
            "total_count": stats["total_analyses"],
            "limit": limit,
            "offset": offset
        }
    
    async def get_user_stats(self, user_id: uuid.UUID) -> AnalysisStats:
        """Get analysis statistics for a user."""
        stats = await self.repository.get_user_stats(user_id)
        
        return AnalysisStats(
            total_analyses=stats["total_analyses"],
            completed_analyses=stats["completed_analyses"],
            failed_analyses=stats["failed_analyses"],
            average_score=stats["average_score"],
            industry_breakdown=stats["industry_breakdown"],
            tier_breakdown=stats["tier_breakdown"]
        )
    
    async def cancel_analysis(
        self,
        analysis_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Cancel an ongoing analysis."""
        analysis = self.repository.get(analysis_id)
        if not analysis or analysis.user_id != user_id:
            return False
        
        if analysis.status in [AnalysisStatus.COMPLETED, AnalysisStatus.ERROR, AnalysisStatus.CANCELLED]:
            return False
        
        await self.repository.mark_cancelled(analysis_id)
        return True
    
    # ========================================================================
    # LEGACY METHODS (TODO: Remove in next cleanup - not used by new API)
    # ========================================================================
    
    async def _validate_analysis_request(
        self,
        request: AnalysisRequest,
        user_id: uuid.UUID
    ) -> None:
        """Validate analysis request parameters."""
        # Validate resume text
        if not request.text or not request.text.strip():
            raise AnalysisValidationException("Resume text cannot be empty")
        
        if len(request.text) < self.config["min_resume_length"]:
            raise AnalysisValidationException(
                f"Resume text too short (minimum {self.config['min_resume_length']} characters)"
            )
        
        if len(request.text) > self.config["max_resume_length"]:
            raise AnalysisValidationException(
                f"Resume text too long (maximum {self.config['max_resume_length']} characters)"
            )
        
        # Validate industry
        if request.industry not in self.config["supported_industries"]:
            raise AnalysisValidationException(
                f"Unsupported industry: {request.industry}"
            )
        
        # Business logic: rate limiting check
        await self._check_rate_limits(user_id)
    
    def _preprocess_resume_text(self, resume_text: str) -> str:
        """Preprocess resume text for analysis."""
        text = resume_text.strip()
        
        # Remove null bytes and problematic characters
        text = text.replace('\x00', '')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Limit excessive whitespace
        import re
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        
        return text
    
    async def _call_ai_orchestrator(
        self,
        text: str,
        industry: str,
        analysis_id: str
    ) -> Dict[str, Any]:
        """Call the AI orchestrator from the isolated ai_agents module."""
        try:
            # Use the isolated AI orchestrator
            result = await self.ai_orchestrator.analyze(
                resume_text=text,
                industry=industry,
                analysis_id=analysis_id
            )
            
            if not result.get("success", False):
                raise AnalysisException(f"AI analysis failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI orchestrator call failed: {str(e)}")
            raise AnalysisException(f"AI analysis failed: {str(e)}")
    
    async def _validate_ai_result(self, result: Dict[str, Any]) -> None:
        """Validate AI analysis result."""
        if not result:
            raise AnalysisException("AI analysis produced no result")
        
        overall_score = result.get("overall_score", 0)
        if not (0 <= overall_score <= 100):
            raise AnalysisException(f"Invalid overall score: {overall_score}")
        
        if not result.get("summary"):
            raise AnalysisException("Analysis summary is missing")
        
        structure = result.get("structure", {})
        appeal = result.get("appeal", {})
        
        if not structure or not appeal:
            raise AnalysisException("Incomplete analysis results")
    
    async def _parse_ai_result(
        self,
        ai_result: Dict[str, Any],
        analysis_id: uuid.UUID
    ) -> AnalysisResult:
        """Parse AI result into our domain model."""
        
        # Extract scores
        structure_data = ai_result.get("structure", {})
        appeal_data = ai_result.get("appeal", {})
        
        structure_scores = ScoreDetails(
            overall=structure_data.get("scores", {}).get("overall", 0),
            formatting=structure_data.get("scores", {}).get("formatting"),
            content=structure_data.get("scores", {}).get("content"),
            structure=structure_data.get("scores", {}).get("structure")
        ) if structure_data.get("scores") else None
        
        appeal_scores = ScoreDetails(
            overall=appeal_data.get("scores", {}).get("overall", 0),
            impact=appeal_data.get("scores", {}).get("impact"),
            relevance=appeal_data.get("scores", {}).get("relevance")
        ) if appeal_data.get("scores") else None
        
        # Extract feedback
        structure_feedback = FeedbackSection(
            strengths=structure_data.get("feedback", {}).get("strengths", []),
            improvements=structure_data.get("feedback", {}).get("improvements", []),
            specific_feedback=structure_data.get("feedback", {}).get("specific_feedback")
        ) if structure_data.get("feedback") else None
        
        appeal_feedback = FeedbackSection(
            strengths=appeal_data.get("feedback", {}).get("strengths", []),
            improvements=appeal_data.get("feedback", {}).get("improvements", []),
            specific_feedback=appeal_data.get("feedback", {}).get("specific_feedback")
        ) if appeal_data.get("feedback") else None
        
        # Determine market tier
        overall_score = ai_result.get("overall_score", 0)
        market_tier = self._determine_market_tier(overall_score, ai_result.get("market_tier"))
        
        return AnalysisResult(
            analysis_id=str(analysis_id),
            overall_score=overall_score,
            market_tier=market_tier,
            industry=Industry(ai_result.get("industry", "general")),
            structure_scores=structure_scores,
            appeal_scores=appeal_scores,
            structure_feedback=structure_feedback,
            appeal_feedback=appeal_feedback,
            analysis_summary=ai_result.get("summary", ""),
            improvement_suggestions=ai_result.get("improvement_suggestions", []),
            processing_time_seconds=ai_result.get("processing_time_seconds", 0),
            ai_model_version=ai_result.get("ai_model_version"),
            created_at=utc_now()
        )
    
    def _determine_market_tier(self, score: float, ai_tier: Optional[str] = None) -> MarketTier:
        """Determine market tier based on score and AI suggestion."""
        if ai_tier:
            try:
                return MarketTier(ai_tier.lower())
            except ValueError:
                pass
        
        # Fallback to score-based tier
        if score >= 80:
            return MarketTier.TIER_1
        elif score >= 60:
            return MarketTier.TIER_2
        elif score >= 40:
            return MarketTier.TIER_3
        else:
            return MarketTier.UNKNOWN
    
    
    def _track_analysis_usage(
        self,
        user_id: uuid.UUID,
        industry: Industry,
        score: float
    ) -> None:
        """Track analysis usage for monitoring and billing."""
        logger.info(f"Tracking usage: user={user_id}, industry={industry.value}, score={score:.2f}")
        # In production, would send to analytics/monitoring system
    
    async def _check_rate_limits(self, user_id: uuid.UUID) -> None:
        """Check rate limits for user."""
        logger.debug(f"Checking rate limits for user {user_id}")
        # Placeholder - would integrate with actual rate limiter
        
    # ========================================================================
    # PUBLIC UTILITY METHODS (migrated from old service)
    # ========================================================================
    
    def get_supported_industries(self) -> List[Industry]:
        """Get list of supported industries."""
        return self.config["supported_industries"].copy()
    
    def get_analysis_limits(self) -> Dict[str, Any]:
        """Get analysis configuration limits."""
        return {
            "min_resume_length": self.config["min_resume_length"],
            "max_resume_length": self.config["max_resume_length"],
            "analysis_timeout_seconds": self.config["analysis_timeout_seconds"],
            "supported_industries": [i.value for i in self.config["supported_industries"]]
        }