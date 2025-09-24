"""
Pydantic schemas for review feature API requests and responses.
Defines data validation and serialization models.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, validator
from enum import Enum


class ReviewStatus(str, Enum):
    """Review request status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewType(str, Enum):
    """Review type enumeration."""
    COMPREHENSIVE = "comprehensive"
    QUICK_SCAN = "quick_scan"
    ATS_CHECK = "ats_check"


class ExperienceLevel(str, Enum):
    """Experience level enumeration."""
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    EXECUTIVE = "executive"


# Request Schemas

class CreateReviewRequest(BaseModel):
    """Schema for creating a new review request."""
    
    resume_id: UUID = Field(..., description="ID of the resume to review")
    target_industry: str = Field(..., min_length=1, max_length=100, description="Target industry for the review")
    target_role: Optional[str] = Field(None, max_length=255, description="Optional target role")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Optional experience level")
    review_type: ReviewType = Field(ReviewType.COMPREHENSIVE, description="Type of review to perform")
    
    @validator('target_industry')
    def validate_target_industry(cls, v):
        """Validate target industry is not empty."""
        if not v or not v.strip():
            raise ValueError("Target industry cannot be empty")
        return v.strip()
    
    @validator('target_role')
    def validate_target_role(cls, v):
        """Validate target role if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ProcessReviewRequest(BaseModel):
    """Schema for submitting a review for processing."""
    
    review_request_id: UUID = Field(..., description="ID of the review request to process")


# Response Schemas

class ProcessingInfo(BaseModel):
    """Schema for processing status information."""
    
    found: bool = Field(..., description="Whether the review request was found")
    status: Optional[str] = Field(None, description="Current processing status")
    has_result: Optional[bool] = Field(None, description="Whether results are available")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if any")


class ResultSummary(BaseModel):
    """Schema for review result summary."""
    
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Overall score (0-100)")
    executive_summary: Optional[str] = Field(None, description="Executive summary of the review")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    ai_model_used: Optional[str] = Field(None, description="AI model used for analysis")
    created_at: Optional[datetime] = Field(None, description="When the result was created")


class ReviewRequestResponse(BaseModel):
    """Schema for review request response."""
    
    id: UUID = Field(..., description="Review request ID")
    resume_id: UUID = Field(..., description="Resume ID")
    requested_by_user_id: UUID = Field(..., description="User who requested the review")
    target_role: Optional[str] = Field(None, description="Target role")
    target_industry: str = Field(..., description="Target industry")
    experience_level: Optional[str] = Field(None, description="Experience level")
    review_type: str = Field(..., description="Type of review")
    status: str = Field(..., description="Current status")
    requested_at: datetime = Field(..., description="When the review was requested")
    completed_at: Optional[datetime] = Field(None, description="When the review was completed")
    processing_info: Optional[ProcessingInfo] = Field(None, description="Processing status information")
    result_summary: Optional[ResultSummary] = Field(None, description="Result summary if available")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ReviewResultResponse(BaseModel):
    """Schema for complete review results with raw AI response."""
    
    id: UUID = Field(..., description="Review result ID")
    review_request_id: UUID = Field(..., description="Review request ID")
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Overall score (0-100)")
    executive_summary: Optional[str] = Field(None, description="Executive summary")
    raw_ai_response: Optional[Dict[str, Any]] = Field(None, description="Complete raw AI response JSON")
    ai_model_used: Optional[str] = Field(None, description="AI model used")
    processing_time_ms: Optional[int] = Field(None, description="Processing time in milliseconds")
    created_at: datetime = Field(..., description="When the result was created")
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Schema for list of review requests."""
    
    id: UUID = Field(..., description="Review request ID")
    resume_id: Optional[UUID] = Field(None, description="Resume ID (for user reviews)")
    target_role: Optional[str] = Field(None, description="Target role")
    target_industry: str = Field(..., description="Target industry")
    experience_level: Optional[str] = Field(None, description="Experience level")
    review_type: str = Field(..., description="Type of review")
    status: str = Field(..., description="Current status")
    requested_at: datetime = Field(..., description="When requested")
    completed_at: Optional[datetime] = Field(None, description="When completed")
    result_summary: Optional[ResultSummary] = Field(None, description="Result summary if available")


class TaskSubmissionResponse(BaseModel):
    """Schema for task submission response."""
    
    success: bool = Field(..., description="Whether submission was successful")
    review_request_id: UUID = Field(..., description="Review request ID")
    status: Optional[str] = Field(None, description="Current status")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")


class AIConnectionTestResponse(BaseModel):
    """Schema for AI connection test response."""
    
    success: bool = Field(..., description="Whether test was successful")
    processing_time_ms: Optional[int] = Field(None, description="Test processing time")
    ai_model: Optional[str] = Field(None, description="AI model tested")
    response_valid: Optional[bool] = Field(None, description="Whether test response was valid")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Additional message")


# Analysis-specific schemas for structured data access

class AnalysisScores(BaseModel):
    """Schema for analysis scores section."""
    
    format: Optional[int] = Field(None, ge=0, le=100)
    organization: Optional[int] = Field(None, ge=0, le=100)
    tone: Optional[int] = Field(None, ge=0, le=100)
    completeness: Optional[int] = Field(None, ge=0, le=100)
    achievement_relevance: Optional[int] = Field(None, ge=0, le=100)
    skills_alignment: Optional[int] = Field(None, ge=0, le=100)


class AnalysisFeedback(BaseModel):
    """Schema for analysis feedback section."""
    
    issues: Optional[List[str]] = Field(None, description="List of identified issues")
    recommendations: Optional[List[str]] = Field(None, description="List of recommendations")
    relevant_achievements: Optional[List[str]] = Field(None, description="Relevant achievements")
    improvement_areas: Optional[List[str]] = Field(None, description="Areas for improvement")


class StructureAnalysis(BaseModel):
    """Schema for structure analysis results."""
    
    scores: Optional[AnalysisScores] = Field(None, description="Structure scores")
    feedback: Optional[AnalysisFeedback] = Field(None, description="Structure feedback")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AppealAnalysis(BaseModel):
    """Schema for appeal analysis results."""
    
    scores: Optional[AnalysisScores] = Field(None, description="Appeal scores")
    feedback: Optional[AnalysisFeedback] = Field(None, description="Appeal feedback")


class ParsedAIResponse(BaseModel):
    """Schema for parsed AI response with structured access."""
    
    success: bool = Field(..., description="Whether analysis was successful")
    analysis_id: str = Field(..., description="Analysis tracking ID")
    overall_score: int = Field(..., ge=0, le=100, description="Overall score")
    market_tier: Optional[str] = Field(None, description="Market tier assessment")
    summary: str = Field(..., description="Executive summary")
    structure: Optional[StructureAnalysis] = Field(None, description="Structure analysis")
    appeal: Optional[AppealAnalysis] = Field(None, description="Appeal analysis")
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @classmethod
    def from_raw_response(cls, raw_response: Dict[str, Any]) -> "ParsedAIResponse":
        """
        Create ParsedAIResponse from raw AI response dictionary.
        
        Args:
            raw_response: Raw AI response dict
            
        Returns:
            ParsedAIResponse instance
        """
        return cls(**raw_response)


# Error response schemas

class ErrorDetail(BaseModel):
    """Schema for error details."""
    
    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Main error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


# Validation schemas

class ReviewRequestValidation(BaseModel):
    """Schema for validating review requests."""
    
    resume_exists: bool = Field(..., description="Whether resume exists")
    resume_has_text: bool = Field(..., description="Whether resume has extractable text")
    industry_valid: bool = Field(..., description="Whether industry is valid")
    user_authorized: bool = Field(..., description="Whether user is authorized")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return not self.errors and self.resume_exists and self.resume_has_text