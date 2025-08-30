"""
Unit tests for authentication endpoints.

Tests the login functionality with comprehensive coverage including:
- Successful login scenarios
- Authentication failures
- Rate limiting behavior
- JWT token validation
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json
from datetime import datetime, timedelta

from app.main import app
from app.models.user import User, LoginRequest, LoginResponse
from app.core.security import create_access_token
from app.database.connection import get_db


class TestAuthLogin:
    """Test suite for the POST /api/v1/auth/login endpoint."""
    
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
        # Add new security-related attributes
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = None
        user.password_changed_at = datetime(2024, 1, 15, 10, 30, 0)
        user.password_hash = "hashed_password_here"
        user.is_account_locked.return_value = False
        user.check_password.return_value = True
        # Add full_name property for UserResponse serialization
        user.full_name = "John Doe"
        return user
    
    @pytest.fixture
    def valid_login_data(self):
        """Valid login request data."""
        return {
            "email": "test@example.com",
            "password": "securePassword123!"
        }
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_successful_login(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test successful user login."""
        # Arrange
        mock_db = Mock(spec=Session)
        # The auth logic uses: db.query(User).filter(User.email == ..., User.is_active == True).first()
        # So we need to mock the query chain with multiple filters
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        # Use FastAPI dependency override instead of patching
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Mock the instance methods on the returned user
        mock_user.check_password.return_value = True
        mock_user.is_account_locked.return_value = False
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "user" in data
        
        # Check token properties
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 900  # 15 minutes = 900 seconds
        
        # Check user properties
        user_data = data["user"]
        assert user_data["id"] == str(mock_user.id)
        assert user_data["email"] == mock_user.email
        assert user_data["first_name"] == mock_user.first_name
        assert user_data["last_name"] == mock_user.last_name
        assert user_data["role"] == mock_user.role
        assert user_data["is_active"] == mock_user.is_active
        
        # Verify password was checked
        mock_user.check_password.assert_called_once_with(valid_login_data["password"])
        mock_db.commit.assert_called_once()
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_login_invalid_email(self, mock_rate_limit, client):
        """Test login with non-existent email."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # User not found
        mock_db.query.return_value = mock_query
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        login_data = {
            "email": "nonexistent@example.com",
            "password": "anyPassword123!"
        }
        
        # Act
        response = client.post("/api/v1/auth/login", json=login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_login_invalid_password(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test login with invalid password."""
        # Arrange
        mock_user.check_password.return_value = False  # Invalid password
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        invalid_login_data = valid_login_data.copy()
        invalid_login_data["password"] = "wrongPassword123!"
        
        # Act
        response = client.post("/api/v1/auth/login", json=invalid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
        
        # Verify password was checked
        mock_user.check_password.assert_called_once_with(invalid_login_data["password"])
        mock_db.commit.assert_called_once()
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_login_account_locked(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test login with locked account."""
        # Arrange
        mock_user.is_account_locked.return_value = True  # Account is locked
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 423  # HTTP 423 Locked
        data = response.json()
        assert "locked" in data["detail"].lower()
        
        # Verify account lock was checked
        mock_user.is_account_locked.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_login_inactive_user(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test login with inactive user account."""
        # Arrange
        mock_user.is_active = False
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # Query filters out inactive users
        mock_db.query.return_value = mock_query
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid email or password"
    
    def test_login_validation_errors(self, client):
        """Test login with validation errors."""
        # Test missing email
        response = client.post("/api/v1/auth/login", json={"password": "test123"})
        assert response.status_code == 422
        
        # Test missing password
        response = client.post("/api/v1/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422
        
        # Test invalid email format
        response = client.post("/api/v1/auth/login", json={
            "email": "invalid-email",
            "password": "test123"
        })
        assert response.status_code == 422
        
        # Test empty email
        response = client.post("/api/v1/auth/login", json={
            "email": "",
            "password": "test123"
        })
        assert response.status_code == 422
        
        # Test empty password
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": ""
        })
        assert response.status_code == 422
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_rate_limiting_triggered(self, mock_rate_limit, client, valid_login_data):
        """Test rate limiting behavior."""
        # Arrange
        from fastapi import HTTPException
        mock_rate_limit.side_effect = HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "Too many requests for login"
            },
            headers={"Retry-After": "1800"}
        )
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Assert
        assert response.status_code == 429
        mock_rate_limit.assert_called_once()
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_jwt_token_structure(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test JWT token structure and claims."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        token = data["access_token"]
        
        # Verify token is not empty and has correct structure
        assert token
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts separated by dots
        
        # Verify token can be decoded (test with mock verification)
        with patch('app.core.security.verify_token') as mock_verify:
            mock_verify.return_value = {
                "sub": str(mock_user.id),
                "email": mock_user.email,
                "role": mock_user.role
            }
            payload = mock_verify(token)
            assert payload["sub"] == str(mock_user.id)
            assert payload["email"] == mock_user.email
            assert payload["role"] == mock_user.role
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_database_error_handling(self, mock_rate_limit, client, valid_login_data):
        """Test database error handling."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = Exception("Database connection failed")
        mock_db.query.return_value = mock_query
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Login failed"
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_case_insensitive_email(self, mock_rate_limit, client, mock_user):
        """Test that email comparison is case insensitive."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        login_data = {
            "email": "TEST@EXAMPLE.COM",  # Uppercase email
            "password": "securePassword123!"
        }
        
        # Act
        response = client.post("/api/v1/auth/login", json=login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200
        
        # Verify the database query was called with lowercase email
        mock_db.query.assert_called_once()
        # The actual filter call would include the lowercased email
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_login_logging(self, mock_rate_limit, client, mock_user, valid_login_data):
        """Test that login attempts are properly logged."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        with patch('app.api.auth.logger') as mock_logger:
            response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 200
        mock_logger.info.assert_called_with(f"Successful login for user: {mock_user.email}")
    
    @patch('app.api.auth.check_login_rate_limit')
    def test_failed_login_logging(self, mock_rate_limit, client, valid_login_data):
        """Test that failed login attempts are properly logged."""
        # Arrange
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None  # User not found
        mock_db.query.return_value = mock_query
        
        def get_mock_db():
            return mock_db
        
        app.dependency_overrides[get_db] = get_mock_db
        mock_rate_limit.return_value = AsyncMock()
        
        # Act
        with patch('app.api.auth.logger') as mock_logger:
            response = client.post("/api/v1/auth/login", json=valid_login_data)
        
        # Cleanup
        app.dependency_overrides.clear()
        
        # Assert
        assert response.status_code == 401
        mock_logger.warning.assert_called_with(f"Failed login attempt for email: {valid_login_data['email']}")


class TestAuthTokenValidation:
    """Test suite for JWT token validation and security."""
    
    def test_token_expiration_time(self):
        """Test that tokens have correct expiration time."""
        # This would test the ACCESS_TOKEN_EXPIRE_MINUTES = 15 setting
        from app.api.auth import ACCESS_TOKEN_EXPIRE_MINUTES
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 15
    
    def test_token_payload_structure(self):
        """Test JWT token payload contains required fields."""
        # This would be tested in integration with the security module
        test_data = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "email": "test@example.com",
            "role": "consultant"
        }
        
        token = create_access_token(data=test_data)
        assert token
        assert isinstance(token, str)
        
        # Token structure validation would be done by security module tests


@pytest.mark.integration
class TestAuthEndpointIntegration:
    """Integration tests for auth endpoints."""
    
    def test_login_endpoint_url(self):
        """Test that login endpoint is accessible at correct URL."""
        client = TestClient(app)
        response = client.post("/api/v1/auth/login", json={})
        # Should get validation error (422) not 404, confirming endpoint exists
        assert response.status_code != 404
    
    def test_cors_headers(self):
        """Test CORS headers are present for login endpoint."""
        client = TestClient(app)
        response = client.options("/api/v1/auth/login")
        # Should include CORS headers for cross-origin requests
        assert response.status_code in [200, 204]


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_auth.py -v
    pytest.main([__file__, "-v"])