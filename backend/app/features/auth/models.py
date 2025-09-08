"""
User model with secure password handling for the AI Resume Review Platform.
Integrates with PostgreSQL database and implements secure authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID, uuid4
import logging
from enum import Enum

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import validates
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, computed_field

from app.core.security import (
    password_hasher, 
    PasswordValidationResult,
    SecurityError
)
from app.core.datetime_utils import utc_now, ensure_utc

# Configure logging
logger = logging.getLogger(__name__)

Base = declarative_base()


class UserRole(str, Enum):
    """User role enumeration."""
    CONSULTANT = "consultant"
    ADMIN = "admin"


class User(Base):
    """
    User model with secure password handling.
    
    Implements bcrypt password hashing, validation, and secure authentication.
    Never stores or logs plain text passwords.
    """
    
    __tablename__ = "users"
    
    # Primary key and basic info
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Account status and permissions
    role = Column(String(50), nullable=False, default=UserRole.CONSULTANT.value)
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password security tracking
    password_changed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    def __init__(self, email: str, password: str, first_name: str, last_name: str, 
                 role: UserRole = UserRole.CONSULTANT, **kwargs):
        """
        Initialize user with secure password handling.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            first_name: User first name
            last_name: User last name  
            role: User role (consultant or admin)
            **kwargs: Additional fields
        """
        super().__init__(**kwargs)
        
        self.email = email.lower().strip()
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.role = role.value if isinstance(role, UserRole) else role
        
        # Set default values for unit testing (normally handled by database)
        if self.is_active is None:
            self.is_active = True
        if self.email_verified is None:
            self.email_verified = False
        if self.failed_login_attempts is None:
            self.failed_login_attempts = 0
        if self.created_at is None:
            self.created_at = utc_now()
        if self.updated_at is None:
            self.updated_at = utc_now()
        if self.password_changed_at is None:
            self.password_changed_at = utc_now()
        
        # Hash password securely
        self.set_password(password)
        
        logger.info(f"User created with email: {self.email}")
    
    def set_password(self, password: str) -> None:
        """
        Set user password with secure hashing.
        
        Args:
            password: Plain text password
            
        Raises:
            SecurityError: If password validation fails
        """
        try:
            # Hash password (validation happens inside password_hasher)
            self.password_hash = password_hasher.hash_password(password)
            self.password_changed_at = utc_now()
            
            # Reset security counters on successful password change
            self.failed_login_attempts = 0
            self.locked_until = None
            
            logger.info(f"Password updated for user: {self.email}")
            
        except SecurityError as e:
            logger.error(f"Password update failed for user {self.email}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating password for user {self.email}: {str(e)}")
            raise SecurityError("Failed to update password")
    
    def check_password(self, password: str) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        if not password or not self.password_hash:
            return False
            
        try:
            is_valid = password_hasher.verify_password(password, self.password_hash)
            
            if is_valid:
                # Reset failed attempts on successful login
                self.failed_login_attempts = 0
                self.locked_until = None
                self.last_login_at = utc_now()
                logger.info(f"Successful login for user: {self.email}")
            else:
                # Increment failed attempts
                self.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if self.failed_login_attempts >= 5:
                    self.locked_until = utc_now() + timedelta(minutes=30)
                    logger.warning(f"Account locked due to failed attempts: {self.email}")
                else:
                    logger.warning(f"Failed login attempt ({self.failed_login_attempts}/5) for user: {self.email}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Password verification error for user {self.email}: {str(e)}")
            return False
    
    def is_account_locked(self) -> bool:
        """
        Check if account is currently locked.
        
        Returns:
            True if account is locked, False otherwise
        """
        if not self.locked_until:
            return False
            
        if utc_now() >= ensure_utc(self.locked_until):
            # Lock period expired, unlock account
            self.locked_until = None
            self.failed_login_attempts = 0
            return False
            
        return True
    
    def unlock_account(self) -> None:
        """Unlock user account (admin function)."""
        self.locked_until = None
        self.failed_login_attempts = 0
        logger.info(f"Account manually unlocked: {self.email}")
    
    def needs_password_rehash(self) -> bool:
        """
        Check if password hash needs to be updated.
        
        Returns:
            True if password should be rehashed
        """
        return password_hasher.needs_rehash(self.password_hash)
    
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value
    
    def is_consultant(self) -> bool:
        """Check if user has consultant role."""
        return self.role == UserRole.CONSULTANT.value
    
    def get_full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def full_name(self) -> str:
        """Full name property for Pydantic serialization."""
        return self.get_full_name()
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if not email or '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower().strip()
    
    @validates('role')
    def validate_role(self, key, role):
        """Validate user role."""
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
        return role
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert user to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            User dictionary (never includes password_hash)
        """
        data = {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "role": self.role,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        
        if include_sensitive:
            data.update({
                "failed_login_attempts": self.failed_login_attempts,
                "is_locked": self.is_account_locked(),
                "locked_until": self.locked_until.isoformat() if self.locked_until else None,
                "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            })
        
        return data
    
    def __repr__(self) -> str:
        """String representation (never includes sensitive data)."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


# Pydantic models for API requests/responses

class UserBase(BaseModel):
    """Base user model for shared attributes."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.CONSULTANT)


class UserCreate(UserBase):
    """User creation model with password."""
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, password):
        """Validate password strength."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class UserUpdate(BaseModel):
    """User update model."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class PasswordUpdate(BaseModel):
    """Password update model."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, password):
        """Validate new password strength."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class AdminPasswordReset(BaseModel):
    """Admin password reset model."""
    user_id: UUID
    new_password: str = Field(..., min_length=8, max_length=128)
    force_password_change: bool = Field(default=True)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, password):
        """Validate new password strength."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class UserResponse(UserBase):
    """User response model."""
    id: UUID
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name from first_name and last_name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """Detailed user response model (admin only)."""
    failed_login_attempts: int
    is_locked: bool
    locked_until: Optional[datetime] = None
    password_changed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============================================================================
# Session Management Models (from app/models/session.py)
# ============================================================================

import hashlib
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import validates
from uuid import uuid4
from datetime import timedelta

from app.core.security import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.datetime_utils import utc_now, ensure_utc


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RefreshToken(Base):
    """
    Refresh token model for JWT token management.
    
    Stores refresh tokens securely with session tracking and expiration.
    Supports concurrent session management and token rotation.
    """
    
    __tablename__ = "refresh_tokens"
    
    # Primary key and references
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Token storage (hashed for security)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_used_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    
    # Session management
    status = Column(String(50), nullable=False, default=SessionStatus.ACTIVE.value)
    device_info = Column(Text, nullable=True)  # User agent, device info
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    
    # Relationships
    # user = relationship("User", back_populates="refresh_tokens")
    
    def __init__(self, user_id: UUID, token: str, session_id: str, 
                 device_info: Optional[str] = None, ip_address: Optional[str] = None, **kwargs):
        """
        Initialize refresh token with secure token hashing.
        
        Args:
            user_id: ID of the user this token belongs to
            token: JWT refresh token string (will be hashed)
            session_id: Unique session identifier
            device_info: Optional device/browser information
            ip_address: Optional IP address
            **kwargs: Additional fields
        """
        # Initialize with default values for unit testing
        super().__init__(**kwargs)
        
        # Set basic fields
        self.user_id = user_id
        self.session_id = session_id
        self.device_info = device_info
        self.ip_address = ip_address
        
        # Set default status if not provided (for unit testing)
        if not hasattr(self, 'status') or self.status is None:
            self.status = SessionStatus.ACTIVE.value
        
        # Set timestamps if not provided (for unit testing)
        if not hasattr(self, 'created_at') or self.created_at is None:
            self.created_at = utc_now()
        if not hasattr(self, 'last_used_at') or self.last_used_at is None:
            self.last_used_at = utc_now()
        
        # Hash the token for secure storage
        self.token_hash = self._hash_token(token)
        
        # Set expiration
        self.expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Generate ID for unit testing if not provided
        if not hasattr(self, 'id') or self.id is None:
            self.id = uuid4()
        
        logger.info(f"Refresh token created for user {user_id} with session {session_id}")
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Create secure hash of refresh token.
        
        Args:
            token: JWT token string
            
        Returns:
            SHA-256 hash of token
        """
        if token is None:
            return ""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def verify_token(self, token: str) -> bool:
        """
        Verify if provided token matches stored hash.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            True if token matches, False otherwise
        """
        token_hash = self._hash_token(token)
        return token_hash == self.token_hash
    
    def is_expired(self) -> bool:
        """
        Check if refresh token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return utc_now() >= ensure_utc(self.expires_at)
    
    def is_active(self) -> bool:
        """
        Check if refresh token is active (not expired or revoked).
        
        Returns:
            True if token is active, False otherwise
        """
        return (self.status == SessionStatus.ACTIVE.value and 
                not self.is_expired())
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.status = SessionStatus.REVOKED.value
        logger.info(f"Refresh token revoked for session {self.session_id}")
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = utc_now()
    
    def rotate_token(self, new_token: str) -> None:
        """
        Rotate refresh token for security.
        
        Args:
            new_token: New JWT refresh token string
        """
        self.token_hash = self._hash_token(new_token)
        self.last_used_at = utc_now()
        # Extend expiration on rotation
        self.expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        logger.info(f"Refresh token rotated for session {self.session_id}")
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate session status."""
        valid_statuses = [s.value for s in SessionStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return status
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert refresh token to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            Refresh token dictionary (never includes token_hash)
        """
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat(),
            "is_active": self.is_active(),
            "is_expired": self.is_expired(),
        }
        
        if include_sensitive:
            data.update({
                "device_info": self.device_info,
                "ip_address": self.ip_address,
            })
        
        return data
    
    def __repr__(self) -> str:
        """String representation (never includes sensitive data)."""
        return f"<RefreshToken(id={self.id}, session={self.session_id}, status={self.status})>"


# Session management Pydantic models
class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_used_at: datetime
    is_current: bool = False


class SessionListResponse(BaseModel):
    """Session list response model."""
    sessions: List[SessionInfo]
    total_sessions: int
    max_sessions: int = 3


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str = Field(..., min_length=1)


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionRevokeRequest(BaseModel):
    """Session revoke request model."""
    session_id: str = Field(..., min_length=1)


class SessionRevokeResponse(BaseModel):
    """Session revoke response model."""
    success: bool
    message: str