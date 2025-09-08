"""
Legacy AI Adapter
==================

This adapter wraps the existing ResumeAnalysisOrchestrator to conform to the new AIAnalyzer interface.
It provides a clean migration path by allowing the old AI system to work with the new architecture
without any changes to the existing implementation.

Key Features:
- Zero-risk wrapper around existing orchestrator
- Data transformation between old and new models
- Identical behavior preservation
- Performance monitoring and logging
- Error handling compatibility
"""

import time
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from app.ai_agents.interface import (
    AIAnalyzer, 
    AnalysisRequest, 
    AnalysisResult, 
    AnalysisScore,
    Industry,
    ExperienceLevel,
    AIServiceError,
    AIServiceUnavailable,
    AIAnalysisTimeout,
    InvalidResumeContent
)
from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.integrations.openai_client import OpenAIClient
from app.ai.models.analysis_request import CompleteAnalysisResult
from app.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class LegacyAIAdapter:
    """
    Adapter that wraps the existing ResumeAnalysisOrchestrator to implement the new AIAnalyzer interface.
    
    This adapter serves as a bridge between the old AI system and the new architecture,
    allowing for zero-risk migration while maintaining identical behavior.
    """
    
    def __init__(self):
        """Initialize the adapter with the legacy orchestrator."""
        try:
            # Initialize the legacy AI components
            from app.core.config import get_settings
            settings = get_settings()
            
            llm_client = OpenAIClient(
                api_key=settings.OPENAI_API_KEY,
                model=getattr(settings, 'OPENAI_MODEL_NAME', 'gpt-4'),
                max_tokens=getattr(settings, 'OPENAI_MAX_TOKENS', 4000),
                temperature=getattr(settings, 'OPENAI_TEMPERATURE', 0.3),
                timeout_seconds=getattr(settings, 'OPENAI_REQUEST_TIMEOUT_SECONDS', 30)
            )
            self.orchestrator = ResumeAnalysisOrchestrator(llm_client)
            
            # Adapter configuration
            self.config = {
                "timeout_seconds": 120,  # 2 minutes timeout for analysis
                "max_text_length": 50000,  # Maximum resume text length
                "supported_industries": {
                    # Map new industry enum to legacy industry strings
                    Industry.STRATEGY_TECH: "tech_consulting",
                    Industry.MA_FINANCIAL: "finance_banking", 
                    Industry.CONSULTING: "general_business",
                    Industry.SYSTEM_INTEGRATOR: "system_integrator",
                    Industry.GENERAL: "general_business"
                }
            }
            
            logger.info("LegacyAIAdapter initialized successfully with ResumeAnalysisOrchestrator")
            
        except Exception as e:
            logger.error(f"Failed to initialize LegacyAIAdapter: {str(e)}")
            raise AIServiceUnavailable(f"Could not initialize AI service: {str(e)}")
    
    async def analyze_resume(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Analyze a resume using the legacy orchestrator and transform results to new format.
        
        Args:
            request: Analysis request with resume text and context
            
        Returns:
            AnalysisResult: Transformed analysis results in new format
            
        Raises:
            InvalidResumeContent: If resume content is invalid
            AIAnalysisTimeout: If analysis times out
            AIServiceError: For other analysis failures
        """
        start_time = time.time()
        analysis_id = str(uuid.uuid4())
        
        try:
            # Validate input
            await self._validate_input(request)
            
            # Transform new request to legacy format
            legacy_industry = self._map_industry_to_legacy(request.industry)
            user_id = "legacy_adapter_user"  # Default user for adapter
            
            logger.info(f"Starting legacy analysis for industry: {legacy_industry}")
            
            # Call the legacy orchestrator
            legacy_result = await self.orchestrator.analyze_resume(
                resume_text=request.text,
                industry=legacy_industry,
                analysis_id=analysis_id,
                user_id=user_id
            )
            
            # Transform legacy result to new format
            analysis_result = await self._transform_legacy_result(
                legacy_result, 
                request, 
                start_time
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Legacy analysis completed in {processing_time:.2f}s")
            
            return analysis_result
            
        except (InvalidResumeContent, AIAnalysisTimeout, AIServiceError):
            # Re-raise our own exceptions without modification
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Legacy analysis failed after {processing_time:.2f}s: {str(e)}")
            
            # Map exceptions to new error types
            if "timeout" in str(e).lower():
                raise AIAnalysisTimeout(f"Analysis timed out: {str(e)}")
            elif "invalid" in str(e).lower() or "content" in str(e).lower():
                raise InvalidResumeContent(f"Invalid resume content: {str(e)}")
            else:
                raise AIServiceError(f"Analysis failed: {str(e)}")
    
    async def get_structure_analysis(self, request: AnalysisRequest) -> AnalysisScore:
        """
        Get structure-only analysis by running full analysis and extracting structure component.
        
        Args:
            request: The analysis request
            
        Returns:
            AnalysisScore: Structure analysis score and feedback
        """
        try:
            # Run full analysis
            full_result = await self.analyze_resume(request)
            
            # Extract and return structure score
            return full_result.structure_score
            
        except Exception as e:
            logger.error(f"Structure analysis failed: {str(e)}")
            raise AIServiceError(f"Structure analysis failed: {str(e)}")
    
    async def get_appeal_analysis(self, request: AnalysisRequest) -> AnalysisScore:
        """
        Get appeal-only analysis by running full analysis and extracting appeal component.
        
        Args:
            request: The analysis request
            
        Returns:
            AnalysisScore: Appeal analysis score and feedback
        """
        try:
            # Run full analysis
            full_result = await self.analyze_resume(request)
            
            # Extract and return appeal score
            return full_result.appeal_score
            
        except Exception as e:
            logger.error(f"Appeal analysis failed: {str(e)}")
            raise AIServiceError(f"Appeal analysis failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if the legacy AI service is healthy and ready.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Test with minimal content
            test_request = AnalysisRequest(
                text="John Doe\nSoftware Engineer\n• Experience in programming",
                industry=Industry.GENERAL
            )
            
            # Try a quick analysis (with shorter timeout)
            result = await self.analyze_resume(test_request)
            
            # Check if we got a valid result
            health_ok = (
                result.overall_score >= 0 and 
                result.overall_score <= 100 and
                len(result.summary) > 0
            )
            
            logger.info(f"Health check {'passed' if health_ok else 'failed'}")
            return health_ok
            
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False
    
    async def _validate_input(self, request: AnalysisRequest) -> None:
        """Validate input request parameters."""
        if not request.text or len(request.text.strip()) < 10:
            raise InvalidResumeContent("Resume text is too short or empty")
        
        if len(request.text) > self.config["max_text_length"]:
            raise InvalidResumeContent(f"Resume text too long (max {self.config['max_text_length']} chars)")
        
        if request.industry not in self.config["supported_industries"]:
            raise InvalidResumeContent(f"Unsupported industry: {request.industry}")
    
    def _map_industry_to_legacy(self, industry: Industry) -> str:
        """Map new industry enum to legacy industry string."""
        return self.config["supported_industries"].get(industry, "general_business")
    
    def _map_experience_level(self, level: Optional[ExperienceLevel]) -> str:
        """Map experience level to legacy format."""
        if not level:
            return "mid"  # Default
        
        mapping = {
            ExperienceLevel.ENTRY: "entry",
            ExperienceLevel.MID: "mid", 
            ExperienceLevel.SENIOR: "senior",
            ExperienceLevel.EXECUTIVE: "executive"
        }
        return mapping.get(level, "mid")
    
    async def _transform_legacy_result(
        self, 
        legacy_result: CompleteAnalysisResult, 
        original_request: AnalysisRequest,
        start_time: float
    ) -> AnalysisResult:
        """
        Transform legacy analysis result to new AnalysisResult format.
        
        Args:
            legacy_result: Result from ResumeAnalysisOrchestrator
            original_request: Original analysis request
            start_time: When analysis started (for timing)
            
        Returns:
            AnalysisResult: Transformed result in new format
        """
        processing_time_ms = max(1, int((time.time() - start_time) * 1000))  # Ensure at least 1ms
        
        # Extract structure information
        structure_score = AnalysisScore(
            score=int(
                (legacy_result.structure_analysis.format_score + 
                 legacy_result.structure_analysis.section_organization_score +
                 legacy_result.structure_analysis.professional_tone_score +
                 legacy_result.structure_analysis.completeness_score) / 4
            ),
            feedback=f"Structure Analysis: Format ({legacy_result.structure_analysis.format_score:.1f}), "
                    f"Organization ({legacy_result.structure_analysis.section_organization_score:.1f}), "
                    f"Tone ({legacy_result.structure_analysis.professional_tone_score:.1f}), "
                    f"Completeness ({legacy_result.structure_analysis.completeness_score:.1f})",
            suggestions=legacy_result.structure_analysis.recommendations
        )
        
        # Extract appeal information  
        appeal_score = AnalysisScore(
            score=int(
                (legacy_result.appeal_analysis.achievement_relevance_score +
                 legacy_result.appeal_analysis.skills_alignment_score +
                 legacy_result.appeal_analysis.experience_fit_score +
                 legacy_result.appeal_analysis.competitive_positioning_score) / 4
            ),
            feedback=f"Appeal Analysis: Achievements ({legacy_result.appeal_analysis.achievement_relevance_score:.1f}), "
                    f"Skills ({legacy_result.appeal_analysis.skills_alignment_score:.1f}), "
                    f"Experience ({legacy_result.appeal_analysis.experience_fit_score:.1f}), "
                    f"Competitiveness ({legacy_result.appeal_analysis.competitive_positioning_score:.1f})",
            suggestions=legacy_result.appeal_analysis.improvement_areas
        )
        
        # Calculate content score as average of relevant metrics
        content_score = AnalysisScore(
            score=int((appeal_score.score + structure_score.score) / 2),
            feedback=f"Content quality combines structure and appeal elements. "
                    f"Strong areas: {', '.join(legacy_result.key_strengths[:3])}",
            suggestions=legacy_result.priority_improvements
        )
        
        # Build comprehensive strengths and weaknesses
        strengths = []
        strengths.extend(legacy_result.structure_analysis.strengths[:3])
        strengths.extend(legacy_result.appeal_analysis.competitive_advantages[:2])
        
        weaknesses = []
        if legacy_result.structure_analysis.formatting_issues:
            weaknesses.extend(legacy_result.structure_analysis.formatting_issues[:2])
        if legacy_result.appeal_analysis.missing_skills:
            weaknesses.extend([f"Missing skill: {skill}" for skill in legacy_result.appeal_analysis.missing_skills[:2]])
        
        # Calculate confidence score
        avg_confidence = (
            legacy_result.structure_analysis.confidence_score +
            legacy_result.appeal_analysis.confidence_score
        ) / 2
        
        # Create final result
        return AnalysisResult(
            overall_score=int(legacy_result.overall_score),
            summary=legacy_result.analysis_summary,
            structure_score=structure_score,
            content_score=content_score,
            appeal_score=appeal_score,
            strengths=strengths[:5],  # Limit to top 5
            weaknesses=weaknesses[:5],  # Limit to top 5 
            recommendations=legacy_result.priority_improvements,
            ai_model_used=f"{legacy_result.structure_analysis.model_used} (via legacy adapter)",
            processing_time_ms=processing_time_ms,
            confidence_score=avg_confidence
        )