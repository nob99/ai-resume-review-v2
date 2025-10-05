"""Pydantic models for AI agents results."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.industries import IndustryConfig, get_supported_industries


class SpecificFeedbackItem(BaseModel):
    """Detailed feedback item with context and actionable suggestion.

    This model supports v1.1 prompts for granular, recruiter-friendly feedback.
    """
    category: str = Field(
        ...,
        description="Feedback category: 'grammar', 'structure', 'scr_framework', 'quantitative_impact', 'appeal_point'"
    )
    target_text: Optional[str] = Field(
        None,
        description="The specific resume text being referenced (achievement, sentence, etc.)"
    )
    issue: str = Field(..., description="What is wrong or missing")
    suggestion: str = Field(..., description="Concrete recommendation on how to fix it")


class StructureScores(BaseModel):
    """Scores from structure analysis."""
    format: float = Field(ge=0, le=100, description="Format and layout score")
    organization: float = Field(ge=0, le=100, description="Section organization score")
    tone: float = Field(ge=0, le=100, description="Professional tone score")
    completeness: float = Field(ge=0, le=100, description="Completeness score")


class StructureFeedback(BaseModel):
    """Feedback from structure analysis.

    V1.1: Two-level feedback approach
    - Level 1: Overall strengths/improvement_areas (summary)
    - Level 2: specific_feedback (detailed, actionable items)

    V1.0 fields kept for backward compatibility but deprecated.
    """
    # V1.1: Two-level feedback
    strengths: List[str] = Field(default_factory=list, description="Overall structure strengths")
    improvement_areas: List[str] = Field(default_factory=list, description="Overall improvement points")
    specific_feedback: List[SpecificFeedbackItem] = Field(
        default_factory=list,
        description="Detailed, actionable feedback items (v1.1)"
    )

    # V1.0: Deprecated but kept for backward compatibility
    issues: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Formatting issues identified")
    missing_sections: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Missing resume sections")
    tone_problems: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Tone and language issues")
    recommendations: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Improvement recommendations")


class StructureMetadata(BaseModel):
    """Metadata from structure analysis."""
    total_sections: Optional[int] = Field(None, description="Number of sections found")
    word_count: Optional[int] = Field(None, description="Approximate word count")
    reading_time: Optional[int] = Field(None, description="Estimated reading time in minutes")


class StructureAnalysisResult(BaseModel):
    """Complete structure analysis result."""
    scores: StructureScores
    feedback: StructureFeedback
    metadata: StructureMetadata = Field(default_factory=StructureMetadata)


class AppealScores(BaseModel):
    """Scores from appeal analysis."""
    achievement_relevance: float = Field(ge=0, le=100, description="Achievement relevance score")
    skills_alignment: float = Field(ge=0, le=100, description="Skills alignment score")
    experience_fit: float = Field(ge=0, le=100, description="Experience fit score")
    competitive_positioning: float = Field(ge=0, le=100, description="Competitive positioning score")


class AppealFeedback(BaseModel):
    """Feedback from appeal analysis.

    V1.1: Two-level feedback approach
    - Level 1: Overall strengths/improvement_areas (summary)
    - Level 2: specific_feedback (SCR framework, quantitative impact, appeal points)

    V1.0 fields kept for backward compatibility but deprecated.
    """
    # V1.1: Two-level feedback
    strengths: List[str] = Field(default_factory=list, description="Overall appeal strengths")
    improvement_areas: List[str] = Field(default_factory=list, description="Overall improvement points")
    specific_feedback: List[SpecificFeedbackItem] = Field(
        default_factory=list,
        description="Detailed, actionable feedback items (v1.1)"
    )

    # V1.0: Deprecated but kept for backward compatibility
    relevant_achievements: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Most relevant achievements")
    missing_skills: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Missing critical skills")
    transferable_experience: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Transferable experience")
    competitive_advantages: List[str] = Field(default_factory=list, description="[DEPRECATED v1.0] Competitive advantages")


class AppealAnalysisResult(BaseModel):
    """Complete appeal analysis result."""
    scores: AppealScores
    feedback: AppealFeedback


class ResumeAnalysisRequest(BaseModel):
    """Request model for resume analysis."""
    resume_text: str = Field(..., description="Resume text to analyze")
    industry: str = Field(..., description="Target industry for analysis")


class ResumeAnalysisResponse(BaseModel):
    """Complete resume analysis response."""
    success: bool = Field(..., description="Whether analysis completed successfully")
    analysis_id: str = Field(..., description="Unique analysis identifier")
    overall_score: float = Field(ge=0, le=100, description="Overall resume score")
    market_tier: str = Field(..., description="Market tier (entry/mid/senior/executive)")
    summary: str = Field(..., description="Executive summary of analysis")
    structure: StructureAnalysisResult = Field(..., description="Structure analysis results")
    appeal: AppealAnalysisResult = Field(..., description="Appeal analysis results")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class SupportedIndustries(BaseModel):
    """List of supported industries."""
    industries: List[IndustryConfig] = Field(default_factory=get_supported_industries)