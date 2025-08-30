"""
User model with secure password handling for the AI Resume Review Platform.
Integrates with PostgreSQL database and implements secure authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
import logging
from enum import Enum

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from pydantic import BaseModel, EmailStr, Field, validator

from app.core.security import (
    password_hasher, 
    PasswordValidationResult,
    SecurityError
)

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
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Password security tracking
    password_changed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
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
            self.password_changed_at = datetime.utcnow()
            
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
                self.last_login_at = datetime.utcnow()
                logger.info(f"Successful login for user: {self.email}")
            else:
                # Increment failed attempts
                self.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if self.failed_login_attempts >= 5:
                    self.locked_until = datetime.utcnow() + timedelta(minutes=30)
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
            
        if datetime.utcnow() >= self.locked_until:
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
    
    @validator('password')
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
    
    @validator('new_password')
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
    
    @validator('new_password')
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
    full_name: str
    
    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response model (admin only)."""
    failed_login_attempts: int
    is_locked: bool
    locked_until: Optional[datetime] = None
    password_changed_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse