"""
Unit tests for logout functionality.

Tests the logout endpoint with comprehensive coverage including:
- Successful logout scenarios
- Token blacklisting behavior
- Authentication validation
- Redis integration
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime

from app.main import app
from app.models.user import User
from app.database.connection import get_db
from app.api.auth import get_current_user


class TestAuthLogout:
    """Test suite for the POST /api/v1/auth/logout endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = "550e8400-e29b-41d4-a716-446655440000"
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.role = "consultant"
        user.is_active = True
        user.email_verified = True
        user.created_at = datetime(2024, 1, 15, 10, 30, 0)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime(2024, 1, 15, 10, 30, 0)
        user.password_changed_at = datetime(2024, 1, 15, 10, 30, 0)
        user.is_account_locked.return_value = False
        user.full_name = "John Doe"
        return user
    
    @pytest.fixture
    def valid_token(self):
        """Valid JWT token for testing."""
        return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"
    
    @pytest.fixture
    def mock_credentials(self, valid_token):
        """Mock HTTP authorization credentials."""
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = valid_token
        return credentials
    
    @patch('app.api.auth.blacklist_token')
    @patch('app.api.auth.initialize_redis_for_tokens')
    def test_successful_logout(self, mock_init_redis, mock_blacklist_token, 
                              client, mock_user, valid_token):
        """Test successful user logout."""
        # Arrange
        def get_mock_current_user():
            return mock_user
        
        app.dependency_overrides[get_current_user] = get_mock_current_user
        mock_init_redis.return_value = AsyncMock()
        mock_blacklist_token.return_value = True
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"
        
        # Verify Redis was initialized and token was blacklisted
        mock_init_redis.assert_called_once()
        mock_blacklist_token.assert_called_once_with(valid_token)
    
    @patch('app.api.auth.blacklist_token')
    @patch('app.api.auth.initialize_redis_for_tokens')
    def test_logout_with_blacklist_failure(self, mock_init_redis, 
                                          mock_blacklist_token, client, mock_user, valid_token):
        """Test logout when token blacklisting fails."""
        # Arrange
        def get_mock_current_user():
            return mock_user
        
        app.dependency_overrides[get_current_user] = get_mock_current_user
        mock_init_redis.return_value = AsyncMock()
        mock_blacklist_token.return_value = False  # Blacklisting fails
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200  # Still returns success for security
        data = response.json()
        assert data["message"] == "Successfully logged out"
        
        # Verify blacklisting was attempted
        mock_blacklist_token.assert_called_once_with(valid_token)
    
    def test_logout_without_authentication(self, client):
        """Test logout without valid authentication."""
        # Act - Try to logout without token
        response = client.post("/api/v1/auth/logout")
        
        # Assert
        assert response.status_code == 403  # Forbidden (missing auth header)
    
    @patch('app.api.auth.blacklist_token')
    @patch('app.api.auth.initialize_redis_for_tokens')
    def test_logout_with_invalid_token_format(self, mock_init_redis, 
                                            mock_blacklist_token, client, mock_user):
        """Test logout with malformed token."""
        # Arrange
        def get_mock_current_user():
            return mock_user
        
        app.dependency_overrides[get_current_user] = get_mock_current_user
        mock_init_redis.return_value = AsyncMock()
        mock_blacklist_token.return_value = True
        
        invalid_token = "invalid_token_format"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200  # Should still succeed
        data = response.json()
        assert data["message"] == "Successfully logged out"
        
        # Verify blacklisting was attempted with the invalid token
        mock_blacklist_token.assert_called_once_with(invalid_token)
    
    @patch('app.api.auth.blacklist_token')
    @patch('app.api.auth.initialize_redis_for_tokens')
    def test_logout_with_exception_handling(self, mock_init_redis, 
                                          mock_blacklist_token, client, mock_user, valid_token):
        """Test logout error handling."""
        # Arrange
        def get_mock_current_user():
            return mock_user
        
        app.dependency_overrides[get_current_user] = get_mock_current_user
        mock_init_redis.return_value = AsyncMock()
        mock_blacklist_token.side_effect = Exception("Redis connection error")
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=headers)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 500  # Internal server error
        data = response.json()
        assert data["detail"] == "Logout failed"
    
    @patch('app.api.auth.is_token_blacklisted')
    @patch('app.api.auth.get_current_user')
    def test_get_current_user_with_blacklisted_token(self, mock_get_current_user_original, 
                                                   mock_is_blacklisted, client, valid_token):
        """Test that blacklisted tokens are rejected in get_current_user dependency."""
        # Arrange
        mock_is_blacklisted.return_value = True  # Token is blacklisted
        
        headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Act - Try to access a protected endpoint after logout
        response = client.get("/api/v1/auth/me", headers=headers)
        
        # Assert
        assert response.status_code == 401  # Should be unauthorized
        
        # Verify blacklist check was performed
        mock_is_blacklisted.assert_called_once_with(valid_token)
    
    def test_logout_endpoint_requires_authentication(self, client):
        """Test that logout endpoint requires authentication."""
        # Act - Try to logout without token
        response = client.post("/api/v1/auth/logout")
        
        # Assert
        assert response.status_code == 403  # Forbidden (no auth header)
        assert "detail" in response.json()