"""
Auth service layer implementing business logic.
Extracted from the original auth API to separate concerns.
"""

from datetime import timedelta
from typing import Optional, Tuple, List, Dict, Any
from uuid import UUID, uuid4
import logging

from sqlalchemy.exc import IntegrityError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    validate_password,
    SecurityError,
    PasswordValidationResult,
    blacklist_token,
    is_token_blacklisted
)
from app.core.rate_limiter import (
    check_login_rate_limit,
    check_registration_rate_limit,
    check_password_reset_rate_limit,
    RateLimitType
)
from app.core.datetime_utils import utc_now
from .models import User, RefreshToken, SessionStatus, UserRole
from .repository import UserRepository, RefreshTokenRepository
from .schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    TokenRefreshResponse,
    SessionInfo,
    SessionListResponse
)

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling business logic.
    
    This service encapsulates all authentication-related operations
    and business rules, using repositories for data access.
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: RefreshTokenRepository
    ):
        """
        Initialize the auth service.
        
        Args:
            user_repository: User repository for data access
            token_repository: Refresh token repository for data access
        """
        self.user_repo = user_repository
        self.token_repo = token_repository
    
    async def login(
        self,
        login_request: LoginRequest,
        client_ip: str,
        user_agent: Optional[str] = None
    ) -> LoginResponse:
        """
        Authenticate user and create tokens.
        
        Args:
            login_request: Login credentials
            client_ip: Client IP address for rate limiting
            user_agent: Client user agent string
            
        Returns:
            Login response with tokens and user info
            
        Raises:
            SecurityError: If authentication fails
            HTTPException: If rate limited
        """
        # Check rate limiting
        await check_login_rate_limit(client_ip)
        
        # Get user by email
        user = await self.user_repo.get_by_email(login_request.email)
        if not user:
            logger.warning(f"Login attempt with non-existent email: {login_request.email}")
            raise SecurityError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {user.email}")
            raise SecurityError("Account is deactivated")
        
        # Verify password
        if not user.verify_password(login_request.password):
            logger.warning(f"Invalid password for user: {user.email}")
            raise SecurityError("Invalid email or password")
        
        # Update last login
        await self.user_repo.update(user.id, last_login_at=utc_now())
        
        # Create session
        session_id = str(uuid4())
        
        # Generate tokens
        access_token = create_access_token({"sub": str(user.id), "email": user.email})
        refresh_token_str = create_refresh_token({"sub": str(user.id), "session_id": session_id})
        
        # Store refresh token
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            session_id=session_id,
            device_info=user_agent,
            ip_address=client_ip
        )
        
        await self.token_repo.create(
            user_id=refresh_token.user_id,
            token_hash=refresh_token.token_hash,
            session_id=refresh_token.session_id,
            expires_at=refresh_token.expires_at,
            status=refresh_token.status,
            device_info=refresh_token.device_info,
            ip_address=refresh_token.ip_address
        )
        
        await self.token_repo.commit()
        
        logger.info(f"User {user.email} logged in successfully from {client_ip}")
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=1800,  # 30 minutes
            user=UserResponse.from_orm(user)
        )
    
    async def refresh_token(
        self,
        refresh_token_str: str,
        client_ip: str,
        user_agent: Optional[str] = None
    ) -> TokenRefreshResponse:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token_str: Refresh token string
            client_ip: Client IP address
            user_agent: Client user agent string
            
        Returns:
            New access and refresh tokens
            
        Raises:
            SecurityError: If refresh token is invalid
        """
        # Check if token is blacklisted
        if is_token_blacklisted(refresh_token_str):
            raise SecurityError("Token has been revoked")
        
        # Find refresh token by hash
        token_hash = RefreshToken._hash_token(refresh_token_str)
        refresh_token = await self.token_repo.get_by_token_hash(token_hash)
        
        if not refresh_token:
            raise SecurityError("Invalid refresh token")
        
        # Check if token is active
        if not refresh_token.is_active():
            raise SecurityError("Token has expired or been revoked")
        
        # Get user
        user = await self.user_repo.get_by_id(refresh_token.user_id)
        if not user or not user.is_active:
            raise SecurityError("User account is not available")
        
        # Generate new tokens
        new_access_token = create_access_token({"sub": str(user.id), "email": user.email})
        new_refresh_token = create_refresh_token({"sub": str(user.id), "session_id": refresh_token.session_id})
        
        # Rotate refresh token
        refresh_token.rotate_token(new_refresh_token)
        await self.token_repo.session.flush()
        await self.token_repo.commit()
        
        # Blacklist old refresh token
        blacklist_token(refresh_token_str)
        
        logger.info(f"Token refreshed for user {user.email}")
        
        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800
        )
    
    async def logout(
        self,
        refresh_token_str: str,
        access_token: str,
        revoke_all_sessions: bool = False
    ) -> bool:
        """
        Logout user by revoking tokens.
        
        Args:
            refresh_token_str: Refresh token to revoke
            access_token: Access token to blacklist
            revoke_all_sessions: Whether to revoke all user sessions
            
        Returns:
            True if logout successful
        """
        # Blacklist access token
        blacklist_token(access_token)
        
        if refresh_token_str:
            # Find and revoke refresh token
            token_hash = RefreshToken._hash_token(refresh_token_str)
            refresh_token = await self.token_repo.get_by_token_hash(token_hash)
            
            if refresh_token:
                if revoke_all_sessions:
                    # Revoke all sessions for this user
                    await self.token_repo.revoke_user_sessions(refresh_token.user_id)
                else:
                    # Revoke just this session
                    refresh_token.revoke()
                
                await self.token_repo.commit()
                
                # Blacklist refresh token
                blacklist_token(refresh_token_str)
                
                logger.info(f"User logged out (session: {refresh_token.session_id})")
        
        return True
    
    async def register_user(
        self,
        user_data: UserCreate,
        client_ip: str
    ) -> UserResponse:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            client_ip: Client IP address for rate limiting
            
        Returns:
            Created user response
            
        Raises:
            SecurityError: If registration fails
            HTTPException: If rate limited
        """
        # Check rate limiting
        await check_registration_rate_limit(client_ip)
        
        # Check if email already exists
        if await self.user_repo.email_exists(user_data.email):
            raise SecurityError("Email already registered")
        
        # Validate password
        password_result = validate_password(user_data.password)
        if not password_result.is_valid:
            raise SecurityError(f"Password validation failed: {password_result.message}")
        
        try:
            # Create user
            user = await self.user_repo.create(
                email=user_data.email.lower(),
                password_hash=hash_password(user_data.password),
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role=user_data.role.value if user_data.role else UserRole.CONSULTANT.value
            )
            
            await self.user_repo.commit()
            
            logger.info(f"New user registered: {user.email}")
            
            return UserResponse.from_orm(user)
            
        except IntegrityError:
            await self.user_repo.rollback()
            raise SecurityError("Email already registered")
    
    async def get_user_sessions(self, user_id: UUID) -> SessionListResponse:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user sessions
        """
        tokens = await self.token_repo.get_user_sessions(user_id, active_only=True)
        
        sessions = []
        for token in tokens:
            sessions.append(SessionInfo(
                session_id=token.session_id,
                device_info=token.device_info,
                ip_address=token.ip_address,
                created_at=token.created_at,
                last_used_at=token.last_used_at,
                is_current=False  # Could be enhanced to detect current session
            ))
        
        return SessionListResponse(
            sessions=sessions,
            total_sessions=len(sessions),
            max_sessions=3
        )
    
    async def revoke_session(self, user_id: UUID, session_id: str) -> bool:
        """
        Revoke a specific user session.
        
        Args:
            user_id: User ID (for authorization)
            session_id: Session ID to revoke
            
        Returns:
            True if session was revoked
        """
        refresh_token = await self.token_repo.get_by_session_id(session_id)
        
        if not refresh_token or refresh_token.user_id != user_id:
            return False
        
        refresh_token.revoke()
        await self.token_repo.commit()
        
        logger.info(f"Session {session_id} revoked for user {user_id}")
        return True
    
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        revoke_other_sessions: bool = True
    ) -> bool:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password for verification
            new_password: New password
            revoke_other_sessions: Whether to revoke other sessions
            
        Returns:
            True if password changed successfully
            
        Raises:
            SecurityError: If current password is incorrect or new password is invalid
        """
        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise SecurityError("User not found")
        
        # Verify current password
        if not user.verify_password(current_password):
            raise SecurityError("Current password is incorrect")
        
        # Validate new password
        password_result = validate_password(new_password)
        if not password_result.is_valid:
            raise SecurityError(f"New password validation failed: {password_result.message}")
        
        # Update password
        new_password_hash = hash_password(new_password)
        await self.user_repo.update(user_id, password_hash=new_password_hash)
        
        # Optionally revoke other sessions for security
        if revoke_other_sessions:
            await self.token_repo.revoke_user_sessions(user_id)
        
        await self.user_repo.commit()
        
        logger.info(f"Password changed for user {user.email}")
        return True
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired refresh tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        count = await self.token_repo.cleanup_expired_tokens()
        await self.token_repo.commit()
        logger.info(f"Cleaned up {count} expired tokens")
        return count