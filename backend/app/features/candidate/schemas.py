"""Candidate management schemas."""

import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class CandidateCreate(BaseModel):
    """Schema for creating a new candidate."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    current_company: Optional[str] = Field(None, max_length=255)
    current_position: Optional[str] = Field(None, max_length=255)
    years_experience: Optional[int] = Field(None, ge=0, le=50)
    
    @validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v


class CandidateInfo(BaseModel):
    """Basic candidate information."""
    id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    current_company: Optional[str]
    current_position: Optional[str]
    years_experience: Optional[int]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CandidateWithStats(CandidateInfo):
    """Candidate with resume statistics."""
    total_resumes: int = 0
    latest_resume_version: int = 0
    last_resume_upload: Optional[datetime] = None


class CandidateListResponse(BaseModel):
    """Response for listing candidates."""
    candidates: List[CandidateWithStats]
    total_count: int
    limit: int
    offset: int


class CandidateCreateResponse(BaseModel):
    """Response for candidate creation."""
    success: bool
    message: str
    candidate: Optional[CandidateInfo] = None
    error: Optional[str] = None