"""
Unit tests for User model with secure password handling.
Tests AUTH-004 requirements for user authentication and security.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from app.core.datetime_utils import utc_now

from app.models.user import (
    User,
    UserRole,
    UserCreate,
    UserUpdate,
    PasswordUpdate,
    AdminPasswordReset,
    UserResponse
)
from app.core.security import SecurityError


class TestUser:
    """Test User model functionality."""
    
    def test_user_creation(self, test_db, test_user_data):
        """Test user creation with password hashing."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Check user was created
        assert user.id is not None
        assert user.email == test_user_data["email"].lower()
        assert user.first_name == test_user_data["first_name"]
        assert user.last_name == test_user_data["last_name"]
        assert user.role == UserRole.CONSULTANT.value
        assert user.is_active is True
        assert user.email_verified is False
        
        # Password should be hashed, not stored as plain text
        assert user.password_hash != test_user_data["password"]
        assert user.password_hash.startswith("$2b$")
        assert len(user.password_hash) == 60
    
    def test_user_creation_admin(self, test_db, test_admin_data):
        """Test admin user creation."""
        user = User(**test_admin_data)
        test_db.add(user)
        test_db.commit()
        
        assert user.role == UserRole.ADMIN.value
        assert user.is_admin() is True
        assert user.is_consultant() is False
    
    def test_user_creation_invalid_password(self, test_db, invalid_passwords):
        """Test user creation with invalid passwords."""
        for invalid_password in invalid_passwords:
            with pytest.raises(SecurityError):
                User(
                    email="test@example.com",
                    password=invalid_password,
                    first_name="Test",
                    last_name="User"
                )
    
    def test_email_normalization(self, test_db):
        """Test email normalization to lowercase."""
        import uuid
        unique_email = f"TEST_{uuid.uuid4().hex[:8]}@EXAMPLE.COM"
        expected_email = unique_email.lower()
        
        user = User(
            email=unique_email,
            password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        test_db.add(user)
        test_db.commit()
        
        assert user.email == expected_email
    
    def test_unique_email_constraint(self, test_db, test_user_data):
        """Test unique email constraint."""
        # Create first user
        user1 = User(**test_user_data)
        test_db.add(user1)
        test_db.commit()
        
        # Try to create second user with same email
        user2 = User(**test_user_data)
        test_db.add(user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_password_verification(self, test_db, test_user_data):
        """Test password verification."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Correct password should verify
        assert user.check_password(test_user_data["password"]) is True
        
        # Wrong password should not verify
        assert user.check_password("wrongpassword") is False
        assert user.check_password("") is False
        assert user.check_password(None) is False
    
    def test_set_password(self, test_db, test_user_data, strong_passwords):
        """Test password setting and updating."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        original_hash = user.password_hash
        original_changed_at = user.password_changed_at
        
        # Set new password
        new_password = strong_passwords[0]
        user.set_password(new_password)
        test_db.commit()
        
        # Hash should be different
        assert user.password_hash != original_hash
        assert user.password_changed_at > original_changed_at
        
        # New password should verify
        assert user.check_password(new_password) is True
        # Old password should not verify
        assert user.check_password(test_user_data["password"]) is False
        
        # Security counters should be reset
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_account_locking(self, test_db, test_user_data):
        """Test account locking mechanism."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Initially not locked
        assert user.is_account_locked() is False
        assert user.failed_login_attempts == 0
        
        # Failed login attempts
        for i in range(4):
            user.check_password("wrongpassword")
            test_db.commit()
            assert user.failed_login_attempts == i + 1
            assert user.is_account_locked() is False
        
        # 5th failed attempt should lock account
        user.check_password("wrongpassword")
        test_db.commit()
        
        assert user.failed_login_attempts == 5
        assert user.is_account_locked() is True
        assert user.locked_until is not None
        assert user.locked_until > utc_now()
    
    def test_account_unlock_after_time(self, test_db, test_user_data):
        """Test automatic account unlock after time expires."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Simulate expired lock
        user.failed_login_attempts = 5
        user.locked_until = utc_now() - timedelta(minutes=1)  # Past
        test_db.commit()
        
        # Should be unlocked now
        assert user.is_account_locked() is False
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_manual_account_unlock(self, test_db, test_user_data):
        """Test manual account unlock (admin function)."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Lock account
        user.failed_login_attempts = 5
        user.locked_until = utc_now() + timedelta(minutes=30)
        test_db.commit()
        
        assert user.is_account_locked() is True
        
        # Unlock manually
        user.unlock_account()
        test_db.commit()
        
        assert user.is_account_locked() is False
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
    
    def test_successful_login_resets_attempts(self, test_db, test_user_data):
        """Test that successful login resets failed attempts."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Some failed attempts
        user.failed_login_attempts = 3
        test_db.commit()
        
        # Successful login
        assert user.check_password(test_user_data["password"]) is True
        test_db.commit()
        
        # Should reset counter and update last login
        assert user.failed_login_attempts == 0
        assert user.last_login_at is not None
        assert user.last_login_at > utc_now() - timedelta(minutes=1)
    
    def test_password_rehash_check(self, test_db, test_user_data):
        """Test password rehash checking."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Fresh hash should not need rehash
        assert user.needs_password_rehash() is False
    
    def test_role_methods(self, test_db):
        """Test role checking methods."""
        import uuid
        
        # Consultant user
        consultant = User(
            email=f"consultant_{uuid.uuid4().hex[:8]}@example.com",
            password="Password123!",
            first_name="Con",
            last_name="Sultant",
            role=UserRole.CONSULTANT
        )
        test_db.add(consultant)
        
        # Admin user
        admin = User(
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com", 
            password="Password123!",
            first_name="Ad",
            last_name="Min",
            role=UserRole.ADMIN
        )
        test_db.add(admin)
        test_db.commit()
        
        # Test consultant
        assert consultant.is_consultant() is True
        assert consultant.is_admin() is False
        
        # Test admin
        assert admin.is_admin() is True
        assert admin.is_consultant() is False
    
    def test_get_full_name(self, test_db, test_user_data):
        """Test full name generation."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        expected_full_name = f"{test_user_data['first_name']} {test_user_data['last_name']}"
        assert user.get_full_name() == expected_full_name
    
    def test_to_dict(self, test_db, test_user_data):
        """Test user dictionary conversion."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        # Basic dict (no sensitive info)
        user_dict = user.to_dict()
        
        assert "id" in user_dict
        assert "email" in user_dict
        assert "first_name" in user_dict
        assert "last_name" in user_dict
        assert "full_name" in user_dict
        assert "role" in user_dict
        assert "is_active" in user_dict
        assert "email_verified" in user_dict
        assert "created_at" in user_dict
        
        # Should not include password hash
        assert "password_hash" not in user_dict
        assert "failed_login_attempts" not in user_dict
        
        # Sensitive dict
        sensitive_dict = user.to_dict(include_sensitive=True)
        assert "failed_login_attempts" in sensitive_dict
        assert "is_locked" in sensitive_dict
        assert "password_changed_at" in sensitive_dict
        
        # Still should not include password hash
        assert "password_hash" not in sensitive_dict
    
    def test_user_repr(self, test_db, test_user_data):
        """Test user string representation."""
        user = User(**test_user_data)
        test_db.add(user)
        test_db.commit()
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user.id) in repr_str
        assert user.email in repr_str
        assert user.role in repr_str
        
        # Should not include sensitive information
        assert test_user_data["password"] not in repr_str
        assert user.password_hash not in repr_str


class TestUserValidation:
    """Test user model validation."""
    
    def test_email_validation(self, test_db):
        """Test email validation."""
        import uuid
        
        # Valid email
        user = User(
            email=f"valid_{uuid.uuid4().hex[:8]}@example.com",
            password="Password123!",
            first_name="Test",
            last_name="User"
        )
        test_db.add(user)
        test_db.commit()  # Should not raise
        
        # Invalid email format
        with pytest.raises(ValueError):
            User(
                email="invalid-email",
                password="Password123!",
                first_name="Test",
                last_name="User"
            )
    
    def test_role_validation(self, test_db):
        """Test role validation."""
        # Valid roles
        for role in [UserRole.CONSULTANT, UserRole.ADMIN]:
            user = User(
                email=f"user{role.value}@example.com",
                password="Password123!",
                first_name="Test",
                last_name="User",
                role=role
            )
            test_db.add(user)
        
        test_db.commit()  # Should not raise
        
        # Invalid role
        with pytest.raises(ValueError):
            user = User(
                email="invalid@example.com",
                password="Password123!",
                first_name="Test",
                last_name="User"
            )
            user.role = "invalid_role"  # Set after creation
            user.validate_role("role", "invalid_role")


class TestPydanticModels:
    """Test Pydantic models for API requests/responses."""
    
    def test_user_create_model(self, strong_passwords):
        """Test UserCreate model validation."""
        # Valid data
        user_data = UserCreate(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password=strong_passwords[0],
            role=UserRole.CONSULTANT
        )
        
        assert user_data.email == "test@example.com"
        assert user_data.first_name == "Test"
        assert user_data.last_name == "User"
        assert user_data.password == strong_passwords[0]
        assert user_data.role == UserRole.CONSULTANT
    
    def test_user_create_model_validation(self, invalid_passwords):
        """Test UserCreate model password validation."""
        for invalid_password in invalid_passwords:
            with pytest.raises(ValueError):
                UserCreate(
                    email="test@example.com",
                    first_name="Test", 
                    last_name="User",
                    password=invalid_password
                )
    
    def test_user_update_model(self):
        """Test UserUpdate model."""
        # Partial update
        update_data = UserUpdate(first_name="Updated")
        assert update_data.first_name == "Updated"
        assert update_data.last_name is None
        
        # Full update
        update_data = UserUpdate(
            first_name="New First",
            last_name="New Last", 
            email="new@example.com",
            is_active=False,
            role=UserRole.ADMIN
        )
        
        assert update_data.first_name == "New First"
        assert update_data.last_name == "New Last"
        assert update_data.email == "new@example.com"
        assert update_data.is_active is False
        assert update_data.role == UserRole.ADMIN
    
    def test_password_update_model(self, strong_passwords):
        """Test PasswordUpdate model."""
        password_data = PasswordUpdate(
            current_password="OldPassword123!",
            new_password=strong_passwords[0]
        )
        
        assert password_data.current_password == "OldPassword123!"
        assert password_data.new_password == strong_passwords[0]
    
    def test_password_update_model_validation(self, invalid_passwords):
        """Test PasswordUpdate model validation."""
        for invalid_password in invalid_passwords:
            with pytest.raises(ValueError):
                PasswordUpdate(
                    current_password="OldPassword123!",
                    new_password=invalid_password
                )
    
    def test_admin_password_reset_model(self, strong_passwords):
        """Test AdminPasswordReset model."""
        from uuid import uuid4
        
        reset_data = AdminPasswordReset(
            user_id=uuid4(),
            new_password=strong_passwords[0],
            force_password_change=True
        )
        
        assert reset_data.user_id is not None
        assert reset_data.new_password == strong_passwords[0]
        assert reset_data.force_password_change is True
    
    def test_user_response_model(self, test_db, create_test_user):
        """Test UserResponse model."""
        user = create_test_user()
        
        response = UserResponse.from_orm(user)
        
        assert response.id == user.id
        assert response.email == user.email
        assert response.first_name == user.first_name
        assert response.last_name == user.last_name
        assert response.role == user.role
        assert response.is_active == user.is_active
        assert response.email_verified == user.email_verified
        assert response.created_at == user.created_at
        assert response.full_name == user.get_full_name()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])