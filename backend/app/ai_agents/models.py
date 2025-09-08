"""Pydantic models for AI agents results."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StructureScores(BaseModel):
    """Scores from structure analysis."""
    format: float = Field(ge=0, le=100, description="Format and layout score")
    organization: float = Field(ge=0, le=100, description="Section organization score")
    tone: float = Field(ge=0, le=100, description="Professional tone score")
    completeness: float = Field(ge=0, le=100, description="Completeness score")


class StructureFeedback(BaseModel):
    """Feedback from structure analysis."""
    issues: List[str] = Field(default_factory=list, description="Formatting issues identified")
    missing_sections: List[str] = Field(default_factory=list, description="Missing resume sections")
    tone_problems: List[str] = Field(default_factory=list, description="Tone and language issues")
    strengths: List[str] = Field(default_factory=list, description="Structure strengths")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")


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
    """Feedback from appeal analysis."""
    relevant_achievements: List[str] = Field(default_factory=list, description="Most relevant achievements")
    missing_skills: List[str] = Field(default_factory=list, description="Missing critical skills")
    transferable_experience: List[str] = Field(default_factory=list, description="Transferable experience")
    competitive_advantages: List[str] = Field(default_factory=list, description="Competitive advantages")
    improvement_areas: List[str] = Field(default_factory=list, description="Priority improvement areas")


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


class IndustryConfig(BaseModel):
    """Industry configuration model."""
    code: str = Field(..., description="Industry code")
    display_name: str = Field(..., description="Display name")
    key_skills: List[str] = Field(..., description="Key skills for this industry")


class SupportedIndustries(BaseModel):
    """List of supported industries."""
    industries: List[IndustryConfig] = Field(
        default_factory=lambda: [
            IndustryConfig(
                code="tech_consulting",
                display_name="Technology Consulting",
                key_skills=["Python", "JavaScript", "Cloud Architecture", "System Design", "Agile", "DevOps"]
            ),
            IndustryConfig(
                code="finance_banking",
                display_name="Finance & Banking",
                key_skills=["Financial Modeling", "Risk Management", "Regulatory Compliance", "Bloomberg", "Excel", "VBA"]
            ),
            IndustryConfig(
                code="general_business",
                display_name="General Business",
                key_skills=["Project Management", "Strategic Planning", "Data Analysis", "Leadership", "Communication"]
            ),
            IndustryConfig(
                code="system_integrator",
                display_name="Systems Integration",
                key_skills=["Systems Integration", "Enterprise Architecture", "API Development", "Database Management"]
            ),
            IndustryConfig(
                code="strategy_consulting",
                display_name="Strategy Consulting",
                key_skills=["Strategic Analysis", "Market Research", "Business Modeling", "PowerPoint", "Excel"]
            ),
            IndustryConfig(
                code="full_service_consulting",
                display_name="Full Service Consulting",
                key_skills=["Business Analysis", "Change Management", "Process Improvement", "Stakeholder Management"]
            )
        ]
    )