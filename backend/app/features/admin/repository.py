"""
Admin repository for user management data access.
Extends UserRepository with admin-specific queries.
"""

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository import UserRepository
from database.models.auth import User
from database.models.assignment import UserCandidateAssignment
from database.models.resume import Resume
from database.models.review import ReviewRequest


class AdminUserRepository(UserRepository):
    """
    Repository for admin user management operations.
    Extends UserRepository with admin-specific queries.
    """

    def __init__(self, session: AsyncSession):
        """Initialize admin repository with database session."""
        super().__init__(session)

    async def list_with_filters(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Tuple[User, int]], int]:
        """
        List users with pagination, filtering, and assignment counts.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            search: Search term for email/name
            role: Filter by role
            is_active: Filter by active status

        Returns:
            Tuple of (list of (User, assignment_count) tuples, total_count)
        """
        # Build query with LEFT JOIN to get assignment counts in single query
        query = (
            select(
                User,
                func.count(UserCandidateAssignment.id).label('assigned_count')
            )
            .outerjoin(
                UserCandidateAssignment,
                and_(
                    UserCandidateAssignment.user_id == User.id,
                    UserCandidateAssignment.is_active == True
                )
            )
            .group_by(User.id)
        )

        # Apply filters
        if search:
            search_pattern = f"%{search.lower()}%"
            query = query.where(
                or_(
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            )

        if role:
            query = query.where(User.role == role)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        # Execute single query that gets users + assignment counts
        result = await self.session.execute(query)
        rows = result.all()

        # Convert to list of tuples (User, count)
        users_with_counts = [(row.User, row.assigned_count) for row in rows]

        return users_with_counts, total

    async def get_with_statistics(
        self,
        user_id: UUID
    ) -> Optional[Tuple[User, int, int, int]]:
        """
        Get user with statistics in a single query.

        Args:
            user_id: User ID

        Returns:
            Tuple of (User, assigned_count, resume_count, review_count) or None
        """
        # Single query with scalar subqueries for all statistics
        query = (
            select(
                User,
                # Count assigned candidates (only active assignments)
                select(func.count(UserCandidateAssignment.id))
                .where(
                    UserCandidateAssignment.user_id == user_id,
                    UserCandidateAssignment.is_active == True
                )
                .scalar_subquery()
                .label('assigned_count'),
                # Count resumes uploaded
                select(func.count(Resume.id))
                .where(Resume.uploaded_by_user_id == user_id)
                .scalar_subquery()
                .label('resume_count'),
                # Count reviews requested
                select(func.count(ReviewRequest.id))
                .where(ReviewRequest.requested_by_user_id == user_id)
                .scalar_subquery()
                .label('review_count')
            )
            .where(User.id == user_id)
        )

        result = await self.session.execute(query)
        row = result.one_or_none()

        if not row:
            return None

        return (row.User, row.assigned_count, row.resume_count, row.review_count)

    async def list_active_users(self) -> List[User]:
        """
        Get all active users for directory.

        Returns:
            List of active users ordered by name
        """
        query = (
            select(User)
            .where(User.is_active == True)
            .order_by(User.last_name, User.first_name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())