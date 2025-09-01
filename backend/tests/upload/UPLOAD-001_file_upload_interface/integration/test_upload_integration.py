"""
Integration tests for file upload endpoints.
Tests the complete upload flow including database operations and file storage.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.upload import UploadStatus


@pytest.mark.asyncio
class TestFileUploadIntegration:
    """Integration tests for file upload functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
        self.temp_storage = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_storage).exists():
            shutil.rmtree(self.temp_storage)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def create_test_pdf_content(self) -> bytes:
        """Create minimal valid PDF content for testing."""
        return b"""%PDF-1.4
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
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000015 00000 n 
0000000074 00000 n 
0000000120 00000 n 
0000000179 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
274
%%EOF"""
    
    def create_test_doc_content(self) -> bytes:
        """Create minimal DOC content for testing."""
        # Create a minimal OLE compound document structure
        ole_header = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        padding = b'\x00' * 504  # Pad to 512 bytes minimum
        return ole_header + padding + b'Microsoft Word Document Content'
    
    def create_invalid_content(self) -> bytes:
        """Create invalid file content for testing."""
        return b"This is just plain text, not a valid document"
    
    @patch('app.services.file_service.file_storage_service')
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_pdf_success(self, mock_rate_limit, mock_storage, auth_headers, test_db):
        """Test successful PDF upload."""
        # Mock rate limiting to pass
        mock_rate_limit.return_value = None
        
        # Mock file storage to succeed
        from app.services.file_service import FileStorageResult
        from app.core.file_validation import FileValidationResult
        
        validation_result = FileValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            file_info={
                'file_size': 1000,
                'mime_type': 'application/pdf',
                'file_extension': '.pdf',
                'file_hash': 'abc123def456'
            }
        )
        
        storage_result = FileStorageResult(
            success=True,
            file_path="2024/01/15/test-file.pdf",
            file_id="file123",
            validation_result=validation_result
        )
        mock_storage.store_file.return_value = storage_result
        
        # Create test PDF content
        pdf_content = self.create_test_pdf_content()
        
        # Prepare upload data
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        data = {
            "target_role": "Software Engineer",
            "target_industry": "Technology",
            "experience_level": "mid"
        }
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 201
        response_data = response.json()
        
        assert "id" in response_data
        assert response_data["original_filename"] == "resume.pdf"
        assert response_data["file_size"] == 1000
        assert response_data["mime_type"] == "application/pdf"
        assert response_data["status"] == "pending"
        assert response_data["target_role"] == "Software Engineer"
        assert response_data["target_industry"] == "Technology"
        assert response_data["experience_level"] == "mid"
        
        # Check validation info
        validation_info = response_data["validation_info"]
        assert validation_info["is_valid"] is True
        assert validation_info["file_size"] == 1000
        assert validation_info["mime_type"] == "application/pdf"
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_validation_failure(self, mock_rate_limit, auth_headers):
        """Test upload with file validation failure."""
        # Mock rate limiting to pass
        mock_rate_limit.return_value = None
        
        # Create invalid content (text file)
        invalid_content = self.create_invalid_content()
        
        # Prepare upload data with invalid file
        files = {"file": ("resume.txt", invalid_content, "text/plain")}
        data = {"target_role": "Software Engineer"}
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Check response - should fail validation
        assert response.status_code == 400
        response_data = response.json()
        
        assert "detail" in response_data
        if isinstance(response_data["detail"], dict):
            assert response_data["detail"]["error"] == "FILE_VALIDATION_FAILED"
        else:
            assert "validation failed" in response_data["detail"].lower()
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_rate_limit_exceeded(self, mock_rate_limit, auth_headers):
        """Test upload with rate limit exceeded."""
        from fastapi import HTTPException
        
        # Mock rate limiting to fail
        mock_rate_limit.side_effect = HTTPException(
            status_code=429,
            detail="Too many requests"
        )
        
        pdf_content = self.create_test_pdf_content()
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 429
        assert "Too many requests" in response.json()["detail"]
    
    def test_upload_resume_unauthorized(self):
        """Test upload without authentication."""
        pdf_content = self.create_test_pdf_content()
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        
        # Make upload request without auth header
        response = self.client.post("/api/v1/upload/resume", files=files)
        
        # Check response
        assert response.status_code in [401, 403]
    
    def test_upload_resume_no_file(self, auth_headers):
        """Test upload without file."""
        data = {"target_role": "Software Engineer"}
        
        # Make upload request without file
        response = self.client.post(
            "/api/v1/upload/resume",
            data=data,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 422  # Validation error
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_empty_file(self, mock_rate_limit, auth_headers):
        """Test upload with empty file."""
        mock_rate_limit.return_value = None
        
        # Empty file
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 400
        response_data = response.json()
        assert "empty" in response_data["detail"].lower()
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_no_filename(self, mock_rate_limit, auth_headers):
        """Test upload with file but no filename."""
        mock_rate_limit.return_value = None
        
        pdf_content = self.create_test_pdf_content()
        files = {"file": ("", pdf_content, "application/pdf")}  # Empty filename
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 400
        response_data = response.json()
        assert "filename" in response_data["detail"].lower()
    
    @patch('app.services.file_service.file_storage_service')
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_storage_failure(self, mock_rate_limit, mock_storage, auth_headers):
        """Test upload with storage service failure."""
        mock_rate_limit.return_value = None
        
        # Mock storage to fail
        from app.services.file_service import FileStorageResult
        
        storage_result = FileStorageResult(
            success=False,
            error_message="Storage service unavailable"
        )
        mock_storage.store_file.return_value = storage_result
        
        pdf_content = self.create_test_pdf_content()
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        
        # Make upload request
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            headers=auth_headers
        )
        
        # Check response
        assert response.status_code == 500
        response_data = response.json()
        assert "Storage service unavailable" in response_data["detail"]
    
    @patch('app.services.file_service.file_storage_service')
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_database_error(self, mock_rate_limit, mock_storage, auth_headers, test_db):
        """Test upload with database error."""
        mock_rate_limit.return_value = None
        
        # Mock storage to succeed
        from app.services.file_service import FileStorageResult
        from app.core.file_validation import FileValidationResult
        
        validation_result = FileValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            file_info={
                'file_size': 1000,
                'mime_type': 'application/pdf',
                'file_extension': '.pdf',
                'file_hash': 'abc123'
            }
        )
        
        storage_result = FileStorageResult(
            success=True,
            file_path="2024/01/15/test-file.pdf",
            file_id="file123",
            validation_result=validation_result
        )
        mock_storage.store_file.return_value = storage_result
        
        pdf_content = self.create_test_pdf_content()
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        
        # Mock database execute to fail
        with patch.object(test_db, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Database connection error")
            
            # Make upload request
            response = self.client.post(
                "/api/v1/upload/resume",
                files=files,
                headers=auth_headers
            )
        
        # Check response
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to create analysis request" in response_data["detail"]


@pytest.mark.asyncio
class TestUploadListIntegration:
    """Integration tests for upload listing endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_list_user_uploads_empty(self, auth_headers, test_db):
        """Test listing uploads when user has no uploads."""
        response = self.client.get("/api/v1/upload/list", headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["uploads"] == []
        assert response_data["total"] == 0
        assert response_data["page"] == 1
        assert response_data["per_page"] == 20
        assert response_data["has_more"] is False
    
    def test_list_user_uploads_pagination(self, auth_headers):
        """Test upload listing with pagination parameters."""
        response = self.client.get(
            "/api/v1/upload/list?page=2&per_page=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["page"] == 2
        assert response_data["per_page"] == 10
    
    def test_list_user_uploads_invalid_pagination(self, auth_headers):
        """Test upload listing with invalid pagination parameters."""
        response = self.client.get(
            "/api/v1/upload/list?page=0&per_page=150",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Should normalize invalid values
        assert response_data["page"] == 1  # Normalized from 0
        assert response_data["per_page"] == 20  # Normalized from 150
    
    def test_list_user_uploads_unauthorized(self):
        """Test listing uploads without authentication."""
        response = self.client.get("/api/v1/upload/list")
        
        assert response.status_code in [401, 403]  # Either unauthorized or forbidden


@pytest.mark.asyncio 
class TestUploadStatusIntegration:
    """Integration tests for upload status endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_get_upload_status_not_found(self, auth_headers):
        """Test getting status for nonexistent upload."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = self.client.get(
            f"/api/v1/upload/{fake_uuid}/status",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"].lower()
    
    def test_get_upload_status_invalid_uuid(self, auth_headers):
        """Test getting status with invalid UUID format."""
        response = self.client.get(
            "/api/v1/upload/invalid-uuid/status",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_upload_status_unauthorized(self):
        """Test getting upload status without authentication."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = self.client.get(f"/api/v1/upload/{fake_uuid}/status")
        
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestUploadDeleteIntegration:
    """Integration tests for upload deletion endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_delete_upload_not_found(self, auth_headers):
        """Test deleting nonexistent upload."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = self.client.delete(
            f"/api/v1/upload/{fake_uuid}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        response_data = response.json()
        assert "not found" in response_data["detail"].lower()
    
    def test_delete_upload_invalid_uuid(self, auth_headers):
        """Test deleting upload with invalid UUID format."""
        response = self.client.delete(
            "/api/v1/upload/invalid-uuid",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_delete_upload_unauthorized(self):
        """Test deleting upload without authentication."""
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = self.client.delete(f"/api/v1/upload/{fake_uuid}")
        
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestUploadStatsIntegration:
    """Integration tests for upload statistics endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_get_upload_stats_empty(self, auth_headers):
        """Test getting upload stats when user has no uploads."""
        response = self.client.get("/api/v1/upload/stats", headers=auth_headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Check stats structure
        assert "stats" in response_data
        assert "rate_limit_info" in response_data
        
        stats = response_data["stats"]
        assert stats["total_uploads"] == 0
        assert stats["pending_uploads"] == 0
        assert stats["completed_uploads"] == 0
        assert stats["failed_uploads"] == 0
        assert stats["total_storage_bytes"] == 0
        assert stats["most_recent_upload"] is None
        assert isinstance(stats["file_type_breakdown"], dict)
        
        # Check rate limit info structure
        rate_limit = response_data["rate_limit_info"]
        assert "uploads_allowed_per_hour" in rate_limit
        assert rate_limit["uploads_allowed_per_hour"] == 30
    
    def test_get_upload_stats_unauthorized(self):
        """Test getting upload stats without authentication."""
        response = self.client.get("/api/v1/upload/stats")
        
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
class TestUploadEndpointValidation:
    """Test input validation for upload endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_invalid_experience_level(self, mock_rate_limit, auth_headers):
        """Test upload with invalid experience level."""
        mock_rate_limit.return_value = None
        
        pdf_content = b"%PDF-1.4 fake content %%EOF"
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        data = {"experience_level": "invalid_level"}
        
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Should return validation error
        assert response.status_code == 422
    
    @patch('app.core.rate_limiter.check_file_upload_rate_limit')
    def test_upload_resume_long_target_role(self, mock_rate_limit, auth_headers):
        """Test upload with very long target role."""
        mock_rate_limit.return_value = None
        
        pdf_content = b"%PDF-1.4 fake content %%EOF"
        files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
        data = {"target_role": "x" * 300}  # Very long role name
        
        response = self.client.post(
            "/api/v1/upload/resume",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        # Depending on validation, this might pass or fail
        # The important thing is it doesn't crash the server
        assert response.status_code in [200, 201, 400, 422]


@pytest.mark.asyncio
class TestUploadErrorHandling:
    """Test error handling in upload endpoints."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.client = TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, test_user_token):
        """Get authorization headers for authenticated requests."""
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_upload_resume_malformed_request(self, auth_headers):
        """Test upload with malformed request data."""
        # Send invalid JSON data
        response = self.client.post(
            "/api/v1/upload/resume",
            data="invalid json data",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 422]
    
    def test_upload_endpoints_handle_exceptions(self, auth_headers):
        """Test that endpoints handle unexpected exceptions gracefully."""
        # This test ensures that any unexpected errors don't crash the server
        # and return appropriate error responses
        
        with patch('app.api.upload.get_current_user') as mock_get_user:
            mock_get_user.side_effect = Exception("Unexpected error")
            
            response = self.client.get("/api/v1/upload/list", headers=auth_headers)
            
            # Should return 500 error, not crash
            assert response.status_code == 500
            assert "error" in response.json()["detail"].lower() or "failed" in response.json()["detail"].lower()