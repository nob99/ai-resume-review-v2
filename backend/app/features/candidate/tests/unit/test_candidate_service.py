"""Unit tests for candidate service."""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.features.candidate.service import CandidateService
from database.models.candidate import Candidate
from database.models.assignment import UserCandidateAssignment
from database.models.auth import User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def candidate_service(mock_db):
    """Create candidate service with mock DB."""
    return CandidateService(mock_db)


@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.role = 'junior_recruiter'
    user.email = 'test@example.com'
    return user


@pytest.fixture
def sample_admin_user():
    """Create sample admin user for testing."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.role = 'admin'
    user.email = 'admin@example.com'
    return user


@pytest.fixture
def sample_candidate():
    """Create sample candidate for testing."""
    candidate = Mock(spec=Candidate)
    candidate.id = uuid.uuid4()
    candidate.first_name = 'John'
    candidate.last_name = 'Doe'
    candidate.email = 'john@example.com'
    candidate.status = 'active'
    return candidate


class TestCandidateService:
    """Test candidate service functionality."""

    @pytest.mark.asyncio
    async def test_create_candidate_success(self, candidate_service, mock_db, sample_user):
        """Test successful candidate creation."""
        created_candidate = Mock(spec=Candidate)
        created_candidate.id = uuid.uuid4()

        # Mock database operations
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()

        # Mock Candidate constructor
        with patch('app.features.candidate.service.Candidate') as mock_candidate_class:
            mock_candidate_class.return_value = created_candidate

            with patch('app.features.candidate.service.UserCandidateAssignment') as mock_assignment_class:
                mock_assignment = Mock()
                mock_assignment_class.return_value = mock_assignment

                result = await candidate_service.create_candidate(
                    first_name='John',
                    last_name='Doe',
                    created_by_user_id=sample_user.id,
                    email='john@example.com'
                )

                assert result == created_candidate
                assert mock_db.add.call_count == 2  # Candidate + Assignment
                mock_db.flush.assert_called_once()
                mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_candidate_database_error(self, candidate_service, mock_db, sample_user):
        """Test candidate creation with database error."""
        mock_db.add = Mock()
        mock_db.flush = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = Mock()

        with patch('app.features.candidate.service.Candidate'):
            with pytest.raises(HTTPException) as exc_info:
                await candidate_service.create_candidate(
                    first_name='John',
                    last_name='Doe',
                    created_by_user_id=sample_user.id
                )

            assert exc_info.value.status_code == 500
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_candidates_for_admin_user(self, candidate_service, mock_db, sample_admin_user, sample_candidate):
        """Test getting candidates for admin user (sees all)."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [sample_candidate]

        mock_db.query.return_value = mock_query
        mock_db.query.return_value.filter.return_value.first.return_value = sample_admin_user

        result = await candidate_service.get_candidates_for_user(
            user_id=sample_admin_user.id,
            limit=10,
            offset=0
        )

        assert len(result) == 1
        assert result[0] == sample_candidate

    @pytest.mark.asyncio
    async def test_get_candidates_for_junior_recruiter(self, candidate_service, mock_db, sample_user, sample_candidate):
        """Test getting candidates for junior recruiter (only assigned)."""
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [sample_candidate]

        # First query for user
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_user

        # Second query for candidates
        mock_db.query.side_effect = [mock_user_query, mock_query]

        result = await candidate_service.get_candidates_for_user(
            user_id=sample_user.id,
            limit=10,
            offset=0
        )

        assert len(result) == 1
        assert result[0] == sample_candidate

    @pytest.mark.asyncio
    async def test_get_candidates_user_not_found(self, candidate_service, mock_db):
        """Test getting candidates when user not found."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(HTTPException) as exc_info:
            await candidate_service.get_candidates_for_user(
                user_id=uuid.uuid4(),
                limit=10,
                offset=0
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_candidate_by_id_success(self, candidate_service, mock_db, sample_user, sample_candidate):
        """Test successfully getting candidate by ID."""
        # Mock access check
        with patch.object(candidate_service, '_user_has_candidate_access', return_value=True):
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = sample_candidate
            mock_db.query.return_value = mock_query

            result = await candidate_service.get_candidate_by_id(
                candidate_id=sample_candidate.id,
                user_id=sample_user.id
            )

            assert result == sample_candidate

    @pytest.mark.asyncio
    async def test_get_candidate_by_id_access_denied(self, candidate_service, sample_user, sample_candidate):
        """Test getting candidate by ID with access denied."""
        with patch.object(candidate_service, '_user_has_candidate_access', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await candidate_service.get_candidate_by_id(
                    candidate_id=sample_candidate.id,
                    user_id=sample_user.id
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_candidate_success(self, candidate_service, mock_db, sample_admin_user):
        """Test successful candidate assignment."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock admin user check
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_admin_user

        # Mock existing assignment check (none found)
        mock_assignment_query = Mock()
        mock_assignment_query.filter.return_value.first.return_value = None

        mock_db.query.side_effect = [mock_user_query, mock_assignment_query]
        mock_db.add = Mock()
        mock_db.commit = Mock()

        with patch('app.features.candidate.service.UserCandidateAssignment') as mock_assignment_class:
            mock_assignment = Mock()
            mock_assignment_class.return_value = mock_assignment

            result = await candidate_service.assign_candidate(
                candidate_id=candidate_id,
                user_id=user_id,
                assigned_by_user_id=sample_admin_user.id
            )

            assert result is True
            mock_db.add.assert_called_once_with(mock_assignment)
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_candidate_insufficient_permissions(self, candidate_service, mock_db, sample_user):
        """Test candidate assignment with insufficient permissions."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock junior recruiter user (insufficient permissions)
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value = mock_user_query

        with pytest.raises(HTTPException) as exc_info:
            await candidate_service.assign_candidate(
                candidate_id=candidate_id,
                user_id=user_id,
                assigned_by_user_id=sample_user.id
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_assign_candidate_already_assigned(self, candidate_service, mock_db, sample_admin_user):
        """Test candidate assignment when already assigned."""
        candidate_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock admin user check
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_admin_user

        # Mock existing assignment (found)
        existing_assignment = Mock()
        mock_assignment_query = Mock()
        mock_assignment_query.filter.return_value.first.return_value = existing_assignment

        mock_db.query.side_effect = [mock_user_query, mock_assignment_query]

        result = await candidate_service.assign_candidate(
            candidate_id=candidate_id,
            user_id=user_id,
            assigned_by_user_id=sample_admin_user.id
        )

        assert result is True  # Returns True for already assigned

    @pytest.mark.asyncio
    async def test_user_has_candidate_access_admin(self, candidate_service, mock_db, sample_admin_user):
        """Test admin user has access to all candidates."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_admin_user
        mock_db.query.return_value = mock_query

        result = await candidate_service._user_has_candidate_access(
            user_id=sample_admin_user.id,
            candidate_id=uuid.uuid4()
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_user_has_candidate_access_junior_with_assignment(self, candidate_service, mock_db, sample_user):
        """Test junior recruiter with assignment has access."""
        candidate_id = uuid.uuid4()

        # Mock user query
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_user

        # Mock assignment query (found)
        assignment = Mock()
        mock_assignment_query = Mock()
        mock_assignment_query.filter.return_value.first.return_value = assignment

        mock_db.query.side_effect = [mock_user_query, mock_assignment_query]

        result = await candidate_service._user_has_candidate_access(
            user_id=sample_user.id,
            candidate_id=candidate_id
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_user_has_candidate_access_junior_without_assignment(self, candidate_service, mock_db, sample_user):
        """Test junior recruiter without assignment has no access."""
        candidate_id = uuid.uuid4()

        # Mock user query
        mock_user_query = Mock()
        mock_user_query.filter.return_value.first.return_value = sample_user

        # Mock assignment query (not found)
        mock_assignment_query = Mock()
        mock_assignment_query.filter.return_value.first.return_value = None

        mock_db.query.side_effect = [mock_user_query, mock_assignment_query]

        result = await candidate_service._user_has_candidate_access(
            user_id=sample_user.id,
            candidate_id=candidate_id
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_user_has_candidate_access_user_not_found(self, candidate_service, mock_db):
        """Test access check when user not found."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = await candidate_service._user_has_candidate_access(
            user_id=uuid.uuid4(),
            candidate_id=uuid.uuid4()
        )

        assert result is False