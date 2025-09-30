"""
Admin service layer for user management.
Implements business logic for admin operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, SecurityError
from app.core.datetime_utils import utc_now
from app.features.auth.repository import UserRepository
from database.models.auth import User, UserRole
from database.models.assignment import UserCandidateAssignment
from database.models.resume import Resume
from database.models.review import ReviewRequest
from .schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset,
    UserListItem,
    UserDetailResponse,
    UserListResponse,
    UserDirectoryItem,
    UserDirectoryResponse
)

logger = logging.getLogger(__name__)


class AdminService:
    """
    Admin service for user management operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize admin service.

        Args:
            session: Database session
        """
        self.session = session
        self.user_repo = UserRepository(session)

    async def create_user(
        self,
        user_data: AdminUserCreate,
        created_by_user_id: UUID
    ) -> User:
        """
        Create a new user with admin privileges.

        Args:
            user_data: User creation data
            created_by_user_id: ID of the admin creating the user

        Returns:
            Created user object

        Raises:
            SecurityError: If email already exists
        """
        # Check if email already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise SecurityError(f"User with email {user_data.email} already exists")

        # Create new user with temporary password
        new_user = User(
            email=user_data.email,
            password=user_data.temporary_password,  # Will be hashed in User.__init__
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role.value
        )

        # Force password change on first login
        new_user.password_changed_at = utc_now()  # Will trigger password change requirement

        # Add to session and commit
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        logger.info(f"Admin {created_by_user_id} created new user: {new_user.email}")

        return new_user

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> UserListResponse:
        """
        List users with pagination and filtering.

        Args:
            page: Page number (1-based)
            page_size: Items per page
            search: Search term for email/name
            role: Filter by role
            is_active: Filter by active status

        Returns:
            Paginated user list response
        """
        # Build query with LEFT JOIN to get assignment counts in single query
        # This eliminates N+1 problem (was: 1 query for users + N queries for counts)
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

        # Build response items from query results
        user_items = [
            UserListItem(
                id=row.User.id,
                email=row.User.email,
                first_name=row.User.first_name,
                last_name=row.User.last_name,
                role=row.User.role,
                is_active=row.User.is_active,
                email_verified=row.User.email_verified,
                last_login_at=row.User.last_login_at,
                created_at=row.User.created_at,
                assigned_candidates_count=row.assigned_count
            )
            for row in rows
        ]

        total_pages = (total + page_size - 1) // page_size

        return UserListResponse(
            users=user_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def get_user_details(self, user_id: UUID) -> Optional[UserDetailResponse]:
        """
        Get detailed user information with statistics in a single query.

        Args:
            user_id: User ID

        Returns:
            Detailed user information or None if not found
        """
        # Single query with scalar subqueries for all statistics
        # Eliminates 4 separate queries (1 for user + 3 for counts)
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

        user = row.User
        return UserDetailResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_active=user.is_active,
            email_verified=user.email_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
            password_changed_at=user.password_changed_at,
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            assigned_candidates_count=row.assigned_count,
            total_resumes_uploaded=row.resume_count,
            total_reviews_requested=row.review_count
        )

    async def update_user(
        self,
        user_id: UUID,
        update_data: AdminUserUpdate,
        updated_by_user_id: UUID
    ) -> Optional[User]:
        """
        Update user information.

        Args:
            user_id: User ID to update
            update_data: Update data
            updated_by_user_id: ID of the admin making the update

        Returns:
            Updated user or None if not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        # Update fields if provided
        if update_data.first_name is not None:
            old_first_name = user.first_name
            user.first_name = update_data.first_name.strip()
            logger.info(f"Admin {updated_by_user_id} changed user {user_id} first_name from '{old_first_name}' to '{user.first_name}'")

        if update_data.last_name is not None:
            old_last_name = user.last_name
            user.last_name = update_data.last_name.strip()
            logger.info(f"Admin {updated_by_user_id} changed user {user_id} last_name from '{old_last_name}' to '{user.last_name}'")

        if update_data.email is not None:
            old_email = user.email
            user.email = update_data.email.lower().strip()
            logger.info(f"Admin {updated_by_user_id} changed user {user_id} email from '{old_email}' to '{user.email}'")

        if update_data.is_active is not None:
            user.is_active = update_data.is_active
            logger.info(f"Admin {updated_by_user_id} {'activated' if update_data.is_active else 'deactivated'} user {user_id}")

        if update_data.role is not None:
            old_role = user.role
            user.role = update_data.role.value
            logger.info(f"Admin {updated_by_user_id} changed user {user_id} role from {old_role} to {update_data.role.value}")

        if update_data.email_verified is not None:
            old_verified = user.email_verified
            user.email_verified = update_data.email_verified
            logger.info(f"Admin {updated_by_user_id} changed user {user_id} email_verified from {old_verified} to {update_data.email_verified}")

        user.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def reset_user_password(
        self,
        user_id: UUID,
        reset_data: AdminPasswordReset,
        reset_by_user_id: UUID
    ) -> bool:
        """
        Reset a user's password.

        Args:
            user_id: User ID
            reset_data: Password reset data
            reset_by_user_id: ID of the admin resetting the password

        Returns:
            True if successful, False if user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False

        # Set new password
        user.set_password(reset_data.new_password)

        # Force password change on next login if requested
        if reset_data.force_password_change:
            # Setting password_changed_at to a past date will trigger password change
            from datetime import timedelta
            user.password_changed_at = utc_now() - timedelta(days=365)

        # Clear any account locks
        user.unlock_account()

        await self.session.commit()

        logger.info(f"Admin {reset_by_user_id} reset password for user {user_id}")

        return True

    async def get_user_directory(self) -> UserDirectoryResponse:
        """
        Get basic user directory (for senior recruiters).

        Returns:
            User directory response
        """
        query = select(User).where(User.is_active == True).order_by(User.last_name, User.first_name)
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        directory_items = [
            UserDirectoryItem(
                id=user.id,
                email=user.email,
                full_name=f"{user.first_name} {user.last_name}",
                role=user.role,
                is_active=user.is_active
            )
            for user in users
        ]

        return UserDirectoryResponse(
            users=directory_items,
            total=len(directory_items)
        )