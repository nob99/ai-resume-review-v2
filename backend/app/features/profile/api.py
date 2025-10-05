"""
Profile management API endpoints for user self-service.

Provides endpoints for users to:
- View their profile
- Update their profile information (first_name, last_name)
- Change their password (UX-friendly, keeps user logged in)

Architecture: Simple CRUD operations → API → Repository (no service layer)
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import password_hasher
from app.core.datetime_utils import utc_now
from app.core.dependencies import get_current_user
from app.features.auth.repository import UserRepository
from app.features.auth.schemas import UserResponse
from database.models.auth import User
from .schemas import ProfileUpdate, PasswordChange, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_repository(
    session: AsyncSession = Depends(get_async_session)
) -> UserRepository:
    """Dependency to get user repository."""
    return UserRepository(session)


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    Get current user's profile information.

    Returns:
        Current user profile data

    Required: Authentication
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserResponse:
    """
    Update current user's profile information.

    Allows users to update their first name and last name.
    Email, role, and account status cannot be changed via this endpoint.

    Args:
        profile_data: Profile update data (first_name, last_name)
        current_user: Current authenticated user (from JWT)
        user_repo: User repository for database operations

    Returns:
        Updated user profile

    Raises:
        HTTPException: 400 if validation fails, 500 if database error

    Required: Authentication
    """
    try:
        # Update profile fields
        current_user.first_name = profile_data.first_name
        current_user.last_name = profile_data.last_name
        current_user.updated_at = utc_now()

        # Commit changes
        await user_repo.session.commit()
        await user_repo.session.refresh(current_user)

        logger.info(f"User {current_user.email} updated their profile")

        return UserResponse.model_validate(current_user)

    except ValueError as e:
        logger.warning(f"Profile update validation failed for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating profile for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
) -> MessageResponse:
    """
    Change current user's password.

    This is the UX-friendly version that keeps the user logged in.
    For security-critical password changes that revoke all sessions,
    use /auth/change-password instead.

    Requires:
    - Current password verification
    - New password must meet strength requirements
    - New password must be different from current password

    Args:
        password_data: Password change data
        current_user: Current authenticated user (from JWT)
        user_repo: User repository for database operations

    Returns:
        Success message

    Raises:
        HTTPException: 400 if current password is incorrect or validation fails

    Required: Authentication

    Note: This endpoint does NOT revoke existing sessions.
    """
    try:
        # Verify current password
        if not current_user.check_password(password_data.current_password):
            logger.warning(f"User {current_user.email} provided incorrect current password")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Check that new password is different from current
        if password_hasher.verify_password(
            password_data.new_password,
            current_user.password_hash
        ):
            logger.warning(f"User {current_user.email} tried to set same password")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )

        # Set new password (automatically updates password_changed_at, resets failed_login_attempts)
        current_user.set_password(password_data.new_password)

        # Commit changes
        await user_repo.session.commit()

        logger.info(f"User {current_user.email} changed their password")

        return MessageResponse(
            message="Password changed successfully",
            success=True
        )

    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except ValueError as e:
        logger.warning(f"Password change validation failed for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error changing password for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )