"""
Auth API endpoints using the new feature-based architecture.
This is the new implementation that will be used via feature flags.
"""

from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_token,
    SecurityError
)
from app.core.rate_limiter import rate_limiter, RateLimitType
from app.infrastructure.persistence.postgres.connection import get_async_session
from .repository import UserRepository, RefreshTokenRepository
from .service import AuthService
from .schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    SessionListResponse,
    SessionRevokeRequest,
    SessionRevokeResponse,
    PasswordUpdate
)

logger = logging.getLogger(__name__)

# Router for the new auth implementation
router = APIRouter()
security = HTTPBearer()


async def get_auth_service(session: AsyncSession = Depends(get_async_session)) -> AuthService:
    """
    Dependency to get auth service with repositories.
    
    Args:
        session: Database session
        
    Returns:
        Configured AuthService instance
    """
    user_repo = UserRepository(session)
    token_repo = RefreshTokenRepository(session)
    return AuthService(user_repo, token_repo)


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Handle test environment where request.client might be None
    return request.client.host if request.client else "127.0.0.1"


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request."""
    return request.headers.get("User-Agent")


def get_current_user_from_token(token: str) -> dict:
    """
    Extract user information from access token.
    
    Args:
        token: JWT access token
        
    Returns:
        User data from token
        
    Raises:
        SecurityError: If token is invalid
    """
    user_data = verify_token(token)
    if not user_data:
        raise SecurityError("Invalid or expired token")
    return user_data


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    login_request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> LoginResponse:
    """
    Authenticate user and return access/refresh tokens.
    
    This endpoint:
    - Validates user credentials
    - Applies rate limiting
    - Creates new session
    - Returns JWT tokens
    """
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        response = await auth_service.login(login_request, client_ip, user_agent, request)
        
        return response
        
    except SecurityError as e:
        logger.warning(f"Login failed from {get_client_ip(request)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Register a new user account.
    
    This endpoint:
    - Validates registration data
    - Applies rate limiting  
    - Creates new user account
    - Returns user information
    """
    try:
        client_ip = get_client_ip(request)
        
        response = await auth_service.register_user(user_data, client_ip)
        
        logger.info(f"User registered successfully: {user_data.email}")
        return response
        
    except SecurityError as e:
        logger.warning(f"Registration failed from {get_client_ip(request)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request,
    token_request: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.
    
    This endpoint:
    - Validates refresh token
    - Rotates refresh token
    - Returns new tokens
    """
    try:
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        response = await auth_service.refresh_token(
            token_request.refresh_token,
            client_ip,
            user_agent
        )
        
        return response
        
    except SecurityError as e:
        logger.warning(f"Token refresh failed from {get_client_ip(request)}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by revoking tokens.
    
    This endpoint:
    - Blacklists access token
    - Revokes refresh token
    - Optionally revokes all user sessions
    """
    try:
        access_token = credentials.credentials
        
        # Get refresh token from request body (if provided)
        refresh_token = getattr(request, "refresh_token", None)
        
        await auth_service.logout(
            refresh_token_str=refresh_token,
            access_token=access_token,
            revoke_all_sessions=False
        )
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Unexpected error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """
    Get current user information.
    
    This endpoint:
    - Validates access token
    - Returns user profile
    """
    try:
        access_token = credentials.credentials
        user_data = get_current_user_from_token(access_token)
        
        user = await auth_service.user_repo.get_by_id(UUID(user_data["sub"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(user)
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> SessionListResponse:
    """
    Get all active sessions for the current user.
    
    This endpoint:
    - Validates access token
    - Returns list of active sessions
    """
    try:
        access_token = credentials.credentials
        user_data = get_current_user_from_token(access_token)
        user_id = UUID(user_data["sub"])
        
        sessions = await auth_service.get_user_sessions(user_id)
        return sessions
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error getting sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/sessions/revoke", response_model=SessionRevokeResponse)
async def revoke_session(
    session_request: SessionRevokeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> SessionRevokeResponse:
    """
    Revoke a specific user session.
    
    This endpoint:
    - Validates access token
    - Revokes specified session
    """
    try:
        access_token = credentials.credentials
        user_data = get_current_user_from_token(access_token)
        user_id = UUID(user_data["sub"])
        
        success = await auth_service.revoke_session(user_id, session_request.session_id)
        
        return SessionRevokeResponse(
            success=success,
            message="Session revoked successfully" if success else "Session not found"
        )
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Unexpected error revoking session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change user password.
    
    This endpoint:
    - Validates access token
    - Verifies current password
    - Updates to new password
    - Optionally revokes other sessions
    """
    try:
        access_token = credentials.credentials
        user_data = get_current_user_from_token(access_token)
        user_id = UUID(user_data["sub"])
        
        await auth_service.change_password(
            user_id=user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
            revoke_other_sessions=True
        )
        
        return {"message": "Password changed successfully"}
        
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )