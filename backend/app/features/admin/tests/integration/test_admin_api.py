"""
Integration tests for Admin API endpoints.
Tests complete request-response flow with real database.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.security import create_access_token
from database.models.auth import User, UserRole
from app.core.datetime_utils import utc_now

pytestmark = pytest.mark.asyncio


class TestAdminAPI:
    """Test Admin API endpoints with real database."""

    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    async def admin_user(self, test_session: AsyncSession):
        """Create admin user for testing."""
        admin = User(
            email="admin@example.com",
            password="AdminPass123!",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        admin.email_verified = True
        test_session.add(admin)
        await test_session.commit()
        await test_session.refresh(admin)
        return admin

    @pytest.fixture
    async def junior_user(self, test_session: AsyncSession):
        """Create junior recruiter for testing."""
        junior = User(
            email="junior@example.com",
            password="JuniorPass123!",
            first_name="Junior",
            last_name="Recruiter",
            role=UserRole.JUNIOR_RECRUITER
        )
        junior.email_verified = True
        test_session.add(junior)
        await test_session.commit()
        await test_session.refresh(junior)
        return junior

    @pytest.fixture
    async def senior_user(self, test_session: AsyncSession):
        """Create senior recruiter for testing."""
        senior = User(
            email="senior@example.com",
            password="SeniorPass123!",
            first_name="Senior",
            last_name="Recruiter",
            role=UserRole.SENIOR_RECRUITER
        )
        senior.email_verified = True
        test_session.add(senior)
        await test_session.commit()
        await test_session.refresh(senior)
        return senior

    def get_auth_headers(self, user: User) -> dict:
        """Get authorization headers for user."""
        token = create_access_token({"sub": str(user.id), "email": user.email})
        return {"Authorization": f"Bearer {token}"}

    async def test_create_user_success(self, client, admin_user):
        """Test successful user creation by admin."""
        headers = self.get_auth_headers(admin_user)

        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "junior_recruiter",
            "temporary_password": "TempPass123!"
        }

        response = client.post("/api/v1/admin/users", json=user_data, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["first_name"] == "New"
        assert data["last_name"] == "User"
        assert data["role"] == "junior_recruiter"
        assert data["is_active"] == True

    async def test_create_user_duplicate_email(self, client, admin_user, junior_user):
        """Test creating user with existing email."""
        headers = self.get_auth_headers(admin_user)

        user_data = {
            "email": junior_user.email,  # Existing email
            "first_name": "Duplicate",
            "last_name": "User",
            "role": "junior_recruiter",
            "temporary_password": "TempPass123!"
        }

        response = client.post("/api/v1/admin/users", json=user_data, headers=headers)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_create_user_non_admin(self, client, junior_user):
        """Test user creation by non-admin (should fail)."""
        headers = self.get_auth_headers(junior_user)

        user_data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "role": "junior_recruiter",
            "temporary_password": "TempPass123!"
        }

        response = client.post("/api/v1/admin/users", json=user_data, headers=headers)

        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    async def test_list_users_success(self, client, admin_user, junior_user, senior_user):
        """Test listing users by admin."""
        headers = self.get_auth_headers(admin_user)

        response = client.get("/api/v1/admin/users", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 3  # At least admin, junior, senior
        assert len(data["users"]) >= 3

        # Check user structure
        user_emails = [user["email"] for user in data["users"]]
        assert admin_user.email in user_emails
        assert junior_user.email in user_emails
        assert senior_user.email in user_emails

    async def test_list_users_with_search(self, client, admin_user, junior_user):
        """Test listing users with search filter."""
        headers = self.get_auth_headers(admin_user)

        response = client.get("/api/v1/admin/users?search=junior", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Should find junior user
        found_junior = False
        for user in data["users"]:
            if "junior" in user["email"].lower():
                found_junior = True
                break
        assert found_junior

    async def test_list_users_with_role_filter(self, client, admin_user, senior_user):
        """Test listing users with role filter."""
        headers = self.get_auth_headers(admin_user)

        response = client.get("/api/v1/admin/users?role=senior_recruiter", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # All returned users should be senior recruiters
        for user in data["users"]:
            assert user["role"] == "senior_recruiter"

    async def test_get_user_details_success(self, client, admin_user, junior_user):
        """Test getting user details by admin."""
        headers = self.get_auth_headers(admin_user)

        response = client.get(f"/api/v1/admin/users/{junior_user.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(junior_user.id)
        assert data["email"] == junior_user.email
        assert "assigned_candidates_count" in data
        assert "total_resumes_uploaded" in data
        assert "total_reviews_requested" in data

    async def test_get_user_details_not_found(self, client, admin_user):
        """Test getting details for non-existent user."""
        headers = self.get_auth_headers(admin_user)
        fake_id = uuid4()

        response = client.get(f"/api/v1/admin/users/{fake_id}", headers=headers)

        assert response.status_code == 404

    async def test_update_user_success(self, client, admin_user, junior_user):
        """Test updating user by admin."""
        headers = self.get_auth_headers(admin_user)

        update_data = {
            "is_active": False,
            "role": "senior_recruiter"
        }

        response = client.patch(f"/api/v1/admin/users/{junior_user.id}", json=update_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] == False
        assert data["role"] == "senior_recruiter"

    async def test_update_user_prevent_self_deactivation(self, client, admin_user):
        """Test admin cannot deactivate themselves."""
        headers = self.get_auth_headers(admin_user)

        update_data = {"is_active": False}

        response = client.patch(f"/api/v1/admin/users/{admin_user.id}", json=update_data, headers=headers)

        assert response.status_code == 400
        assert "Cannot deactivate your own account" in response.json()["detail"]

    async def test_reset_password_success(self, client, admin_user, junior_user):
        """Test password reset by admin."""
        headers = self.get_auth_headers(admin_user)

        reset_data = {
            "new_password": "NewPassword123!",
            "force_password_change": True
        }

        response = client.post(f"/api/v1/admin/users/{junior_user.id}/reset-password", json=reset_data, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "Password reset successfully" in data["message"]

    async def test_get_user_directory_admin(self, client, admin_user, junior_user, senior_user):
        """Test user directory access by admin."""
        headers = self.get_auth_headers(admin_user)

        response = client.get("/api/v1/admin/directory", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) >= 3

    async def test_get_user_directory_senior(self, client, senior_user):
        """Test user directory access by senior recruiter."""
        headers = self.get_auth_headers(senior_user)

        response = client.get("/api/v1/admin/directory", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "users" in data

    async def test_get_user_directory_junior_forbidden(self, client, junior_user):
        """Test user directory access denied for junior recruiter."""
        headers = self.get_auth_headers(junior_user)

        response = client.get("/api/v1/admin/directory", headers=headers)

        assert response.status_code == 403

    async def test_unauthorized_access(self, client, junior_user):
        """Test that junior recruiters cannot access admin endpoints."""
        headers = self.get_auth_headers(junior_user)

        # Try to list users
        response = client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 403

        # Try to create user
        user_data = {
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "junior_recruiter",
            "temporary_password": "TempPass123!"
        }
        response = client.post("/api/v1/admin/users", json=user_data, headers=headers)
        assert response.status_code == 403

    async def test_no_auth_access(self, client):
        """Test that endpoints require authentication."""
        # No auth headers
        response = client.get("/api/v1/admin/users")
        assert response.status_code == 403  # FastAPI security dependency