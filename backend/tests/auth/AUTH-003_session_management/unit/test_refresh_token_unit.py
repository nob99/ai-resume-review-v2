"""
Unit tests for refresh token model and security functionality.
Tests the RefreshToken model, token hashing, and session management without database dependencies.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.core.datetime_utils import utc_now, ensure_utc
from unittest.mock import Mock, patch

from app.models.session import RefreshToken, SessionStatus
from app.core.security import create_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS


class TestRefreshTokenModel:
    """Test RefreshToken model functionality."""
    
    def test_refresh_token_creation(self):
        """Test creating a refresh token with proper initialization."""
        user_id = uuid4()
        session_id = "test-session-123"
        token = "test.jwt.token"
        device_info = "Mozilla/5.0 (Test Browser)"
        ip_address = "192.168.1.1"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id=session_id,
            device_info=device_info,
            ip_address=ip_address
        )
        
        assert refresh_token.user_id == user_id
        assert refresh_token.session_id == session_id
        assert refresh_token.device_info == device_info
        assert refresh_token.ip_address == ip_address
        assert refresh_token.status == SessionStatus.ACTIVE.value
        assert refresh_token.token_hash is not None
        assert refresh_token.token_hash != token  # Token should be hashed
        assert len(refresh_token.token_hash) == 64  # SHA-256 hash length
        
        # Check expiration is set correctly (7 days)
        expected_expiry = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        time_diff = abs((refresh_token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5  # Allow 5 second tolerance
    
    def test_token_hashing_security(self):
        """Test that tokens are securely hashed and not stored in plain text."""
        user_id = uuid4()
        token1 = "test.jwt.token1"
        token2 = "test.jwt.token2"
        
        refresh_token1 = RefreshToken(
            user_id=user_id,
            token=token1,
            session_id="session1"
        )
        
        refresh_token2 = RefreshToken(
            user_id=user_id,
            token=token2,
            session_id="session2"
        )
        
        # Tokens should produce different hashes
        assert refresh_token1.token_hash != refresh_token2.token_hash
        
        # Hashes should be deterministic for same input
        hash1 = RefreshToken._hash_token(token1)
        hash2 = RefreshToken._hash_token(token1)
        assert hash1 == hash2
        
        # Different tokens should produce different hashes
        hash3 = RefreshToken._hash_token(token2)
        assert hash1 != hash3
    
    def test_token_verification(self):
        """Test token verification functionality."""
        user_id = uuid4()
        correct_token = "correct.jwt.token"
        wrong_token = "wrong.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=correct_token,
            session_id="test-session"
        )
        
        # Correct token should verify
        assert refresh_token.verify_token(correct_token) is True
        
        # Wrong token should not verify
        assert refresh_token.verify_token(wrong_token) is False
        
        # Empty/None token should not verify
        assert refresh_token.verify_token("") is False
        assert refresh_token.verify_token(None) is False
    
    def test_expiration_checking(self):
        """Test token expiration functionality."""
        user_id = uuid4()
        token = "test.jwt.token"
        
        # Create token with normal expiration
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session"
        )
        
        # Token should not be expired initially
        assert refresh_token.is_expired() is False
        assert refresh_token.is_active() is True
        
        # Manually set expiration to past
        refresh_token.expires_at = utc_now() - timedelta(hours=1)
        
        # Token should now be expired
        assert refresh_token.is_expired() is True
        assert refresh_token.is_active() is False
    
    def test_token_revocation(self):
        """Test token revocation functionality."""
        user_id = uuid4()
        token = "test.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session"
        )
        
        # Token should be active initially
        assert refresh_token.status == SessionStatus.ACTIVE.value
        assert refresh_token.is_active() is True
        
        # Revoke token
        refresh_token.revoke()
        
        # Token should be revoked
        assert refresh_token.status == SessionStatus.REVOKED.value
        assert refresh_token.is_active() is False
    
    def test_token_rotation(self):
        """Test token rotation functionality."""
        user_id = uuid4()
        original_token = "original.jwt.token"
        new_token = "new.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=original_token,
            session_id="test-session"
        )
        
        original_hash = refresh_token.token_hash
        original_expires = refresh_token.expires_at
        original_last_used = refresh_token.last_used_at
        
        # Wait a moment to ensure timestamp changes
        import time
        time.sleep(0.001)
        
        # Rotate token
        refresh_token.rotate_token(new_token)
        
        # Hash should change
        assert refresh_token.token_hash != original_hash
        
        # Should verify with new token
        assert refresh_token.verify_token(new_token) is True
        assert refresh_token.verify_token(original_token) is False
        
        # Timestamps should update
        assert refresh_token.last_used_at > original_last_used
        assert refresh_token.expires_at > original_expires
    
    def test_last_used_update(self):
        """Test updating last used timestamp."""
        user_id = uuid4()
        token = "test.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session"
        )
        
        original_last_used = refresh_token.last_used_at
        
        # Wait a moment to ensure timestamp changes
        import time
        time.sleep(0.001)
        
        # Update last used
        refresh_token.update_last_used()
        
        # Timestamp should be updated
        assert refresh_token.last_used_at > original_last_used
    
    def test_status_validation(self):
        """Test status validation."""
        user_id = uuid4()
        token = "test.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session"
        )
        
        # Valid statuses should work
        for status in SessionStatus:
            refresh_token.status = status.value
            # Should not raise exception
        
        # Invalid status should raise ValueError
        with pytest.raises(ValueError, match="Invalid status"):
            refresh_token.validate_status("status", "invalid_status")
    
    def test_to_dict_serialization(self):
        """Test converting refresh token to dictionary."""
        user_id = uuid4()
        token = "test.jwt.token"
        device_info = "Test Browser"
        ip_address = "192.168.1.1"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session",
            device_info=device_info,
            ip_address=ip_address
        )
        
        # Basic serialization (no sensitive data)
        basic_dict = refresh_token.to_dict()
        
        assert basic_dict["user_id"] == str(user_id)
        assert basic_dict["session_id"] == "test-session"
        assert basic_dict["status"] == SessionStatus.ACTIVE.value
        assert "token_hash" not in basic_dict  # Should never include token hash
        assert "device_info" not in basic_dict  # Not included by default
        assert "ip_address" not in basic_dict  # Not included by default
        
        # Serialization with sensitive data
        sensitive_dict = refresh_token.to_dict(include_sensitive=True)
        
        assert sensitive_dict["device_info"] == device_info
        assert sensitive_dict["ip_address"] == ip_address
        assert "token_hash" not in sensitive_dict  # Should NEVER include token hash
    
    def test_string_representation(self):
        """Test string representation of refresh token."""
        user_id = uuid4()
        token = "test.jwt.token"
        session_id = "test-session-123"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id=session_id
        )
        
        repr_str = repr(refresh_token)
        
        assert "RefreshToken" in repr_str
        assert str(refresh_token.id) in repr_str
        assert session_id in repr_str
        assert SessionStatus.ACTIVE.value in repr_str
        assert token not in repr_str  # Should not expose token


class TestRefreshTokenSecurity:
    """Test security aspects of refresh token functionality."""
    
    def test_create_refresh_token_function(self):
        """Test the create_refresh_token utility function."""
        user_id = str(uuid4())
        session_id = "test-session"
        
        # Create refresh token
        token = create_refresh_token(user_id, session_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically longer
        
        # Different calls should produce different tokens
        token2 = create_refresh_token(user_id, session_id)
        assert token != token2
    
    def test_token_uniqueness(self):
        """Test that generated tokens are unique."""
        user_id = str(uuid4())
        tokens = set()
        
        # Generate multiple tokens
        for i in range(100):
            token = create_refresh_token(user_id, f"session-{i}")
            tokens.add(token)
        
        # All tokens should be unique
        assert len(tokens) == 100
    
    @patch('app.models.session.logger')
    def test_logging_security(self, mock_logger):
        """Test that sensitive data is not logged."""
        user_id = uuid4()
        token = "sensitive.jwt.token"
        
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            session_id="test-session"
        )
        
        # Check that token creation was logged
        mock_logger.info.assert_called()
        
        # Get all logged messages
        logged_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        
        # Ensure no logged message contains the actual token
        for message in logged_messages:
            assert token not in message
            assert "sensitive" not in message.lower()
        
        # Should log user_id and session_id (not sensitive)
        creation_message = logged_messages[0]
        assert str(user_id) in creation_message
        assert "test-session" in creation_message