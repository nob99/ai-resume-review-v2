"""
Authentication-related database models.

Contains User and RefreshToken models for secure user management
and session handling.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import validates, relationship

from . import Base
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from backend.app.core.datetime_utils import utc_now, ensure_utc
from backend.app.core.security import password_hasher, REFRESH_TOKEN_EXPIRE_DAYS


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


class User(Base):
    """
    User model with secure password handling.
    
    Implements bcrypt password hashing, validation, and secure authentication.
    Never stores or logs plain text passwords.
    """
    
    __tablename__ = "users"
    
    # Primary key and basic info
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Account status and permissions
    role = Column(String(50), nullable=False, default=UserRole.JUNIOR_RECRUITER.value)
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
    
    # Relationships
    file_uploads = relationship("FileUpload", back_populates="user")
    analyses = relationship("ResumeAnalysis", back_populates="user")
    
    def __init__(self, email: str, password: str, first_name: str, last_name: str, 
                 role: UserRole = UserRole.JUNIOR_RECRUITER, **kwargs):
        """
        Initialize user with secure password handling.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            first_name: User first name
            last_name: User last name  
            role: User role (junior_recruiter, senior_recruiter, or admin)
            **kwargs: Additional fields
        """
        super().__init__(**kwargs)
        
        self.email = email.lower().strip()
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.role = role.value if isinstance(role, UserRole) else role
        
        # Set default values for unit testing (normally handled by database)
        if self.id is None:
            self.id = uuid.uuid4()
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
    
    def set_password(self, password: str) -> None:
        """
        Set user password with secure hashing.
        
        Args:
            password: Plain text password
        """
        self.password_hash = password_hasher.hash_password(password)
        self.password_changed_at = utc_now()
        self.failed_login_attempts = 0
        self.locked_until = None
    
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
            
        is_valid = password_hasher.verify_password(password, self.password_hash)
        
        if is_valid:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_login_at = utc_now()
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.locked_until = utc_now() + timedelta(minutes=30)
        
        return is_valid
    
    def is_account_locked(self) -> bool:
        """
        Check if account is currently locked.
        
        Returns:
            True if account is locked, False otherwise
        """
        if not self.locked_until:
            return False
            
        if utc_now() >= ensure_utc(self.locked_until):
            self.locked_until = None
            self.failed_login_attempts = 0
            return False
            
        return True
    
    def unlock_account(self) -> None:
        """Unlock user account (admin function)."""
        self.locked_until = None
        self.failed_login_attempts = 0
    
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
    
    def is_junior_recruiter(self) -> bool:
        """Check if user has junior recruiter role."""
        return self.role == UserRole.JUNIOR_RECRUITER.value
    
    def is_senior_recruiter(self) -> bool:
        """Check if user has senior recruiter role."""
        return self.role == UserRole.SENIOR_RECRUITER.value
    
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
    
    def __repr__(self) -> str:
        """String representation (never includes sensitive data)."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"


class RefreshToken(Base):
    """
    Refresh token model for JWT token management.
    
    Stores refresh tokens securely with session tracking and expiration.
    Supports concurrent session management and token rotation.
    """
    
    __tablename__ = "refresh_tokens"
    
    # Primary key and references
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
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
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def __init__(self, user_id: uuid.UUID, token: str, session_id: str, 
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
        super().__init__(**kwargs)
        
        self.user_id = user_id
        self.session_id = session_id
        self.device_info = device_info
        self.ip_address = ip_address
        
        if not hasattr(self, 'status') or self.status is None:
            self.status = SessionStatus.ACTIVE.value
        
        if not hasattr(self, 'created_at') or self.created_at is None:
            self.created_at = utc_now()
        if not hasattr(self, 'last_used_at') or self.last_used_at is None:
            self.last_used_at = utc_now()
        
        # Hash the token for secure storage
        self.token_hash = self._hash_token(token)
        self.expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        if not hasattr(self, 'id') or self.id is None:
            self.id = uuid.uuid4()
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """Create secure hash of refresh token."""
        if token is None:
            return ""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    def verify_token(self, token: str) -> bool:
        """Verify if provided token matches stored hash."""
        token_hash = self._hash_token(token)
        return token_hash == self.token_hash
    
    def is_expired(self) -> bool:
        """Check if refresh token is expired."""
        return utc_now() >= ensure_utc(self.expires_at)
    
    def is_active(self) -> bool:
        """Check if refresh token is active (not expired or revoked)."""
        return (self.status == SessionStatus.ACTIVE.value and 
                not self.is_expired())
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.status = SessionStatus.REVOKED.value
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = utc_now()
    
    def rotate_token(self, new_token: str) -> None:
        """Rotate refresh token for security."""
        self.token_hash = self._hash_token(new_token)
        self.last_used_at = utc_now()
        self.expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate session status."""
        valid_statuses = [s.value for s in SessionStatus]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return status
    
    def __repr__(self) -> str:
        """String representation (never includes sensitive data)."""
        return f"<RefreshToken(id={self.id}, session={self.session_id}, status={self.status})>"