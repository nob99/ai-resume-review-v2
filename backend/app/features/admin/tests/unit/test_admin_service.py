"""
Unit tests for AdminService.
Tests business logic in isolation using mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4, UUID
from datetime import datetime

from app.features.admin.service import AdminService
from app.features.admin.schemas import AdminUserCreate, AdminUserUpdate, AdminPasswordReset, UserRole
from app.core.security import SecurityError
from database.models.auth import User, UserRole as DBUserRole


class TestAdminService:
    """Test AdminService business logic."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def admin_service(self, mock_session):
        """Create AdminService with mocked session."""
        return AdminService(mock_session)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user creation data."""
        return AdminUserCreate(
            email="test@example.com",
            first_name="Test",
            last_name="User",
            role=UserRole.JUNIOR_RECRUITER,
            temporary_password="TempPass123!"
        )

    @pytest.fixture
    def sample_user(self):
        """Sample user object."""
        return User(
            email="existing@example.com",
            password="ExistingPass123!",
            first_name="Existing",
            last_name="User",
            role=DBUserRole.JUNIOR_RECRUITER
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self, admin_service, sample_user_data):
        """Test successful user creation."""
        admin_id = uuid4()

        # Mock repository methods
        admin_service.user_repo.get_by_email = AsyncMock(return_value=None)
        admin_service.session.add = Mock()
        admin_service.session.commit = AsyncMock()
        admin_service.session.refresh = AsyncMock()

        with patch('app.features.admin.service.User') as mock_user_class:
            mock_user = Mock()
            mock_user.email = sample_user_data.email
            mock_user_class.return_value = mock_user

            result = await admin_service.create_user(sample_user_data, admin_id)

            # Verify user creation
            mock_user_class.assert_called_once_with(
                email=sample_user_data.email,
                password=sample_user_data.temporary_password,
                first_name=sample_user_data.first_name,
                last_name=sample_user_data.last_name,
                role=sample_user_data.role.value
            )

            # Verify database operations
            admin_service.session.add.assert_called_once_with(mock_user)
            admin_service.session.commit.assert_called_once()
            admin_service.session.refresh.assert_called_once_with(mock_user)

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, admin_service, sample_user_data, sample_user):
        """Test user creation with existing email."""
        admin_id = uuid4()

        # Mock existing user found
        admin_service.user_repo.get_by_email = AsyncMock(return_value=sample_user)

        with pytest.raises(SecurityError, match="already exists"):
            await admin_service.create_user(sample_user_data, admin_id)

    @pytest.mark.asyncio
    async def test_list_users_basic(self, admin_service):
        """Test basic user listing."""
        # Mock user data
        mock_users = [
            Mock(
                id=uuid4(),
                email="user1@example.com",
                first_name="User",
                last_name="One",
                role=DBUserRole.JUNIOR_RECRUITER.value,
                is_active=True,
                email_verified=True,
                last_login_at=None,
                created_at=datetime.now()
            ),
            Mock(
                id=uuid4(),
                email="user2@example.com",
                first_name="User",
                last_name="Two",
                role=DBUserRole.SENIOR_RECRUITER.value,
                is_active=True,
                email_verified=True,
                last_login_at=None,
                created_at=datetime.now()
            )
        ]

        # Mock query execution
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users

        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 2

        # Mock the count queries for candidate assignments
        mock_count_result_0 = Mock()
        mock_count_result_0.scalar.return_value = 0
        mock_count_result_2 = Mock()
        mock_count_result_2.scalar.return_value = 0

        admin_service.session.execute = AsyncMock(side_effect=[mock_count_result, mock_result, mock_count_result_0, mock_count_result_2])

        result = await admin_service.list_users()

        # Verify response structure
        assert result.total == 2
        assert result.page == 1
        assert result.page_size == 20
        assert len(result.users) == 2
        assert result.users[0].email == "user1@example.com"
        assert result.users[1].email == "user2@example.com"

    @pytest.mark.asyncio
    async def test_get_user_details_found(self, admin_service, sample_user):
        """Test getting user details when user exists."""
        user_id = uuid4()
        sample_user.id = user_id

        # Mock repository and query results
        admin_service.user_repo.get_by_id = AsyncMock(return_value=sample_user)

        # Mock count queries
        mock_count_results = [Mock(), Mock(), Mock()]
        for mock_result in mock_count_results:
            mock_result.scalar.return_value = 0

        admin_service.session.execute = AsyncMock(side_effect=mock_count_results)

        result = await admin_service.get_user_details(user_id)

        assert result is not None
        assert result.id == user_id
        assert result.email == sample_user.email
        assert result.assigned_candidates_count == 0
        assert result.total_resumes_uploaded == 0
        assert result.total_reviews_requested == 0

    @pytest.mark.asyncio
    async def test_get_user_details_not_found(self, admin_service):
        """Test getting user details when user doesn't exist."""
        user_id = uuid4()

        admin_service.user_repo.get_by_id = AsyncMock(return_value=None)

        result = await admin_service.get_user_details(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, admin_service, sample_user):
        """Test successful user update."""
        user_id = uuid4()
        admin_id = uuid4()
        sample_user.id = user_id

        update_data = AdminUserUpdate(
            is_active=False,
            role=UserRole.SENIOR_RECRUITER
        )

        # Mock repository
        admin_service.user_repo.get_by_id = AsyncMock(return_value=sample_user)
        admin_service.session.commit = AsyncMock()
        admin_service.session.refresh = AsyncMock()

        result = await admin_service.update_user(user_id, update_data, admin_id)

        # Verify updates
        assert result == sample_user
        assert sample_user.is_active == False
        assert sample_user.role == UserRole.SENIOR_RECRUITER.value
        admin_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, admin_service):
        """Test updating non-existent user."""
        user_id = uuid4()
        admin_id = uuid4()

        update_data = AdminUserUpdate(is_active=False)

        admin_service.user_repo.get_by_id = AsyncMock(return_value=None)

        result = await admin_service.update_user(user_id, update_data, admin_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_reset_user_password_success(self, admin_service, sample_user):
        """Test successful password reset."""
        user_id = uuid4()
        admin_id = uuid4()
        sample_user.id = user_id

        reset_data = AdminPasswordReset(
            new_password="NewPass123!",
            force_password_change=True
        )

        # Mock user methods
        sample_user.set_password = Mock()
        sample_user.unlock_account = Mock()

        admin_service.user_repo.get_by_id = AsyncMock(return_value=sample_user)
        admin_service.session.commit = AsyncMock()

        result = await admin_service.reset_user_password(user_id, reset_data, admin_id)

        assert result == True
        sample_user.set_password.assert_called_once_with("NewPass123!")
        sample_user.unlock_account.assert_called_once()
        admin_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_user_password_not_found(self, admin_service):
        """Test password reset for non-existent user."""
        user_id = uuid4()
        admin_id = uuid4()

        reset_data = AdminPasswordReset(
            new_password="NewPass123!",
            force_password_change=True
        )

        admin_service.user_repo.get_by_id = AsyncMock(return_value=None)

        result = await admin_service.reset_user_password(user_id, reset_data, admin_id)

        assert result == False

    @pytest.mark.asyncio
    async def test_get_user_directory(self, admin_service):
        """Test getting user directory."""
        mock_users = [
            Mock(
                id=uuid4(),
                email="user1@example.com",
                first_name="User",
                last_name="One",
                role=DBUserRole.JUNIOR_RECRUITER.value,
                is_active=True
            ),
            Mock(
                id=uuid4(),
                email="user2@example.com",
                first_name="User",
                last_name="Two",
                role=DBUserRole.SENIOR_RECRUITER.value,
                is_active=True
            )
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users

        admin_service.session.execute = AsyncMock(return_value=mock_result)

        result = await admin_service.get_user_directory()

        assert result.total == 2
        assert len(result.users) == 2
        assert result.users[0].email == "user1@example.com"
        assert result.users[0].full_name == "User One"