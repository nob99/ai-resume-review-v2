"""
Candidate database model for the recruitment platform.

Contains the Candidate model as the central business entity in the candidate-centric architecture.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from app.core.datetime_utils import utc_now


class Candidate(Base):
    """
    Candidate model - central business entity.
    
    In the new candidate-centric architecture, everything revolves around candidates:
    - Recruiters are assigned to candidates
    - Resumes belong to candidates
    - Reviews are performed on candidate resumes
    """
    
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True)  # Optional as some candidates may not have email initially
    phone = Column(String(50), nullable=True)
    current_company = Column(String(255), nullable=True)
    current_position = Column(String(255), nullable=True)  # Note: DB has 'current_position' not 'current_role'
    years_experience = Column(Integer, nullable=True)
    status = Column(String(20), default='active')  # active, placed, archived
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    created_by = relationship("User", back_populates="created_candidates")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    assignments = relationship("UserCandidateAssignment", back_populates="candidate")
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate candidate status."""
        allowed_statuses = ['active', 'placed', 'archived']
        if status not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return status
    
    @validates('email')
    def validate_email(self, key, email):
        """Basic email validation."""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email
    
    @property
    def full_name(self) -> str:
        """Get candidate's full name."""
        return f"{self.first_name} {self.last_name}"
    
    @property 
    def is_active(self) -> bool:
        """Check if candidate is in active status."""
        return self.status == 'active'
    
    def __repr__(self) -> str:
        return f"<Candidate(id={self.id}, name='{self.full_name}', status='{self.status}')>"