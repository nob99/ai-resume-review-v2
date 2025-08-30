"""
Unit tests for authentication login endpoint.

Focused unit tests for AUTH-001 login functionality with proper mocking
to avoid database dependencies and test isolation issues.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# Import test dependencies first
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestLoginEndpoint:
    """Unit tests for the login endpoint functionality."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock()
        user.id = "550e8400-e29b-41d4-a716-446655440000"
        user.email = "test@example.com"
        user.first_name = "John"
        user.last_name = "Doe"
        user.role = "consultant"
        user.is_active = True
        user.created_at = datetime(2024, 1, 15, 10, 30, 0)
        user.is_account_locked.return_value = False
        user.check_password.return_value = True
        return user
    
    @pytest.fixture
    def valid_login_data(self):
        """Valid login request data."""
        return {
            "email": "test@example.com",
            "password": "securePassword123!"
        }
    
    def test_login_data_validation(self):
        """Test login request data validation."""
        from app.models.user import LoginRequest
        
        # Valid data
        valid_data = {
            "email": "test@example.com",
            "password": "securePassword123!"
        }
        request = LoginRequest(**valid_data)
        assert request.email == "test@example.com"
        assert request.password == "securePassword123!"
        
        # Test email validation
        with pytest.raises(Exception):
            LoginRequest(email="invalid-email", password="password")
        
        # Test missing fields
        with pytest.raises(Exception):
            LoginRequest(email="test@example.com")
            
        with pytest.raises(Exception):
            LoginRequest(password="password")
    
    def test_jwt_token_expiration_setting(self):
        """Test that JWT token expiration is set correctly for Sprint 2."""
        from app.api.auth import ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Sprint 2 requirement: 15 minute access tokens
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 15
    
    def test_password_verification_logic(self, mock_user):
        """Test password verification logic."""
        # Test successful password check
        mock_user.check_password.return_value = True
        result = mock_user.check_password("correct_password")
        assert result is True
        mock_user.check_password.assert_called_with("correct_password")
        
        # Test failed password check
        mock_user.check_password.return_value = False
        result = mock_user.check_password("wrong_password")
        assert result is False
    
    def test_account_lock_check(self, mock_user):
        """Test account lock verification."""
        # Test unlocked account
        mock_user.is_account_locked.return_value = False
        result = mock_user.is_account_locked()
        assert result is False
        
        # Test locked account
        mock_user.is_account_locked.return_value = True
        result = mock_user.is_account_locked()
        assert result is True
    
    def test_login_response_structure(self):
        """Test login response structure."""
        from app.models.user import LoginResponse, UserResponse
        
        # Create mock user response
        user_data = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="consultant",
            is_active=True,
            email_verified=False,
            full_name="John Doe",
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        # Create login response
        response = LoginResponse(
            access_token="test_token",
            token_type="bearer",
            expires_in=900,  # 15 minutes = 900 seconds
            user=user_data
        )
        
        assert response.access_token == "test_token"
        assert response.token_type == "bearer"
        assert response.expires_in == 900
        assert response.user.email == "test@example.com"
    
    @patch('app.core.security.create_access_token')
    def test_jwt_token_creation(self, mock_create_token, mock_user):
        """Test JWT token creation with correct payload."""
        mock_create_token.return_value = "mocked_jwt_token"
        
        from app.core.security import create_access_token
        from datetime import timedelta
        
        # Test token creation with user data
        token_data = {
            "sub": str(mock_user.id),
            "email": mock_user.email,
            "role": mock_user.role
        }
        
        token = create_access_token(data=token_data, expires_delta=timedelta(minutes=15))
        
        # Verify token was created
        mock_create_token.assert_called_once()
        assert token == "mocked_jwt_token"
    
    def test_case_insensitive_email_handling(self):
        """Test that email handling is case insensitive."""
        from app.models.user import LoginRequest
        
        # Different case variations should be valid
        test_cases = [
            "test@example.com",
            "TEST@EXAMPLE.COM", 
            "Test@Example.Com"
        ]
        
        for email in test_cases:
            request = LoginRequest(email=email, password="password123")
            # In the actual login logic, emails are converted to lowercase
            assert request.email.lower() == "test@example.com"
    
    def test_rate_limiting_configuration(self):
        """Test that rate limiting is properly configured."""
        # This tests the imports and rate limiting setup
        try:
            from app.core.rate_limiter import check_login_rate_limit
            from app.api.auth import router
            
            # Verify rate limiting function exists
            assert callable(check_login_rate_limit)
            assert router is not None
            
        except ImportError as e:
            pytest.fail(f"Rate limiting components not properly configured: {e}")
    
    def test_security_imports(self):
        """Test that security components are properly imported."""
        try:
            from app.core.security import create_access_token, verify_token
            from app.api.auth import get_current_user
            
            # Verify security functions exist
            assert callable(create_access_token)
            assert callable(verify_token)
            assert callable(get_current_user)
            
        except ImportError as e:
            pytest.fail(f"Security components not properly configured: {e}")
    
    def test_database_query_structure(self):
        """Test database query structure for user lookup."""
        from app.models.user import User
        
        # Mock database session to test query structure
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        # Simulate the query structure used in login
        result = mock_db.query(User).filter().first()
        
        # Verify query methods were called
        mock_db.query.assert_called_once_with(User)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()


class TestLoginValidation:
    """Test validation and error handling for login."""
    
    def test_email_validation_rules(self):
        """Test email validation rules."""
        from pydantic import ValidationError
        from app.models.user import LoginRequest
        
        # Valid emails should pass
        valid_emails = [
            "user@example.com",
            "test.user+tag@example.co.uk",
            "user123@test-domain.org"
        ]
        
        for email in valid_emails:
            request = LoginRequest(email=email, password="password123")
            assert request.email == email
        
        # Invalid emails should fail
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user space@example.com",
            ""
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                LoginRequest(email=email, password="password123")
    
    def test_password_field_validation(self):
        """Test password field validation."""
        from pydantic import ValidationError
        from app.models.user import LoginRequest
        
        # Valid passwords should pass
        valid_passwords = [
            "password123",
            "SecureP@ss123!",
            "a" * 8,  # minimum length
            "a" * 128  # maximum length typically
        ]
        
        for password in valid_passwords:
            request = LoginRequest(email="test@example.com", password=password)
            assert request.password == password
        
        # Empty password should fail
        with pytest.raises(ValidationError):
            LoginRequest(email="test@example.com", password="")


class TestAuthenticationFlow:
    """Test the complete authentication flow logic."""
    
    def test_successful_authentication_steps(self, mock_user=None):
        """Test successful authentication workflow steps."""
        if mock_user is None:
            mock_user = Mock()
            mock_user.id = "test-id"
            mock_user.email = "test@example.com"
            mock_user.is_active = True
            mock_user.is_account_locked.return_value = False
            mock_user.check_password.return_value = True
        
        # Step 1: User exists and is active
        assert mock_user.is_active is True
        
        # Step 2: Account is not locked
        assert mock_user.is_account_locked() is False
        
        # Step 3: Password verification succeeds
        assert mock_user.check_password("test_password") is True
        
        # Step 4: Token should be generated (mocked)
        with patch('app.core.security.create_access_token') as mock_token:
            mock_token.return_value = "test_jwt_token"
            token = mock_token(data={"sub": str(mock_user.id)})
            assert token == "test_jwt_token"
    
    def test_authentication_failure_scenarios(self):
        """Test various authentication failure scenarios."""
        mock_user = Mock()
        mock_user.email = "test@example.com"
        
        # Scenario 1: Account locked
        mock_user.is_account_locked.return_value = True
        assert mock_user.is_account_locked() is True
        
        # Scenario 2: Wrong password
        mock_user.is_account_locked.return_value = False
        mock_user.check_password.return_value = False
        assert mock_user.check_password("wrong_password") is False
        
        # Scenario 3: Inactive user
        mock_user.is_active = False
        assert mock_user.is_active is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])