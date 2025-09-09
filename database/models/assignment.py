"""
User-Candidate Assignment database model.

Contains the UserCandidateAssignment model for managing role-based access control
and assignment history tracking.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from app.core.datetime_utils import utc_now


class UserCandidateAssignment(Base):
    """
    User-Candidate Assignment model for role-based access control.
    
    This model manages which users can access which candidates, with full history tracking:
    - Junior recruiters only see assigned candidates
    - Senior recruiters see all candidates
    - Assignment history is preserved for audit purposes
    """
    
    __tablename__ = 'user_candidate_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)
    assignment_type = Column(String(20), default='primary')  # primary, secondary, viewer
    assigned_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    unassigned_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    unassigned_reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="assignments")
    candidate = relationship("Candidate", back_populates="assignments")
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
    
    @validates('assignment_type')
    def validate_assignment_type(self, key, assignment_type):
        """Validate assignment type."""
        allowed_types = ['primary', 'secondary', 'viewer']
        if assignment_type not in allowed_types:
            raise ValueError(f"Assignment type must be one of: {', '.join(allowed_types)}")
        return assignment_type
    
    @property
    def is_currently_active(self) -> bool:
        """Check if assignment is currently active (not unassigned)."""
        return self.is_active and self.unassigned_at is None
    
    @property
    def assignment_duration_days(self) -> Optional[int]:
        """Get duration of assignment in days."""
        if not self.unassigned_at:
            return None
        delta = self.unassigned_at - self.assigned_at
        return delta.days
    
    def unassign(self, reason: Optional[str] = None, unassigned_by_user_id: Optional[uuid.UUID] = None) -> None:
        """Mark assignment as inactive."""
        self.is_active = False
        self.unassigned_at = utc_now()
        self.unassigned_reason = reason
        # Note: We could add unassigned_by_user_id field if needed for full audit trail
    
    def __repr__(self) -> str:
        status = "Active" if self.is_currently_active else "Inactive"
        return f"<UserCandidateAssignment(user_id={self.user_id}, candidate_id={self.candidate_id}, type='{self.assignment_type}', status='{status}')>"