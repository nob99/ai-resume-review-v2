"""Resume analysis service - migrated from services/analysis_service.py."""

import logging
import uuid
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.datetime_utils import utc_now

# Import AI orchestrator from the isolated ai_agents module
from app.ai_agents.orchestrator import ResumeAnalysisOrchestrator

from .repository import AnalysisRepository
from .models import (
    ResumeAnalysis,
    AnalysisStatus,
    Industry,
    MarketTier,
    AnalysisRequest,
    AnalysisResult,
    AnalysisResponse,
    AnalysisSummary,
    AnalysisStats,
    ScoreDetails,
    ConfidenceMetrics,
    FeedbackSection,
    CompleteAnalysisResult
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
    
    def __init__(self, db: Session):
        """Initialize the analysis service."""
        self.db = db
        self.repository = AnalysisRepository(db)
        self.settings = get_settings()
        
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
    
    async def analyze_resume(
        self,
        request: AnalysisRequest,
        user_id: uuid.UUID
    ) -> AnalysisResponse:
        """
        Main business logic interface for resume analysis.
        
        Args:
            request: Analysis request with text and industry
            user_id: User requesting the analysis
            
        Returns:
            AnalysisResponse: Complete analysis response
            
        Raises:
            AnalysisValidationException: When input validation fails
            AnalysisException: When analysis processing fails
        """
        
        try:
            # Step 1: Business logic - input validation
            await self._validate_analysis_request(request, user_id)
            
            # Step 2: Create analysis record
            file_upload_id = uuid.UUID(request.file_upload_id) if request.file_upload_id else None
            analysis = await self.repository.create_analysis(
                user_id=user_id,
                industry=request.industry,
                file_upload_id=file_upload_id
            )
            
            logger.info(f"Starting analysis {analysis.id} for user {user_id}, industry: {request.industry}")
            
            # Step 3: Update status to processing
            await self.repository.update_status(analysis.id, AnalysisStatus.PROCESSING)
            
            # Step 4: Business logic - preprocessing
            processed_text = self._preprocess_resume_text(request.text)
            
            # Step 5: Delegate to AI orchestrator (isolated module)
            ai_result = await self._call_ai_orchestrator(
                text=processed_text,
                industry=request.industry.value,
                analysis_id=str(analysis.id)
            )
            
            # Step 6: Business logic - post-processing and validation
            await self._validate_ai_result(ai_result)
            
            # Step 7: Parse and store results
            analysis_result = await self._parse_ai_result(ai_result, analysis.id)
            
            await self.repository.save_results(
                analysis_id=analysis.id,
                overall_score=analysis_result.overall_score,
                market_tier=analysis_result.market_tier,
                structure_scores=analysis_result.structure_scores.dict() if analysis_result.structure_scores else None,
                appeal_scores=analysis_result.appeal_scores.dict() if analysis_result.appeal_scores else None,
                confidence_metrics=analysis_result.confidence_metrics.dict() if analysis_result.confidence_metrics else None,
                structure_feedback=analysis_result.structure_feedback.specific_feedback if analysis_result.structure_feedback else None,
                appeal_feedback=analysis_result.appeal_feedback.specific_feedback if analysis_result.appeal_feedback else None,
                analysis_summary=analysis_result.analysis_summary,
                improvement_suggestions=", ".join(analysis_result.improvement_suggestions or []),
                ai_model_version=analysis_result.ai_model_version
            )
            
            # Step 8: Mark as completed
            await self.repository.update_status(analysis.id, AnalysisStatus.COMPLETED)
            
            # Step 9: Business logic - usage tracking
            self._track_analysis_usage(user_id, request.industry, analysis_result.overall_score)
            
            logger.info(
                f"Analysis {analysis.id} completed successfully "
                f"(score: {analysis_result.overall_score}, time: {analysis_result.processing_time_seconds:.2f}s)"
            )
            
            return AnalysisResponse(
                analysis_id=str(analysis.id),
                status=AnalysisStatus.COMPLETED,
                result=analysis_result
            )
            
        except AnalysisValidationException as e:
            logger.warning(f"Analysis validation failed: {str(e)}")
            if 'analysis' in locals():
                await self.repository.update_status(analysis.id, AnalysisStatus.ERROR, str(e))
            raise
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            if 'analysis' in locals():
                await self.repository.update_status(analysis.id, AnalysisStatus.ERROR, str(e))
            raise AnalysisException(f"Resume analysis failed: {str(e)}")
    
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
    # PRIVATE BUSINESS LOGIC METHODS (migrated from old service)
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
    
    def _convert_to_analysis_result(self, analysis: ResumeAnalysis) -> AnalysisResult:
        """Convert database model to analysis result."""
        
        structure_scores = ScoreDetails(**analysis.structure_scores) if analysis.structure_scores else None
        appeal_scores = ScoreDetails(**analysis.appeal_scores) if analysis.appeal_scores else None
        confidence_metrics = ConfidenceMetrics(**analysis.confidence_metrics) if analysis.confidence_metrics else None
        
        structure_feedback = FeedbackSection(specific_feedback=analysis.structure_feedback) if analysis.structure_feedback else None
        appeal_feedback = FeedbackSection(specific_feedback=analysis.appeal_feedback) if analysis.appeal_feedback else None
        
        improvement_suggestions = analysis.improvement_suggestions.split(", ") if analysis.improvement_suggestions else None
        
        return AnalysisResult(
            analysis_id=str(analysis.id),
            overall_score=analysis.overall_score or 0,
            market_tier=MarketTier(analysis.market_tier) if analysis.market_tier else MarketTier.UNKNOWN,
            industry=Industry(analysis.industry),
            structure_scores=structure_scores,
            appeal_scores=appeal_scores,
            confidence_metrics=confidence_metrics,
            structure_feedback=structure_feedback,
            appeal_feedback=appeal_feedback,
            analysis_summary=analysis.analysis_summary,
            improvement_suggestions=improvement_suggestions,
            processing_time_seconds=analysis.processing_time_seconds,
            ai_model_version=analysis.ai_model_version,
            created_at=analysis.created_at
        )
    
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