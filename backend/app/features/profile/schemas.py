"""
Profile management Pydantic schemas for API requests/responses.
Contains schemas for profile updates and password changes.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.security import password_hasher


class ProfileUpdate(BaseModel):
    """Schema for updating user profile (first_name, last_name only)."""
    first_name: str = Field(..., min_length=1, max_length=100, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User's last name")

    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate that name is not empty after stripping whitespace."""
        if not value.strip():
            raise ValueError('Name cannot be empty')
        return value.strip()


class PasswordChange(BaseModel):
    """Schema for changing user password."""
    current_password: str = Field(..., min_length=1, description="Current password for verification")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        """Validate new password strength using existing password hasher."""
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password


class MessageResponse(BaseModel):
    """Simple message response for success/failure operations."""
    message: str
    success: bool = True