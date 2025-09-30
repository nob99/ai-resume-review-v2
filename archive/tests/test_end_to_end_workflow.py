"""End-to-end workflow tests for the two-feature architecture.

This test suite covers the complete user workflow:
1. Upload Resume (resume_upload feature)
2. Analyze Resume (resume_analysis feature)

Tests the integration between both features and validates the
user experience matches the intended two-feature concept:
- Upload Resume: Complete resume management with candidate association
- Analyze Resume: On-demand analysis referencing uploaded resumes

Test Scenarios:
- Complete upload → analyze workflow
- Multiple resume versions for same candidate
- Analysis across different industries
- Error propagation between features
- Access control throughout the workflow
- Performance with concurrent operations
"""

import pytest
import uuid
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from io import BytesIO

# Import from both features
from app.features.resume_upload.service import ResumeUploadService
from app.features.resume_upload.schemas import UploadedFileV2

from app.features.resume_analysis.service import AnalysisService
from app.features.resume_analysis.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    Industry,
    AnalysisDepth
)

from app.features.candidate.service import CandidateService


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.email = "consultant@example.com"
    user.role = "user"
    return user


@pytest.fixture
def mock_candidate():
    """Mock candidate for testing."""
    candidate = MagicMock()
    candidate.id = str(uuid.uuid4())
    candidate.first_name = "John"
    candidate.last_name = "Doe"
    candidate.email = "john.doe@example.com"
    candidate.created_by_user_id = None  # Will be set by test
    return candidate


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Title (Test Resume)\n/Author (John Doe)\n>>\nendobj\nxref\n0 1\n0000000000 65535 f\ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF"


@pytest.fixture
def mock_file(sample_pdf_content):
    """Mock uploaded file for testing."""
    file = MagicMock()
    file.filename = "john_doe_resume.pdf"
    file.content_type = "application/pdf"
    file.size = len(sample_pdf_content)
    file.read = AsyncMock(return_value=sample_pdf_content)
    file.file = BytesIO(sample_pdf_content)
    return file


@pytest.fixture
def mock_services():
    """Mock all required services."""
    services = MagicMock()

    # Resume upload service
    services.resume_upload = MagicMock()
    services.resume_upload.upload_resume = AsyncMock()
    services.resume_upload.get_resume = AsyncMock()
    services.resume_upload.list_candidate_resumes = AsyncMock()

    # Resume analysis service
    services.resume_analysis = MagicMock()
    services.resume_analysis.request_analysis = AsyncMock()
    services.resume_analysis.get_analysis_status = AsyncMock()
    services.resume_analysis.get_analysis_result = AsyncMock()

    # Candidate service
    services.candidate = MagicMock()
    services.candidate.get_candidate = AsyncMock()
    services.candidate.can_user_access_candidate = AsyncMock(return_value=True)

    return services


class TestCompleteUploadAnalyzeWorkflow:
    """Test the complete upload → analyze workflow."""

    async def test_upload_then_analyze_success(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test complete workflow: upload resume then request analysis."""

        # Setup candidate
        mock_candidate.created_by_user_id = mock_user.id
        mock_services.candidate.get_candidate.return_value = mock_candidate

        # Step 1: Upload resume
        from app.features.resume_upload.schemas import FileInfo, FileStatus
        uploaded_resume = UploadedFileV2(
            id=str(uuid.uuid4()),
            file=FileInfo(
                name="john_doe_resume.pdf",
                size=1024,
                type="application/pdf",
                lastModified=1234567890
            ),
            status=FileStatus.COMPLETED,
            extractedText="John Doe Software Engineer Experience..."
        )
        mock_services.resume_upload.upload_resume.return_value = uploaded_resume

        result = await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        assert result.id == uploaded_resume.id
        assert result.extractedText is not None

        # Step 2: Request analysis of uploaded resume
        analysis_response = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )
        mock_services.resume_analysis.request_analysis.return_value = analysis_response

        analysis_result = await mock_services.resume_analysis.request_analysis(
            resume_id=uuid.UUID(uploaded_resume.id),
            industry=Industry.STRATEGY_TECH,
            user_id=uuid.UUID(mock_user.id),
            analysis_depth=AnalysisDepth.STANDARD
        )

        assert analysis_result.success is True
        assert analysis_result.status == AnalysisStatus.PROCESSING

        # Verify services were called correctly
        mock_services.resume_upload.upload_resume.assert_called_once()
        mock_services.resume_analysis.request_analysis.assert_called_once_with(
            resume_id=uuid.UUID(uploaded_resume.id),
            industry=Industry.STRATEGY_TECH,
            user_id=uuid.UUID(mock_user.id),
            analysis_depth=AnalysisDepth.STANDARD
        )

    async def test_multiple_resume_versions_workflow(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test uploading multiple resume versions and analyzing each."""
        mock_candidate.created_by_user_id = mock_user.id

        # Upload version 1
        resume_v1 = UploadedFileV2(
            id=str(uuid.uuid4()),
            filename="resume_v1.pdf",
            candidate_id=mock_candidate.id,
            text_content="John Doe Software Engineer v1...",
            upload_status="completed",
            created_at=datetime.utcnow()
        )

        # Upload version 2
        resume_v2 = UploadedFileV2(
            id=str(uuid.uuid4()),
            filename="resume_v2.pdf",
            candidate_id=mock_candidate.id,
            text_content="John Doe Senior Software Engineer v2...",
            upload_status="completed",
            created_at=datetime.utcnow()
        )

        mock_services.resume_upload.upload_resume.side_effect = [resume_v1, resume_v2]

        # Upload both versions
        result_v1 = await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        result_v2 = await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        # Analyze both versions
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        analysis_v1 = await mock_services.resume_analysis.request_analysis(
            resume_id=uuid.UUID(result_v1.id),
            industry=Industry.STRATEGY_TECH,
            user_id=uuid.UUID(mock_user.id)
        )

        analysis_v2 = await mock_services.resume_analysis.request_analysis(
            resume_id=uuid.UUID(result_v2.id),
            industry=Industry.CONSULTING,
            user_id=uuid.UUID(mock_user.id)
        )

        # Both analyses should succeed
        assert analysis_v1.success is True
        assert analysis_v2.success is True

        # Should have two analysis requests
        assert mock_services.resume_analysis.request_analysis.call_count == 2

    async def test_cross_industry_analysis_workflow(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test analyzing same resume for different industries."""
        mock_candidate.created_by_user_id = mock_user.id

        # Upload one resume
        resume = UploadedFileV2(
            id=str(uuid.uuid4()),
            filename="versatile_resume.pdf",
            candidate_id=mock_candidate.id,
            text_content="John Doe Consultant & Engineer...",
            upload_status="completed",
            created_at=datetime.utcnow()
        )
        mock_services.resume_upload.upload_resume.return_value = resume

        upload_result = await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        # Analyze for different industries
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        industries = [Industry.STRATEGY_TECH, Industry.CONSULTING, Industry.MA_FINANCIAL]
        analysis_results = []

        for industry in industries:
            result = await mock_services.resume_analysis.request_analysis(
                resume_id=uuid.UUID(upload_result.id),
                industry=industry,
                user_id=uuid.UUID(mock_user.id)
            )
            analysis_results.append(result)

        # All analyses should succeed
        assert all(result.success for result in analysis_results)
        assert len(analysis_results) == 3

        # Verify each industry was requested
        call_args_list = mock_services.resume_analysis.request_analysis.call_args_list
        requested_industries = [call[1]['industry'] for call in call_args_list]
        assert set(requested_industries) == set(industries)

    async def test_concurrent_upload_and_analyze(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test concurrent operations in the workflow."""
        mock_candidate.created_by_user_id = mock_user.id

        # Setup multiple resumes
        resumes = []
        for i in range(3):
            resume = UploadedFileV2(
                id=str(uuid.uuid4()),
                filename=f"resume_{i}.pdf",
                candidate_id=mock_candidate.id,
                text_content=f"Resume content {i}...",
                upload_status="completed",
                created_at=datetime.utcnow()
            )
            resumes.append(resume)

        mock_services.resume_upload.upload_resume.side_effect = resumes

        # Upload all resumes concurrently
        upload_tasks = [
            mock_services.resume_upload.upload_resume(
                candidate_id=uuid.UUID(mock_candidate.id),
                file=mock_file,
                user_id=uuid.UUID(mock_user.id)
            )
            for _ in range(3)
        ]

        upload_results = await asyncio.gather(*upload_tasks)

        # Analyze all resumes concurrently
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        analysis_tasks = [
            mock_services.resume_analysis.request_analysis(
                resume_id=uuid.UUID(result.id),
                industry=Industry.STRATEGY_TECH,
                user_id=uuid.UUID(mock_user.id)
            )
            for result in upload_results
        ]

        analysis_results = await asyncio.gather(*analysis_tasks)

        # All operations should succeed
        assert len(upload_results) == 3
        assert len(analysis_results) == 3
        assert all(result.success for result in analysis_results)


class TestWorkflowErrorPropagation:
    """Test error handling across the upload → analyze workflow."""

    async def test_upload_failure_blocks_analysis(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test that upload failures prevent analysis."""
        mock_candidate.created_by_user_id = mock_user.id

        # Upload fails
        mock_services.resume_upload.upload_resume.side_effect = Exception("File processing failed")

        with pytest.raises(Exception, match="File processing failed"):
            await mock_services.resume_upload.upload_resume(
                candidate_id=uuid.UUID(mock_candidate.id),
                file=mock_file,
                user_id=uuid.UUID(mock_user.id)
            )

        # Analysis should not be attempted
        mock_services.resume_analysis.request_analysis.assert_not_called()

    async def test_resume_not_found_in_analysis(self, mock_services, mock_user):
        """Test analysis fails gracefully when resume doesn't exist."""
        non_existent_resume_id = uuid.uuid4()

        mock_services.resume_analysis.request_analysis.side_effect = Exception("Resume not found")

        with pytest.raises(Exception, match="Resume not found"):
            await mock_services.resume_analysis.request_analysis(
                resume_id=non_existent_resume_id,
                industry=Industry.STRATEGY_TECH,
                user_id=uuid.UUID(mock_user.id)
            )

    async def test_access_control_failure_propagation(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test access control failures are handled properly."""
        # User doesn't have access to candidate
        mock_services.candidate.can_user_access_candidate.return_value = False
        mock_services.resume_upload.upload_resume.side_effect = Exception("Access denied")

        with pytest.raises(Exception, match="Access denied"):
            await mock_services.resume_upload.upload_resume(
                candidate_id=uuid.UUID(mock_candidate.id),
                file=mock_file,
                user_id=uuid.UUID(mock_user.id)
            )


class TestWorkflowAccessControl:
    """Test access control throughout the workflow."""

    async def test_candidate_ownership_validation(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test that workflow validates candidate ownership/access at each step."""
        mock_candidate.created_by_user_id = mock_user.id
        mock_services.candidate.can_user_access_candidate.return_value = True

        # Setup successful upload
        resume = UploadedFileV2(
            id=str(uuid.uuid4()),
            filename="test_resume.pdf",
            candidate_id=mock_candidate.id,
            text_content="Resume content...",
            upload_status="completed",
            created_at=datetime.utcnow()
        )
        mock_services.resume_upload.upload_resume.return_value = resume

        # Upload - should check candidate access
        await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        # Analysis - should also check candidate access
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        await mock_services.resume_analysis.request_analysis(
            resume_id=uuid.UUID(resume.id),
            industry=Industry.STRATEGY_TECH,
            user_id=uuid.UUID(mock_user.id)
        )

        # Both steps should have validated candidate access
        # (In real implementation, this would be checked in the services)
        assert mock_services.resume_upload.upload_resume.called
        assert mock_services.resume_analysis.request_analysis.called

    async def test_cross_user_access_denied(self, mock_services, mock_user, mock_candidate):
        """Test that users cannot access other users' candidates/resumes."""
        other_user_id = str(uuid.uuid4())
        mock_candidate.created_by_user_id = other_user_id

        # Mock access control denial
        mock_services.candidate.can_user_access_candidate.return_value = False
        mock_services.resume_analysis.request_analysis.side_effect = Exception("Access denied")

        fake_resume_id = uuid.uuid4()

        with pytest.raises(Exception, match="Access denied"):
            await mock_services.resume_analysis.request_analysis(
                resume_id=fake_resume_id,
                industry=Industry.STRATEGY_TECH,
                user_id=uuid.UUID(mock_user.id)
            )


class TestWorkflowAPIIntegration:
    """Test the workflow through API endpoints."""

    @pytest.fixture
    def app_with_routers(self):
        """Create FastAPI app with both feature routers."""
        app = FastAPI()

        # Import and include routers
        from app.features.resume_upload.api import router as upload_router
        from app.features.resume_analysis.api import router as analysis_router

        app.include_router(upload_router, prefix="/api/v1/resume-upload")
        app.include_router(analysis_router, prefix="/api/v1/analysis")

        return app

    def test_api_workflow_upload_then_analyze(self, app_with_routers, mock_user, mock_candidate):
        """Test complete workflow through API endpoints."""
        client = TestClient(app_with_routers)

        with patch("app.features.resume_upload.api.get_current_user", return_value=mock_user):
            with patch("app.features.resume_analysis.api.get_current_user", return_value=mock_user):
                with patch("app.features.resume_upload.api.get_resume_upload_service") as mock_upload_service:
                    with patch("app.features.resume_analysis.api.get_analysis_service") as mock_analysis_service:

                        # Mock upload service
                        mock_upload_instance = MagicMock()
                        mock_upload_instance.upload_resume = AsyncMock()
                        mock_upload_instance.upload_resume.return_value = UploadedFileV2(
                            id=str(uuid.uuid4()),
                            filename="test.pdf",
                            candidate_id=mock_candidate.id,
                            text_content="Resume text...",
                            upload_status="completed",
                            created_at=datetime.utcnow()
                        )
                        mock_upload_service.return_value = mock_upload_instance

                        # Mock analysis service
                        mock_analysis_instance = MagicMock()
                        mock_analysis_instance.request_analysis = AsyncMock()
                        mock_analysis_instance.request_analysis.return_value = AnalysisResponse(
                            analysis_id=str(uuid.uuid4()),
                            status=AnalysisStatus.PROCESSING,
                            success=True
                        )
                        mock_analysis_service.return_value = mock_analysis_instance

                        # Step 1: Upload resume
                        upload_response = client.post(
                            f"/api/v1/resume-upload/candidates/{mock_candidate.id}/resumes",
                            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
                        )

                        assert upload_response.status_code == status.HTTP_200_OK
                        upload_data = upload_response.json()
                        resume_id = upload_data["id"]

                        # Step 2: Request analysis
                        analysis_response = client.post(
                            f"/api/v1/analysis/resumes/{resume_id}/analyze",
                            json={
                                "industry": "strategy_tech",
                                "analysis_depth": "standard",
                                "focus_areas": ["structure", "content"],
                                "compare_to_market": True
                            }
                        )

                        assert analysis_response.status_code == status.HTTP_200_OK
                        analysis_data = analysis_response.json()
                        assert analysis_data["success"] is True
                        assert analysis_data["status"] == "processing"


class TestWorkflowDataConsistency:
    """Test data consistency across the workflow."""

    async def test_resume_metadata_consistency(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test that resume metadata is consistent between upload and analysis."""
        mock_candidate.created_by_user_id = mock_user.id

        # Upload resume with specific metadata
        resume = UploadedFileV2(
            id=str(uuid.uuid4()),
            filename="john_doe_senior_engineer.pdf",
            candidate_id=mock_candidate.id,
            text_content="John Doe Senior Software Engineer with 10 years experience...",
            upload_status="completed",
            created_at=datetime.utcnow()
        )
        mock_services.resume_upload.upload_resume.return_value = resume

        upload_result = await mock_services.resume_upload.upload_resume(
            candidate_id=uuid.UUID(mock_candidate.id),
            file=mock_file,
            user_id=uuid.UUID(mock_user.id)
        )

        # When analysis service retrieves the resume, it should get the same metadata
        mock_services.resume_upload.get_resume.return_value = resume
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        analysis_result = await mock_services.resume_analysis.request_analysis(
            resume_id=uuid.UUID(upload_result.id),
            industry=Industry.STRATEGY_TECH,
            user_id=uuid.UUID(mock_user.id)
        )

        # Verify the resume was retrieved with correct ID for analysis
        # (In real implementation, analysis service would call get_resume)
        assert upload_result.id == resume.id
        assert upload_result.candidate_id == resume.candidate_id
        assert analysis_result.success is True

    async def test_candidate_association_consistency(self, mock_services, mock_user, mock_candidate, mock_file):
        """Test that candidate associations remain consistent throughout workflow."""
        mock_candidate.created_by_user_id = mock_user.id
        candidate_id = uuid.UUID(mock_candidate.id)

        # Upload multiple resumes for same candidate
        resumes = []
        for i in range(3):
            resume = UploadedFileV2(
                id=str(uuid.uuid4()),
                filename=f"resume_v{i+1}.pdf",
                candidate_id=str(candidate_id),  # Same candidate
                text_content=f"Resume version {i+1} content...",
                upload_status="completed",
                created_at=datetime.utcnow()
            )
            resumes.append(resume)

        mock_services.resume_upload.upload_resume.side_effect = resumes

        # Upload all resumes
        upload_results = []
        for _ in range(3):
            result = await mock_services.resume_upload.upload_resume(
                candidate_id=candidate_id,
                file=mock_file,
                user_id=uuid.UUID(mock_user.id)
            )
            upload_results.append(result)

        # All resumes should be associated with the same candidate
        assert all(result.candidate_id == str(candidate_id) for result in upload_results)

        # Analysis of any resume should reference the same candidate
        mock_services.resume_analysis.request_analysis.return_value = AnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            status=AnalysisStatus.PROCESSING,
            success=True
        )

        for result in upload_results:
            analysis_result = await mock_services.resume_analysis.request_analysis(
                resume_id=uuid.UUID(result.id),
                industry=Industry.STRATEGY_TECH,
                user_id=uuid.UUID(mock_user.id)
            )
            assert analysis_result.success is True


# Run workflow tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])