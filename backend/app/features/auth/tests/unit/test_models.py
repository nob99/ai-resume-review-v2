"""
Unit tests for Auth models (User, RefreshToken).
Tests model behavior, validation, and business logic in isolation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.features.auth.models import User, RefreshToken, UserRole
from app.features.auth.tests.fixtures.mock_data import MockAuthData
from app.core.datetime_utils import utc_now
from app.core.security import SecurityError


class TestUserModel:
    """Test suite for User model."""
    
    @pytest.fixture
    def user_data(self):
        """Create valid user data for testing."""
        return {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "role": UserRole.CONSULTANT
        }
    
    def test_user_creation(self, user_data):
        """Test creating a user with valid data."""
        # Act
        user = User(**user_data)
        
        # Assert
        assert user.email == user_data["email"]
        assert user.first_name == user_data["first_name"]
        assert user.last_name == user_data["last_name"]
        assert user.role == user_data["role"]
        assert user.is_active is True  # Default value
        assert user.email_verified is False  # Default value
        assert user.failed_login_attempts == 0  # Default value
        assert user.locked_until is None  # Default value
        
        # Password should be hashed, not stored as plaintext
        assert user.password_hash != user_data["password"]
        assert len(user.password_hash) > 20  # Bcrypt hash is longer
        
        # Timestamps should be set
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.password_changed_at is not None
    
    def test_user_id_generation(self, user_data):
        """Test that user ID is automatically generated."""
        # Act
        user = User(**user_data)
        
        # Assert
        assert user.id is not None
        assert isinstance(user.id, UUID)
    
    def test_user_email_normalization(self, user_data):
        """Test that email is normalized to lowercase."""
        # Arrange
        user_data["email"] = "TEST@EXAMPLE.COM"
        
        # Act
        user = User(**user_data)
        
        # Assert
        assert user.email == "test@example.com"
    
    @pytest.mark.parametrize("role", [UserRole.CONSULTANT, UserRole.ADMIN])
    def test_user_role_validation(self, user_data, role):
        """Test that user roles are properly validated."""
        # Arrange
        user_data["role"] = role
        
        # Act
        user = User(**user_data)
        
        # Assert
        assert user.role == role
    
    def test_user_password_hashing(self, user_data):
        """Test that password is properly hashed on creation."""
        # Act
        user = User(**user_data)
        
        # Assert
        # Password hash should be bcrypt format
        assert user.password_hash.startswith("$2b$")
        assert user.password_hash != user_data["password"]
        
        # Should be able to verify the password
        assert user.check_password(user_data["password"]) is True
        assert user.check_password("wrong_password") is False
    
    def test_check_password_method(self, user_data):
        """Test password verification method."""
        # Arrange
        user = User(**user_data)
        
        # Act & Assert
        assert user.check_password(user_data["password"]) is True
        assert user.check_password("wrong_password") is False
        assert user.check_password("") is False
        assert user.check_password(None) is False
    
    def test_set_password_method(self, user_data):
        """Test password change method."""
        # Arrange
        user = User(**user_data)
        old_hash = user.password_hash
        new_password = "NewPassword123!"
        
        # Act
        user.set_password(new_password)
        
        # Assert
        assert user.password_hash != old_hash
        assert user.check_password(new_password) is True
        assert user.check_password(user_data["password"]) is False
        assert user.password_changed_at is not None
    
    def test_set_password_validation(self, user_data):
        """Test password validation in set_password method."""
        # Arrange
        user = User(**user_data)
        
        # Act & Assert - weak passwords should raise SecurityError
        with pytest.raises(SecurityError):
            user.set_password("weak")
        
        with pytest.raises(SecurityError):
            user.set_password("")
        
        with pytest.raises(SecurityError):
            user.set_password("12345678")  # No special chars, uppercase, etc.
    
    def test_is_admin_method(self, user_data):
        """Test admin role checking method."""
        # Test consultant user
        user_data["role"] = UserRole.CONSULTANT
        consultant = User(**user_data)
        assert consultant.is_admin() is False
        
        # Test admin user
        user_data["role"] = UserRole.ADMIN
        admin = User(**user_data)
        assert admin.is_admin() is True
    
    def test_account_locking_mechanism(self, user_data):
        """Test account locking after failed login attempts."""
        # Arrange
        user = User(**user_data)
        
        # Simulate failed login attempts
        for i in range(4):
            user.check_password("wrong_password")
            assert user.is_account_locked() is False
        
        # 5th failed attempt should lock the account
        user.check_password("wrong_password")
        assert user.is_account_locked() is True
        assert user.locked_until is not None
        assert user.failed_login_attempts == 5
    
    def test_unlock_account_method(self, user_data):
        """Test account unlocking method."""
        # Arrange
        user = User(**user_data)
        # Manually set account as locked
        user.failed_login_attempts = 5
        user.locked_until = utc_now() + timedelta(minutes=15)
        
        assert user.is_account_locked() is True
        
        # Act
        user.unlock_account()
        
        # Assert
        assert user.is_account_locked() is False
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_successful_login_resets_failed_attempts(self, user_data):
        """Test that successful login resets failed attempt counter."""
        # Arrange
        user = User(**user_data)
        user.failed_login_attempts = 3
        
        # Act - successful password check
        result = user.check_password(user_data["password"])
        
        # Assert
        assert result is True
        assert user.failed_login_attempts == 0
    
    def test_account_lock_expiration(self, user_data):
        """Test that account lock expires after timeout."""
        # Arrange
        user = User(**user_data)
        user.failed_login_attempts = 5
        user.locked_until = utc_now() - timedelta(minutes=1)  # Expired lock
        
        # Act & Assert
        assert user.is_account_locked() is False  # Should be unlocked due to expiration
    
    def test_update_last_login(self, user_data):
        """Test updating last login timestamp."""
        # Arrange
        user = User(**user_data)
        original_last_login = user.last_login_at
        
        # Act
        user.update_last_login()
        
        # Assert
        assert user.last_login_at != original_last_login
        assert user.last_login_at is not None
    
    def test_user_string_representation(self, user_data):
        """Test user string representation."""
        # Arrange
        user = User(**user_data)
        
        # Act
        str_repr = str(user)
        
        # Assert
        assert user_data["email"] in str_repr
        assert user_data["first_name"] in str_repr
        assert user_data["last_name"] in str_repr
    
    def test_user_repr(self, user_data):
        """Test user repr representation."""
        # Arrange
        user = User(**user_data)
        
        # Act
        repr_str = repr(user)
        
        # Assert
        assert "User" in repr_str
        assert str(user.id) in repr_str
        assert user_data["email"] in repr_str


class TestRefreshTokenModel:
    """Test suite for RefreshToken model."""
    
    @pytest.fixture
    def token_data(self):
        """Create valid refresh token data for testing."""
        return {
            "user_id": UUID("550e8400-e29b-41d4-a716-446655440000"),
            "token": "sample.refresh.token.here",
            "session_id": "session-550e-8400-e29b-41d4a716446655440000",
            "device_info": "Mozilla/5.0 Test Browser",
            "ip_address": "192.168.1.100"
        }
    
    def test_refresh_token_creation(self, token_data):
        """Test creating a refresh token with valid data."""
        # Act
        token = RefreshToken(**token_data)
        
        # Assert
        assert token.user_id == token_data["user_id"]
        assert token.token_hash is not None  # Token is hashed, not stored as plaintext
        assert token.token_hash != token_data["token"]  # Should be hashed, not original
        assert token.session_id == token_data["session_id"]
        assert token.device_info == token_data["device_info"]
        assert token.ip_address == token_data["ip_address"]
        
        # Default values
        assert token.status == "active"
        assert token.created_at is not None
        assert token.last_used_at is not None
        assert token.expires_at is not None
        
        # Should expire in 7 days by default
        expected_expiry = utc_now() + timedelta(days=7)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_refresh_token_id_generation(self, token_data):
        """Test that token ID is automatically generated."""
        # Act
        token = RefreshToken(**token_data)
        
        # Assert
        assert token.id is not None
        assert isinstance(token.id, UUID)
    
    def test_is_active_method(self, token_data):
        """Test token active status checking."""
        # Test active token
        token = RefreshToken(**token_data)
        assert token.is_active() is True
        
        # Test expired token
        token.expires_at = utc_now() - timedelta(days=1)
        assert token.is_active() is False
        
        # Test revoked token
        token.expires_at = utc_now() + timedelta(days=1)  # Not expired
        token.status = "revoked"
        assert token.is_active() is False
        
        # Test used token
        token.status = "used"
        assert token.is_active() is False
    
    def test_verify_token_method(self, token_data):
        """Test token verification method."""
        # Arrange
        token = RefreshToken(**token_data)
        
        # Act & Assert
        assert token.verify_token(token_data["token"]) is True
        assert token.verify_token("wrong.token") is False
        assert token.verify_token("") is False
        assert token.verify_token(None) is False
    
    def test_rotate_token_method(self, token_data):
        """Test token rotation for security."""
        # Arrange
        token = RefreshToken(**token_data)
        old_token = token.token
        new_token = "new.rotated.token.here"
        
        # Act
        token.rotate_token(new_token)
        
        # Assert
        assert token.token == new_token
        assert token.token != old_token
        assert token.last_used_at is not None
        # Updated timestamp should be recent
        time_diff = abs((utc_now() - token.updated_at).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_revoke_method(self, token_data):
        """Test token revocation method."""
        # Arrange
        token = RefreshToken(**token_data)
        assert token.is_active() is True
        
        # Act
        token.revoke()
        
        # Assert
        assert token.status == "revoked"
        assert token.is_active() is False
        # Updated timestamp should be recent
        time_diff = abs((utc_now() - token.updated_at).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_mark_as_used_method(self, token_data):
        """Test marking token as used."""
        # Arrange
        token = RefreshToken(**token_data)
        assert token.is_active() is True
        
        # Act
        token.mark_as_used()
        
        # Assert
        assert token.status == "used"
        assert token.is_active() is False
        assert token.last_used_at is not None
    
    def test_extend_expiry_method(self, token_data):
        """Test extending token expiry."""
        # Arrange
        token = RefreshToken(**token_data)
        original_expiry = token.expires_at
        
        # Act
        token.extend_expiry(days=3)
        
        # Assert
        assert token.expires_at > original_expiry
        expected_expiry = original_expiry + timedelta(days=3)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_refresh_token_string_representation(self, token_data):
        """Test refresh token string representation."""
        # Arrange
        token = RefreshToken(**token_data)
        
        # Act
        str_repr = str(token)
        
        # Assert
        assert token_data["session_id"] in str_repr
        assert str(token_data["user_id"]) in str_repr
        assert token.status in str_repr
    
    def test_refresh_token_repr(self, token_data):
        """Test refresh token repr representation."""
        # Arrange
        token = RefreshToken(**token_data)
        
        # Act
        repr_str = repr(token)
        
        # Assert
        assert "RefreshToken" in repr_str
        assert str(token.id) in repr_str
        assert token.session_id in repr_str
    
    def test_cleanup_expired_query_method(self):
        """Test method that would be used for cleanup queries."""
        # This tests the logic that would be used in repository cleanup
        # Create tokens with different statuses and expiry dates
        tokens = [
            RefreshToken(
                user_id=uuid4(),
                token=f"token{i}",
                session_id=f"session{i}",
                expires_at=utc_now() - timedelta(days=i)  # Varying expiry
            )
            for i in range(3)
        ]
        
        # Check which tokens should be cleaned up
        expired_tokens = [token for token in tokens if not token.is_active()]
        active_tokens = [token for token in tokens if token.is_active()]
        
        # Token 0 expires today (might be active), tokens 1&2 are expired
        assert len(expired_tokens) >= 2
        assert len(active_tokens) <= 1


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_user_invalid_email_format(self):
        """Test user creation with invalid email format."""
        # This would be handled at the Pydantic schema level in practice
        # But testing model robustness
        with pytest.raises((ValueError, SecurityError)):
            User(
                email="not-an-email",
                password="ValidPassword123!",
                first_name="John",
                last_name="Doe",
                role=UserRole.CONSULTANT
            )
    
    def test_user_empty_required_fields(self):
        """Test user creation with empty required fields."""
        with pytest.raises((ValueError, SecurityError)):
            User(
                email="",
                password="ValidPassword123!",
                first_name="John",
                last_name="Doe",
                role=UserRole.CONSULTANT
            )
        
        with pytest.raises((ValueError, SecurityError)):
            User(
                email="test@example.com",
                password="",
                first_name="John",
                last_name="Doe",
                role=UserRole.CONSULTANT
            )
    
    def test_refresh_token_invalid_user_id(self):
        """Test refresh token creation with invalid user ID."""
        with pytest.raises((ValueError, TypeError)):
            RefreshToken(
                user_id="not-a-uuid",
                token="sample.token",
                session_id="session-123"
            )
    
    def test_model_timestamp_consistency(self):
        """Test that model timestamps are consistent."""
        # Arrange
        user = User(
            email="test@example.com",
            password="ValidPassword123!",
            first_name="John",
            last_name="Doe",
            role=UserRole.CONSULTANT
        )
        
        # Act & Assert
        assert user.created_at <= user.updated_at
        assert user.created_at == user.password_changed_at
        
        # Test token timestamps
        token = RefreshToken(
            user_id=user.id,
            token="sample.token",
            session_id="session-123"
        )
        
        assert token.created_at <= token.updated_at
        assert token.created_at == token.last_used_at