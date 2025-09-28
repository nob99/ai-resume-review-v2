"""
Authentication-related Pydantic schemas for API requests/responses.

Contains all Pydantic models for authentication endpoints,
separated from SQLAlchemy database models.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, computed_field

from app.core.security import password_hasher


class UserRole(str, Enum):
    """User role enumeration."""
    JUNIOR_RECRUITER = "junior_recruiter"
    SENIOR_RECRUITER = "senior_recruiter"
    ADMIN = "admin"


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


# User schemas
class UserBase(BaseModel):
    """Base user model for shared attributes."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.JUNIOR_RECRUITER)


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


# Session management schemas
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