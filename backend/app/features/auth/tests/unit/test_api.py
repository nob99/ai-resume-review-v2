"""
Unit tests for Auth API endpoints.
Tests the FastAPI route handlers in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from datetime import datetime, timedelta
from uuid import UUID

from app.main import app
from app.features.auth.service import AuthService
from app.features.auth.schemas import LoginRequest, LoginResponse, UserResponse
from app.features.auth.tests.fixtures.mock_data import (
    MockAuthData,
    MockAuthComponents,
    AuthTestScenarios
)


class TestAuthAPILogin:
    """Test suite for POST /api/v1/auth/login endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled and mocked dependencies."""
        from app.main import app as main_app
        
        # Create mock async session
        mock_session = AsyncMock()
        
        # Create mock auth service
        self.mock_auth_service = Mock(spec=AuthService)
        self.mock_auth_service.login = AsyncMock()
        self.mock_auth_service.logout = AsyncMock()
        self.mock_auth_service.register = AsyncMock()
        self.mock_auth_service.refresh_token = AsyncMock()
        self.mock_auth_service.change_password = AsyncMock()
        self.mock_auth_service.get_user_sessions = AsyncMock()
        self.mock_auth_service.revoke_session = AsyncMock()
        
        def mock_get_async_session():
            return mock_session
            
        def mock_get_auth_service():
            return self.mock_auth_service
        
        # Override dependencies
        from app.core.database import get_async_session
        from app.features.auth.api import get_auth_service
        main_app.dependency_overrides[get_async_session] = mock_get_async_session
        main_app.dependency_overrides[get_auth_service] = mock_get_auth_service
        
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            client = TestClient(main_app)
            yield client
        
        # Clean up overrides after test
        main_app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_auth_service(self):
        """Create mock AuthService."""
        service = Mock()
        service.login = AsyncMock()
        return service
    
    def test_login_endpoint_exists(self, client):
        """Test that login endpoint is accessible."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        # Should not return 404, even if it fails authentication
        assert response.status_code != 404
    
    def test_successful_login(self, client):
        """Test successful login with valid credentials."""
        # Arrange
        mock_login_response = LoginResponse(
            access_token="mock.access.token",
            refresh_token="mock.refresh.token",
            token_type="bearer",
            expires_in=1800,
            user=UserResponse(**MockAuthData.EXPECTED_LOGIN_RESPONSE["user"])
        )
        self.mock_auth_service.login.return_value = mock_login_response
        
        login_data = MockAuthData.VALID_LOGIN_REQUEST
        
        # Act
        response = client.post("/api/v1/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        
        assert response_data["access_token"] == "mock.access.token"
        assert response_data["refresh_token"] == "mock.refresh.token"
        assert response_data["token_type"] == "bearer"
        assert response_data["expires_in"] == 1800
        assert response_data["user"]["email"] == login_data["email"]
        
        # Verify service was called
        self.mock_auth_service.login.assert_called_once()
    
    @patch('app.features.auth.api.AuthService')
    def test_login_invalid_credentials(self, MockAuthService, client):
        """Test login with invalid credentials."""
        # Arrange
        from app.core.security import SecurityError
        
        mock_service = Mock()
        mock_service.login.side_effect = SecurityError("Invalid email or password")
        MockAuthService.return_value = mock_service
        
        login_data = MockAuthData.INVALID_LOGIN_REQUEST
        
        # Act
        response = client.post("/api/v1/auth/login", json=login_data)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert response_data["detail"] == "Invalid email or password"
    
    def test_login_missing_email(self, client):
        """Test login with missing email field."""
        # Act
        response = client.post("/api/v1/auth/login", json={
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        # Should indicate missing email field
        assert any("email" in str(error).lower() for error in response_data["detail"])
    
    def test_login_missing_password(self, client):
        """Test login with missing password field."""
        # Act
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        # Should indicate missing password field
        assert any("password" in str(error).lower() for error in response_data["detail"])
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        # Act
        response = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
    
    def test_login_empty_request_body(self, client):
        """Test login with empty request body."""
        # Act
        response = client.post("/api/v1/auth/login", json={})
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.features.auth.api.check_rate_limit_middleware')
    @patch('app.features.auth.api.AuthService')
    def test_login_rate_limiting(self, MockAuthService, mock_rate_limit, client):
        """Test that rate limiting is applied to login attempts."""
        # Arrange
        from app.core.rate_limiter import RateLimitExceeded
        mock_rate_limit.side_effect = RateLimitExceeded("Rate limit exceeded")
        
        # Act
        response = client.post("/api/v1/auth/login", json=MockAuthData.VALID_LOGIN_REQUEST)
        
        # Assert
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        mock_rate_limit.assert_called_once()
        # AuthService should not be called if rate limited
        MockAuthService.assert_not_called()


class TestAuthAPILogout:
    """Test suite for POST /api/v1/auth/logout endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authorization headers with mock token."""
        return {"Authorization": "Bearer mock.jwt.token"}
    
    def test_logout_requires_authentication(self, client):
        """Test that logout requires authentication."""
        # Act - no auth header
        response = client.post("/api/v1/auth/logout")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_logout_invalid_token_format(self, client):
        """Test logout with invalid token format."""
        # Act
        response = client.post("/api/v1/auth/logout", headers={
            "Authorization": "Invalid Token Format"
        })
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.features.auth.api.get_current_user')
    @patch('app.features.auth.api.AuthService')
    def test_successful_logout(self, MockAuthService, mock_get_user, client, auth_headers):
        """Test successful logout."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.logout.return_value = {"message": "Successfully logged out"}
        MockAuthService.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["message"] == "Successfully logged out"
        
        mock_service.logout.assert_called_once()
    
    @patch('app.features.auth.api.get_current_user')
    def test_logout_with_blacklisted_token(self, mock_get_user, client, auth_headers):
        """Test logout when token is already blacklisted."""
        # Arrange
        from fastapi import HTTPException
        mock_get_user.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        
        # Act
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthAPIRegistration:
    """Test suite for POST /api/v1/auth/register endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @pytest.fixture
    def valid_registration_data(self):
        """Create valid registration data."""
        return {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "first_name": "New",
            "last_name": "User",
            "role": "consultant"
        }
    
    @patch('app.features.auth.api.AuthService')
    def test_successful_registration(self, MockAuthService, client, valid_registration_data):
        """Test successful user registration."""
        # Arrange
        mock_service = Mock()
        mock_user_response = UserResponse(
            id=str(UUID("550e8400-e29b-41d4-a716-446655440000")),
            email=valid_registration_data["email"],
            first_name=valid_registration_data["first_name"],
            last_name=valid_registration_data["last_name"],
            role=valid_registration_data["role"],
            is_active=True,
            email_verified=False,
            created_at=datetime.now()
        )
        mock_service.register_user.return_value = mock_user_response
        MockAuthService.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/auth/register", json=valid_registration_data)
        
        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["email"] == valid_registration_data["email"]
        assert response_data["first_name"] == valid_registration_data["first_name"]
        assert response_data["is_active"] is True
        
        mock_service.register_user.assert_called_once()
    
    @patch('app.features.auth.api.AuthService')
    def test_registration_duplicate_email(self, MockAuthService, client, valid_registration_data):
        """Test registration with existing email."""
        # Arrange
        from app.core.security import SecurityError
        
        mock_service = Mock()
        mock_service.register_user.side_effect = SecurityError("Email already registered")
        MockAuthService.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/auth/register", json=valid_registration_data)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["detail"] == "Email already registered"
    
    def test_registration_weak_password(self, client, valid_registration_data):
        """Test registration with weak password."""
        # Arrange
        weak_password_data = {**valid_registration_data, "password": "weak"}
        
        # Act
        response = client.post("/api/v1/auth/register", json=weak_password_data)
        
        # Assert
        # Should either fail validation or be handled by service layer
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_registration_invalid_email(self, client, valid_registration_data):
        """Test registration with invalid email format."""
        # Arrange
        invalid_email_data = {**valid_registration_data, "email": "not-an-email"}
        
        # Act
        response = client.post("/api/v1/auth/register", json=invalid_email_data)
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_registration_missing_required_fields(self, client):
        """Test registration with missing required fields."""
        # Act
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com"
            # Missing password, first_name, last_name, role
        })
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        
        # Should mention missing required fields
        required_fields = ["password", "first_name", "last_name", "role"]
        error_text = str(response_data["detail"]).lower()
        missing_fields = [field for field in required_fields if field in error_text]
        assert len(missing_fields) > 0


class TestAuthAPITokenRefresh:
    """Test suite for POST /api/v1/auth/refresh endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @patch('app.features.auth.api.AuthService')
    def test_successful_token_refresh(self, MockAuthService, client):
        """Test successful token refresh."""
        # Arrange
        mock_service = Mock()
        mock_refresh_response = {
            "access_token": "new.access.token",
            "refresh_token": "new.refresh.token",
            "token_type": "bearer",
            "expires_in": 1800
        }
        mock_service.refresh_token.return_value = mock_refresh_response
        MockAuthService.return_value = mock_service
        
        request_data = {"refresh_token": "valid.refresh.token"}
        
        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["access_token"] == "new.access.token"
        assert response_data["refresh_token"] == "new.refresh.token"
        
        mock_service.refresh_token.assert_called_once()
    
    @patch('app.features.auth.api.AuthService')
    def test_refresh_invalid_token(self, MockAuthService, client):
        """Test token refresh with invalid token."""
        # Arrange
        from app.core.security import SecurityError
        
        mock_service = Mock()
        mock_service.refresh_token.side_effect = SecurityError("Invalid refresh token")
        MockAuthService.return_value = mock_service
        
        request_data = {"refresh_token": "invalid.refresh.token"}
        
        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        response_data = response.json()
        assert response_data["detail"] == "Invalid refresh token"
    
    def test_refresh_missing_token(self, client):
        """Test token refresh without providing refresh token."""
        # Act
        response = client.post("/api/v1/auth/refresh", json={})
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data


class TestAuthAPIUserInfo:
    """Test suite for GET /api/v1/auth/me endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authorization headers with mock token."""
        return {"Authorization": "Bearer mock.jwt.token"}
    
    def test_get_user_info_requires_authentication(self, client):
        """Test that user info endpoint requires authentication."""
        # Act
        response = client.get("/api/v1/auth/me")
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.features.auth.api.get_current_user')
    def test_get_user_info_success(self, mock_get_user, client, auth_headers):
        """Test successful retrieval of user information."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_get_user.return_value = mock_user
        
        # Act
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["email"] == mock_user.email
        assert response_data["first_name"] == mock_user.first_name
        assert response_data["last_name"] == mock_user.last_name
        assert response_data["role"] == mock_user.role
    
    @patch('app.features.auth.api.get_current_user')
    def test_get_user_info_invalid_token(self, mock_get_user, client, auth_headers):
        """Test user info with invalid token."""
        # Arrange
        from fastapi import HTTPException
        mock_get_user.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
        
        # Act
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthAPIPasswordChange:
    """Test suite for POST /api/v1/auth/change-password endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client with feature flag enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authorization headers with mock token."""
        return {"Authorization": "Bearer mock.jwt.token"}
    
    @pytest.fixture
    def password_change_data(self):
        """Create valid password change data."""
        return {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!"
        }
    
    @patch('app.features.auth.api.get_current_user')
    @patch('app.features.auth.api.AuthService')
    def test_successful_password_change(self, MockAuthService, mock_get_user, client, auth_headers, password_change_data):
        """Test successful password change."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_get_user.return_value = mock_user
        
        mock_service = Mock()
        mock_service.change_password.return_value = {"message": "Password changed successfully"}
        MockAuthService.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/auth/change-password", 
                             json=password_change_data, 
                             headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["message"] == "Password changed successfully"
        
        mock_service.change_password.assert_called_once_with(
            mock_user.id,
            password_change_data["current_password"],
            password_change_data["new_password"]
        )
    
    def test_password_change_requires_authentication(self, client, password_change_data):
        """Test that password change requires authentication."""
        # Act
        response = client.post("/api/v1/auth/change-password", json=password_change_data)
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @patch('app.features.auth.api.get_current_user')
    @patch('app.features.auth.api.AuthService')
    def test_password_change_wrong_current_password(self, MockAuthService, mock_get_user, client, auth_headers, password_change_data):
        """Test password change with wrong current password."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_get_user.return_value = mock_user
        
        from app.core.security import SecurityError
        mock_service = Mock()
        mock_service.change_password.side_effect = SecurityError("Current password is incorrect")
        MockAuthService.return_value = mock_service
        
        # Act
        response = client.post("/api/v1/auth/change-password", 
                             json=password_change_data, 
                             headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert response_data["detail"] == "Current password is incorrect"