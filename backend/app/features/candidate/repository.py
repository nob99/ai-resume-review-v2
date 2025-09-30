"""
Candidate repository for data access.
Handles role-based access control at the query level.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.postgres.base import BaseRepository
from database.models.candidate import Candidate
from database.models.assignment import UserCandidateAssignment


class CandidateRepository(BaseRepository[Candidate]):
    """
    Repository for candidate data access with role-based filtering.

    Encapsulates role-based access control logic at the query level.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        super().__init__(session, Candidate)

    async def list_for_user(
        self,
        user_id: UUID,
        user_role: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Candidate]:
        """
        Get candidates visible to user based on role.

        Business rules:
        - Admin/Senior recruiters: See all active candidates
        - Junior recruiters: See only assigned candidates

        Args:
            user_id: User ID
            user_role: User role ('admin', 'senior_recruiter', 'junior_recruiter')
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of candidates visible to the user
        """
        if user_role in ['admin', 'senior_recruiter']:
            # Admin and senior recruiters see all active candidates
            query = (
                select(Candidate)
                .where(Candidate.status == 'active')
                .order_by(Candidate.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        else:
            # Junior recruiters see only assigned candidates
            query = (
                select(Candidate)
                .join(
                    UserCandidateAssignment,
                    Candidate.id == UserCandidateAssignment.candidate_id
                )
                .where(
                    and_(
                        UserCandidateAssignment.user_id == user_id,
                        UserCandidateAssignment.is_active == True,
                        Candidate.status == 'active'
                    )
                )
                .order_by(Candidate.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_for_user(
        self,
        candidate_id: UUID,
        user_id: UUID,
        user_role: str
    ) -> Optional[Candidate]:
        """
        Get candidate if user has access based on role.

        Business rules:
        - Admin/Senior recruiters: Access all candidates
        - Junior recruiters: Access only assigned candidates

        Args:
            candidate_id: Candidate ID
            user_id: User ID
            user_role: User role ('admin', 'senior_recruiter', 'junior_recruiter')

        Returns:
            Candidate if user has access, None otherwise
        """
        if user_role in ['admin', 'senior_recruiter']:
            # Admin and senior recruiters have access to all candidates
            query = select(Candidate).where(Candidate.id == candidate_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        else:
            # Junior recruiters need active assignment
            query = (
                select(Candidate)
                .join(
                    UserCandidateAssignment,
                    Candidate.id == UserCandidateAssignment.candidate_id
                )
                .where(
                    and_(
                        Candidate.id == candidate_id,
                        UserCandidateAssignment.user_id == user_id,
                        UserCandidateAssignment.is_active == True
                    )
                )
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()

    async def create_with_assignment(
        self,
        candidate_data: dict,
        assigned_to_user_id: UUID
    ) -> Candidate:
        """
        Create candidate and auto-assign to a user in single transaction.

        Note: This is a helper for service layer. Consider if this belongs
        in repository or should stay in service.

        Args:
            candidate_data: Dictionary with candidate fields
            assigned_to_user_id: User ID to assign candidate to

        Returns:
            Created candidate
        """
        # Create candidate
        candidate = Candidate(**candidate_data)
        self.session.add(candidate)
        await self.session.flush()  # Get the ID

        # Create assignment
        assignment = UserCandidateAssignment(
            user_id=assigned_to_user_id,
            candidate_id=candidate.id,
            assignment_type='primary',
            assigned_by_user_id=assigned_to_user_id,
            is_active=True
        )
        self.session.add(assignment)

        return candidate