"""
Test fixtures and mock data for auth feature tests.
Provides reusable test data, mocks, and utilities for auth testing.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from unittest.mock import Mock, AsyncMock
import pytest

from database.models.auth import User, RefreshToken
from app.features.auth.schemas import LoginRequest, UserResponse, LoginResponse
from app.core.datetime_utils import utc_now


class MockAuthData:
    """Container for mock auth-related test data."""
    
    # Test user data
    VALID_USER_DATA = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com", 
        "first_name": "John",
        "last_name": "Doe",
        "role": "consultant",
        "is_active": True,
        "email_verified": True,
        "password_hash": "$2b$12$example.hash.here",
        "created_at": datetime(2024, 1, 15, 10, 30, 0),
        "updated_at": datetime(2024, 1, 15, 10, 30, 0),
        "last_login_at": None,
        "failed_login_attempts": 0,
        "locked_until": None,
        "password_changed_at": datetime(2024, 1, 15, 10, 30, 0)
    }
    
    ADMIN_USER_DATA = {
        **VALID_USER_DATA,
        "id": "admin-550e-8400-e29b-41d4a716446655440000",
        "email": "admin@example.com",
        "role": "admin",
        "first_name": "Admin",
        "last_name": "User"
    }
    
    INACTIVE_USER_DATA = {
        **VALID_USER_DATA,
        "id": "inactive-550e-8400-e29b-41d4a716446655440000", 
        "email": "inactive@example.com",
        "is_active": False,
        "first_name": "Inactive",
        "last_name": "User"
    }
    
    LOCKED_USER_DATA = {
        **VALID_USER_DATA,
        "id": "locked-550e-8400-e29b-41d4a716446655440000",
        "email": "locked@example.com", 
        "failed_login_attempts": 5,
        "locked_until": utc_now() + timedelta(minutes=15),
        "first_name": "Locked",
        "last_name": "User"
    }
    
    # Login request data
    VALID_LOGIN_REQUEST = {
        "email": "test@example.com",
        "password": "TestPassword123!"
    }
    
    INVALID_LOGIN_REQUEST = {
        "email": "test@example.com", 
        "password": "WrongPassword"
    }
    
    NONEXISTENT_USER_LOGIN = {
        "email": "nonexistent@example.com",
        "password": "TestPassword123!"
    }
    
    # Refresh token data
    VALID_REFRESH_TOKEN_DATA = {
        "id": "token-550e-8400-e29b-41d4a716446655440000",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "token": "valid.refresh.token.here",
        "session_id": "session-550e-8400-e29b-41d4a716446655440000",
        "device_info": "Mozilla/5.0 Test Browser",
        "ip_address": "192.168.1.100",
        "status": "active",
        "created_at": utc_now() - timedelta(hours=1),
        "updated_at": utc_now() - timedelta(minutes=30),
        "last_used_at": utc_now() - timedelta(minutes=5),
        "expires_at": utc_now() + timedelta(days=6)
    }
    
    EXPIRED_REFRESH_TOKEN_DATA = {
        **VALID_REFRESH_TOKEN_DATA,
        "id": "expired-token-550e-8400-e29b-41d4a716446655440000",
        "token": "expired.refresh.token.here", 
        "expires_at": utc_now() - timedelta(days=1),
        "status": "expired"
    }
    
    # Expected response data
    EXPECTED_LOGIN_RESPONSE = {
        "access_token": "mock.jwt.access.token",
        "refresh_token": "mock.jwt.refresh.token",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": VALID_USER_DATA["id"],
            "email": VALID_USER_DATA["email"],
            "first_name": VALID_USER_DATA["first_name"],
            "last_name": VALID_USER_DATA["last_name"],
            "role": VALID_USER_DATA["role"],
            "is_active": VALID_USER_DATA["is_active"],
            "email_verified": VALID_USER_DATA["email_verified"],
            "created_at": VALID_USER_DATA["created_at"]
        }
    }


class MockAuthComponents:
    """Factory for creating mock auth components."""
    
    @staticmethod
    def create_mock_user(user_data: Optional[Dict] = None) -> Mock:
        """Create a mock User object with realistic behavior."""
        data = user_data or MockAuthData.VALID_USER_DATA.copy()
        
        user = Mock(spec=User)
        for key, value in data.items():
            setattr(user, key, value)
        
        # Add realistic method behaviors
        user.check_password = Mock(return_value=True)
        user.is_account_locked = Mock(return_value=False)
        user.set_password = Mock()
        user.unlock_account = Mock()
        user.is_admin = Mock(return_value=data.get("role") == "admin")
        
        return user
    
    @staticmethod
    def create_mock_refresh_token(token_data: Optional[Dict] = None) -> Mock:
        """Create a mock RefreshToken object."""
        data = token_data or MockAuthData.VALID_REFRESH_TOKEN_DATA.copy()
        
        token = Mock(spec=RefreshToken)
        for key, value in data.items():
            setattr(token, key, value)
        
        # Add realistic method behaviors
        token.is_active = Mock(return_value=data.get("status") == "active")
        token.verify_token = Mock(return_value=True)
        token.rotate_token = Mock()
        token.revoke = Mock()
        
        return token
    
    @staticmethod 
    def create_mock_repository(user_data: Optional[Dict] = None) -> Mock:
        """Create a mock repository with async methods."""
        mock_repo = Mock()
        
        # Create mock user for repository responses
        mock_user = MockAuthComponents.create_mock_user(user_data)
        
        # Mock repository methods
        mock_repo.get_by_email = AsyncMock(return_value=mock_user)
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_repo.create = AsyncMock(return_value=mock_user)
        mock_repo.update = AsyncMock(return_value=mock_user)
        mock_repo.delete = AsyncMock(return_value=True)
        mock_repo.commit = AsyncMock()
        mock_repo.rollback = AsyncMock()
        
        return mock_repo
    
    @staticmethod
    def create_mock_token_repository() -> Mock:
        """Create a mock refresh token repository."""
        mock_repo = Mock()
        mock_token = MockAuthComponents.create_mock_refresh_token()
        
        mock_repo.create = AsyncMock(return_value=mock_token)
        mock_repo.get_by_session = AsyncMock(return_value=mock_token)
        mock_repo.get_user_tokens = AsyncMock(return_value=[mock_token])
        mock_repo.update = AsyncMock(return_value=mock_token)
        mock_repo.delete = AsyncMock(return_value=True)
        mock_repo.commit = AsyncMock()
        mock_repo.rollback = AsyncMock()
        mock_repo.cleanup_expired = AsyncMock(return_value=5)
        
        return mock_repo


class AuthTestScenarios:
    """Pre-defined test scenarios for common auth testing patterns."""
    
    # Login scenarios
    SUCCESSFUL_LOGIN = {
        "name": "successful_login",
        "user_data": MockAuthData.VALID_USER_DATA,
        "login_request": MockAuthData.VALID_LOGIN_REQUEST,
        "expected_success": True,
        "expected_error": None
    }
    
    INVALID_PASSWORD = {
        "name": "invalid_password",
        "user_data": MockAuthData.VALID_USER_DATA,
        "login_request": MockAuthData.INVALID_LOGIN_REQUEST,
        "expected_success": False,
        "expected_error": "Invalid email or password"
    }
    
    NONEXISTENT_USER = {
        "name": "nonexistent_user",
        "user_data": None,  # No user found
        "login_request": MockAuthData.NONEXISTENT_USER_LOGIN,
        "expected_success": False,
        "expected_error": "Invalid email or password"
    }
    
    INACTIVE_USER_LOGIN = {
        "name": "inactive_user",
        "user_data": MockAuthData.INACTIVE_USER_DATA,
        "login_request": {"email": "inactive@example.com", "password": "TestPassword123!"},
        "expected_success": False,
        "expected_error": "Account is deactivated"
    }
    
    LOCKED_USER_LOGIN = {
        "name": "locked_user",
        "user_data": MockAuthData.LOCKED_USER_DATA,
        "login_request": {"email": "locked@example.com", "password": "TestPassword123!"},
        "expected_success": False,
        "expected_error": "Account is temporarily locked"
    }
    
    @classmethod
    def get_all_login_scenarios(cls) -> List[Dict]:
        """Get all login test scenarios."""
        return [
            cls.SUCCESSFUL_LOGIN,
            cls.INVALID_PASSWORD,
            cls.NONEXISTENT_USER,
            cls.INACTIVE_USER_LOGIN,
            cls.LOCKED_USER_LOGIN
        ]


# Pytest fixtures for reuse across tests
@pytest.fixture
def mock_user():
    """Fixture providing a standard mock user."""
    return MockAuthComponents.create_mock_user()

@pytest.fixture
def admin_user():
    """Fixture providing a mock admin user.""" 
    return MockAuthComponents.create_mock_user(MockAuthData.ADMIN_USER_DATA)

@pytest.fixture
def inactive_user():
    """Fixture providing a mock inactive user."""
    return MockAuthComponents.create_mock_user(MockAuthData.INACTIVE_USER_DATA)

@pytest.fixture
def locked_user():
    """Fixture providing a mock locked user."""
    return MockAuthComponents.create_mock_user(MockAuthData.LOCKED_USER_DATA)

@pytest.fixture
def mock_refresh_token():
    """Fixture providing a mock refresh token."""
    return MockAuthComponents.create_mock_refresh_token()

@pytest.fixture
def mock_user_repository():
    """Fixture providing a mock user repository."""
    return MockAuthComponents.create_mock_repository()

@pytest.fixture
def mock_token_repository():
    """Fixture providing a mock token repository."""
    return MockAuthComponents.create_mock_token_repository()

@pytest.fixture
def login_scenarios():
    """Fixture providing all login test scenarios."""
    return AuthTestScenarios.get_all_login_scenarios()

@pytest.fixture
def valid_login_request():
    """Fixture providing a valid login request."""
    return LoginRequest(**MockAuthData.VALID_LOGIN_REQUEST)

@pytest.fixture
def invalid_login_request():
    """Fixture providing an invalid login request."""
    return LoginRequest(**MockAuthData.INVALID_LOGIN_REQUEST)