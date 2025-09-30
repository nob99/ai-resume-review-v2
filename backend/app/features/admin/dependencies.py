"""
Admin authentication dependencies.
Provides decorators and dependencies for admin-only access control.
"""

from typing import Any
from uuid import UUID
from functools import wraps

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
    Get the current authenticated user from the token.

    Args:
        credentials: Bearer token from request
        session: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
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

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not admin
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

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if authorized

    Raises:
        HTTPException: If user is not senior or admin
    """
    allowed_roles = [UserRole.SENIOR_RECRUITER.value, UserRole.ADMIN.value]

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Senior recruiter or admin access required"
        )

    return current_user