"""
Admin API endpoints for user management.
Provides RESTful endpoints for admin operations.
"""

from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.postgres.connection import get_async_session
from app.core.security import SecurityError
from .dependencies import require_admin, require_senior_or_admin
from .service import AdminService
from .schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset,
    UserListResponse,
    UserDetailResponse,
    UserDirectoryResponse,
    MessageResponse,
    UserRole
)
from database.models.auth import User
from .schemas import UserListItem as AdminUserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new user (admin only).

    Creates a new user account with a temporary password.
    The user will be required to change their password on first login.

    Required role: Admin
    """
    try:
        service = AdminService(session)
        new_user = await service.create_user(user_data, current_user.id)

        logger.info(f"Admin {current_user.email} created new user: {new_user.email}")

        return AdminUserResponse.model_validate(new_user)

    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for email/name"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all users with pagination and filtering (admin only).

    Returns a paginated list of users with basic information.
    Supports filtering by role, active status, and text search.

    Required role: Admin
    """
    try:
        service = AdminService(session)
        response = await service.list_users(
            page=page,
            page_size=page_size,
            search=search,
            role=role.value if role else None,
            is_active=is_active
        )

        return response

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed user information (admin only).

    Returns comprehensive user details including statistics
    such as assigned candidates, uploaded resumes, and review requests.

    Required role: Admin
    """
    try:
        service = AdminService(session)
        user_details = await service.get_user_details(user_id)

        if not user_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return user_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    update_data: AdminUserUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update user information (admin only).

    Allows updating user's active status, role, and email verification.

    Required role: Admin
    """
    try:
        # Prevent admin from deactivating themselves
        if user_id == current_user.id and update_data.is_active == False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )

        service = AdminService(session)
        updated_user = await service.update_user(user_id, update_data, current_user.id)

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"Admin {current_user.email} updated user {user_id}")

        return AdminUserResponse.model_validate(updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password(
    user_id: UUID,
    reset_data: AdminPasswordReset,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Reset a user's password (admin only).

    Sets a new temporary password for the user.
    Optionally forces the user to change password on next login.
    Also clears any account locks.

    Required role: Admin
    """
    try:
        service = AdminService(session)
        success = await service.reset_user_password(user_id, reset_data, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"Admin {current_user.email} reset password for user {user_id}")

        return MessageResponse(
            message=f"Password reset successfully. {'User must change password on next login.' if reset_data.force_password_change else ''}",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.get("/directory", response_model=UserDirectoryResponse)
async def get_user_directory(
    current_user: User = Depends(require_senior_or_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get user directory (senior recruiters and admins).

    Returns a basic directory of all active users.
    Useful for senior recruiters who need to see the team.

    Required role: Senior Recruiter or Admin
    """
    try:
        service = AdminService(session)
        directory = await service.get_user_directory()

        return directory

    except Exception as e:
        logger.error(f"Error getting user directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user directory"
        )