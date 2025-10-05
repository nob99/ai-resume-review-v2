"""Comprehensive integration tests for resume_analysis feature.

This test suite covers the new resume-referencing architecture where analysis
requests reference uploaded resumes by ID instead of requiring text copy/paste.

Test Coverage:
- Service layer: Resume-referencing analysis, polling, async processing
- API layer: All endpoints with authentication and validation
- Integration: Communication with resume_upload service
- Access control: User permission validation via candidates
- Performance: Concurrent analysis handling and rate limiting
- Error scenarios: Invalid resumes, processing failures, timeout handling
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status

# Import the schemas and service
from app.features.resume_analysis.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResult,
    AnalysisStatus,
    Industry,
    AnalysisDepth,
    MarketTier,
    ScoreDetails,
    FeedbackSection
)
from app.features.resume_analysis.service import (
    AnalysisService,
    AnalysisValidationException,
    AnalysisException
)
from app.features.resume_analysis.api import router


@pytest.fixture
def mock_resume_upload_service():
    """Mock resume upload service for testing integration."""
    service = MagicMock()
    service.get_resume = AsyncMock()
    service.get_resume.return_value = MagicMock(
        id=str(uuid.uuid4()),
        candidate_id=str(uuid.uuid4()),
        text_content="Sample resume content for testing analysis",
        file_name="test_resume.pdf",
        created_at=datetime.utcnow()
    )
    return service


@pytest.fixture
def mock_candidate_service():
    """Mock candidate service for access control testing."""
    service = MagicMock()
    service.can_user_access_candidate = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_ai_orchestrator():
    """Mock AI orchestrator for analysis processing."""
    orchestrator = MagicMock()
    orchestrator.analyze_resume = AsyncMock()
    orchestrator.analyze_resume.return_value = {
        "overall_score": 85.5,
        "market_tier": MarketTier.TIER_1,
        "structure_scores": {
            "overall": 88.0,
            "formatting": 85.0,
            "content": 90.0
        },
        "appeal_scores": {
            "overall": 83.0,
            "impact": 85.0,
            "relevance": 81.0
        },
        "structure_feedback": {
            "strengths": ["Clear section organization", "Professional formatting"],
            "improvements": ["Add more quantifiable achievements"],
            "specific_feedback": "Resume structure is well organized"
        },
        "appeal_feedback": {
            "strengths": ["Strong technical skills", "Relevant experience"],
            "improvements": ["Highlight leadership experience more"],
            "specific_feedback": "Good industry fit"
        },
        "analysis_summary": "Strong resume with good technical foundation",
        "improvement_suggestions": ["Add metrics", "Highlight achievements"],
        "processing_time_seconds": 12.5,
        "ai_model_version": "v2.1.0"
    }
    return orchestrator


@pytest.fixture
def analysis_service(mock_db, mock_resume_upload_service, mock_candidate_service, mock_ai_orchestrator):
    """Create analysis service with mocked dependencies."""
    service = AnalysisService(mock_db)
    service.resume_service = mock_resume_upload_service
    service.candidate_service = mock_candidate_service
    service.ai_orchestrator = mock_ai_orchestrator
    return service


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.email = "test@example.com"
    user.role = "user"
    return user


@pytest.fixture
def mock_resume():
    """Mock resume for testing."""
    resume = MagicMock()
    resume.id = str(uuid.uuid4())
    resume.candidate_id = str(uuid.uuid4())
    resume.text_content = "Sample resume text content for analysis testing"
    resume.file_name = "test_resume.pdf"
    resume.created_at = datetime.utcnow()
    return resume


@pytest.fixture
def sample_analysis_request():
    """Sample analysis request for testing."""
    return AnalysisRequest(
        industry=Industry.STRATEGY_TECH,
        analysis_depth=AnalysisDepth.STANDARD,
        focus_areas=["structure", "content"],
        compare_to_market=True
    )


class TestResumeAnalysisService:
    """Test the AnalysisService with resume-referencing architecture."""

    async def test_request_analysis_success(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test successful analysis request with resume ID."""
        resume_id = uuid.UUID(mock_resume.id)

        result = await analysis_service.request_analysis(
            resume_id=resume_id,
            industry=sample_analysis_request.industry,
            user_id=uuid.UUID(mock_user.id),
            analysis_depth=sample_analysis_request.analysis_depth,
            focus_areas=sample_analysis_request.focus_areas,
            compare_to_market=sample_analysis_request.compare_to_market
        )

        assert result.success is True
        assert result.status == AnalysisStatus.PROCESSING
        assert result.analysis_id is not None

        # Verify resume was accessed
        analysis_service.resume_service.get_resume.assert_called_once_with(resume_id, uuid.UUID(mock_user.id))

    async def test_request_analysis_resume_not_found(self, analysis_service, mock_user, sample_analysis_request):
        """Test analysis request with invalid resume ID."""
        analysis_service.resume_service.get_resume.side_effect = Exception("Resume not found")
        resume_id = uuid.uuid4()

        with pytest.raises(AnalysisValidationException, match="Resume not found"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_request_analysis_access_denied(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test analysis request with no access to candidate."""
        analysis_service.candidate_service.can_user_access_candidate.return_value = False
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisValidationException, match="Access denied"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_get_analysis_status_processing(self, analysis_service, mock_user):
        """Test getting status of processing analysis."""
        analysis_id = uuid.uuid4()

        with patch.object(analysis_service, '_get_analysis_from_db') as mock_get:
            mock_analysis = MagicMock()
            mock_analysis.status = AnalysisStatus.PROCESSING
            mock_analysis.user_id = mock_user.id
            mock_get.return_value = mock_analysis

            result = await analysis_service.get_analysis_status(analysis_id, uuid.UUID(mock_user.id))

            assert result.status == AnalysisStatus.PROCESSING
            assert result.result is None

    async def test_get_analysis_status_completed(self, analysis_service, mock_user):
        """Test getting status of completed analysis."""
        analysis_id = uuid.uuid4()

        with patch.object(analysis_service, '_get_analysis_from_db') as mock_get:
            mock_analysis = MagicMock()
            mock_analysis.status = AnalysisStatus.COMPLETED
            mock_analysis.user_id = mock_user.id
            mock_analysis.result_data = {"overall_score": 85.5}
            mock_get.return_value = mock_analysis

            result = await analysis_service.get_analysis_status(analysis_id, uuid.UUID(mock_user.id))

            assert result.status == AnalysisStatus.COMPLETED
            assert result.result is not None

    async def test_get_resume_analyses_history(self, analysis_service, mock_user, mock_resume):
        """Test getting analysis history for a resume."""
        resume_id = uuid.UUID(mock_resume.id)

        with patch.object(analysis_service, '_get_resume_analyses_from_db') as mock_get:
            mock_analyses = [
                MagicMock(id=str(uuid.uuid4()), industry="strategy_tech", status="completed"),
                MagicMock(id=str(uuid.uuid4()), industry="consulting", status="processing")
            ]
            mock_get.return_value = mock_analyses

            result = await analysis_service.get_resume_analyses(resume_id, uuid.UUID(mock_user.id))

            assert len(result) == 2
            assert result[0].industry == "strategy_tech"
            assert result[1].status == "processing"

    async def test_cancel_analysis_success(self, analysis_service, mock_user):
        """Test successful analysis cancellation."""
        analysis_id = uuid.uuid4()

        with patch.object(analysis_service, '_cancel_analysis_in_db') as mock_cancel:
            mock_cancel.return_value = True

            result = await analysis_service.cancel_analysis(analysis_id, uuid.UUID(mock_user.id))

            assert result is True

    async def test_get_user_stats(self, analysis_service, mock_user):
        """Test getting user analysis statistics."""
        with patch.object(analysis_service, '_get_user_stats_from_db') as mock_stats:
            mock_stats.return_value = {
                "total_analyses": 15,
                "completed_analyses": 12,
                "failed_analyses": 1,
                "average_score": 78.5,
                "industry_breakdown": {"strategy_tech": 8, "consulting": 4},
                "tier_breakdown": {"tier_1": 5, "tier_2": 7}
            }

            result = await analysis_service.get_user_stats(uuid.UUID(mock_user.id))

            assert result.total_analyses == 15
            assert result.completed_analyses == 12
            assert result.average_score == 78.5


class TestResumeAnalysisAPI:
    """Test the API endpoints for resume analysis."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/analysis")
        return TestClient(app)

    def test_request_analysis_endpoint(self, client, mock_user, mock_resume):
        """Test POST /resumes/{resume_id}/analyze endpoint."""
        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.request_analysis = AsyncMock()
                mock_service_instance.request_analysis.return_value = AnalysisResponse(
                    analysis_id=str(uuid.uuid4()),
                    status=AnalysisStatus.PROCESSING
                )
                mock_service.return_value = mock_service_instance

                response = client.post(
                    f"/api/v1/analysis/resumes/{mock_resume.id}/analyze",
                    json={
                        "industry": "strategy_tech",
                        "analysis_depth": "standard",
                        "focus_areas": ["structure", "content"],
                        "compare_to_market": True
                    }
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["success"] is True
                assert data["status"] == "processing"

    def test_get_analysis_status_endpoint(self, client, mock_user):
        """Test GET /analysis/{analysis_id}/status endpoint."""
        analysis_id = str(uuid.uuid4())

        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_analysis_status = AsyncMock()
                mock_service_instance.get_analysis_status.return_value = AnalysisResponse(
                    analysis_id=analysis_id,
                    status=AnalysisStatus.COMPLETED,
                    result=AnalysisResult(
                        analysis_id=analysis_id,
                        overall_score=85.5,
                        market_tier=MarketTier.TIER_1,
                        industry=Industry.STRATEGY_TECH,
                        created_at=datetime.utcnow()
                    )
                )
                mock_service.return_value = mock_service_instance

                response = client.get(f"/api/v1/analysis/analysis/{analysis_id}/status")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "completed"
                assert data["result"]["overall_score"] == 85.5

    def test_get_resume_analysis_history_endpoint(self, client, mock_user, mock_resume):
        """Test GET /resumes/{resume_id}/analyses endpoint."""
        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_resume_analyses = AsyncMock()
                mock_service_instance.get_resume_analyses.return_value = [
                    MagicMock(
                        id=str(uuid.uuid4()),
                        industry=Industry.STRATEGY_TECH,
                        status=AnalysisStatus.COMPLETED,
                        overall_score=85.5
                    )
                ]
                mock_service.return_value = mock_service_instance

                response = client.get(f"/api/v1/analysis/resumes/{mock_resume.id}/analyses")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["total_count"] == 1
                assert len(data["analyses"]) == 1

    def test_cancel_analysis_endpoint(self, client, mock_user):
        """Test DELETE /{analysis_id}/cancel endpoint."""
        analysis_id = str(uuid.uuid4())

        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.cancel_analysis = AsyncMock(return_value=True)
                mock_service.return_value = mock_service_instance

                response = client.delete(f"/api/v1/analysis/{analysis_id}/cancel")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["message"] == "Analysis cancelled successfully"

    def test_list_analyses_endpoint(self, client, mock_user):
        """Test GET / endpoint with pagination."""
        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.list_user_analyses = AsyncMock()
                mock_service_instance.list_user_analyses.return_value = {
                    "analyses": [
                        MagicMock(id=str(uuid.uuid4()), industry=Industry.STRATEGY_TECH, status=AnalysisStatus.COMPLETED)
                    ],
                    "total_count": 1
                }
                mock_service.return_value = mock_service_instance

                response = client.get("/api/v1/analysis/?page=1&page_size=10")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["page"] == 1
                assert data["page_size"] == 10
                assert data["total_count"] == 1

    def test_get_analysis_stats_endpoint(self, client, mock_user):
        """Test GET /stats/summary endpoint."""
        with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_analysis_service") as mock_service:
                mock_service_instance = MagicMock()
                mock_service_instance.get_user_stats = AsyncMock()
                mock_service_instance.get_user_stats.return_value = MagicMock(
                    total_analyses=10,
                    completed_analyses=8,
                    failed_analyses=1,
                    average_score=82.5
                )
                mock_service.return_value = mock_service_instance

                response = client.get("/api/v1/analysis/stats/summary")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["total_analyses"] == 10
                assert data["completed_analyses"] == 8


class TestResumeAnalysisAccessControl:
    """Test access control and security for resume analysis."""

    async def test_analysis_request_with_invalid_user_access(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test analysis request is denied for users without candidate access."""
        analysis_service.candidate_service.can_user_access_candidate.return_value = False
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisValidationException, match="Access denied"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_get_analysis_status_cross_user_access_denied(self, analysis_service, mock_user):
        """Test users cannot access other users' analysis results."""
        analysis_id = uuid.uuid4()
        other_user_id = str(uuid.uuid4())

        with patch.object(analysis_service, '_get_analysis_from_db') as mock_get:
            mock_analysis = MagicMock()
            mock_analysis.user_id = other_user_id  # Different user
            mock_get.return_value = mock_analysis

            result = await analysis_service.get_analysis_status(analysis_id, uuid.UUID(mock_user.id))

            assert result is None

    async def test_resume_analysis_validates_candidate_ownership(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test analysis validates user owns/manages the candidate."""
        resume_id = uuid.UUID(mock_resume.id)

        # Simulate user doesn't have access to candidate
        analysis_service.candidate_service.can_user_access_candidate.return_value = False

        with pytest.raises(AnalysisValidationException):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

        # Verify candidate access was checked
        analysis_service.candidate_service.can_user_access_candidate.assert_called_once()


class TestResumeAnalysisPerformance:
    """Test performance and concurrency scenarios."""

    async def test_concurrent_analysis_requests(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test handling multiple concurrent analysis requests."""
        resume_id = uuid.UUID(mock_resume.id)
        user_id = uuid.UUID(mock_user.id)

        # Create multiple analysis requests concurrently
        tasks = []
        for _ in range(5):
            task = analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=user_id
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(result.success for result in results)
        assert len(set(result.analysis_id for result in results)) == 5  # All unique IDs

    async def test_analysis_caching(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test that recent analyses are cached to avoid duplicate processing."""
        resume_id = uuid.UUID(mock_resume.id)
        user_id = uuid.UUID(mock_user.id)

        with patch.object(analysis_service, '_get_recent_analysis') as mock_recent:
            # First call - no recent analysis
            mock_recent.return_value = None
            result1 = await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=user_id
            )

            # Second call - recent analysis exists
            mock_analysis = MagicMock()
            mock_analysis.id = str(uuid.uuid4())
            mock_analysis.status = AnalysisStatus.COMPLETED
            mock_recent.return_value = mock_analysis

            result2 = await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=user_id
            )

            # Should return cached result
            assert result2.analysis_id == mock_analysis.id


class TestResumeAnalysisErrorScenarios:
    """Test error handling and edge cases."""

    async def test_ai_orchestrator_failure(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test handling AI orchestrator failures."""
        analysis_service.ai_orchestrator.analyze_resume.side_effect = Exception("AI service unavailable")
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisException):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_resume_content_extraction_failure(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test handling resume text extraction failures."""
        analysis_service.resume_service.get_resume.return_value.text_content = None
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisValidationException, match="Resume text content not available"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_analysis_timeout_handling(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test analysis timeout scenarios."""
        # Simulate timeout
        async def timeout_side_effect(*args, **kwargs):
            await asyncio.sleep(31)  # Longer than expected timeout

        analysis_service.ai_orchestrator.analyze_resume.side_effect = timeout_side_effect
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisException, match="timeout"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry=sample_analysis_request.industry,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_invalid_industry_validation(self, analysis_service, mock_user, mock_resume):
        """Test validation of invalid industry values."""
        resume_id = uuid.UUID(mock_resume.id)

        with pytest.raises(AnalysisValidationException, match="Unsupported industry"):
            await analysis_service.request_analysis(
                resume_id=resume_id,
                industry="invalid_industry",  # Invalid industry
                user_id=uuid.UUID(mock_user.id)
            )


class TestResumeAnalysisIntegration:
    """Test integration between resume_analysis and resume_upload services."""

    async def test_analysis_retrieves_resume_from_upload_service(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test that analysis correctly retrieves resume from upload service."""
        resume_id = uuid.UUID(mock_resume.id)

        await analysis_service.request_analysis(
            resume_id=resume_id,
            industry=sample_analysis_request.industry,
            user_id=uuid.UUID(mock_user.id)
        )

        # Verify resume was retrieved from upload service
        analysis_service.resume_service.get_resume.assert_called_once_with(
            resume_id, uuid.UUID(mock_user.id)
        )

    async def test_analysis_uses_resume_text_content(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test that analysis uses resume text content for AI processing."""
        resume_id = uuid.UUID(mock_resume.id)
        expected_text = "Sample resume text for AI analysis"
        mock_resume.text_content = expected_text

        await analysis_service.request_analysis(
            resume_id=resume_id,
            industry=sample_analysis_request.industry,
            user_id=uuid.UUID(mock_user.id)
        )

        # Verify AI orchestrator was called with resume text
        analysis_service.ai_orchestrator.analyze_resume.assert_called_once()
        call_args = analysis_service.ai_orchestrator.analyze_resume.call_args
        assert expected_text in str(call_args)

    async def test_analysis_inherits_resume_permissions(self, analysis_service, mock_user, mock_resume, sample_analysis_request):
        """Test that analysis permissions are based on resume access via candidates."""
        resume_id = uuid.UUID(mock_resume.id)
        candidate_id = uuid.UUID(mock_resume.candidate_id)

        await analysis_service.request_analysis(
            resume_id=resume_id,
            industry=sample_analysis_request.industry,
            user_id=uuid.UUID(mock_user.id)
        )

        # Verify candidate access was checked
        analysis_service.candidate_service.can_user_access_candidate.assert_called_once_with(
            candidate_id, uuid.UUID(mock_user.id)
        )


# Run integration tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])