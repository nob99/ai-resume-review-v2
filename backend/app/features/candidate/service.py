"""Candidate management service."""

import uuid
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.core.datetime_utils import utc_now
from database.models.candidate import Candidate
from database.models.assignment import UserCandidateAssignment
from database.models.auth import User

logger = logging.getLogger(__name__)


class CandidateService:
    """Service for candidate management operations."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    async def create_candidate(
        self,
        first_name: str,
        last_name: str,
        created_by_user_id: uuid.UUID,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        current_company: Optional[str] = None,
        current_position: Optional[str] = None,
        years_experience: Optional[int] = None
    ) -> Candidate:
        """Create a new candidate and auto-assign to creator."""
        
        try:
            # Create candidate
            candidate = Candidate(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                current_company=current_company,
                current_position=current_position,
                years_experience=years_experience,
                created_by_user_id=created_by_user_id,
                status='active'
            )
            
            self.db.add(candidate)
            self.db.flush()  # Get the ID
            
            # Auto-assign candidate to creator
            assignment = UserCandidateAssignment(
                user_id=created_by_user_id,
                candidate_id=candidate.id,
                assignment_type='primary',
                assigned_by_user_id=created_by_user_id,
                is_active=True
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            logger.info(f"Created candidate {candidate.id} and assigned to user {created_by_user_id}")
            return candidate
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create candidate: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create candidate")
    
    async def get_candidates_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        offset: int = 0
    ) -> List[Candidate]:
        """Get candidates based on user role and assignments."""
        
        # Get user to check role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.role in ['admin', 'senior_recruiter']:
            # Admin and senior recruiters see all candidates
            query = (
                self.db.query(Candidate)
                .filter(Candidate.status == 'active')
                .order_by(Candidate.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        else:
            # Junior recruiters see only assigned candidates
            query = (
                self.db.query(Candidate)
                .join(UserCandidateAssignment)
                .filter(
                    UserCandidateAssignment.user_id == user_id,
                    UserCandidateAssignment.is_active == True,
                    Candidate.status == 'active'
                )
                .order_by(Candidate.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        
        return query.all()
    
    async def get_candidate_by_id(
        self,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Candidate]:
        """Get a candidate by ID (with access control)."""
        
        # Check if user has access
        if not await self._user_has_candidate_access(user_id, candidate_id):
            raise HTTPException(status_code=403, detail="Access denied to this candidate")
        
        return self.db.query(Candidate).filter(Candidate.id == candidate_id).first()
    
    async def assign_candidate(
        self,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID,
        assignment_type: str = 'secondary'
    ) -> bool:
        """Assign a candidate to a user."""
        
        # Check if assigner has permission (admin or senior recruiter)
        assigner = self.db.query(User).filter(User.id == assigned_by_user_id).first()
        if not assigner or assigner.role not in ['admin', 'senior_recruiter']:
            raise HTTPException(status_code=403, detail="Insufficient permissions to assign candidates")
        
        # Check if assignment already exists
        existing = (
            self.db.query(UserCandidateAssignment)
            .filter(
                UserCandidateAssignment.user_id == user_id,
                UserCandidateAssignment.candidate_id == candidate_id,
                UserCandidateAssignment.is_active == True
            )
            .first()
        )
        
        if existing:
            return True  # Already assigned
        
        try:
            assignment = UserCandidateAssignment(
                user_id=user_id,
                candidate_id=candidate_id,
                assignment_type=assignment_type,
                assigned_by_user_id=assigned_by_user_id,
                is_active=True
            )
            
            self.db.add(assignment)
            self.db.commit()
            
            logger.info(f"Assigned candidate {candidate_id} to user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to assign candidate: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to assign candidate")
    
    async def _user_has_candidate_access(
        self,
        user_id: uuid.UUID,
        candidate_id: uuid.UUID
    ) -> bool:
        """Check if user has access to a candidate."""
        
        # Get user role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admin and senior recruiters have access to all candidates
        if user.role in ['admin', 'senior_recruiter']:
            return True
        
        # Junior recruiters need active assignment
        assignment = (
            self.db.query(UserCandidateAssignment)
            .filter(
                UserCandidateAssignment.user_id == user_id,
                UserCandidateAssignment.candidate_id == candidate_id,
                UserCandidateAssignment.is_active == True
            )
            .first()
        )
        
        return assignment is not None