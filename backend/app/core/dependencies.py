"""
Shared authentication and authorization dependencies.

This module contains dependencies used across multiple features for:
- Authentication: Extracting and validating current user from JWT tokens
- Authorization: Role-based access control (admin, senior recruiter, etc.)
- Database sessions: Providing async database connections

Architecture Pattern:
- Cross-cutting concerns (auth, authz, db) → core/dependencies.py
- Feature-specific business logic → features/*/api.py or service.py
"""

from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token, SecurityError
from app.core.database import get_async_session
from app.features.auth.repository import UserRepository
from database.models.auth import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get the current authenticated user from the JWT token.

    This is a shared dependency used across all features that require authentication.
    It validates the bearer token, extracts user information, and returns the user object.

    Args:
        credentials: Bearer token from Authorization header
        session: Async database session

    Returns:
        Current authenticated user object

    Raises:
        HTTPException: 401 if token is invalid/expired or user not found
        HTTPException: 403 if user account is deactivated

    Usage:
        @router.get("/protected-endpoint")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user": current_user.email}
    """
    try:
        token = credentials.credentials
        user_data = verify_token(token)

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(UUID(user_data["sub"]))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        return user

    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the current user to have admin role.

    This dependency combines authentication (via get_current_user) with
    authorization (role checking) to enforce admin-only access.

    Args:
        current_user: Current authenticated user (injected by get_current_user)

    Returns:
        Current user if they have admin role

    Raises:
        HTTPException: 403 if user is not admin

    Usage:
        @router.post("/admin/users")
        async def create_user(
            admin: User = Depends(require_admin)
        ):
            return {"message": "Admin access granted"}
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def require_senior_or_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the current user to be senior recruiter or admin.

    This dependency allows access to users with elevated privileges
    (senior recruiters and admins).

    Args:
        current_user: Current authenticated user (injected by get_current_user)

    Returns:
        Current user if they have senior or admin role

    Raises:
        HTTPException: 403 if user is not senior recruiter or admin

    Usage:
        @router.get("/admin/directory")
        async def get_directory(
            user: User = Depends(require_senior_or_admin)
        ):
            return {"message": "Senior or admin access granted"}
    """
    allowed_roles = [UserRole.SENIOR_RECRUITER.value, UserRole.ADMIN.value]

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Senior recruiter or admin access required"
        )

    return current_user