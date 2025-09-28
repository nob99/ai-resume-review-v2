"""Resume analysis service - minimal version for two-table workflow."""

import asyncio
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
from database.models.analysis import Industry, AnalysisStatus
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisResult,
    AnalysisListResponse,
    AnalysisSummary,
    AnalysisStats
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

            # Step 1: Validate industry support
            if not self.validate_industry_support(industry):
                raise AnalysisValidationException(f"Industry '{industry.value}' is not supported by AI agents")

            # Step 2: Get resume text
            resume = await self.resume_service.get_upload(resume_id, user_id)
            if not resume or not resume.extracted_text:
                raise ValueError("Resume text not available")

            # Step 3: Create review request
            review_request = await self.repository.create_analysis(
                user_id=user_id,
                resume_id=resume_id,
                target_industry=industry.value,
                review_type="comprehensive"
            )

            # Step 4: Map industry for AI agent compatibility
            ai_agent_industry = self._map_database_industry_to_ai_agent(industry)

            # Step 5: Queue background analysis job
            await self._queue_analysis_job(
                request_id=review_request.id,
                resume_text=resume.extracted_text,
                ai_agent_industry=ai_agent_industry
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
        ai_agent_industry: str
    ):
        """Queue background analysis job for two-table workflow."""
        logger.info(f"Queuing analysis job {request_id} for AI agent industry '{ai_agent_industry}'")

        # Start the background analysis task
        asyncio.create_task(
            self._process_analysis_background(
                request_id=request_id,
                resume_text=resume_text,
                ai_agent_industry=ai_agent_industry
            )
        )

        logger.info(f"Background analysis task created for request {request_id}")

    async def _process_analysis_background(
        self,
        request_id: uuid.UUID,
        resume_text: str,
        ai_agent_industry: str
    ):
        """Process analysis in the background using AI agents."""
        try:
            logger.info(f"Starting background analysis for request {request_id}")

            # Step 1: Update status to processing
            await self._update_analysis_status(request_id, "processing")

            # Step 2: Run AI analysis
            logger.info(f"Running AI analysis for request {request_id}")
            try:
                ai_result = await self.ai_orchestrator.analyze(
                    resume_text=resume_text,
                    industry=ai_agent_industry,
                    analysis_id=str(request_id)
                )
            except Exception as ai_error:
                logger.error(f"AI orchestrator error for request {request_id}: {str(ai_error)}")
                # Check if we should use mock results for development/testing
                settings = get_settings()
                use_mock_results = getattr(settings, 'USE_MOCK_AI_RESULTS', False)

                if use_mock_results:
                    logger.info(f"Using mock AI results for request {request_id} due to AI service error")
                    ai_result = self._create_mock_ai_result(request_id, ai_agent_industry)
                else:
                    # Create a failure response
                    ai_result = {
                        "success": False,
                        "error": f"AI analysis failed: {str(ai_error)}",
                        "analysis_id": str(request_id)
                    }

            # Step 3: Store results and update status
            if ai_result.get("success", False):
                logger.info(f"AI analysis successful for request {request_id}")
                await self._store_analysis_results(request_id, ai_result)
                await self._update_analysis_status(request_id, "completed")
                logger.info(f"Analysis completed successfully for request {request_id}")
            else:
                error_msg = ai_result.get("error", "AI analysis failed")
                logger.error(f"AI analysis failed for request {request_id}: {error_msg}")
                await self._update_analysis_status(request_id, "failed", error_msg)

        except Exception as e:
            logger.error(f"Background analysis failed for request {request_id}: {str(e)}")
            await self._update_analysis_status(request_id, "failed", str(e))

    async def _update_analysis_status(
        self,
        request_id: uuid.UUID,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update the analysis request status."""
        try:
            await self.repository.update_request_status(
                request_id=request_id,
                status=status,
                error_message=error_message
            )
            logger.info(f"Updated analysis {request_id} status to '{status}'")
        except Exception as e:
            logger.error(f"Failed to update status for request {request_id}: {str(e)}")

    async def _store_analysis_results(
        self,
        request_id: uuid.UUID,
        ai_result: Dict[str, Any]
    ):
        """Store AI analysis results in the database."""
        logger.info(f"Storing analysis results for request {request_id}")

        try:
            # Extract and convert AI result data to database format
            overall_score = self._convert_score_to_int(ai_result.get("overall_score", 0))

            # Extract structure scores for ATS, content, and formatting
            structure_scores = ai_result.get("structure", {}).get("scores", {})
            appeal_scores = ai_result.get("appeal", {}).get("scores", {})

            # Map AI agent scores to database fields
            ats_score = self._convert_score_to_int(structure_scores.get("format", 0))  # Format/layout for ATS
            content_score = self._convert_score_to_int(appeal_scores.get("achievement_relevance", 0))  # Content quality
            formatting_score = self._convert_score_to_int(structure_scores.get("completeness", 0))  # Overall completeness

            # Extract executive summary
            executive_summary = ai_result.get("summary", "Analysis completed successfully.")

            # Ensure executive summary is not empty and has reasonable length
            if not executive_summary or len(executive_summary.strip()) < 10:
                executive_summary = f"Resume analysis completed for {ai_agent_industry} industry. Overall score: {overall_score}/100."

            # Create detailed scores JSON structure
            detailed_scores = self._create_detailed_scores(ai_result)

            # Determine AI model used (default if not specified)
            ai_model_used = "gpt-4"  # Default model

            # Calculate processing time (estimate if not provided)
            processing_time_ms = 30000  # Default 30 seconds

            # Store results using repository
            result = await self.repository.save_results(
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

            logger.info(f"Successfully stored analysis results for request {request_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to store analysis results for request {request_id}: {str(e)}")
            raise

    def _convert_score_to_int(self, score: Any) -> int:
        """Convert score to integer, handling various input types."""
        if score is None:
            return 0

        try:
            # Convert to float first, then int
            float_score = float(score)
            # Ensure score is between 0 and 100
            return max(0, min(100, int(round(float_score))))
        except (ValueError, TypeError):
            logger.warning(f"Invalid score value: {score}, defaulting to 0")
            return 0

    def _create_detailed_scores(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed scores JSON structure from AI result."""
        structure_data = ai_result.get("structure", {})
        appeal_data = ai_result.get("appeal", {})

        detailed_scores = {
            "structure_analysis": {
                "scores": structure_data.get("scores", {}),
                "feedback": structure_data.get("feedback", {}),
                "metadata": structure_data.get("metadata", {})
            },
            "appeal_analysis": {
                "scores": appeal_data.get("scores", {}),
                "feedback": appeal_data.get("feedback", {})
            },
            "market_tier": ai_result.get("market_tier", "unknown"),
            "ai_analysis_id": ai_result.get("analysis_id"),
            "conversion_timestamp": utc_now().isoformat()
        }

        return detailed_scores

    def _create_mock_ai_result(self, request_id: uuid.UUID, ai_agent_industry: str) -> Dict[str, Any]:
        """Create mock AI result for testing when AI service is unavailable."""
        mock_result = {
            "success": True,
            "analysis_id": str(request_id),
            "overall_score": 75.0,
            "market_tier": "mid",
            "summary": f"Mock analysis completed for {ai_agent_industry} industry. This is a test result generated when AI services are unavailable.",
            "structure": {
                "scores": {
                    "format": 80.0,
                    "organization": 75.0,
                    "tone": 70.0,
                    "completeness": 85.0
                },
                "feedback": {
                    "issues": ["Mock formatting issue identified"],
                    "missing_sections": ["Mock missing section"],
                    "strengths": ["Mock strength identified"],
                    "recommendations": ["Mock recommendation for improvement"]
                },
                "metadata": {
                    "total_sections": 6,
                    "word_count": 450,
                    "reading_time": 2
                }
            },
            "appeal": {
                "scores": {
                    "achievement_relevance": 78.0,
                    "skills_alignment": 72.0,
                    "experience_fit": 76.0,
                    "competitive_positioning": 74.0
                },
                "feedback": {
                    "relevant_achievements": ["Mock relevant achievement"],
                    "missing_skills": ["Mock missing skill"],
                    "competitive_advantages": ["Mock competitive advantage"],
                    "improvement_areas": ["Mock improvement area"]
                }
            }
        }

        logger.info(f"Created mock AI result for request {request_id}, industry {ai_agent_industry}")
        return mock_result

    async def get_analysis_result(self, request_id: uuid.UUID, user_id: uuid.UUID) -> AnalysisResult:
        """Get detailed analysis results by ID (only for completed analyses)."""
        logger.info(f"Getting analysis result for request {request_id}, user {user_id}")

        try:
            # Get analysis data with access control
            analysis_data = await self.repository.get_analysis_with_results(request_id)
            if not analysis_data:
                raise ValueError("Analysis not found")

            request, result = analysis_data

            # TODO: Add proper access control - verify user owns this analysis
            # if request.requested_by_user_id != user_id:
            #     raise ValueError("Access denied")

            if not result:
                raise ValueError("Analysis results not available yet")

            # Convert two-table data to AnalysisResult schema
            return AnalysisResult(
                analysis_id=str(request.id),
                overall_score=result.overall_score or 0,
                ats_score=result.ats_score or 0,
                content_score=result.content_score or 0,
                formatting_score=result.formatting_score or 0,
                industry=request.target_industry,
                executive_summary=result.executive_summary or "Analysis completed.",
                detailed_scores=result.detailed_scores or {},
                processing_time_ms=result.processing_time_ms or 0,
                ai_model_used=result.ai_model_used or "unknown",
                completed_at=request.completed_at
            )

        except Exception as e:
            logger.error(f"Error getting analysis result: {str(e)}")
            raise AnalysisException(f"Failed to get analysis result: {str(e)}")

    async def list_user_analyses(self, user_id: uuid.UUID, limit: int = 10, offset: int = 0,
                               status: Optional[AnalysisStatus] = None, industry: Optional[Industry] = None) -> dict:
        """List user's analyses with optional filtering and pagination."""
        logger.info(f"Listing analyses for user {user_id}, limit {limit}, offset {offset}")

        try:
            # For now, return basic structure - TODO: implement actual repository method
            # This should call a repository method that does proper filtering and pagination
            analyses = []  # TODO: await self.repository.list_user_analyses(user_id, limit, offset, status, industry)

            return {
                "analyses": analyses,
                "total_count": 0  # TODO: Get actual count
            }

        except Exception as e:
            logger.error(f"Error listing user analyses: {str(e)}")
            raise AnalysisException(f"Failed to list analyses: {str(e)}")

    async def get_resume_analyses(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> list[AnalysisSummary]:
        """Get analysis history for a specific resume."""
        logger.info(f"Getting resume analyses for resume {resume_id}, user {user_id}")

        try:
            # TODO: Implement actual resume-specific analysis query
            # For now, return empty list to prevent errors
            return []

        except Exception as e:
            logger.error(f"Error getting resume analyses: {str(e)}")
            raise AnalysisException(f"Failed to get resume analyses: {str(e)}")

    async def cancel_analysis(self, request_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Cancel an ongoing analysis."""
        logger.info(f"Cancelling analysis {request_id} for user {user_id}")

        try:
            # TODO: Implement proper cancellation logic
            # For now, return False to indicate cancellation not available
            logger.warning(f"Analysis cancellation not yet implemented for {request_id}")
            return False

        except Exception as e:
            logger.error(f"Error cancelling analysis: {str(e)}")
            raise AnalysisException(f"Failed to cancel analysis: {str(e)}")

    async def get_user_stats(self, user_id: uuid.UUID) -> AnalysisStats:
        """Get comprehensive analysis statistics for the current user."""
        logger.info(f"Getting user stats for user {user_id}")

        try:
            # TODO: Implement actual statistics aggregation
            # For now, return basic stats structure
            return AnalysisStats(
                total_analyses=0,
                completed_analyses=0,
                failed_analyses=0,
                average_score=None,
                industry_breakdown={},
                tier_breakdown={}
            )

        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            raise AnalysisException(f"Failed to get user stats: {str(e)}")

    def get_analysis_limits(self) -> dict:
        """Get analysis configuration limits and supported options."""
        return {
            "max_file_size_mb": 10,
            "max_analyses_per_day": 50,
            "supported_file_types": ["pdf", "docx", "txt"]
        }

    def _map_database_industry_to_ai_agent(self, db_industry: Industry) -> str:
        """Map database industry enum to AI agent expected industry string.

        Args:
            db_industry: Industry enum from database

        Returns:
            AI agent compatible industry string

        Raises:
            AnalysisValidationException: If industry mapping not found
        """
        industry_mapping = {
            Industry.STRATEGY_TECH: "tech_consulting",
            Industry.MA_FINANCIAL: "finance_banking",
            Industry.CONSULTING: "strategy_consulting",
            Industry.SYSTEM_INTEGRATOR: "system_integrator",
            Industry.GENERAL: "general_business"
        }

        ai_industry = industry_mapping.get(db_industry)
        if not ai_industry:
            raise AnalysisValidationException(f"Unsupported industry: {db_industry}")

        logger.info(f"Mapped database industry '{db_industry.value}' to AI agent industry '{ai_industry}'")
        return ai_industry

    def _map_ai_agent_industry_to_database(self, ai_industry: str) -> Industry:
        """Map AI agent industry string back to database enum.

        Args:
            ai_industry: AI agent industry string

        Returns:
            Database Industry enum

        Raises:
            AnalysisValidationException: If industry mapping not found
        """
        reverse_mapping = {
            "tech_consulting": Industry.STRATEGY_TECH,
            "finance_banking": Industry.MA_FINANCIAL,
            "strategy_consulting": Industry.CONSULTING,
            "system_integrator": Industry.SYSTEM_INTEGRATOR,
            "general_business": Industry.GENERAL
        }

        db_industry = reverse_mapping.get(ai_industry)
        if not db_industry:
            raise AnalysisValidationException(f"Unknown AI agent industry: {ai_industry}")

        return db_industry

    def validate_industry_support(self, industry: Industry) -> bool:
        """Validate that the given industry is supported by AI agents.

        Args:
            industry: Database industry enum

        Returns:
            True if industry is supported, False otherwise
        """
        try:
            self._map_database_industry_to_ai_agent(industry)
            return True
        except AnalysisValidationException:
            return False

    def get_supported_industries(self) -> list[Industry]:
        """Get list of supported industries."""
        return [
            Industry.STRATEGY_TECH,
            Industry.MA_FINANCIAL,
            Industry.CONSULTING,
            Industry.SYSTEM_INTEGRATOR,
            Industry.GENERAL
        ]