"""
Admin API endpoints for user management.
Provides RESTful endpoints for admin operations.

Architecture:
- Simple read operations: API → Repository
- Complex operations (create, update, password reset): API → Service → Repository
"""

from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import SecurityError
from .dependencies import require_admin, require_senior_or_admin
from .service import AdminService
from .repository import AdminUserRepository
from .schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminPasswordReset,
    UserListResponse,
    UserDetailResponse,
    UserDirectoryResponse,
    MessageResponse,
    UserRole,
    UserListItem,
    UserDirectoryItem
)
from database.models.auth import User
from .schemas import UserListItem as AdminUserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency injection
async def get_admin_repository(
    session: AsyncSession = Depends(get_async_session)
) -> AdminUserRepository:
    """Dependency to get admin repository."""
    return AdminUserRepository(session)


async def get_admin_service(
    session: AsyncSession = Depends(get_async_session)
) -> AdminService:
    """Dependency to get admin service (for complex operations)."""
    return AdminService(session)


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: AdminUserCreate,
    current_user: User = Depends(require_admin),
    service: AdminService = Depends(get_admin_service)
):
    """
    Create a new user (admin only).

    Creates a new user account with a temporary password.
    The user will be required to change their password on first login.

    Required role: Admin

    Architecture: Complex operation → Uses service layer for password hashing and validation
    """
    try:
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
    repo: AdminUserRepository = Depends(get_admin_repository)
):
    """
    List all users with pagination and filtering (admin only).

    Returns a paginated list of users with basic information.
    Supports filtering by role, active status, and text search.

    Required role: Admin

    Architecture: Simple read → API calls repository directly
    """
    try:
        # Get users with assignment counts from repository
        users_with_counts, total = await repo.list_with_filters(
            page=page,
            page_size=page_size,
            search=search,
            role=role.value if role else None,
            is_active=is_active
        )

        # Build response items
        user_items = [
            UserListItem(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                email_verified=user.email_verified,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                assigned_candidates_count=count
            )
            for user, count in users_with_counts
        ]

        total_pages = (total + page_size - 1) // page_size

        return UserListResponse(
            users=user_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

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
    repo: AdminUserRepository = Depends(get_admin_repository)
):
    """
    Get detailed user information (admin only).

    Returns comprehensive user details including statistics
    such as assigned candidates, uploaded resumes, and review requests.

    Required role: Admin

    Architecture: Simple read → API calls repository directly
    """
    try:
        # Get user with statistics from repository (single query)
        result = await repo.get_with_statistics(user_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user, assigned_count, resume_count, review_count = result

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
            assigned_candidates_count=assigned_count,
            total_resumes_uploaded=resume_count,
            total_reviews_requested=review_count
        )

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
    service: AdminService = Depends(get_admin_service)
):
    """
    Update user information (admin only).

    Allows updating user's active status, role, and email verification.

    Required role: Admin

    Architecture: Complex operation → Uses service layer for audit logging
    """
    try:
        # Prevent admin from deactivating themselves
        if user_id == current_user.id and update_data.is_active == False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )

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
    service: AdminService = Depends(get_admin_service)
):
    """
    Reset a user's password (admin only).

    Sets a new temporary password for the user.
    Optionally forces the user to change password on next login.
    Also clears any account locks.

    Required role: Admin

    Architecture: Complex operation → Uses service layer for password hashing and account unlock
    """
    try:
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
    repo: AdminUserRepository = Depends(get_admin_repository)
):
    """
    Get user directory (senior recruiters and admins).

    Returns a basic directory of all active users.
    Useful for senior recruiters who need to see the team.

    Required role: Senior Recruiter or Admin

    Architecture: Simple read → API calls repository directly
    """
    try:
        # Get active users from repository
        users = await repo.list_active_users()

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

    except Exception as e:
        logger.error(f"Error getting user directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user directory"
        )