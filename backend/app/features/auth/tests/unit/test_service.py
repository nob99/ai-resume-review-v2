"""
Unit tests for AuthService.
Tests business logic in isolation with mocked dependencies.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import UUID

from app.features.auth.service import AuthService
from app.features.auth.schemas import LoginRequest, LoginResponse, TokenRefreshRequest
from app.core.security import SecurityError
from app.features.auth.tests.fixtures.mock_data import (
    MockAuthData, 
    MockAuthComponents,
    AuthTestScenarios
)


class TestAuthServiceLogin:
    """Test suite for AuthService.login method."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_successful_login(self, auth_service, mock_user_repository, mock_token_repository):
        """Test successful login with valid credentials."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_user.check_password.return_value = True
        mock_user_repository.get_by_email.return_value = mock_user
        mock_user_repository.update.return_value = mock_user
        
        mock_token = MockAuthComponents.create_mock_refresh_token()
        mock_token_repository.create.return_value = mock_token
        
        login_request = LoginRequest(**MockAuthData.VALID_LOGIN_REQUEST)
        client_ip = "192.168.1.100"
        user_agent = "Test Browser"
        
        with patch('app.features.auth.service.create_access_token') as mock_access_token, \
             patch('app.features.auth.service.create_refresh_token') as mock_refresh_token:
            
            mock_access_token.return_value = "mock.access.token"
            mock_refresh_token.return_value = "mock.refresh.token"
            
            # Act
            result = await auth_service.login(
                login_request=login_request,
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            # Assert
            assert isinstance(result, LoginResponse)
            assert result.access_token == "mock.access.token"
            assert result.refresh_token == "mock.refresh.token"
            assert result.token_type == "bearer"
            assert result.expires_in == 1800
            assert result.user.email == mock_user.email
            
            # Verify repository calls
            mock_user_repository.get_by_email.assert_called_once_with(login_request.email)
            mock_user.check_password.assert_called_once_with(login_request.password)
            mock_user_repository.update.assert_called_once()
            mock_token_repository.create.assert_called_once()
            mock_token_repository.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_service, mock_user_repository):
        """Test login with non-existent email."""
        # Arrange
        mock_user_repository.get_by_email.return_value = None
        login_request = LoginRequest(**MockAuthData.NONEXISTENT_USER_LOGIN)
        
        # Act & Assert
        with pytest.raises(SecurityError, match="Invalid email or password"):
            await auth_service.login(
                login_request=login_request,
                client_ip="192.168.1.100"
            )
        
        mock_user_repository.get_by_email.assert_called_once_with(login_request.email)
        # Should not try to create tokens or update user
        mock_user_repository.update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_service, mock_user_repository):
        """Test login with invalid password."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_user.check_password.return_value = False  # Password check fails
        mock_user_repository.get_by_email.return_value = mock_user
        
        login_request = LoginRequest(**MockAuthData.INVALID_LOGIN_REQUEST)
        
        # Act & Assert
        with pytest.raises(SecurityError, match="Invalid email or password"):
            await auth_service.login(
                login_request=login_request,
                client_ip="192.168.1.100"
            )
        
        mock_user.check_password.assert_called_once_with(login_request.password)
        # Should not create tokens
        mock_user_repository.update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, auth_service, mock_user_repository):
        """Test login with inactive user account."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user(MockAuthData.INACTIVE_USER_DATA)
        mock_user_repository.get_by_email.return_value = mock_user
        
        login_request = LoginRequest(
            email=MockAuthData.INACTIVE_USER_DATA["email"],
            password="TestPassword123!"
        )
        
        # Act & Assert
        with pytest.raises(SecurityError, match="Account is deactivated"):
            await auth_service.login(
                login_request=login_request,
                client_ip="192.168.1.100"
            )
        
        # Should not check password for inactive users
        mock_user.check_password.assert_not_called()
    
    @pytest.mark.parametrize("scenario", AuthTestScenarios.get_all_login_scenarios())
    @pytest.mark.asyncio
    async def test_login_scenarios(self, auth_service, mock_user_repository, mock_token_repository, scenario):
        """Test various login scenarios using parameterized data."""
        # Arrange
        if scenario["user_data"]:
            mock_user = MockAuthComponents.create_mock_user(scenario["user_data"])
            mock_user_repository.get_by_email.return_value = mock_user
            
            # Set up password check behavior
            if scenario["name"] == "invalid_password":
                mock_user.check_password.return_value = False
            else:
                mock_user.check_password.return_value = True
        else:
            mock_user_repository.get_by_email.return_value = None
        
        # Set up token repository for successful scenarios
        if scenario["expected_success"]:
            mock_token = MockAuthComponents.create_mock_refresh_token()
            mock_token_repository.create.return_value = mock_token
        
        login_request = LoginRequest(**scenario["login_request"])
        
        with patch('app.features.auth.service.create_access_token') as mock_access_token, \
             patch('app.features.auth.service.create_refresh_token') as mock_refresh_token:
            
            mock_access_token.return_value = "mock.access.token"
            mock_refresh_token.return_value = "mock.refresh.token"
            
            # Act & Assert
            if scenario["expected_success"]:
                result = await auth_service.login(
                    login_request=login_request,
                    client_ip="192.168.1.100"
                )
                assert isinstance(result, LoginResponse)
                assert result.access_token == "mock.access.token"
            else:
                with pytest.raises(SecurityError, match=scenario["expected_error"]):
                    await auth_service.login(
                        login_request=login_request,
                        client_ip="192.168.1.100"
                    )


class TestAuthServiceRefreshToken:
    """Test suite for AuthService.refresh_token method."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_successful_token_refresh(self, auth_service, mock_user_repository, mock_token_repository):
        """Test successful refresh token validation and new token generation."""
        # Arrange
        mock_user = MockAuthComponents.create_mock_user()
        mock_token = MockAuthComponents.create_mock_refresh_token()
        
        mock_user_repository.get_by_id.return_value = mock_user
        mock_token_repository.get_by_session.return_value = mock_token
        mock_token_repository.update.return_value = mock_token
        
        with patch('app.features.auth.service.create_access_token') as mock_access_token, \
             patch('app.features.auth.service.create_refresh_token') as mock_refresh_token, \
             patch('app.features.auth.service.verify_token') as mock_verify:
            
            mock_verify.return_value = {
                "user_id": str(mock_user.id),
                "session_id": mock_token.session_id,
                "type": "refresh"
            }
            mock_access_token.return_value = "new.access.token"
            mock_refresh_token.return_value = "new.refresh.token"
            
            # Act
            result = await auth_service.refresh_token(
                refresh_token_str="valid.refresh.token",
                client_ip="192.168.1.100"
            )
            
            # Assert
            assert result.access_token == "new.access.token"
            assert result.refresh_token == "new.refresh.token"
            assert result.token_type == "bearer"
            
            # Verify calls
            mock_verify.assert_called_once_with("valid.refresh.token")
            mock_token_repository.get_by_session.assert_called_once()
            mock_token_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, auth_service):
        """Test refresh with invalid token."""
        with patch('app.features.auth.service.verify_token') as mock_verify:
            mock_verify.return_value = None  # Invalid token
            
            with pytest.raises(SecurityError, match="Invalid refresh token"):
                await auth_service.refresh_token(
                    refresh_token_str="invalid.token",
                    client_ip="192.168.1.100"
                )


class TestAuthServiceLogout:
    """Test suite for AuthService.logout method."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_successful_logout(self, auth_service, mock_token_repository):
        """Test successful logout and token blacklisting."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        access_token = "valid.access.token"
        
        with patch('app.features.auth.service.blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = True
            
            # Act
            result = await auth_service.logout(user_id, access_token)
            
            # Assert
            assert result["message"] == "Successfully logged out"
            mock_blacklist.assert_called_once_with(access_token)
    
    @pytest.mark.asyncio
    async def test_logout_blacklist_failure(self, auth_service):
        """Test logout when token blacklisting fails."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        access_token = "valid.access.token"
        
        with patch('app.features.auth.service.blacklist_token') as mock_blacklist:
            mock_blacklist.return_value = False  # Blacklisting failed
            
            # Act
            result = await auth_service.logout(user_id, access_token)
            
            # Assert - should still return success for security
            assert result["message"] == "Successfully logged out"


class TestAuthServiceRegistration:
    """Test suite for AuthService.register_user method."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_successful_registration(self, auth_service, mock_user_repository):
        """Test successful user registration."""
        # Arrange
        from app.features.auth.schemas import UserCreate
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="NewPassword123!",
            first_name="New",
            last_name="User",
            role="consultant"
        )
        
        mock_user_repository.get_by_email.return_value = None  # User doesn't exist
        new_mock_user = MockAuthComponents.create_mock_user({
            **MockAuthData.VALID_USER_DATA,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name
        })
        mock_user_repository.create.return_value = new_mock_user
        
        # Act
        result = await auth_service.register_user(user_data)
        
        # Assert
        assert result.email == user_data.email
        assert result.first_name == user_data.first_name
        assert result.last_name == user_data.last_name
        
        mock_user_repository.get_by_email.assert_called_once_with(user_data.email)
        mock_user_repository.create.assert_called_once()
        mock_user_repository.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_registration_duplicate_email(self, auth_service, mock_user_repository):
        """Test registration with existing email."""
        # Arrange
        from app.features.auth.schemas import UserCreate
        
        user_data = UserCreate(
            email="existing@example.com",
            password="NewPassword123!",
            first_name="New",
            last_name="User",
            role="consultant"
        )
        
        # User already exists
        existing_user = MockAuthComponents.create_mock_user()
        mock_user_repository.get_by_email.return_value = existing_user
        
        # Act & Assert
        with pytest.raises(SecurityError, match="Email already registered"):
            await auth_service.register_user(user_data)
        
        # Should not try to create new user
        mock_user_repository.create.assert_not_called()


class TestAuthServicePasswordChange:
    """Test suite for AuthService.change_password method."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_successful_password_change(self, auth_service, mock_user_repository):
        """Test successful password change."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        current_password = "OldPassword123!"
        new_password = "NewPassword123!"
        
        mock_user = MockAuthComponents.create_mock_user()
        mock_user.check_password.return_value = True  # Current password is correct
        mock_user_repository.get_by_id.return_value = mock_user
        mock_user_repository.update.return_value = mock_user
        
        # Act
        result = await auth_service.change_password(user_id, current_password, new_password)
        
        # Assert
        assert result["message"] == "Password changed successfully"
        mock_user.check_password.assert_called_once_with(current_password)
        mock_user.set_password.assert_called_once_with(new_password)
        mock_user_repository.update.assert_called_once()
        mock_user_repository.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_password_change_wrong_current_password(self, auth_service, mock_user_repository):
        """Test password change with incorrect current password."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        current_password = "WrongPassword"
        new_password = "NewPassword123!"
        
        mock_user = MockAuthComponents.create_mock_user()
        mock_user.check_password.return_value = False  # Current password is wrong
        mock_user_repository.get_by_id.return_value = mock_user
        
        # Act & Assert
        with pytest.raises(SecurityError, match="Current password is incorrect"):
            await auth_service.change_password(user_id, current_password, new_password)
        
        # Should not update password
        mock_user.set_password.assert_not_called()
        mock_user_repository.update.assert_not_called()


class TestAuthServiceSessionManagement:
    """Test suite for AuthService session management methods."""
    
    @pytest.fixture
    def auth_service(self, mock_user_repository, mock_token_repository):
        """Create AuthService with mocked dependencies."""
        return AuthService(
            user_repository=mock_user_repository,
            token_repository=mock_token_repository
        )
    
    @pytest.mark.asyncio
    async def test_get_user_sessions(self, auth_service, mock_token_repository):
        """Test retrieving user sessions."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_tokens = [
            MockAuthComponents.create_mock_refresh_token(),
            MockAuthComponents.create_mock_refresh_token()
        ]
        mock_token_repository.get_user_tokens.return_value = mock_tokens
        
        # Act
        result = await auth_service.get_user_sessions(user_id)
        
        # Assert
        assert len(result.sessions) == 2
        assert result.total_sessions == 2
        mock_token_repository.get_user_tokens.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_revoke_session(self, auth_service, mock_token_repository):
        """Test revoking a specific session."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        session_id = "session-123"
        
        mock_token = MockAuthComponents.create_mock_refresh_token()
        mock_token_repository.get_by_session.return_value = mock_token
        
        # Act
        result = await auth_service.revoke_session(user_id, session_id)
        
        # Assert
        assert result is True
        mock_token.revoke.assert_called_once()
        mock_token_repository.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, auth_service, mock_token_repository):
        """Test cleaning up expired tokens."""
        # Arrange
        mock_token_repository.cleanup_expired.return_value = 10  # 10 tokens cleaned
        
        # Act
        result = await auth_service.cleanup_expired_tokens()
        
        # Assert
        assert result == 10
        mock_token_repository.cleanup_expired.assert_called_once()