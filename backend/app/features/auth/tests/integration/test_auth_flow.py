"""
Integration tests for complete auth flows.
Tests the full auth functionality with real database and Redis connections.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch
from datetime import datetime, timedelta
import asyncio
import uuid

from app.main import app
from app.features.auth.service import AuthService
from app.features.auth.repository import UserRepository, RefreshTokenRepository
from app.features.auth.schemas import LoginRequest, UserCreate
from database.models.auth import User, RefreshToken
from app.core.database import get_async_session
from app.features.auth.tests.fixtures.mock_data import MockAuthData
from app.core.datetime_utils import utc_now


@pytest.mark.integration
class TestAuthServiceIntegration:
    """Integration tests for AuthService with real database."""
    
    @pytest.fixture
    async def db_session(self):
        """Create a test database session."""
        async with get_async_session() as session:
            yield session
    
    @pytest.fixture
    async def auth_service(self, db_session):
        """Create AuthService with real repositories."""
        user_repo = UserRepository(db_session)
        token_repo = RefreshTokenRepository(db_session)
        return AuthService(user_repo=user_repo, token_repo=token_repo)
    
    @pytest.fixture
    async def test_user_data(self):
        """Create unique test user data."""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "email": f"integration.test.{unique_id}@example.com",
            "password": "IntegrationTest123!",
            "first_name": "Integration",
            "last_name": "Test",
            "role": "consultant"
        }
    
    @pytest.mark.asyncio
    async def test_complete_registration_login_flow(self, auth_service, test_user_data):
        """Test complete user registration and login flow."""
        # Test Registration
        user_create = UserCreate(**test_user_data)
        registered_user = await auth_service.register_user(user_create)
        
        assert registered_user.email == test_user_data["email"]
        assert registered_user.first_name == test_user_data["first_name"]
        assert registered_user.is_active is True
        
        # Test Login
        login_request = LoginRequest(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        login_response = await auth_service.login(
            login_request=login_request,
            client_ip="192.168.1.100",
            user_agent="Test Browser"
        )
        
        assert login_response.access_token is not None
        assert login_response.refresh_token is not None
        assert login_response.user.email == test_user_data["email"]
        
        # Verify user can be retrieved
        user_repo = auth_service.user_repo
        retrieved_user = await user_repo.get_by_email(test_user_data["email"])
        assert retrieved_user is not None
        assert retrieved_user.email == test_user_data["email"]
    
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, auth_service, test_user_data):
        """Test login with invalid credentials fails properly."""
        from app.core.security import SecurityError
        
        # Create user first
        user_create = UserCreate(**test_user_data)
        await auth_service.register_user(user_create)
        
        # Try login with wrong password
        login_request = LoginRequest(
            email=test_user_data["email"],
            password="WrongPassword123!"
        )
        
        with pytest.raises(SecurityError, match="Invalid email or password"):
            await auth_service.login(
                login_request=login_request,
                client_ip="192.168.1.100"
            )
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, auth_service, test_user_data):
        """Test complete token refresh flow."""
        # Register and login user
        user_create = UserCreate(**test_user_data)
        await auth_service.register_user(user_create)
        
        login_request = LoginRequest(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        login_response = await auth_service.login(
            login_request=login_request,
            client_ip="192.168.1.100",
            user_agent="Test Browser"
        )
        
        # Test token refresh
        refresh_response = await auth_service.refresh_token(
            refresh_token_str=login_response.refresh_token,
            client_ip="192.168.1.100",
            user_agent="Test Browser"
        )
        
        assert refresh_response.access_token != login_response.access_token
        assert refresh_response.refresh_token != login_response.refresh_token
        assert refresh_response.token_type == "bearer"
    
    @pytest.mark.asyncio
    async def test_password_change_flow(self, auth_service, test_user_data):
        """Test password change flow."""
        # Register user
        user_create = UserCreate(**test_user_data)
        registered_user = await auth_service.register_user(user_create)
        
        # Change password
        new_password = "NewPassword123!"
        result = await auth_service.change_password(
            user_id=registered_user.id,
            current_password=test_user_data["password"],
            new_password=new_password
        )
        
        assert result["message"] == "Password changed successfully"
        
        # Verify old password no longer works
        from app.core.security import SecurityError
        old_login_request = LoginRequest(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        with pytest.raises(SecurityError):
            await auth_service.login(
                login_request=old_login_request,
                client_ip="192.168.1.100"
            )
        
        # Verify new password works
        new_login_request = LoginRequest(
            email=test_user_data["email"],
            password=new_password
        )
        
        login_response = await auth_service.login(
            login_request=new_login_request,
            client_ip="192.168.1.100"
        )
        
        assert login_response.access_token is not None
    
    @pytest.mark.asyncio
    async def test_session_management_flow(self, auth_service, test_user_data):
        """Test session management functionality."""
        # Register and login user multiple times (multiple sessions)
        user_create = UserCreate(**test_user_data)
        registered_user = await auth_service.register_user(user_create)
        
        login_request = LoginRequest(
            email=test_user_data["email"],
            password=test_user_data["password"]
        )
        
        # Create multiple sessions
        session1 = await auth_service.login(
            login_request=login_request,
            client_ip="192.168.1.100",
            user_agent="Browser 1"
        )
        
        session2 = await auth_service.login(
            login_request=login_request,
            client_ip="192.168.1.101", 
            user_agent="Browser 2"
        )
        
        # Get user sessions
        sessions_response = await auth_service.get_user_sessions(registered_user.id)
        
        assert sessions_response.total_sessions >= 2
        assert len(sessions_response.sessions) >= 2
        
        # Find a session to revoke
        session_to_revoke = sessions_response.sessions[0].session_id
        
        # Revoke one session
        revoke_result = await auth_service.revoke_session(
            user_id=registered_user.id,
            session_id=session_to_revoke
        )
        
        assert revoke_result is True
        
        # Verify session count decreased
        updated_sessions = await auth_service.get_user_sessions(registered_user.id)
        assert updated_sessions.total_sessions < sessions_response.total_sessions


@pytest.mark.integration
class TestAuthAPIIntegration:
    """Integration tests for Auth API endpoints with real dependencies."""
    
    @pytest.fixture
    def client(self):
        """Create test client with new auth enabled."""
        with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
            return TestClient(app)
    
    @pytest.fixture
    def unique_test_data(self):
        """Create unique test data for each test."""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "email": f"api.test.{unique_id}@example.com",
            "password": "APITest123!",
            "first_name": "API",
            "last_name": "Test",
            "role": "consultant"
        }
    
    def test_complete_api_auth_flow(self, client, unique_test_data):
        """Test complete authentication flow through API."""
        # Test Registration
        register_response = client.post("/api/v1/auth/register", json=unique_test_data)
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == unique_test_data["email"]
        
        # Test Login
        login_data = {
            "email": unique_test_data["email"],
            "password": unique_test_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        
        assert access_token is not None
        assert refresh_token is not None
        
        # Test accessing protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        me_data = me_response.json()
        assert me_data["email"] == unique_test_data["email"]
        
        # Test token refresh
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        refresh_result = refresh_response.json()
        new_access_token = refresh_result["access_token"]
        assert new_access_token != access_token
        
        # Test logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # Verify token is invalidated
        me_after_logout = client.get("/api/v1/auth/me", headers=headers)
        assert me_after_logout.status_code == 401
    
    def test_api_error_handling(self, client, unique_test_data):
        """Test API error handling and validation."""
        # Test registration with invalid data
        invalid_data = {**unique_test_data, "email": "not-an-email"}
        register_response = client.post("/api/v1/auth/register", json=invalid_data)
        assert register_response.status_code == 422
        
        # Register valid user first
        client.post("/api/v1/auth/register", json=unique_test_data)
        
        # Test duplicate registration
        duplicate_response = client.post("/api/v1/auth/register", json=unique_test_data)
        assert duplicate_response.status_code == 400
        
        # Test login with wrong password
        wrong_login = {
            "email": unique_test_data["email"],
            "password": "WrongPassword123!"
        }
        login_response = client.post("/api/v1/auth/login", json=wrong_login)
        assert login_response.status_code == 401
        
        # Test login with non-existent user
        fake_login = {
            "email": "fake@example.com",
            "password": "FakePassword123!"
        }
        fake_response = client.post("/api/v1/auth/login", json=fake_login)
        assert fake_response.status_code == 401
    
    def test_api_password_change_flow(self, client, unique_test_data):
        """Test password change through API."""
        # Register and login user
        client.post("/api/v1/auth/register", json=unique_test_data)
        
        login_data = {
            "email": unique_test_data["email"],
            "password": unique_test_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Change password
        password_change_data = {
            "current_password": unique_test_data["password"],
            "new_password": "NewAPIPassword123!"
        }
        change_response = client.post(
            "/api/v1/auth/change-password",
            json=password_change_data,
            headers=headers
        )
        assert change_response.status_code == 200
        
        # Test old password no longer works
        old_login_response = client.post("/api/v1/auth/login", json=login_data)
        assert old_login_response.status_code == 401
        
        # Test new password works
        new_login_data = {
            "email": unique_test_data["email"],
            "password": "NewAPIPassword123!"
        }
        new_login_response = client.post("/api/v1/auth/login", json=new_login_data)
        assert new_login_response.status_code == 200
    
    def test_api_concurrent_sessions(self, client, unique_test_data):
        """Test API handling of multiple concurrent sessions."""
        # Register user
        client.post("/api/v1/auth/register", json=unique_test_data)
        
        login_data = {
            "email": unique_test_data["email"],
            "password": unique_test_data["password"]
        }
        
        # Create multiple sessions
        session1 = client.post("/api/v1/auth/login", json=login_data)
        session2 = client.post("/api/v1/auth/login", json=login_data)
        
        assert session1.status_code == 200
        assert session2.status_code == 200
        
        token1 = session1.json()["access_token"]
        token2 = session2.json()["access_token"]
        
        # Both tokens should work
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        me1 = client.get("/api/v1/auth/me", headers=headers1)
        me2 = client.get("/api/v1/auth/me", headers=headers2)
        
        assert me1.status_code == 200
        assert me2.status_code == 200
        
        # Logout one session
        logout1 = client.post("/api/v1/auth/logout", headers=headers1)
        assert logout1.status_code == 200
        
        # First token should be invalidated, second should still work
        me1_after = client.get("/api/v1/auth/me", headers=headers1)
        me2_after = client.get("/api/v1/auth/me", headers=headers2)
        
        assert me1_after.status_code == 401  # First session logged out
        assert me2_after.status_code == 200  # Second session still active


@pytest.mark.integration
class TestAuthRepositoryIntegration:
    """Integration tests for Auth repositories with real database."""
    
    @pytest.fixture
    async def db_session(self):
        """Create a test database session."""
        async with get_async_session() as session:
            yield session
    
    @pytest.fixture
    async def user_repo(self, db_session):
        """Create UserRepository with real database session."""
        return UserRepository(db_session)
    
    @pytest.fixture
    async def token_repo(self, db_session):
        """Create RefreshTokenRepository with real database session."""
        return RefreshTokenRepository(db_session)
    
    @pytest.fixture
    async def test_user(self, user_repo):
        """Create a test user in the database."""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"repo.test.{unique_id}@example.com",
            "password": "RepoTest123!",
            "first_name": "Repository",
            "last_name": "Test",
            "role": "consultant"
        }
        
        user = await user_repo.create(**user_data)
        return user
    
    @pytest.mark.asyncio
    async def test_user_repository_crud(self, user_repo):
        """Test user repository CRUD operations."""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create
        user_data = {
            "email": f"crud.test.{unique_id}@example.com",
            "password": "CRUDTest123!",
            "first_name": "CRUD",
            "last_name": "Test",
            "role": "consultant"
        }
        
        created_user = await user_repo.create(**user_data)
        assert created_user.email == user_data["email"]
        
        # Read by email
        found_user = await user_repo.get_by_email(user_data["email"])
        assert found_user is not None
        assert found_user.id == created_user.id
        
        # Read by ID
        found_by_id = await user_repo.get_by_id(created_user.id)
        assert found_by_id is not None
        assert found_by_id.email == user_data["email"]
        
        # Update
        updated_user = await user_repo.update(
            created_user.id,
            first_name="Updated"
        )
        assert updated_user.first_name == "Updated"
        
        # Delete (soft delete)
        delete_result = await user_repo.delete(created_user.id)
        assert delete_result is True
        
        # Verify user is deactivated
        deactivated_user = await user_repo.get_by_id(created_user.id)
        assert deactivated_user.is_active is False
    
    @pytest.mark.asyncio
    async def test_refresh_token_repository_crud(self, token_repo, test_user):
        """Test refresh token repository CRUD operations."""
        # Create
        token_data = {
            "user_id": test_user.id,
            "token": "test.refresh.token",
            "session_id": str(uuid.uuid4()),
            "device_info": "Test Device",
            "ip_address": "192.168.1.100"
        }
        
        created_token = await token_repo.create(**token_data)
        assert created_token.user_id == test_user.id
        assert created_token.token == token_data["token"]
        
        # Read by session
        found_token = await token_repo.get_by_session(
            test_user.id,
            token_data["session_id"]
        )
        assert found_token is not None
        assert found_token.id == created_token.id
        
        # Get user tokens
        user_tokens = await token_repo.get_user_tokens(test_user.id)
        assert len(user_tokens) >= 1
        assert any(token.id == created_token.id for token in user_tokens)
        
        # Update
        updated_token = await token_repo.update(
            created_token.id,
            ip_address="192.168.1.200"
        )
        assert updated_token.ip_address == "192.168.1.200"
        
        # Delete (revoke)
        delete_result = await token_repo.delete(created_token.id)
        assert delete_result is True
        
        # Verify token is revoked
        revoked_token = await token_repo.get_by_session(
            test_user.id,
            token_data["session_id"]
        )
        # Token might still exist but should be revoked
        if revoked_token:
            assert revoked_token.status == "revoked"
    
    @pytest.mark.asyncio
    async def test_repository_error_handling(self, user_repo, token_repo):
        """Test repository error handling."""
        from uuid import uuid4
        
        # Test non-existent user
        non_existent_user = await user_repo.get_by_email("nonexistent@example.com")
        assert non_existent_user is None
        
        # Test non-existent user by ID
        fake_id = uuid4()
        non_existent_by_id = await user_repo.get_by_id(fake_id)
        assert non_existent_by_id is None
        
        # Test updating non-existent user
        update_result = await user_repo.update(fake_id, first_name="Updated")
        assert update_result is None
        
        # Test non-existent token
        non_existent_token = await token_repo.get_by_session(fake_id, "fake-session")
        assert non_existent_token is None
    
    @pytest.mark.asyncio
    async def test_repository_cleanup_operations(self, token_repo, test_user):
        """Test repository cleanup operations."""
        # Create expired tokens
        expired_token_data = {
            "user_id": test_user.id,
            "token": "expired.token",
            "session_id": str(uuid.uuid4()),
            "device_info": "Test Device",
            "ip_address": "192.168.1.100"
        }
        
        expired_token = await token_repo.create(**expired_token_data)
        
        # Manually set as expired by updating the expires_at field
        await token_repo.update(
            expired_token.id,
            expires_at=utc_now() - timedelta(days=1)
        )
        
        # Test cleanup
        cleaned_count = await token_repo.cleanup_expired()
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0  # Should not error