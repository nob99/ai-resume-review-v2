"""
Analysis Request Models
=======================

This module defines the core data models for the AI analysis workflow.
It includes the LangGraph state schema and all result models used by agents.

Key Models:
- AnalysisState: TypedDict for LangGraph workflow state management
- StructureAnalysisResult: Structured output from Structure Agent
- AppealAnalysisResult: Structured output from Appeal Agent
- CompleteAnalysisResult: Final aggregated analysis result
"""

from typing import TypedDict, Optional, List, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AnalysisState(TypedDict):
    """
    LangGraph workflow state for resume analysis.
    
    This TypedDict defines all state that flows through the LangGraph workflow.
    Each node can read from and update this state as the analysis progresses.
    """
    
    # Input Data (immutable during workflow)
    resume_text: str
    industry: Literal[
        "tech_consulting", 
        "system_integrator", 
        "finance_banking",
        "healthcare_pharma", 
        "manufacturing", 
        "general_business"
    ]
    analysis_id: str
    user_id: str
    
    # Workflow Control State
    current_stage: Literal[
        "preprocessing", 
        "structure_analysis", 
        "structure_validation",
        "appeal_analysis", 
        "appeal_validation",
        "aggregation", 
        "complete", 
        "error"
    ]
    
    # Agent Results
    structure_analysis: Optional["StructureAnalysisResult"]
    structure_confidence: Optional[float]
    structure_errors: List[str]
    
    appeal_analysis: Optional["AppealAnalysisResult"]  
    appeal_confidence: Optional[float]
    appeal_errors: List[str]
    
    # Final Output
    final_result: Optional["CompleteAnalysisResult"]
    overall_score: Optional[float]
    
    # Error Handling & Recovery
    has_errors: bool
    error_messages: List[str]
    retry_count: int
    max_retries: int
    
    # Workflow Metadata
    started_at: Optional[str]  # ISO timestamp
    completed_at: Optional[str]  # ISO timestamp
    processing_time_seconds: Optional[float]


class BaseAnalysisResult(BaseModel):
    """Base class for all agent analysis results with common metadata."""
    
    confidence_score: float = Field(
        ge=0.0, le=1.0, 
        description="Analysis confidence score (0.0 to 1.0)"
    )
    processing_time_ms: int = Field(
        ge=0,
        description="Processing time in milliseconds"
    )
    model_used: str = Field(
        description="LLM model used for analysis"
    )
    prompt_version: str = Field(
        description="Version of prompt template used"
    )


class StructureAnalysisResult(BaseAnalysisResult):
    """
    Structured output from the Structure Agent.
    
    Analyzes resume structure, formatting, completeness, and professional presentation.
    All scores are on a 0-100 scale for consistency.
    """
    
    # Core Structural Scores (0-100 scale)
    format_score: float = Field(
        ge=0, le=100, 
        description="Resume formatting and visual presentation quality"
    )
    section_organization_score: float = Field(
        ge=0, le=100,
        description="Organization and logical flow of resume sections"
    )
    professional_tone_score: float = Field(
        ge=0, le=100,
        description="Professional language and tone assessment"
    )
    completeness_score: float = Field(
        ge=0, le=100,
        description="Completeness of required information and sections"
    )
    
    # Detailed Issue Analysis
    formatting_issues: List[str] = Field(
        description="Specific formatting problems identified",
        default_factory=list
    )
    missing_sections: List[str] = Field(
        description="Expected resume sections that are missing",
        default_factory=list
    )
    tone_problems: List[str] = Field(
        description="Instances of unprofessional language or tone",
        default_factory=list
    )
    completeness_gaps: List[str] = Field(
        description="Missing critical information or details",
        default_factory=list
    )
    
    # Positive Feedback
    strengths: List[str] = Field(
        description="Well-executed structural and formatting elements",
        default_factory=list
    )
    recommendations: List[str] = Field(
        description="Specific improvement suggestions for structure",
        default_factory=list
    )
    
    # Analytical Metadata
    total_sections_found: int = Field(
        ge=0,
        description="Number of distinct resume sections identified"
    )
    word_count: int = Field(
        ge=0,
        description="Total word count of the resume"
    )
    estimated_reading_time_minutes: int = Field(
        ge=1,
        description="Estimated reading time in minutes"
    )


class AppealAnalysisResult(BaseAnalysisResult):
    """
    Structured output from the Appeal Agent.
    
    Provides industry-specific analysis of resume appeal, competitiveness,
    and alignment with target industry requirements.
    """
    
    # Core Industry Appeal Scores (0-100 scale)
    achievement_relevance_score: float = Field(
        ge=0, le=100,
        description="Relevance of achievements to target industry"
    )
    skills_alignment_score: float = Field(
        ge=0, le=100,
        description="Alignment of skills with industry requirements"
    )
    experience_fit_score: float = Field(
        ge=0, le=100,
        description="Relevance and fit of experience for industry"
    )
    competitive_positioning_score: float = Field(
        ge=0, le=100,
        description="Competitive positioning within industry market"
    )
    
    # Industry-Specific Analysis
    relevant_achievements: List[str] = Field(
        description="Standout achievements most relevant to this industry",
        default_factory=list
    )
    missing_skills: List[str] = Field(
        description="Critical skills gaps for target industry",
        default_factory=list
    )
    transferable_experience: List[str] = Field(
        description="Cross-industry experience that adds value",
        default_factory=list
    )
    industry_keywords: List[str] = Field(
        description="Industry-specific terms and keywords found",
        default_factory=list
    )
    
    # Competitive Market Assessment
    market_tier: Literal["entry", "mid", "senior", "executive"] = Field(
        description="Assessed market level based on experience and achievements"
    )
    competitive_advantages: List[str] = Field(
        description="Unique selling points and competitive advantages",
        default_factory=list
    )
    improvement_areas: List[str] = Field(
        description="Priority areas for enhancement to improve appeal",
        default_factory=list
    )
    
    # Context Integration
    structure_context_used: bool = Field(
        description="Whether structure analysis results informed this analysis",
        default=False
    )
    
    # Industry Context
    target_industry: str = Field(
        description="Target industry for this analysis"
    )


class CompleteAnalysisResult(BaseModel):
    """
    Final aggregated result combining structure and appeal analysis.
    
    This model represents the complete analysis output that will be
    returned to the business logic layer and displayed to users.
    """
    
    # Overall Assessment
    overall_score: float = Field(
        ge=0, le=100,
        description="Weighted overall score combining structure and appeal"
    )
    
    # Component Analysis Results
    structure_analysis: StructureAnalysisResult = Field(
        description="Complete structure analysis results"
    )
    appeal_analysis: AppealAnalysisResult = Field(
        description="Complete industry appeal analysis results"
    )
    
    # Executive Summary
    analysis_summary: str = Field(
        description="Executive summary of the complete analysis"
    )
    key_strengths: List[str] = Field(
        description="Top 3-5 resume strengths across all dimensions",
        max_length=5
    )
    priority_improvements: List[str] = Field(
        description="Top 3-5 priority improvement areas",
        max_length=5
    )
    
    # Analysis Context
    industry: str = Field(
        description="Target industry for this analysis"
    )
    analysis_id: str = Field(
        description="Unique identifier for this analysis"
    )
    
    # Processing Metadata
    completed_at: str = Field(
        description="ISO timestamp when analysis was completed"
    )
    processing_time_seconds: float = Field(
        ge=0,
        description="Total processing time for the analysis"
    )
    
    # Quality Metrics
    confidence_metrics: Dict[str, float] = Field(
        description="Confidence scores for different analysis components",
        default_factory=dict
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda dt: dt.isoformat()
        }
    )
        
    def get_score_breakdown(self) -> Dict[str, float]:
        """Get detailed score breakdown for frontend display."""
        return {
            "structure": {
                "format": self.structure_analysis.format_score,
                "organization": self.structure_analysis.section_organization_score,
                "tone": self.structure_analysis.professional_tone_score,
                "completeness": self.structure_analysis.completeness_score,
            },
            "appeal": {
                "achievements": self.appeal_analysis.achievement_relevance_score,
                "skills": self.appeal_analysis.skills_alignment_score,
                "experience": self.appeal_analysis.experience_fit_score,
                "competitiveness": self.appeal_analysis.competitive_positioning_score,
            },
            "overall": self.overall_score
        }
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for monitoring and analytics."""
        return {
            "analysis_id": self.analysis_id,
            "industry": self.industry,
            "overall_score": self.overall_score,
            "processing_time_seconds": self.processing_time_seconds,
            "structure_confidence": self.structure_analysis.confidence_score,
            "appeal_confidence": self.appeal_analysis.confidence_score,
            "word_count": self.structure_analysis.word_count,
            "sections_found": self.structure_analysis.total_sections_found,
            "market_tier": self.appeal_analysis.market_tier,
            "completed_at": self.completed_at
        }


# Type aliases for convenience
AnalysisResult = CompleteAnalysisResult
WorkflowState = AnalysisState