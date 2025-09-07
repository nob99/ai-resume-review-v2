"""
AI agents interface for the new infrastructure layer.
Defines the contract that AI services must implement, decoupling AI logic from business logic.
"""

from typing import Protocol, List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class Industry(str, Enum):
    """Supported industries for resume analysis."""
    STRATEGY_TECH = "strategy_tech"
    MA_FINANCIAL = "ma_financial_advisory"
    CONSULTING = "full_service_consulting"
    SYSTEM_INTEGRATOR = "system_integrator"
    GENERAL = "general"


class ExperienceLevel(str, Enum):
    """Experience levels for candidates."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"


class AnalysisRequest(BaseModel):
    """
    Input for AI analysis.
    
    This model defines what information the AI needs to analyze a resume.
    """
    text: str = Field(..., description="The resume text to analyze")
    industry: Industry = Field(..., description="Target industry for the analysis")
    role: Optional[str] = Field(None, description="Target role/position")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Candidate's experience level")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Any additional context for analysis")


class AnalysisScore(BaseModel):
    """Individual score component."""
    score: int = Field(..., ge=0, le=100, description="Score out of 100")
    feedback: str = Field(..., description="Detailed feedback for this score")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class AnalysisResult(BaseModel):
    """
    Output from AI analysis.
    
    This model defines the structure of analysis results that all AI implementations must return.
    """
    # Overall assessment
    overall_score: int = Field(..., ge=0, le=100, description="Overall resume score")
    summary: str = Field(..., description="Executive summary of the analysis")
    
    # Detailed scores
    structure_score: AnalysisScore = Field(..., description="Resume structure and formatting score")
    content_score: AnalysisScore = Field(..., description="Content quality and relevance score")
    appeal_score: AnalysisScore = Field(..., description="Industry-specific appeal score")
    
    # Strengths and weaknesses
    strengths: List[str] = Field(..., description="Key strengths identified")
    weaknesses: List[str] = Field(..., description="Areas for improvement")
    recommendations: List[str] = Field(..., description="Specific recommendations")
    
    # Metadata
    ai_model_used: str = Field(..., description="AI model/version used for analysis")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="AI confidence in the analysis")


class AIAnalyzer(Protocol):
    """
    Protocol defining the interface for AI analysis services.
    
    All AI implementations must conform to this interface, ensuring
    that the business logic can work with any AI provider.
    """
    
    async def analyze_resume(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Analyze a resume and provide comprehensive feedback.
        
        Args:
            request: The analysis request with resume text and context
            
        Returns:
            Comprehensive analysis results
            
        Raises:
            AIServiceError: If the analysis fails
        """
        ...
    
    async def get_structure_analysis(self, request: AnalysisRequest) -> AnalysisScore:
        """
        Analyze resume structure and formatting.
        
        Args:
            request: The analysis request
            
        Returns:
            Structure analysis score and feedback
            
        Raises:
            AIServiceError: If the analysis fails
        """
        ...
    
    async def get_appeal_analysis(self, request: AnalysisRequest) -> AnalysisScore:
        """
        Analyze resume appeal for the target industry.
        
        Args:
            request: The analysis request
            
        Returns:
            Industry-specific appeal score and feedback
            
        Raises:
            AIServiceError: If the analysis fails
        """
        ...
    
    async def health_check(self) -> bool:
        """
        Check if the AI service is healthy and ready.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        ...


class PromptTemplate(BaseModel):
    """
    Template for AI prompts.
    
    This model defines how prompts are structured for versioning and A/B testing.
    """
    name: str = Field(..., description="Unique name for the prompt")
    version: str = Field(..., description="Version identifier (e.g., '1.0.0')")
    template: str = Field(..., description="The prompt template with placeholders")
    system_prompt: Optional[str] = Field(None, description="System prompt for the AI")
    variables: List[str] = Field(default_factory=list, description="Required variables for the template")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AIServiceError(Exception):
    """Base exception for AI service errors."""
    pass


class AIServiceUnavailable(AIServiceError):
    """Raised when the AI service is unavailable."""
    pass


class AIAnalysisTimeout(AIServiceError):
    """Raised when AI analysis times out."""
    pass


class InvalidResumeContent(AIServiceError):
    """Raised when resume content is invalid or cannot be processed."""
    pass