"""Unit tests for candidate API endpoints."""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.features.candidate.api import router
from app.features.candidate.schemas import CandidateCreate
from database.models.auth import User
from database.models.candidate import Candidate


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def mock_current_user():
    """Create a mock current user."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.role = "junior_recruiter"
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@example.com"
    user.role = "admin"
    return user


@pytest.fixture
def sample_candidate():
    """Create a sample candidate."""
    from datetime import datetime

    candidate = Mock(spec=Candidate)
    candidate.id = uuid.uuid4()
    candidate.first_name = "John"
    candidate.last_name = "Doe"
    candidate.email = "john@example.com"
    candidate.phone = "123-456-7890"
    candidate.current_company = "Tech Corp"
    candidate.current_position = "Engineer"
    candidate.years_experience = 5
    candidate.status = "active"
    candidate.created_at = datetime.now()
    return candidate


class TestCandidateAPI:
    """Test candidate API endpoints."""

    @pytest.mark.asyncio
    async def test_create_candidate_success(self, mock_db, mock_current_user, sample_candidate):
        """Test successful candidate creation via API."""

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.create_candidate = AsyncMock(return_value=sample_candidate)
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import create_candidate

                    candidate_data = CandidateCreate(
                        first_name="John",
                        last_name="Doe",
                        email="john@example.com"
                    )

                    response = await create_candidate(
                        candidate_data=candidate_data,
                        current_user=mock_current_user,
                        db=mock_db
                    )

                    assert response.success is True
                    assert response.message == "Candidate created successfully"
                    assert response.candidate is not None
                    assert response.error is None

                    mock_service.create_candidate.assert_called_once_with(
                        first_name="John",
                        last_name="Doe",
                        created_by_user_id=mock_current_user.id,
                        email="john@example.com",
                        phone=None,
                        current_company=None,
                        current_position=None,
                        years_experience=None
                    )

    @pytest.mark.asyncio
    async def test_create_candidate_service_error(self, mock_db, mock_current_user):
        """Test candidate creation with service error."""

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.create_candidate = AsyncMock(side_effect=HTTPException(status_code=500, detail="Database error"))
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import create_candidate

                    candidate_data = CandidateCreate(
                        first_name="John",
                        last_name="Doe"
                    )

                    with pytest.raises(HTTPException) as exc_info:
                        await create_candidate(
                            candidate_data=candidate_data,
                            current_user=mock_current_user,
                            db=mock_db
                        )

                    assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_candidates_success(self, mock_db, mock_current_user, sample_candidate):
        """Test successful candidate retrieval."""

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_candidates_for_user = AsyncMock(return_value=[sample_candidate])
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import get_candidates

                    response = await get_candidates(
                        limit=10,
                        offset=0,
                        current_user=mock_current_user,
                        db=mock_db
                    )

                    assert len(response.candidates) == 1
                    assert response.total_count == 1
                    assert response.limit == 10
                    assert response.offset == 0

                    mock_service.get_candidates_for_user.assert_called_once_with(
                        user_id=mock_current_user.id,
                        limit=10,
                        offset=0
                    )

    @pytest.mark.asyncio
    async def test_get_candidates_empty_result(self, mock_db, mock_current_user):
        """Test candidate retrieval with empty result."""

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_candidates_for_user = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import get_candidates

                    response = await get_candidates(
                        limit=10,
                        offset=0,
                        current_user=mock_current_user,
                        db=mock_db
                    )

                    assert len(response.candidates) == 0
                    assert response.total_count == 0

    @pytest.mark.asyncio
    async def test_get_candidate_by_id_success(self, mock_db, mock_current_user, sample_candidate):
        """Test successful candidate retrieval by ID."""

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_candidate_by_id = AsyncMock(return_value=sample_candidate)
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import get_candidate

                    response = await get_candidate(
                        candidate_id=sample_candidate.id,
                        current_user=mock_current_user,
                        db=mock_db
                    )

                    assert response.id == sample_candidate.id
                    assert response.first_name == sample_candidate.first_name

                    mock_service.get_candidate_by_id.assert_called_once_with(
                        candidate_id=sample_candidate.id,
                        user_id=mock_current_user.id
                    )

    @pytest.mark.asyncio
    async def test_get_candidate_by_id_not_found(self, mock_db, mock_current_user):
        """Test candidate retrieval by ID when not found."""
        candidate_id = uuid.uuid4()

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_candidate_by_id = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import get_candidate

                    with pytest.raises(HTTPException) as exc_info:
                        await get_candidate(
                            candidate_id=candidate_id,
                            current_user=mock_current_user,
                            db=mock_db
                        )

                    assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_candidate_by_id_access_denied(self, mock_db, mock_current_user):
        """Test candidate retrieval with access denied."""
        candidate_id = uuid.uuid4()

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.get_candidate_by_id = AsyncMock(
                side_effect=HTTPException(status_code=403, detail="Access denied")
            )
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import get_candidate

                    with pytest.raises(HTTPException) as exc_info:
                        await get_candidate(
                            candidate_id=candidate_id,
                            current_user=mock_current_user,
                            db=mock_db
                        )

                    assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_candidate_success(self, mock_db, mock_admin_user):
        """Test successful candidate assignment."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.assign_candidate = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_admin_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import assign_candidate

                    response = await assign_candidate(
                        candidate_id=candidate_id,
                        user_id=user_id,
                        assignment_type="secondary",
                        current_user=mock_admin_user,
                        db=mock_db
                    )

                    assert response["success"] is True
                    assert response["message"] == "Candidate assigned successfully"

                    mock_service.assign_candidate.assert_called_once_with(
                        candidate_id=candidate_id,
                        user_id=user_id,
                        assigned_by_user_id=mock_admin_user.id,
                        assignment_type="secondary"
                    )

    @pytest.mark.asyncio
    async def test_assign_candidate_insufficient_permissions(self, mock_db, mock_current_user):
        """Test candidate assignment with insufficient permissions."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.assign_candidate = AsyncMock(
                side_effect=HTTPException(status_code=403, detail="Insufficient permissions")
            )
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import assign_candidate

                    with pytest.raises(HTTPException) as exc_info:
                        await assign_candidate(
                            candidate_id=candidate_id,
                            user_id=user_id,
                            assignment_type="secondary",
                            current_user=mock_current_user,
                            db=mock_db
                        )

                    assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_candidate_failure(self, mock_db, mock_admin_user):
        """Test candidate assignment failure."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with patch('app.features.candidate.api.CandidateService') as mock_service_class:
            mock_service = Mock()
            mock_service.assign_candidate = AsyncMock(return_value=False)
            mock_service_class.return_value = mock_service

            with patch('app.features.candidate.api.get_current_user', return_value=mock_admin_user):
                with patch('app.features.candidate.api.get_db', return_value=mock_db):
                    from app.features.candidate.api import assign_candidate

                    with pytest.raises(HTTPException) as exc_info:
                        await assign_candidate(
                            candidate_id=candidate_id,
                            user_id=user_id,
                            assignment_type="secondary",
                            current_user=mock_admin_user,
                            db=mock_db
                        )

                    assert exc_info.value.status_code == 400


class TestCandidateAPIValidation:
    """Test API input validation."""

    @pytest.mark.asyncio
    async def test_create_candidate_invalid_data(self, mock_db, mock_current_user):
        """Test candidate creation with invalid data."""

        with patch('app.features.candidate.api.get_current_user', return_value=mock_current_user):
            with patch('app.features.candidate.api.get_db', return_value=mock_db):
                from app.features.candidate.api import create_candidate

                # Test with invalid email in CandidateCreate schema
                with pytest.raises(Exception):  # Pydantic validation error
                    candidate_data = CandidateCreate(
                        first_name="John",
                        last_name="Doe",
                        email="invalid-email"  # Invalid email format
                    )

    def test_candidate_create_schema_validation(self):
        """Test CandidateCreate schema validation."""

        # Valid data should work
        valid_data = CandidateCreate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            years_experience=5
        )
        assert valid_data.first_name == "John"

        # Invalid email should raise validation error
        with pytest.raises(Exception):
            CandidateCreate(
                first_name="John",
                last_name="Doe",
                email="invalid-email"
            )

        # Negative years experience should raise validation error
        with pytest.raises(Exception):
            CandidateCreate(
                first_name="John",
                last_name="Doe",
                years_experience=-1
            )