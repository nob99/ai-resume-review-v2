"""
Admin service layer for user management.
Implements business logic for COMPLEX admin operations only.

Simple read operations are handled directly by API → Repository.
This service contains ONLY operations with complex business logic:
- create_user: Password hashing, validation, force password change
- update_user: Audit logging for all changes
- reset_user_password: Password hashing, account unlock, force password change
"""

from typing import Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityError
from app.core.datetime_utils import utc_now
from app.features.auth.repository import UserRepository
from database.models.auth import User
from .schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset
)

logger = logging.getLogger(__name__)


class AdminService:
    """
    Admin service for COMPLEX user management operations.

    Simple operations (list, get, directory) are handled by repository directly.
    This service handles operations requiring business logic.
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