"""
Unit tests for security module - password hashing, validation, and JWT tokens.
Comprehensive test coverage for AUTH-004 requirements.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from app.core.security import (
    PasswordHasher, 
    PasswordPolicy,
    PasswordValidationResult,
    TokenManager,
    SecurityError,
    hash_password,
    verify_password,
    validate_password,
    create_access_token,
    verify_token,
    password_hasher,
    token_manager,
    COMMON_PASSWORDS
)


class TestPasswordHasher:
    """Test password hashing functionality."""
    
    def test_init_default_policy(self):
        """Test PasswordHasher initialization with default policy."""
        hasher = PasswordHasher()
        assert hasher.policy.min_length == 8
        assert hasher.policy.require_uppercase is True
        assert hasher.policy.require_lowercase is True
        assert hasher.policy.require_digit is True
        assert hasher.policy.require_special is True
        assert hasher.policy.check_common_passwords is True
    
    def test_init_custom_policy(self):
        """Test PasswordHasher initialization with custom policy."""
        policy = PasswordPolicy(
            min_length=12,
            require_uppercase=False,
            require_special=False
        )
        hasher = PasswordHasher(policy)
        assert hasher.policy.min_length == 12
        assert hasher.policy.require_uppercase is False
        assert hasher.policy.require_special is False
        assert hasher.policy.require_lowercase is True  # Default
    
    def test_hash_password_valid(self, strong_passwords):
        """Test password hashing with valid passwords."""
        hasher = PasswordHasher()
        
        for password in strong_passwords:
            hashed = hasher.hash_password(password)
            
            # Hash should be different from original password
            assert hashed != password
            # Hash should start with bcrypt identifier
            assert hashed.startswith("$2b$")
            # Hash should be consistent length
            assert len(hashed) == 60
    
    def test_hash_password_invalid(self, invalid_passwords):
        """Test password hashing with invalid passwords."""
        hasher = PasswordHasher()
        
        for password in invalid_passwords:
            with pytest.raises(SecurityError):
                hasher.hash_password(password)
    
    def test_verify_password_correct(self, strong_passwords):
        """Test password verification with correct passwords."""
        hasher = PasswordHasher()
        
        for password in strong_passwords:
            hashed = hasher.hash_password(password)
            assert hasher.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self, strong_passwords):
        """Test password verification with incorrect passwords.""" 
        hasher = PasswordHasher()
        
        correct_password = strong_passwords[0]
        hashed = hasher.hash_password(correct_password)
        
        # Test wrong passwords
        wrong_passwords = ["wrong", "incorrect", "notright"]
        for wrong_password in wrong_passwords:
            assert hasher.verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_inputs(self):
        """Test password verification with empty inputs."""
        hasher = PasswordHasher()
        
        assert hasher.verify_password("", "") is False
        assert hasher.verify_password("password", "") is False
        assert hasher.verify_password("", "hash") is False
    
    def test_needs_rehash(self, strong_passwords):
        """Test hash update checking."""
        hasher = PasswordHasher()
        
        password = strong_passwords[0]
        hashed = hasher.hash_password(password)
        
        # Fresh hash should not need update
        assert hasher.needs_rehash(hashed) is False
        
        # Old/invalid hash should need update
        old_hash = "$2a$04$invalid_old_hash"
        assert hasher.needs_rehash(old_hash) is True


class TestPasswordValidation:
    """Test password validation functionality."""
    
    def test_validate_strong_passwords(self, strong_passwords):
        """Test validation of strong passwords."""
        hasher = PasswordHasher()
        
        for password in strong_passwords:
            result = hasher.validate_password(password)
            
            assert isinstance(result, PasswordValidationResult)
            assert result.is_valid is True
            assert len(result.errors) == 0
            assert result.strength_score >= 80  # Strong passwords should score high
    
    def test_validate_weak_passwords(self, weak_passwords):
        """Test validation of weak passwords."""
        hasher = PasswordHasher()
        
        for password in weak_passwords:
            result = hasher.validate_password(password)
            
            assert isinstance(result, PasswordValidationResult)
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert result.strength_score < 80  # Weak passwords should score low
    
    def test_validate_length_requirements(self):
        """Test password length validation."""
        hasher = PasswordHasher()
        
        # Too short
        result = hasher.validate_password("Abc1!")
        assert not result.is_valid
        assert any("8 characters" in error for error in result.errors)
        
        # Minimum length
        result = hasher.validate_password("Abc123!")  
        assert result.is_valid
        
        # Long password (bonus points)
        result = hasher.validate_password("MyVeryLongSecurePassword123!")
        assert result.is_valid
        assert result.strength_score >= 90
    
    def test_validate_character_requirements(self):
        """Test character requirement validation."""
        hasher = PasswordHasher()
        
        # Missing uppercase
        result = hasher.validate_password("lowercase123!")
        assert not result.is_valid
        assert any("uppercase" in error for error in result.errors)
        
        # Missing lowercase  
        result = hasher.validate_password("UPPERCASE123!")
        assert not result.is_valid
        assert any("lowercase" in error for error in result.errors)
        
        # Missing digit
        result = hasher.validate_password("Password!")
        assert not result.is_valid
        assert any("digit" in error for error in result.errors)
        
        # Missing special character
        result = hasher.validate_password("Password123")
        assert not result.is_valid
        assert any("special" in error for error in result.errors)
    
    def test_validate_common_passwords(self):
        """Test common password rejection."""
        hasher = PasswordHasher()
        
        for common_password in ["password", "123456", "admin", "qwerty"]:
            result = hasher.validate_password(common_password)
            assert not result.is_valid
            assert any("common" in error.lower() for error in result.errors)
    
    def test_validate_custom_policy(self):
        """Test validation with custom policy."""
        # Lenient policy
        lenient_policy = PasswordPolicy(
            min_length=4,
            require_uppercase=False,
            require_special=False,
            check_common_passwords=False
        )
        hasher = PasswordHasher(lenient_policy)
        
        result = hasher.validate_password("test123")
        assert result.is_valid
        
        # Strict policy
        strict_policy = PasswordPolicy(
            min_length=12,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special=True
        )
        hasher = PasswordHasher(strict_policy)
        
        result = hasher.validate_password("Short1!")
        assert not result.is_valid
        assert any("12 characters" in error for error in result.errors)
    
    def test_generate_secure_password(self):
        """Test secure password generation."""
        hasher = PasswordHasher()
        
        # Default length
        password = hasher.generate_secure_password()
        assert len(password) == 12
        
        validation_result = hasher.validate_password(password)
        assert validation_result.is_valid
        assert validation_result.strength_score >= 80
        
        # Custom length
        password = hasher.generate_secure_password(16)
        assert len(password) == 16
        
        validation_result = hasher.validate_password(password)
        assert validation_result.is_valid
        
        # Multiple generations should be different
        passwords = [hasher.generate_secure_password() for _ in range(10)]
        assert len(set(passwords)) == 10  # All unique


class TestTokenManager:
    """Test JWT token management."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        manager = TokenManager()
        
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "consultant"
        }
        
        token = manager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long
        assert token.count(".") == 2  # JWT format: header.payload.signature
    
    def test_create_access_token_with_expiry(self):
        """Test access token creation with custom expiry."""
        manager = TokenManager()
        
        data = {"sub": "user123"}
        expires_delta = timedelta(minutes=60)
        
        token = manager.create_access_token(data, expires_delta)
        assert isinstance(token, str)
        
        # Verify token contains expiry
        payload = manager.verify_token(token)
        assert payload is not None
        assert "exp" in payload
    
    def test_verify_token_valid(self):
        """Test valid token verification."""
        manager = TokenManager()
        
        data = {
            "sub": "user123", 
            "email": "test@example.com",
            "role": "admin"
        }
        
        token = manager.create_access_token(data)
        payload = manager.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"
        assert "exp" in payload
    
    def test_verify_token_invalid(self):
        """Test invalid token verification."""
        manager = TokenManager()
        
        # Invalid tokens
        invalid_tokens = [
            "invalid.token.here",
            "not.a.jwt",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
        ]
        
        for token in invalid_tokens:
            payload = manager.verify_token(token)
            assert payload is None
    
    def test_verify_token_expired(self):
        """Test expired token verification."""
        manager = TokenManager()
        
        data = {"sub": "user123"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        
        token = manager.create_access_token(data, expires_delta)
        
        # Small delay to ensure expiry
        time.sleep(0.1)
        
        payload = manager.verify_token(token)
        assert payload is None
    
    def test_verify_token_wrong_secret(self):
        """Test token verification with wrong secret."""
        manager1 = TokenManager("secret1")
        manager2 = TokenManager("secret2")
        
        data = {"sub": "user123"}
        
        # Create token with first manager
        token = manager1.create_access_token(data)
        
        # Try to verify with second manager (different secret)
        payload = manager2.verify_token(token)
        assert payload is None


class TestGlobalFunctions:
    """Test global utility functions."""
    
    def test_global_hash_password(self, strong_passwords):
        """Test global hash_password function."""
        for password in strong_passwords:
            hashed = hash_password(password)
            assert hashed != password
            assert hashed.startswith("$2b$")
    
    def test_global_verify_password(self, strong_passwords):
        """Test global verify_password function."""
        password = strong_passwords[0]
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_global_validate_password(self, strong_passwords, weak_passwords):
        """Test global validate_password function."""
        # Strong passwords should pass
        for password in strong_passwords:
            result = validate_password(password)
            assert result.is_valid is True
        
        # Weak passwords should fail
        for password in weak_passwords:
            result = validate_password(password)
            assert result.is_valid is False
    
    def test_global_token_functions(self):
        """Test global token functions."""
        data = {"sub": "user123", "role": "admin"}
        
        # Create token
        token = create_access_token(data)
        assert isinstance(token, str)
        
        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"


class TestSecurityEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_password_hasher_error_handling(self):
        """Test error handling in password hasher."""
        hasher = PasswordHasher()
        
        # Test with None
        with pytest.raises((SecurityError, AttributeError, TypeError)):
            hasher.hash_password(None)
        
        # Test verification with None  
        assert hasher.verify_password(None, "hash") is False
        assert hasher.verify_password("password", None) is False
    
    def test_token_manager_error_handling(self):
        """Test error handling in token manager."""
        manager = TokenManager()
        
        # Test with invalid data types
        with pytest.raises((SecurityError, TypeError)):
            manager.create_access_token(None)
        
        # Test verification with None
        assert manager.verify_token(None) is None
    
    def test_concurrent_operations(self, strong_passwords):
        """Test thread safety of password operations."""
        import threading
        import concurrent.futures
        
        hasher = PasswordHasher()
        password = strong_passwords[0]
        
        def hash_and_verify():
            hashed = hasher.hash_password(password)
            return hasher.verify_password(password, hashed)
        
        # Run multiple operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(hash_and_verify) for _ in range(20)]
            results = [future.result() for future in futures]
        
        # All operations should succeed
        assert all(results)
    
    def test_password_validation_edge_cases(self):
        """Test password validation edge cases."""
        hasher = PasswordHasher()
        
        # Empty string
        result = hasher.validate_password("")
        assert not result.is_valid
        
        # Very long password
        long_password = "A" * 200 + "1!"
        result = hasher.validate_password(long_password)
        # Should fail due to max_length constraint
        assert not result.is_valid
        
        # Unicode characters
        unicode_password = "Pässwörd123!"
        result = hasher.validate_password(unicode_password)
        # Should work with Unicode
        assert result.is_valid
    
    def test_constant_time_verification(self, strong_passwords):
        """Test that password verification timing is consistent."""
        hasher = PasswordHasher()
        
        password = strong_passwords[0]
        hashed = hasher.hash_password(password)
        
        # Time correct password verification
        start_time = time.time()
        hasher.verify_password(password, hashed)
        correct_time = time.time() - start_time
        
        # Time incorrect password verification
        start_time = time.time()
        hasher.verify_password("wrong", hashed)
        wrong_time = time.time() - start_time
        
        # Times should be similar (within reasonable margin)
        # This is a basic check - real constant-time verification is handled by bcrypt
        time_diff = abs(correct_time - wrong_time)
        assert time_diff < 0.1  # Should be within 100ms


class TestSecurityIntegration:
    """Integration tests for security components."""
    
    def test_full_authentication_flow(self):
        """Test complete authentication flow."""
        hasher = PasswordHasher()
        token_manager = TokenManager()
        
        # User registration flow
        password = "UserPassword123!"
        hashed_password = hasher.hash_password(password)
        
        # Login flow
        is_valid = hasher.verify_password(password, hashed_password)
        assert is_valid
        
        # Token creation
        user_data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "consultant"
        }
        token = token_manager.create_access_token(user_data)
        
        # Token verification
        payload = token_manager.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "consultant"
    
    def test_password_policy_compliance(self):
        """Test password policy compliance across components."""
        # Test that all components use consistent policy
        hasher = PasswordHasher()
        
        # Test password that meets policy
        compliant_password = "CompliantPass123!"
        result = hasher.validate_password(compliant_password)
        assert result.is_valid
        
        # Should be able to hash it
        hashed = hasher.hash_password(compliant_password)
        assert hashed is not None
        
        # Should be able to verify it
        assert hasher.verify_password(compliant_password, hashed)
    
    def test_security_logging(self):
        """Test that security operations are properly logged."""
        # This would test logging in a real implementation
        # For now, we'll just ensure no exceptions are raised
        hasher = PasswordHasher()
        
        with patch('app.core.security.logger') as mock_logger:
            password = "TestPassword123!"
            hashed = hasher.hash_password(password)
            hasher.verify_password(password, hashed)
            
            # Verify logging was called
            assert mock_logger.info.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])