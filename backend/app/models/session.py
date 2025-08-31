"""
Session model for JWT refresh token management and concurrent session tracking.
Implements secure session management for the AI Resume Review Platform.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID, uuid4
import logging
import hashlib
from enum import Enum

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import validates, relationship
from pydantic import BaseModel, Field, validator

from app.core.security import REFRESH_TOKEN_EXPIRE_DAYS
from app.models.user import Base  # Import shared Base
from app.core.datetime_utils import utc_now, ensure_utc

# Configure logging
logger = logging.getLogger(__name__)


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


# Pydantic models for API requests/responses

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