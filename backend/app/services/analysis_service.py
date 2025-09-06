"""
Analysis Service
================

Business logic service for orchestrating complete resume analysis workflow.
This service provides a clean interface between the API layer and the AI module,
handling all business logic concerns while delegating AI processing to the orchestrator.

Key Responsibilities:
- Input validation and sanitization
- User authentication and authorization
- Analysis request lifecycle management
- Results storage and retrieval
- Error handling and user feedback
- Usage monitoring and rate limiting

The service maintains a clear separation between business logic and AI processing,
making it easy to test, monitor, and modify each layer independently.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.ai.orchestrator import ResumeAnalysisOrchestrator
from app.ai.integrations.openai_client import OpenAIClient
from app.ai.models.analysis_request import CompleteAnalysisResult
from app.core.config import get_settings
from app.core.datetime_utils import utc_now

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
    
    This service coordinates the complete analysis workflow:
    1. Input validation and preprocessing
    2. AI analysis orchestration via LangGraph
    3. Results processing and storage
    4. Error handling and user feedback
    """
    
    def __init__(self):
        """Initialize the analysis service with AI orchestrator."""
        self.settings = get_settings()
        self.llm_client = self._create_llm_client()
        self.ai_orchestrator = ResumeAnalysisOrchestrator(self.llm_client)
        
        # Configuration
        self.config = {
            "max_file_size_bytes": 10 * 1024 * 1024,  # 10MB
            "min_resume_length": 100,
            "max_resume_length": 50000,
            "supported_industries": [
                "tech_consulting", "system_integrator", "finance_banking",
                "healthcare_pharma", "manufacturing", "general_business"
            ],
            "analysis_timeout_seconds": 300  # 5 minutes
        }
        
        logger.info("AnalysisService initialized successfully")
    
    async def analyze_resume(
        self,
        resume_text: str,
        industry: str,
        user_id: str,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> CompleteAnalysisResult:
        """
        Main business logic interface for resume analysis.
        
        Args:
            resume_text: Resume text to analyze
            industry: Target industry for analysis
            user_id: User requesting the analysis
            analysis_options: Optional analysis configuration
            
        Returns:
            CompleteAnalysisResult: Complete analysis results
            
        Raises:
            AnalysisValidationException: When input validation fails
            AnalysisException: When analysis processing fails
        """
        # Generate unique analysis ID
        analysis_id = str(uuid.uuid4())
        
        try:
            # Business logic: input validation
            await self._validate_analysis_request(resume_text, industry, user_id)
            
            # Business logic: preprocessing
            processed_text = self._preprocess_resume_text(resume_text)
            
            # Business logic: logging and monitoring
            logger.info(f"Starting analysis {analysis_id} for user {user_id}, industry: {industry}")
            
            # Execute AI workflow (delegated to AI module)
            analysis_result = await self.ai_orchestrator.analyze_resume(
                resume_text=processed_text,
                industry=industry,
                analysis_id=analysis_id,
                user_id=user_id
            )
            
            # Business logic: post-processing and validation
            await self._validate_analysis_result(analysis_result)
            
            # Business logic: store results (would integrate with database)
            await self._store_analysis_result(analysis_result, user_id)
            
            # Business logic: usage tracking
            self._track_analysis_usage(user_id, industry, analysis_result.overall_score)
            
            logger.info(
                f"Analysis {analysis_id} completed successfully "
                f"(score: {analysis_result.overall_score}, time: {analysis_result.processing_time_seconds:.2f}s)"
            )
            
            return analysis_result
            
        except AnalysisValidationException:
            logger.warning(f"Analysis {analysis_id} failed validation: user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Analysis {analysis_id} failed for user {user_id}: {str(e)}")
            raise AnalysisException(f"Resume analysis failed: {str(e)}")
    
    async def get_analysis_result(
        self,
        analysis_id: str,
        user_id: str
    ) -> Optional[CompleteAnalysisResult]:
        """
        Retrieve stored analysis results.
        
        Args:
            analysis_id: Analysis identifier
            user_id: User requesting the results
            
        Returns:
            CompleteAnalysisResult: Stored analysis results if found
        """
        # Business logic: authorization check
        # In production, this would verify the user owns this analysis
        
        # Business logic: result retrieval (would integrate with database)
        # For now, this is a placeholder - in production this would query the database
        logger.info(f"Retrieving analysis {analysis_id} for user {user_id}")
        
        # Placeholder: would retrieve from database
        return None
    
    async def list_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List analysis history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            Dict containing analysis history and pagination info
        """
        # Business logic: pagination and filtering
        # Would integrate with database for actual retrieval
        logger.info(f"Listing analyses for user {user_id} (limit: {limit}, offset: {offset})")
        
        # Placeholder: would query database
        return {
            "analyses": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset
        }
    
    async def delete_analysis(
        self,
        analysis_id: str,
        user_id: str
    ) -> bool:
        """
        Delete an analysis result.
        
        Args:
            analysis_id: Analysis identifier
            user_id: User requesting deletion
            
        Returns:
            bool: True if deleted successfully
        """
        # Business logic: authorization and deletion
        logger.info(f"Deleting analysis {analysis_id} for user {user_id}")
        
        # Placeholder: would delete from database
        return True
    
    async def get_service_health(self) -> Dict[str, Any]:
        """
        Get service health status including AI orchestrator.
        
        Returns:
            Dict containing health status information
        """
        try:
            # Check AI orchestrator health
            ai_health = await self.ai_orchestrator.validate_setup()
            
            # Check LLM connection
            llm_health = await self.llm_client.validate_connection()
            
            # Get usage statistics
            usage_stats = self.llm_client.get_usage_stats()
            
            return {
                "status": "healthy" if (ai_health and llm_health) else "degraded",
                "ai_orchestrator": "healthy" if ai_health else "failed",
                "llm_connection": "healthy" if llm_health else "failed",
                "usage_stats": usage_stats,
                "workflow_info": self.ai_orchestrator.get_workflow_info(),
                "timestamp": utc_now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": utc_now().isoformat()
            }
    
    # ========================================================================
    # PRIVATE VALIDATION AND PROCESSING METHODS
    # ========================================================================
    
    async def _validate_analysis_request(
        self,
        resume_text: str,
        industry: str,
        user_id: str
    ) -> None:
        """
        Validate analysis request parameters.
        
        Args:
            resume_text: Resume text to validate
            industry: Industry to validate
            user_id: User ID to validate
            
        Raises:
            AnalysisValidationException: When validation fails
        """
        # Validate resume text
        if not resume_text or not resume_text.strip():
            raise AnalysisValidationException("Resume text cannot be empty")
        
        if len(resume_text) < self.config["min_resume_length"]:
            raise AnalysisValidationException(
                f"Resume text too short (minimum {self.config['min_resume_length']} characters)"
            )
        
        if len(resume_text) > self.config["max_resume_length"]:
            raise AnalysisValidationException(
                f"Resume text too long (maximum {self.config['max_resume_length']} characters)"
            )
        
        # Validate industry
        if industry not in self.config["supported_industries"]:
            raise AnalysisValidationException(
                f"Unsupported industry: {industry}. "
                f"Supported industries: {', '.join(self.config['supported_industries'])}"
            )
        
        # Validate user ID
        if not user_id or not user_id.strip():
            raise AnalysisValidationException("User ID cannot be empty")
        
        # Business logic: rate limiting check (would integrate with rate limiter)
        await self._check_rate_limits(user_id)
    
    def _preprocess_resume_text(self, resume_text: str) -> str:
        """
        Preprocess resume text for analysis.
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            str: Processed resume text
        """
        # Business logic: text preprocessing
        text = resume_text.strip()
        
        # Remove null bytes and other problematic characters
        text = text.replace('\x00', '')
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Limit excessive whitespace
        import re
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        
        return text
    
    async def _validate_analysis_result(self, result: CompleteAnalysisResult) -> None:
        """
        Validate analysis result before returning to user.
        
        Args:
            result: Analysis result to validate
            
        Raises:
            AnalysisException: When result validation fails
        """
        if not result:
            raise AnalysisException("Analysis produced no result")
        
        # Validate score range
        if not (0 <= result.overall_score <= 100):
            raise AnalysisException(f"Invalid overall score: {result.overall_score}")
        
        # Validate required fields
        if not result.analysis_summary:
            raise AnalysisException("Analysis summary is missing")
        
        if not result.structure_analysis or not result.appeal_analysis:
            raise AnalysisException("Incomplete analysis results")
        
        # Validate confidence metrics
        if not result.confidence_metrics:
            raise AnalysisException("Confidence metrics are missing")
    
    async def _store_analysis_result(
        self,
        result: CompleteAnalysisResult,
        user_id: str
    ) -> None:
        """
        Store analysis result in database.
        
        Args:
            result: Analysis result to store
            user_id: User who owns this analysis
        """
        # Business logic: result storage
        # In production, this would save to database
        logger.info(f"Storing analysis result {result.analysis_id} for user {user_id}")
        
        # Placeholder for database storage
        # await self.database.store_analysis(result, user_id)
    
    def _track_analysis_usage(
        self,
        user_id: str,
        industry: str,
        score: float
    ) -> None:
        """
        Track analysis usage for monitoring and billing.
        
        Args:
            user_id: User identifier
            industry: Industry analyzed
            score: Analysis score
        """
        # Business logic: usage tracking
        logger.info(f"Tracking usage: user={user_id}, industry={industry}, score={score:.2f}")
        
        # In production, would send to analytics/monitoring system
    
    async def _check_rate_limits(self, user_id: str) -> None:
        """
        Check rate limits for user.
        
        Args:
            user_id: User to check limits for
            
        Raises:
            AnalysisValidationException: When rate limits exceeded
        """
        # Business logic: rate limiting
        # In production, would check against rate limiter
        logger.debug(f"Checking rate limits for user {user_id}")
        
        # Placeholder - would integrate with actual rate limiter
        # if await self.rate_limiter.is_rate_limited(user_id):
        #     raise AnalysisValidationException("Rate limit exceeded")
    
    def _create_llm_client(self) -> OpenAIClient:
        """
        Create LLM client based on configuration.
        
        Returns:
            OpenAIClient: Configured LLM client
        """
        # Business logic: LLM client configuration
        return OpenAIClient(
            api_key=self.settings.OPENAI_API_KEY,
            model=getattr(self.settings, 'OPENAI_MODEL_NAME', 'gpt-4'),
            max_tokens=getattr(self.settings, 'OPENAI_MAX_TOKENS', 4000),
            temperature=getattr(self.settings, 'OPENAI_TEMPERATURE', 0.3),
            timeout_seconds=getattr(self.settings, 'OPENAI_REQUEST_TIMEOUT_SECONDS', 30)
        )
    
    # ========================================================================
    # PUBLIC UTILITY METHODS
    # ========================================================================
    
    def get_supported_industries(self) -> List[str]:
        """Get list of supported industries."""
        return self.config["supported_industries"].copy()
    
    def get_analysis_limits(self) -> Dict[str, Any]:
        """Get analysis configuration limits."""
        return {
            "min_resume_length": self.config["min_resume_length"],
            "max_resume_length": self.config["max_resume_length"],
            "max_file_size_bytes": self.config["max_file_size_bytes"],
            "analysis_timeout_seconds": self.config["analysis_timeout_seconds"],
            "supported_industries": self.config["supported_industries"]
        }
    
    def validate_industry(self, industry: str) -> bool:
        """
        Validate if an industry is supported.
        
        Args:
            industry: Industry to validate
            
        Returns:
            bool: True if supported, False otherwise
        """
        return industry in self.config["supported_industries"]