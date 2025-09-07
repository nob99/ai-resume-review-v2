"""
Pydantic schemas for the auth feature.
Re-exports models from models.py to follow the new feature structure.
"""

# Re-export all Pydantic models from models
from .models import (
    # User schemas
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserDetailResponse,
    PasswordUpdate,
    AdminPasswordReset,
    
    # Auth schemas
    LoginRequest,
    LoginResponse,
    
    # Session schemas
    SessionInfo,
    SessionListResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    SessionRevokeRequest,
    SessionRevokeResponse,
)

__all__ = [
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "UserDetailResponse",
    "PasswordUpdate",
    "AdminPasswordReset",
    "LoginRequest",
    "LoginResponse",
    "SessionInfo",
    "SessionListResponse", 
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "SessionRevokeRequest",
    "SessionRevokeResponse",
]