"""
Integration tests for profile management endpoints.
Tests the complete profile feature with real database connections.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.features.auth.service import AuthService
from app.features.auth.repository import UserRepository, RefreshTokenRepository
from app.features.auth.schemas import LoginRequest, UserCreate
from app.core.database import get_async_session
from database.models.auth import User


@pytest.mark.integration
class TestProfileAPI:
    """Integration tests for profile API endpoints."""

    @pytest.fixture
    async def db_session(self):
        """Create a test database session."""
        async with get_async_session() as session:
            yield session

    @pytest.fixture
    async def auth_service(self, db_session):
        """Create AuthService for user creation and authentication."""
        user_repo = UserRepository(db_session)
        token_repo = RefreshTokenRepository(db_session)
        return AuthService(user_repo=user_repo, token_repo=token_repo)

    @pytest.fixture
    async def test_user_with_token(self, auth_service):
        """Create a test user and return access token."""
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"profile.test.{unique_id}@example.com",
            "password": "ProfileTest123!",
            "first_name": "Profile",
            "last_name": "Test",
            "role": "consultant"
        }

        # Register user
        user_create = UserCreate(**user_data)
        registered_user = await auth_service.register_user(user_create)

        # Login to get token
        login_request = LoginRequest(
            email=user_data["email"],
            password=user_data["password"]
        )
        login_response = await auth_service.login(
            login_request=login_request,
            client_ip="127.0.0.1",
            user_agent="Test Client"
        )

        return {
            "user": registered_user,
            "token": login_response.access_token,
            "password": user_data["password"]
        }

    @pytest.mark.asyncio
    async def test_get_profile_success(self, test_user_with_token):
        """Test GET /profile/me returns current user profile."""
        client = TestClient(app)
        token = test_user_with_token["token"]

        response = client.get(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_with_token["user"].email
        assert data["first_name"] == "Profile"
        assert data["last_name"] == "Test"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_profile_unauthenticated(self):
        """Test GET /profile/me returns 401 without token."""
        client = TestClient(app)

        response = client.get("/api/v1/profile/me")

        assert response.status_code == 403  # FastAPI security returns 403 for missing auth

    @pytest.mark.asyncio
    async def test_update_profile_success(self, test_user_with_token):
        """Test PATCH /profile/me updates user profile successfully."""
        client = TestClient(app)
        token = test_user_with_token["token"]

        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }

        response = client.patch(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["email"] == test_user_with_token["user"].email

    @pytest.mark.asyncio
    async def test_update_profile_empty_names(self, test_user_with_token):
        """Test PATCH /profile/me rejects empty names."""
        client = TestClient(app)
        token = test_user_with_token["token"]

        update_data = {
            "first_name": "   ",
            "last_name": "Valid"
        }

        response = client.patch(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_update_profile_unauthenticated(self):
        """Test PATCH /profile/me returns 401 without token."""
        client = TestClient(app)

        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }

        response = client.patch(
            "/api/v1/profile/me",
            json=update_data
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_change_password_success(self, test_user_with_token):
        """Test POST /profile/change-password changes password successfully."""
        client = TestClient(app)
        token = test_user_with_token["token"]
        current_password = test_user_with_token["password"]

        password_data = {
            "current_password": current_password,
            "new_password": "NewSecurePassword123!"
        }

        response = client.post(
            "/api/v1/profile/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json=password_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Password changed successfully"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, test_user_with_token):
        """Test POST /profile/change-password fails with incorrect current password."""
        client = TestClient(app)
        token = test_user_with_token["token"]

        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePassword123!"
        }

        response = client.post(
            "/api/v1/profile/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json=password_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "Current password is incorrect" in data["detail"]

    @pytest.mark.asyncio
    async def test_change_password_same_as_current(self, test_user_with_token):
        """Test POST /profile/change-password fails when new password is same as current."""
        client = TestClient(app)
        token = test_user_with_token["token"]
        current_password = test_user_with_token["password"]

        password_data = {
            "current_password": current_password,
            "new_password": current_password  # Same as current
        }

        response = client.post(
            "/api/v1/profile/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json=password_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "must be different" in data["detail"]

    @pytest.mark.asyncio
    async def test_change_password_weak_password(self, test_user_with_token):
        """Test POST /profile/change-password fails with weak password."""
        client = TestClient(app)
        token = test_user_with_token["token"]
        current_password = test_user_with_token["password"]

        password_data = {
            "current_password": current_password,
            "new_password": "weak"  # Too short, no uppercase, no special chars
        }

        response = client.post(
            "/api/v1/profile/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json=password_data
        )

        assert response.status_code == 422  # Pydantic validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_change_password_unauthenticated(self):
        """Test POST /profile/change-password returns 401 without token."""
        client = TestClient(app)

        password_data = {
            "current_password": "Current123!",
            "new_password": "NewPassword123!"
        }

        response = client.post(
            "/api/v1/profile/change-password",
            json=password_data
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_profile_update_preserves_email(self, test_user_with_token):
        """Test that profile update does not change email."""
        client = TestClient(app)
        token = test_user_with_token["token"]
        original_email = test_user_with_token["user"].email

        update_data = {
            "first_name": "NewFirst",
            "last_name": "NewLast"
        }

        response = client.patch(
            "/api/v1/profile/me",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == original_email  # Email unchanged
        assert data["first_name"] == "NewFirst"
        assert data["last_name"] == "NewLast"