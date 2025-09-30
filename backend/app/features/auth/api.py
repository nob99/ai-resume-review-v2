"""
Auth API endpoints using the new feature-based architecture.
This is the new implementation that will be used via feature flags.
"""

from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_token,
    SecurityError
)
from app.core.rate_limiter import check_rate_limit_middleware, RateLimitType
from infrastructure.persistence.postgres.connection import get_async_session
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
    """Dependency to get auth service with repositories."""
    user_repo = UserRepository(session)
    token_repo = RefreshTokenRepository(session)
    return AuthService(user_repo, token_repo)


async def get_user_repository(session: AsyncSession = Depends(get_async_session)) -> UserRepository:
    """Dependency to get user repository."""
    return UserRepository(session)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UUID:
    """
    Dependency that validates token and returns user_id.

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        User ID extracted from valid token

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        user_data = verify_token(credentials.credentials)
        if not user_data:
            raise SecurityError("Invalid or expired token")
        return UUID(user_data["sub"])
    except SecurityError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


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
        # Rate limiting by IP (prevents brute force attacks)
        client_ip = get_client_ip(request)
        await check_rate_limit_middleware(request, RateLimitType.LOGIN, client_ip)

        # Extract request metadata
        user_agent = request.headers.get("User-Agent")

        # Call service layer (business logic)
        response = await auth_service.login(login_request, client_ip, user_agent)

        return response

    except HTTPException:
        # Re-raise HTTPException (from rate limiter, etc.) without modification
        raise
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
        # Rate limiting by IP (prevents abuse)
        client_ip = get_client_ip(request)
        await check_rate_limit_middleware(request, RateLimitType.REGISTRATION, client_ip)

        # Call service layer (business logic)
        response = await auth_service.register_user(user_data)

        logger.info(f"User registered successfully: {user_data.email}")
        return response

    except HTTPException:
        # Re-raise HTTPException (from rate limiter, etc.) without modification
        raise
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
        # Extract request metadata
        client_ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")

        # Call service layer (business logic)
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
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by revoking tokens.

    This endpoint:
    - Blacklists access token
    - Clears user session

    Note: Refresh token is managed client-side and cleared there.
    Server only blacklists the access token to prevent further use.
    """
    try:
        # Blacklist access token (refresh token is cleared client-side)
        await auth_service.logout(
            refresh_token_str=None,
            access_token=credentials.credentials,
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
    user_id: UUID = Depends(get_current_user_id),
    user_repo: UserRepository = Depends(get_user_repository)
) -> UserResponse:
    """
    Get current user information.

    This endpoint:
    - Validates access token (via dependency)
    - Returns user profile
    """
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.get("/sessions", response_model=SessionListResponse)
async def get_user_sessions(
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
) -> SessionListResponse:
    """
    Get all active sessions for the current user.

    This endpoint:
    - Validates access token (via dependency)
    - Returns list of active sessions
    """
    sessions = await auth_service.get_user_sessions(user_id)
    return sessions


@router.post("/sessions/revoke", response_model=SessionRevokeResponse)
async def revoke_session(
    session_request: SessionRevokeRequest,
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
) -> SessionRevokeResponse:
    """
    Revoke a specific user session.

    This endpoint:
    - Validates access token (via dependency)
    - Revokes specified session
    """
    success = await auth_service.revoke_session(user_id, session_request.session_id)

    return SessionRevokeResponse(
        success=success,
        message="Session revoked successfully" if success else "Session not found"
    )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordUpdate,
    user_id: UUID = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change user password.

    This endpoint:
    - Validates access token (via dependency)
    - Verifies current password
    - Updates to new password
    - Revokes other sessions for security
    """
    try:
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