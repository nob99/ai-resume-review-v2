"""Unit tests for role-based access control in analysis feature."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.features.resume_analysis.service import AnalysisService
from app.features.resume_analysis.repository import AnalysisRepository
from database.models import ReviewRequest, ReviewResult


class TestAnalysisAccessControl:
    """Test role-based access control for analysis operations."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def service(self, mock_session, mock_repository):
        """Create service instance with mocked dependencies."""
        service = AnalysisService(mock_session)
        service.repository = mock_repository
        return service

    @pytest.fixture
    def mock_request(self):
        """Create mock ReviewRequest."""
        request = MagicMock(spec=ReviewRequest)
        request.id = uuid.uuid4()
        request.requested_by_user_id = uuid.uuid4()
        request.status = "completed"
        request.target_industry = "tech_consulting"
        request.requested_at = MagicMock()
        request.completed_at = MagicMock()
        return request

    @pytest.fixture
    def mock_result(self):
        """Create mock ReviewResult."""
        result = MagicMock(spec=ReviewResult)
        result.id = uuid.uuid4()
        result.overall_score = 75
        result.ats_score = 80
        result.content_score = 70
        result.formatting_score = 75
        result.executive_summary = "Test summary"
        result.detailed_scores = {}
        result.ai_model_used = "gpt-4"
        result.processing_time_ms = 1000
        return result

    @pytest.mark.asyncio
    async def test_admin_can_view_any_analysis(
        self,
        service,
        mock_repository,
        mock_request,
        mock_result
    ):
        """Admin can view any user's analysis."""
        # Setup
        admin_id = uuid.uuid4()
        analysis_id = mock_request.id

        mock_repository.get_analysis_for_user.return_value = (mock_request, mock_result)

        # Execute
        result = await service.get_analysis_result(
            request_id=analysis_id,
            user_id=admin_id,
            user_role='admin'
        )

        # Verify
        assert result is not None
        assert result.analysis_id == str(mock_request.id)
        mock_repository.get_analysis_for_user.assert_called_once_with(
            analysis_id=analysis_id,
            user_id=admin_id,
            user_role='admin'
        )

    @pytest.mark.asyncio
    async def test_senior_can_view_any_analysis(
        self,
        service,
        mock_repository,
        mock_request,
        mock_result
    ):
        """Senior can view any user's analysis."""
        # Setup
        senior_id = uuid.uuid4()
        junior_id = uuid.uuid4()
        analysis_id = mock_request.id

        mock_request.requested_by_user_id = junior_id
        mock_repository.get_analysis_for_user.return_value = (mock_request, mock_result)

        # Execute
        result = await service.get_analysis_result(
            request_id=analysis_id,
            user_id=senior_id,
            user_role='senior_recruiter'
        )

        # Verify
        assert result is not None
        assert result.analysis_id == str(mock_request.id)
        mock_repository.get_analysis_for_user.assert_called_once_with(
            analysis_id=analysis_id,
            user_id=senior_id,
            user_role='senior_recruiter'
        )

    @pytest.mark.asyncio
    async def test_junior_can_view_own_analysis(
        self,
        service,
        mock_repository,
        mock_request,
        mock_result
    ):
        """Junior can view their own analysis."""
        # Setup
        junior_id = uuid.uuid4()
        analysis_id = mock_request.id

        mock_request.requested_by_user_id = junior_id
        mock_repository.get_analysis_for_user.return_value = (mock_request, mock_result)

        # Execute
        result = await service.get_analysis_result(
            request_id=analysis_id,
            user_id=junior_id,
            user_role='junior_recruiter'
        )

        # Verify
        assert result is not None
        assert result.analysis_id == str(mock_request.id)
        mock_repository.get_analysis_for_user.assert_called_once_with(
            analysis_id=analysis_id,
            user_id=junior_id,
            user_role='junior_recruiter'
        )

    @pytest.mark.asyncio
    async def test_junior_cannot_view_other_analysis(
        self,
        service,
        mock_repository
    ):
        """Junior cannot view other junior's analysis."""
        # Setup
        junior_a_id = uuid.uuid4()
        analysis_id = uuid.uuid4()

        # Repository returns None when access is denied
        mock_repository.get_analysis_for_user.return_value = None

        # Execute & Verify
        with pytest.raises(ValueError, match="access denied"):
            await service.get_analysis_result(
                request_id=analysis_id,
                user_id=junior_a_id,
                user_role='junior_recruiter'
            )

        mock_repository.get_analysis_for_user.assert_called_once_with(
            analysis_id=analysis_id,
            user_id=junior_a_id,
            user_role='junior_recruiter'
        )

    @pytest.mark.asyncio
    async def test_list_analyses_admin_sees_all(
        self,
        service,
        mock_repository,
        mock_request
    ):
        """Admin sees all analyses in list."""
        # Setup
        admin_id = uuid.uuid4()
        mock_repository.list_analyses_for_user.return_value = [mock_request]
        mock_repository.count_analyses_for_user.return_value = 1
        service.resume_repository = AsyncMock()
        service.resume_repository.get_by_id_with_candidate.return_value = None

        # Execute
        result = await service.list_user_analyses(
            user_id=admin_id,
            user_role='admin',
            limit=10,
            offset=0
        )

        # Verify
        mock_repository.list_analyses_for_user.assert_called_once()
        args = mock_repository.list_analyses_for_user.call_args
        assert args.kwargs['user_role'] == 'admin'

    @pytest.mark.asyncio
    async def test_list_analyses_senior_sees_all(
        self,
        service,
        mock_repository,
        mock_request
    ):
        """Senior sees all analyses in list."""
        # Setup
        senior_id = uuid.uuid4()
        mock_repository.list_analyses_for_user.return_value = [mock_request]
        mock_repository.count_analyses_for_user.return_value = 1
        service.resume_repository = AsyncMock()
        service.resume_repository.get_by_id_with_candidate.return_value = None

        # Execute
        result = await service.list_user_analyses(
            user_id=senior_id,
            user_role='senior_recruiter',
            limit=10,
            offset=0
        )

        # Verify
        mock_repository.list_analyses_for_user.assert_called_once()
        args = mock_repository.list_analyses_for_user.call_args
        assert args.kwargs['user_role'] == 'senior_recruiter'

    @pytest.mark.asyncio
    async def test_list_analyses_junior_sees_own_only(
        self,
        service,
        mock_repository,
        mock_request
    ):
        """Junior sees only own analyses in list."""
        # Setup
        junior_id = uuid.uuid4()
        mock_request.requested_by_user_id = junior_id
        mock_repository.list_analyses_for_user.return_value = [mock_request]
        mock_repository.count_analyses_for_user.return_value = 1
        service.resume_repository = AsyncMock()
        service.resume_repository.get_by_id_with_candidate.return_value = None

        # Execute
        result = await service.list_user_analyses(
            user_id=junior_id,
            user_role='junior_recruiter',
            limit=10,
            offset=0
        )

        # Verify
        mock_repository.list_analyses_for_user.assert_called_once()
        args = mock_repository.list_analyses_for_user.call_args
        assert args.kwargs['user_role'] == 'junior_recruiter'
        assert args.kwargs['user_id'] == junior_id
