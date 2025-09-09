"""
Resume Section database model.

Contains the ResumeSection model for section-level analysis and feedback tracking.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from . import Base


class SectionType(str, Enum):
    """Resume section type enumeration."""
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    OTHER = "other"


class ResumeSection(Base):
    """
    Resume Section model for section-level analysis.
    
    Extracts and stores individual sections of resumes for precise AI feedback
    and highlighting capabilities.
    """
    
    __tablename__ = "resume_sections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey('resumes.id'), nullable=False)
    section_type = Column(String(20), nullable=False)
    section_title = Column(Text, nullable=True)  # e.g., "Work Experience", "Education"
    content = Column(Text, nullable=False)
    start_page = Column(Integer, nullable=True)  # For PDF navigation
    end_page = Column(Integer, nullable=True)
    start_position = Column(Integer, nullable=True)  # Character position for highlighting
    end_position = Column(Integer, nullable=True)
    sequence_order = Column(Integer, default=0)  # Order within the resume
    section_metadata = Column(JSON, nullable=True)  # Additional section-specific data
    
    # Relationships
    resume = relationship("Resume", back_populates="sections")
    feedback_items = relationship("ReviewFeedbackItem", back_populates="resume_section")
    
    @validates('section_type')
    def validate_section_type(self, key, section_type):
        """Validate section type."""
        allowed_types = ['contact', 'summary', 'experience', 'education', 'skills', 'certifications', 'other']
        if section_type not in allowed_types:
            raise ValueError(f"Section type must be one of: {', '.join(allowed_types)}")
        return section_type
    
    @validates('start_position', 'end_position')
    def validate_positions(self, key, position):
        """Validate position values."""
        if position is not None and position < 0:
            raise ValueError(f"{key} must be >= 0")
        return position
    
    @validates('sequence_order')
    def validate_sequence_order(self, key, sequence_order):
        """Validate sequence order."""
        if sequence_order < 0:
            raise ValueError("Sequence order must be >= 0")
        return sequence_order
    
    @property
    def word_count(self) -> int:
        """Get word count for this section."""
        return len(self.content.split()) if self.content else 0
    
    @property
    def character_count(self) -> int:
        """Get character count for this section."""
        return len(self.content) if self.content else 0
    
    @property
    def has_feedback(self) -> bool:
        """Check if this section has feedback items."""
        return len(self.feedback_items) > 0
    
    def get_text_range(self) -> Optional[str]:
        """Get the text range this section covers."""
        if self.start_position is not None and self.end_position is not None:
            # This would be used by the frontend to highlight specific text
            return f"{self.start_position}-{self.end_position}"
        return None
    
    def __repr__(self) -> str:
        return f"<ResumeSection(id={self.id}, resume_id={self.resume_id}, type='{self.section_type}', order={self.sequence_order})>"