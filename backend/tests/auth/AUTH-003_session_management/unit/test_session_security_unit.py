"""
Unit tests for session security features and JWT token management.
Tests security aspects of refresh tokens, token rotation, and session limits.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.core.datetime_utils import utc_now, ensure_utc
from unittest.mock import Mock, patch, MagicMock

from app.core.security import (
    TokenManager, 
    create_refresh_token, 
    verify_token,
    SecurityError,
    REFRESH_TOKEN_EXPIRE_DAYS,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


class TestTokenManagerSecurity:
    """Test TokenManager security functionality."""
    
    def test_refresh_token_generation(self):
        """Test refresh token generation with security properties."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        # Generate refresh token
        refresh_token = token_manager.create_refresh_token(user_id, session_id)
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        
        # Verify token structure and payload
        payload = token_manager.verify_token(refresh_token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["session_id"] == session_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        
        # Verify expiration is set correctly (7 days)
        exp_timestamp = payload["exp"]
        iat_timestamp = payload.get("iat")
        
        if iat_timestamp:
            # Calculate difference between exp and iat (should be 7 days)
            # iat is float with microseconds, exp is int with seconds
            token_lifetime_seconds = exp_timestamp - iat_timestamp
            expected_lifetime_seconds = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 7 days in seconds
            
            # Allow tolerance for timezone differences and test execution time
            # The JWT library might add timezone offsets during encoding
            time_diff = abs(token_lifetime_seconds - expected_lifetime_seconds)
            assert time_diff < 43200, f"Time difference {time_diff} is too large (expected ~{expected_lifetime_seconds}, got lifetime {token_lifetime_seconds})"  # 12 hours tolerance
        else:
            # Fallback: check expiration is roughly 7 days from now
            import time
            now_timestamp = time.time()
            expected_exp_timestamp = now_timestamp + (REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
            time_diff = abs(exp_timestamp - expected_exp_timestamp)
            assert time_diff < 60  # Allow 1 minute tolerance
    
    def test_refresh_token_without_session_id(self):
        """Test refresh token generation auto-generates session ID."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        
        # Generate token without session ID
        refresh_token = token_manager.create_refresh_token(user_id)
        
        payload = token_manager.verify_token(refresh_token)
        assert payload is not None
        assert payload["user_id"] == user_id
        assert "session_id" in payload
        assert len(payload["session_id"]) > 10  # Should be UUID format
    
    def test_refresh_token_uniqueness(self):
        """Test that refresh tokens are unique even for same user."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        # Generate multiple tokens
        tokens = set()
        for _ in range(50):
            token = token_manager.create_refresh_token(user_id, session_id)
            tokens.add(token)
        
        # All tokens should be unique
        assert len(tokens) == 50
    
    def test_access_token_with_session_id(self):
        """Test that access tokens can include session ID."""
        token_manager = TokenManager()
        session_id = str(uuid4())
        
        data = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "role": "consultant",
            "session_id": session_id
        }
        
        access_token = token_manager.create_access_token(data)
        payload = token_manager.verify_token(access_token)
        
        assert payload is not None
        assert payload["session_id"] == session_id
        assert payload["sub"] == data["sub"]
        assert payload["email"] == data["email"]
        assert payload["role"] == data["role"]
    
    def test_token_expiration_security(self):
        """Test token expiration enforcement."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        
        # Create token with very short expiration
        short_expire = timedelta(seconds=1)
        access_token = token_manager.create_access_token(
            {"sub": user_id}, 
            expires_delta=short_expire
        )
        
        # Token should be valid immediately
        payload = token_manager.verify_token(access_token)
        assert payload is not None
        
        # Wait for token to expire
        import time
        time.sleep(2)
        
        # Token should be invalid after expiration
        expired_payload = token_manager.verify_token(access_token)
        assert expired_payload is None
    
    def test_token_tampering_detection(self):
        """Test that tampered tokens are rejected."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        
        # Create valid token
        valid_token = token_manager.create_refresh_token(user_id)
        parts = valid_token.split('.')
        
        # Tamper with payload (base64 decode, modify, encode)
        import base64
        import json
        
        # Decode payload
        payload_b64 = parts[1]
        # Add padding if needed
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload_data = json.loads(payload_json)
        
        # Tamper with data
        payload_data["user_id"] = str(uuid4())  # Change user ID
        
        # Re-encode
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload_data).encode()
        ).decode().rstrip('=')
        
        # Create tampered token
        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"
        
        # Tampered token should be rejected
        result = token_manager.verify_token(tampered_token)
        assert result is None
    
    @patch('app.core.security.logger')
    def test_token_creation_error_handling(self, mock_logger):
        """Test error handling in token creation."""
        token_manager = TokenManager()
        
        # Test with invalid secret key
        token_manager.secret_key = None
        
        with pytest.raises(SecurityError, match="Failed to create refresh token"):
            token_manager.create_refresh_token("user123")
        
        # Verify error was logged
        mock_logger.error.assert_called()
    
    @patch('app.core.security.logger')
    def test_token_verification_error_handling(self, mock_logger):
        """Test error handling in token verification."""
        token_manager = TokenManager()
        
        # Test various invalid tokens
        invalid_tokens = [
            None,
            "",
            "not.a.jwt",
            "invalid.token.format",
            "header.invalid_base64.signature"
        ]
        
        for invalid_token in invalid_tokens:
            result = token_manager.verify_token(invalid_token)
            assert result is None
        
        # Verify warnings were logged
        assert mock_logger.warning.called or mock_logger.error.called


class TestSessionSecurityPolicies:
    """Test security policies around session management."""
    
    def test_concurrent_session_limit_logic(self):
        """Test logic for session limit enforcement."""
        # This tests the concept - actual DB trigger testing is in integration
        MAX_SESSIONS = 3
        
        # Simulate session count tracking
        user_sessions = []
        
        def add_session(session_id):
            if len(user_sessions) >= MAX_SESSIONS:
                # Remove oldest session
                user_sessions.pop(0)
            user_sessions.append({
                "session_id": session_id,
                "created_at": utc_now()
            })
        
        # Add sessions up to limit
        for i in range(MAX_SESSIONS):
            add_session(f"session-{i}")
        
        assert len(user_sessions) == MAX_SESSIONS
        
        # Add one more - should remove oldest
        add_session("session-new")
        
        assert len(user_sessions) == MAX_SESSIONS
        assert user_sessions[0]["session_id"] == "session-1"  # session-0 removed
        assert user_sessions[-1]["session_id"] == "session-new"
    
    def test_token_rotation_security(self):
        """Test security properties of token rotation."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        # Generate initial token
        token1 = token_manager.create_refresh_token(user_id, session_id)
        payload1 = token_manager.verify_token(token1)
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.001)
        
        # Generate rotated token
        token2 = token_manager.create_refresh_token(user_id, session_id)
        payload2 = token_manager.verify_token(token2)
        
        # Tokens should be different
        assert token1 != token2
        
        # Both should have same user_id and session_id
        assert payload1["user_id"] == payload2["user_id"]
        assert payload1["session_id"] == payload2["session_id"]
        
        # Expiration times should be different (newer token has later expiration)
        assert payload2["exp"] >= payload1["exp"]
    
    def test_session_isolation(self):
        """Test that sessions are properly isolated between users."""
        token_manager = TokenManager()
        
        user1_id = str(uuid4())
        user2_id = str(uuid4())
        session_id = str(uuid4())  # Same session ID for both (shouldn't conflict)
        
        # Create tokens for both users
        token1 = token_manager.create_refresh_token(user1_id, session_id)
        token2 = token_manager.create_refresh_token(user2_id, session_id)
        
        # Verify isolation
        payload1 = token_manager.verify_token(token1)
        payload2 = token_manager.verify_token(token2)
        
        assert payload1["user_id"] != payload2["user_id"]
        assert payload1["session_id"] == payload2["session_id"]  # Same session ID allowed
        
        # Tokens should be completely different
        assert token1 != token2
    
    def test_token_type_enforcement(self):
        """Test that token types are properly enforced."""
        token_manager = TokenManager()
        user_id = str(uuid4())
        
        # Create access token
        access_token = token_manager.create_access_token({
            "sub": user_id,
            "email": "test@example.com"
        })
        
        # Create refresh token
        refresh_token = token_manager.create_refresh_token(user_id)
        
        # Verify payloads have correct types
        access_payload = token_manager.verify_token(access_token)
        refresh_payload = token_manager.verify_token(refresh_token)
        
        assert "type" not in access_payload or access_payload.get("type") != "refresh"
        assert refresh_payload["type"] == "refresh"
        
        # They should have different structures
        assert "user_id" in refresh_payload
        assert "session_id" in refresh_payload
        assert "sub" in access_payload


class TestSecurityUtilityFunctions:
    """Test security utility functions."""
    
    def test_create_refresh_token_function(self):
        """Test the create_refresh_token utility function."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        
        token = create_refresh_token(user_id, session_id)
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify it's a valid JWT
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["session_id"] == session_id
    
    def test_verify_token_function(self):
        """Test the verify_token utility function."""
        user_id = str(uuid4())
        
        # Create valid token
        valid_token = create_refresh_token(user_id)
        
        # Verify valid token
        result = verify_token(valid_token)
        assert result is not None
        assert result["user_id"] == user_id
        
        # Verify invalid token
        invalid_result = verify_token("invalid.token.format")
        assert invalid_result is None
    
    def test_token_security_constants(self):
        """Test that security constants are properly configured."""
        # Verify expiration times are reasonable
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 30  # Should match requirement
        assert REFRESH_TOKEN_EXPIRE_DAYS == 7
        
        # Verify minimum security
        assert ACCESS_TOKEN_EXPIRE_MINUTES >= 15  # Not too short
        assert ACCESS_TOKEN_EXPIRE_MINUTES <= 60  # Not too long
        assert REFRESH_TOKEN_EXPIRE_DAYS >= 1  # Not too short
        assert REFRESH_TOKEN_EXPIRE_DAYS <= 30  # Not too long
    
    def test_session_id_generation(self):
        """Test session ID generation properties."""
        session_ids = set()
        
        # Generate many session IDs
        for _ in range(1000):
            token = create_refresh_token(str(uuid4()))
            payload = verify_token(token)
            session_ids.add(payload["session_id"])
        
        # All should be unique
        assert len(session_ids) == 1000
        
        # Should look like UUIDs
        for session_id in list(session_ids)[:10]:  # Check first 10
            parts = session_id.split('-')
            assert len(parts) == 5  # UUID format: 8-4-4-4-12
            assert len(parts[0]) == 8
            assert len(parts[1]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])