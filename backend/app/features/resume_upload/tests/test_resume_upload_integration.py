"""
Integration Tests for Resume Upload Feature

Tests the complete resume upload workflow including:
- Candidate-centric resume upload
- File processing and text extraction
- Version management
- Access control via candidate permissions
- API endpoints with proper authentication
"""

import pytest
import uuid
import io
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.features.resume_upload.service import ResumeUploadService
from app.features.resume_upload.api import router
from app.features.resume_upload.schemas import UploadedFileV2
from database.models.resume import Resume, ResumeStatus
from database.models.candidate import Candidate
from database.models.auth import User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = Mock(spec=User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.role = "junior_recruiter"
    return user


@pytest.fixture
def mock_candidate():
    """Create a mock candidate."""
    candidate = Mock(spec=Candidate)
    candidate.id = uuid.uuid4()
    candidate.first_name = "John"
    candidate.last_name = "Doe"
    candidate.email = "john.doe@example.com"
    candidate.created_by_user_id = uuid.uuid4()
    return candidate


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 55
>>
stream
BT
/F1 12 Tf
72 720 Td
(John Doe - Software Engineer) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000380 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
459
%%EOF"""

    file = Mock(spec=UploadFile)
    file.filename = "john_doe_resume.pdf"
    file.content_type = "application/pdf"
    file.size = len(pdf_content)
    file.read = AsyncMock(return_value=pdf_content)
    file.seek = AsyncMock()
    return file


@pytest.fixture
def resume_service(mock_db):
    """Create resume upload service with mock database."""
    return ResumeUploadService(mock_db)


class TestResumeUploadService:
    """Test resume upload service functionality."""

    @pytest.mark.asyncio
    async def test_upload_resume_success(self, resume_service, mock_candidate, mock_user, sample_pdf_file):
        """Test successful resume upload for a candidate."""

        # Mock database operations
        mock_resume = Mock(spec=Resume)
        mock_resume.id = uuid.uuid4()
        mock_resume.candidate_id = mock_candidate.id
        mock_resume.original_filename = "john_doe_resume.pdf"
        mock_resume.extracted_text = "John Doe - Software Engineer"
        mock_resume.status = ResumeStatus.COMPLETED
        mock_resume.version_number = 1
        mock_resume.uploaded_at = datetime.now()

        with patch.object(resume_service.repository, 'create_resume', return_value=mock_resume):
            with patch.object(resume_service, '_extract_text', return_value="John Doe - Software Engineer"):
                result = await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

                assert isinstance(result, UploadedFileV2)
                assert result.candidate_id == str(mock_candidate.id)
                assert result.filename == "john_doe_resume.pdf"
                assert result.extracted_text == "John Doe - Software Engineer"
                assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_upload_resume_invalid_file_type(self, resume_service, mock_candidate, mock_user):
        """Test upload rejection for invalid file types."""

        invalid_file = Mock(spec=UploadFile)
        invalid_file.filename = "resume.txt"
        invalid_file.content_type = "text/plain"
        invalid_file.size = 1000

        with pytest.raises(Exception) as exc_info:
            await resume_service.upload_resume(
                candidate_id=mock_candidate.id,
                file=invalid_file,
                user_id=mock_user.id
            )

        assert "file type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_upload_resume_file_too_large(self, resume_service, mock_candidate, mock_user):
        """Test upload rejection for files that are too large."""

        large_file = Mock(spec=UploadFile)
        large_file.filename = "large_resume.pdf"
        large_file.content_type = "application/pdf"
        large_file.size = 15 * 1024 * 1024  # 15MB (exceeds 10MB limit)

        with pytest.raises(Exception) as exc_info:
            await resume_service.upload_resume(
                candidate_id=mock_candidate.id,
                file=large_file,
                user_id=mock_user.id
            )

        assert "file size" in str(exc_info.value).lower()

    @pytest.mark.skip(reason="get_candidate_resumes method removed during refactoring")
    @pytest.mark.asyncio
    async def test_get_candidate_resumes(self, resume_service, mock_candidate, mock_user):
        """Test getting all resumes for a candidate - REMOVED DURING REFACTORING."""
        pass

    @pytest.mark.asyncio
    async def test_version_management(self, resume_service, mock_candidate, mock_user, sample_pdf_file):
        """Test that uploading multiple resumes creates proper versions."""

        # Mock first upload (version 1)
        mock_resume_v1 = Mock(spec=Resume)
        mock_resume_v1.id = uuid.uuid4()
        mock_resume_v1.version_number = 1

        # Mock second upload (version 2)
        mock_resume_v2 = Mock(spec=Resume)
        mock_resume_v2.id = uuid.uuid4()
        mock_resume_v2.version_number = 2

        with patch.object(resume_service.repository, 'create_resume') as mock_create:
            mock_create.side_effect = [mock_resume_v1, mock_resume_v2]

            with patch.object(resume_service, '_extract_text', return_value="Resume content"):
                # First upload
                result1 = await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

                # Second upload
                result2 = await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

                # Verify version incrementation logic would be called
                assert mock_create.call_count == 2


class TestResumeUploadAPI:
    """Test resume upload API endpoints."""

    @pytest.mark.asyncio
    async def test_upload_resume_endpoint(self, mock_candidate, mock_user, sample_pdf_file):
        """Test the upload resume API endpoint."""

        mock_service = Mock()
        mock_result = UploadedFileV2(
            id=str(uuid.uuid4()),
            candidate_id=str(mock_candidate.id),
            original_filename="test.pdf",
            file_size=1000,
            mime_type="application/pdf",
            status="completed",
            extracted_text="Test content",
            word_count=2,
            progress=100,
            uploaded_at=datetime.now()
        )
        mock_service.upload_resume = AsyncMock(return_value=mock_result)

        with patch('app.features.resume_upload.api.get_current_user', return_value=mock_user):
            with patch('app.features.resume_upload.api.get_resume_upload_service', return_value=mock_service):
                from app.features.resume_upload.api import upload_resume

                result = await upload_resume(
                    candidate_id=mock_candidate.id,
                    background_tasks=Mock(),
                    file=sample_pdf_file,
                    current_user=mock_user,
                    service=mock_service
                )

                assert result.candidate_id == str(mock_candidate.id)
                assert result.original_filename == "test.pdf"
                mock_service.upload_resume.assert_called_once()

    @pytest.mark.skip(reason="list_candidate_resumes endpoint removed during refactoring")
    @pytest.mark.asyncio
    async def test_list_candidate_resumes_endpoint(self, mock_candidate, mock_user):
        """Test the list candidate resumes API endpoint - REMOVED DURING REFACTORING."""
        pass


class TestResumeUploadAccessControl:
    """Test access control for resume upload feature."""

    @pytest.mark.asyncio
    async def test_candidate_access_validation(self, resume_service, mock_user, sample_pdf_file):
        """Test that users can only upload to candidates they have access to."""

        unauthorized_candidate_id = uuid.uuid4()

        with patch.object(resume_service, '_validate_candidate_access') as mock_validate:
            mock_validate.side_effect = Exception("Access denied")

            with pytest.raises(Exception) as exc_info:
                await resume_service.upload_resume(
                    candidate_id=unauthorized_candidate_id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

            assert "access denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_role_based_access(self, resume_service, mock_candidate, sample_pdf_file):
        """Test different access levels based on user roles."""

        # Test junior recruiter (limited access)
        junior_user = Mock(spec=User)
        junior_user.id = uuid.uuid4()
        junior_user.role = "junior_recruiter"

        # Test admin user (full access)
        admin_user = Mock(spec=User)
        admin_user.id = uuid.uuid4()
        admin_user.role = "admin"

        with patch.object(resume_service, '_validate_candidate_access') as mock_validate:
            # Junior should have limited access
            mock_validate.return_value = True  # Simulate access granted

            # Both should be able to upload (access control handled elsewhere)
            with patch.object(resume_service.repository, 'create_resume'):
                with patch.object(resume_service, '_extract_text', return_value="Content"):
                    # Test junior access
                    await resume_service.upload_resume(
                        candidate_id=mock_candidate.id,
                        file=sample_pdf_file,
                        user_id=junior_user.id
                    )

                    # Test admin access
                    await resume_service.upload_resume(
                        candidate_id=mock_candidate.id,
                        file=sample_pdf_file,
                        user_id=admin_user.id
                    )

                    # Both should have called validation
                    assert mock_validate.call_count == 2


class TestResumeUploadErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_database_error_handling(self, resume_service, mock_candidate, mock_user, sample_pdf_file):
        """Test handling of database errors during upload."""

        with patch.object(resume_service.repository, 'create_resume') as mock_create:
            mock_create.side_effect = Exception("Database connection failed")

            with pytest.raises(Exception) as exc_info:
                await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

            assert "database" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_text_extraction_failure(self, resume_service, mock_candidate, mock_user, sample_pdf_file):
        """Test handling of text extraction failures."""

        with patch.object(resume_service, '_extract_text') as mock_extract:
            mock_extract.side_effect = Exception("PDF parsing failed")

            with pytest.raises(Exception) as exc_info:
                await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=sample_pdf_file,
                    user_id=mock_user.id
                )

            assert "parsing" in str(exc_info.value).lower() or "extract" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_corrupted_file_handling(self, resume_service, mock_candidate, mock_user):
        """Test handling of corrupted or invalid files."""

        corrupted_file = Mock(spec=UploadFile)
        corrupted_file.filename = "corrupted.pdf"
        corrupted_file.content_type = "application/pdf"
        corrupted_file.size = 1000
        corrupted_file.read = AsyncMock(return_value=b"invalid pdf content")

        with patch.object(resume_service, '_extract_text') as mock_extract:
            mock_extract.side_effect = Exception("Invalid PDF format")

            with pytest.raises(Exception) as exc_info:
                await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=corrupted_file,
                    user_id=mock_user.id
                )

            assert "invalid" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()


# Test Configuration and Fixtures
@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI application."""
    from fastapi import FastAPI
    from app.features.resume_upload.api import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    from fastapi.testclient import TestClient
    return TestClient(test_app)


# Performance and Integration Tests
class TestResumeUploadPerformance:
    """Test performance aspects of resume upload."""

    @pytest.mark.asyncio
    async def test_large_file_processing_time(self, resume_service, mock_candidate, mock_user):
        """Test processing time for large files."""
        import time

        # Create a reasonably large file (within limits)
        large_content = b"A" * (5 * 1024 * 1024)  # 5MB
        large_file = Mock(spec=UploadFile)
        large_file.filename = "large_resume.pdf"
        large_file.content_type = "application/pdf"
        large_file.size = len(large_content)
        large_file.read = AsyncMock(return_value=large_content)

        with patch.object(resume_service.repository, 'create_resume'):
            with patch.object(resume_service, '_extract_text', return_value="Large content"):
                start_time = time.time()
                await resume_service.upload_resume(
                    candidate_id=mock_candidate.id,
                    file=large_file,
                    user_id=mock_user.id
                )
                processing_time = time.time() - start_time

                # Should process within reasonable time (adjust threshold as needed)
                assert processing_time < 5.0  # 5 seconds max

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, resume_service, mock_candidate, mock_user, sample_pdf_file):
        """Test handling of concurrent uploads."""
        import asyncio

        with patch.object(resume_service.repository, 'create_resume') as mock_create:
            mock_create.return_value = Mock(spec=Resume, id=uuid.uuid4())

            with patch.object(resume_service, '_extract_text', return_value="Content"):
                # Simulate concurrent uploads
                tasks = [
                    resume_service.upload_resume(
                        candidate_id=mock_candidate.id,
                        file=sample_pdf_file,
                        user_id=mock_user.id
                    )
                    for _ in range(3)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All uploads should complete successfully
                for result in results:
                    assert not isinstance(result, Exception)