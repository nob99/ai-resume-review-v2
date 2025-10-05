"""
Admin schemas for user management.
Defines request and response models for admin operations.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, computed_field

from app.core.security import password_hasher
from database.models.auth import UserRole


class AdminUserCreate(BaseModel):
    """Admin creating a new user."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.JUNIOR_RECRUITER)
    temporary_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('temporary_password')
    @classmethod
    def validate_password(cls, password):
        """Validate password strength."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class AdminUserUpdate(BaseModel):
    """Admin updating a user."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    email_verified: Optional[bool] = None


class AdminPasswordReset(BaseModel):
    """Admin resetting a user's password."""
    new_password: str = Field(..., min_length=8, max_length=128)
    force_password_change: bool = Field(default=True)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, password):
        """Validate password strength."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class UserListItem(BaseModel):
    """User item in list response."""
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    assigned_candidates_count: int = Field(default=0)

    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name from first_name and last_name."""
        return f"{self.first_name} {self.last_name}".strip()

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(BaseModel):
    """Detailed user information for admin view."""
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    password_changed_at: datetime
    failed_login_attempts: int
    locked_until: Optional[datetime] = None
    assigned_candidates_count: int = Field(default=0)
    total_resumes_uploaded: int = Field(default=0)
    total_reviews_requested: int = Field(default=0)

    @computed_field
    @property
    def full_name(self) -> str:
        """Computed full name."""
        return f"{self.first_name} {self.last_name}".strip()

    @computed_field
    @property
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if not self.locked_until:
            return False
        from app.core.datetime_utils import utc_now, ensure_utc
        return utc_now() < ensure_utc(self.locked_until)

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserDirectoryItem(BaseModel):
    """Basic user info for directory (available to senior recruiters)."""
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserDirectoryResponse(BaseModel):
    """User directory response."""
    users: List[UserDirectoryItem]
    total: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True