"""
Candidate management service.

Handles COMPLEX candidate operations requiring business logic.
Simple read operations are handled by CandidateRepository directly.

This service contains:
- create_candidate: Multi-table transaction (Candidate + Assignment)
- assign_candidate: Permission checks + duplicate prevention
"""

import uuid
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from database.models.candidate import Candidate
from database.models.assignment import UserCandidateAssignment
from database.models.auth import User
from .repository import CandidateRepository

logger = logging.getLogger(__name__)


class CandidateService:
    """
    Service for COMPLEX candidate management operations.

    Simple operations (list, get by ID) are handled by CandidateRepository.
    This service handles operations requiring business logic coordination.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with async database session."""
        self.session = session
        self.repository = CandidateRepository(session)
    
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
        """
        Create a new candidate and auto-assign to creator.

        This is a complex operation requiring:
        - Multi-table transaction (Candidate + UserCandidateAssignment)
        - Business rule: Auto-assignment to creator
        - Transaction management with rollback

        Args:
            first_name: Candidate's first name
            last_name: Candidate's last name
            created_by_user_id: User creating the candidate
            email: Optional email address
            phone: Optional phone number
            current_company: Optional current company
            current_position: Optional current position
            years_experience: Optional years of experience

        Returns:
            Created candidate

        Raises:
            HTTPException: If creation fails
        """
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

            self.session.add(candidate)
            await self.session.flush()  # Get the ID

            # Auto-assign candidate to creator
            assignment = UserCandidateAssignment(
                user_id=created_by_user_id,
                candidate_id=candidate.id,
                assignment_type='primary',
                assigned_by_user_id=created_by_user_id,
                is_active=True
            )

            self.session.add(assignment)
            await self.session.commit()
            await self.session.refresh(candidate)

            logger.info(f"Created candidate {candidate.id} and assigned to user {created_by_user_id}")
            return candidate

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create candidate: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create candidate")

    async def assign_candidate(
        self,
        candidate_id: uuid.UUID,
        user_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID,
        assignment_type: str = 'secondary'
    ) -> bool:
        """
        Assign a candidate to a user.

        This is a complex operation requiring:
        - Permission check (only admin/senior can assign)
        - Duplicate prevention
        - Transaction management with rollback

        Args:
            candidate_id: Candidate to assign
            user_id: User to assign candidate to
            assigned_by_user_id: User performing the assignment
            assignment_type: Type of assignment ('primary' or 'secondary')

        Returns:
            True if assignment successful or already exists

        Raises:
            HTTPException: If permission denied or operation fails
        """
        # Check if assigner has permission (admin or senior recruiter)
        query = select(User).where(User.id == assigned_by_user_id)
        result = await self.session.execute(query)
        assigner = result.scalar_one_or_none()

        if not assigner or assigner.role not in ['admin', 'senior_recruiter']:
            raise HTTPException(status_code=403, detail="Insufficient permissions to assign candidates")

        # Check if assignment already exists (duplicate prevention)
        query = select(UserCandidateAssignment).where(
            UserCandidateAssignment.user_id == user_id,
            UserCandidateAssignment.candidate_id == candidate_id,
            UserCandidateAssignment.is_active == True
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

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

            self.session.add(assignment)
            await self.session.commit()

            logger.info(f"Assigned candidate {candidate_id} to user {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to assign candidate: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to assign candidate")