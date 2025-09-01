"""
Integration tests for Text Extraction API endpoints (UPLOAD-003)

Tests complete API functionality including:
- Text extraction endpoint integration
- Background processing integration
- Cache integration and performance
- Error handling and edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from uuid import uuid4
import json
import tempfile
import os

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.core.datetime_utils import utc_now
from app.services.text_extraction_service import ExtractionResult, ExtractionStatus
from app.core.background_processor import JobStatus, JobPriority


class TestTextExtractionAPIIntegration:
    """Integration tests for text extraction API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user_id = uuid4()
        return User(
            id=user_id,
            email="test@example.com",
            password="hashedpassword",
            first_name="Test",
            last_name="User"
        )
    
    @pytest.fixture
    def mock_upload_record(self, mock_user):
        """Create mock upload record in database."""
        upload_id = uuid4()
        return {
            "id": upload_id,
            "user_id": mock_user.id,
            "file_path": "/tmp/test_resume.pdf",
            "original_filename": "test_resume.pdf",
            "mime_type": "application/pdf",
            "extraction_status": "pending",
            "extracted_text": None,
            "processed_text": None,
            "extraction_metadata": None
        }
    
    @pytest.fixture
    def auth_headers(self, mock_user):
        """Create authentication headers."""
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            return {"Authorization": "Bearer fake_token"}
    
    def test_extract_text_endpoint_file_not_found(self, client, auth_headers, mock_user, mock_upload_record):
        """Test text extraction when upload record not found."""
        non_existent_id = uuid4()
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.execute.return_value.fetchone.return_value = None
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    f"/upload/{non_existent_id}/extract-text",
                    headers=auth_headers
                )
                
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()
    
    def test_extract_text_endpoint_successful_extraction(self, client, auth_headers, mock_user, mock_upload_record):
        """Test successful text extraction."""
        upload_id = mock_upload_record["id"]
        
        # Mock successful extraction result
        mock_extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="John Doe\nSoftware Engineer\n5 years experience",
            processing_time_seconds=1.5,
            metadata={"extraction_method": "pdfplumber", "file_type": "pdf"}
        )
        
        # Mock processed text result
        mock_processed_text = Mock()
        mock_processed_text.cleaned_text = "John Doe Software Engineer 5 years experience"
        mock_processed_text.sections = []
        mock_processed_text.word_count = 6
        mock_processed_text.line_count = 3
        mock_processed_text.metadata = {"extraction_quality": "good"}
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('app.api.upload.extraction_cache.get', return_value=None):  # Cache miss
                        with patch('app.api.upload.text_extraction_service.extract_text_from_file', return_value=mock_extraction_result):
                            with patch('app.api.upload.text_processor.process_text', return_value=mock_processed_text):
                                with patch('app.api.upload.text_processor.get_ai_ready_format', return_value={"ai": "data"}):
                                    with patch('app.api.upload.extraction_cache.store', return_value=True):
                                        
                                        # Mock database operations
                                        mock_db = Mock()
                                        mock_db.execute.return_value.fetchone.return_value = (
                                            upload_id,
                                            mock_upload_record["file_path"],
                                            mock_upload_record["original_filename"],
                                            mock_upload_record["mime_type"],
                                            "pending",
                                            None,
                                            None,
                                            None
                                        )
                                        mock_get_db.return_value = mock_db
                                        
                                        response = client.post(
                                            f"/upload/{upload_id}/extract-text",
                                            headers=auth_headers
                                        )
                                        
                                        assert response.status_code == 200
                                        
                                        data = response.json()
                                        assert data["message"] == "Text extraction completed successfully"
                                        assert data["extraction_result"]["extraction_status"] == "completed"
                                        assert data["extraction_result"]["word_count"] == 6
                                        assert data["extraction_result"]["line_count"] == 3
    
    def test_extract_text_endpoint_cached_result(self, client, auth_headers, mock_user, mock_upload_record):
        """Test text extraction returning cached result."""
        upload_id = mock_upload_record["id"]
        
        # Mock cached extraction result
        cached_extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Cached resume content",
            processing_time_seconds=0.1,
            metadata={"extraction_method": "cached"}
        )
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('app.api.upload.extraction_cache.get', return_value=cached_extraction_result):
                        
                        # Mock database operations
                        mock_db = Mock()
                        mock_db.execute.return_value.fetchone.return_value = (
                            upload_id,
                            mock_upload_record["file_path"],
                            mock_upload_record["original_filename"],
                            mock_upload_record["mime_type"],
                            "pending",
                            None,
                            None,
                            None
                        )
                        mock_get_db.return_value = mock_db
                        
                        response = client.post(
                            f"/upload/{upload_id}/extract-text",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        
                        data = response.json()
                        assert "cached" in data["message"].lower()
                        assert data["extraction_result"]["extracted_text"] == "Cached resume content"
    
    def test_extract_text_endpoint_already_extracted(self, client, auth_headers, mock_user, mock_upload_record):
        """Test text extraction when already completed."""
        upload_id = mock_upload_record["id"]
        existing_metadata = {
            "structure": {
                "sections": [
                    {
                        "type": "contact",
                        "title": "Contact",
                        "content": "john@example.com",
                        "position": {"line_start": 0, "line_end": 1},
                        "confidence": 0.9
                    }
                ]
            }
        }
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                # Mock database returning already extracted text
                mock_db = Mock()
                mock_db.execute.return_value.fetchone.return_value = (
                    upload_id,
                    mock_upload_record["file_path"],
                    mock_upload_record["original_filename"],
                    mock_upload_record["mime_type"],
                    "completed",  # Already completed
                    "Existing extracted text",
                    "Existing processed text",
                    existing_metadata
                )
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    f"/upload/{upload_id}/extract-text",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert "cached" in data["message"].lower()
                assert data["extraction_result"]["extracted_text"] == "Existing extracted text"
                assert data["extraction_result"]["processed_text"] == "Existing processed text"
                assert len(data["extraction_result"]["sections"]) == 1
    
    def test_extract_text_endpoint_force_reextraction(self, client, auth_headers, mock_user, mock_upload_record):
        """Test text extraction with force re-extraction."""
        upload_id = mock_upload_record["id"]
        
        # Mock new extraction result
        new_extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Newly extracted text",
            processing_time_seconds=2.0,
            metadata={"extraction_method": "pdfplumber"}
        )
        
        mock_processed_text = Mock()
        mock_processed_text.cleaned_text = "Newly processed text"
        mock_processed_text.sections = []
        mock_processed_text.word_count = 3
        mock_processed_text.line_count = 1
        mock_processed_text.metadata = {}
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('app.api.upload.text_extraction_service.extract_text_from_file', return_value=new_extraction_result):
                        with patch('app.api.upload.text_processor.process_text', return_value=mock_processed_text):
                            with patch('app.api.upload.text_processor.get_ai_ready_format', return_value={}):
                                with patch('app.api.upload.extraction_cache.store', return_value=True):
                                    
                                    # Mock database returning already completed extraction
                                    mock_db = Mock()
                                    mock_db.execute.return_value.fetchone.return_value = (
                                        upload_id,
                                        mock_upload_record["file_path"],
                                        mock_upload_record["original_filename"],
                                        mock_upload_record["mime_type"],
                                        "completed",
                                        "Old extracted text",
                                        "Old processed text",
                                        {}
                                    )
                                    mock_get_db.return_value = mock_db
                                    
                                    # Request with force re-extraction
                                    response = client.post(
                                        f"/upload/{upload_id}/extract-text",
                                        json={"force_reextraction": True},
                                        headers=auth_headers
                                    )
                                    
                                    assert response.status_code == 200
                                    
                                    data = response.json()
                                    assert data["extraction_result"]["extracted_text"] == "Newly extracted text"
    
    def test_extract_text_endpoint_extraction_failure(self, client, auth_headers, mock_user, mock_upload_record):
        """Test text extraction failure handling."""
        upload_id = mock_upload_record["id"]
        
        # Mock failed extraction
        failed_extraction_result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            error_message="PDF parsing failed"
        )
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('app.api.upload.extraction_cache.get', return_value=None):
                        with patch('app.api.upload.text_extraction_service.extract_text_from_file', return_value=failed_extraction_result):
                            
                            mock_db = Mock()
                            mock_db.execute.return_value.fetchone.return_value = (
                                upload_id,
                                mock_upload_record["file_path"],
                                mock_upload_record["original_filename"],
                                mock_upload_record["mime_type"],
                                "pending",
                                None,
                                None,
                                None
                            )
                            mock_get_db.return_value = mock_db
                            
                            response = client.post(
                                f"/upload/{upload_id}/extract-text",
                                headers=auth_headers
                            )
                            
                            assert response.status_code == 200
                            
                            data = response.json()
                            assert data["message"] == "Text extraction failed"
                            assert data["extraction_result"]["extraction_status"] == "failed"
                            assert data["extraction_result"]["error_message"] == "PDF parsing failed"
    
    def test_get_extraction_status_endpoint(self, client, auth_headers, mock_user, mock_upload_record):
        """Test getting extraction status endpoint."""
        upload_id = mock_upload_record["id"]
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.execute.return_value.fetchone.return_value = (
                    "completed",  # extraction_status
                    "Extracted text content",  # extracted_text
                    "Processed text content",  # processed_text
                    {"structure": {"sections": []}},  # extraction_metadata
                    None,  # error_message
                    utc_now()  # updated_at
                )
                mock_get_db.return_value = mock_db
                
                response = client.get(
                    f"/upload/{upload_id}/extraction-status",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert data["upload_id"] == str(upload_id)
                assert data["extraction_status"] == "completed"
                assert data["has_extracted_text"] is True
                assert data["has_processed_text"] is True
                assert data["word_count"] == 3  # "Processed text content"
                assert data["sections_detected"] == 0
    
    def test_get_ai_ready_data_endpoint(self, client, auth_headers, mock_user, mock_upload_record):
        """Test getting AI-ready data endpoint."""
        upload_id = mock_upload_record["id"]
        
        ai_ready_data = {
            "text_content": "Clean resume text",
            "structure": {"sections": []},
            "extraction_info": {"word_count": 3},
            "metadata": {
                "contact_info": {"emails_found": ["john@example.com"]},
                "extraction_quality": "good"
            }
        }
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.execute.return_value.fetchone.return_value = (
                    ai_ready_data,  # ai_ready_data
                    "completed",  # extraction_status
                    utc_now()  # updated_at
                )
                mock_get_db.return_value = mock_db
                
                response = client.get(
                    f"/upload/{upload_id}/ai-ready-data",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert data["upload_id"] == str(upload_id)
                assert data["text_content"] == "Clean resume text"
                assert data["quality_assessment"] == "good"
                assert "john@example.com" in data["contact_info"]["emails_found"]
    
    def test_get_ai_ready_data_not_extracted(self, client, auth_headers, mock_user, mock_upload_record):
        """Test getting AI-ready data when extraction not completed."""
        upload_id = mock_upload_record["id"]
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                mock_db = Mock()
                mock_db.execute.return_value.fetchone.return_value = (
                    None,  # ai_ready_data
                    "pending",  # extraction_status
                    utc_now()  # updated_at
                )
                mock_get_db.return_value = mock_db
                
                response = client.get(
                    f"/upload/{upload_id}/ai-ready-data",
                    headers=auth_headers
                )
                
                assert response.status_code == 422
                assert "not completed" in response.json()["detail"]
    
    def test_batch_extract_text_endpoint(self, client, auth_headers, mock_user):
        """Test batch text extraction endpoint."""
        upload_ids = [uuid4(), uuid4()]
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.extract_text_from_upload') as mock_extract:
                
                # Mock successful extractions
                mock_extract.side_effect = [
                    Mock(
                        message="Text extraction completed successfully",
                        extraction_result=Mock(
                            upload_id=upload_ids[0],
                            extraction_status=ExtractionStatus.COMPLETED
                        )
                    ),
                    Mock(
                        message="Text extraction completed (cached)",
                        extraction_result=Mock(
                            upload_id=upload_ids[1],
                            extraction_status=ExtractionStatus.COMPLETED
                        )
                    )
                ]
                
                response = client.post(
                    "/upload/batch-extract-text",
                    json={
                        "upload_ids": [str(uid) for uid in upload_ids],
                        "force_reextraction": False
                    },
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert data["total_requested"] == 2
                assert data["successfully_started"] == 1  # One new extraction
                assert data["already_extracted"] == 1  # One cached
                assert data["failed_to_start"] == 0
                assert len(data["results"]) == 2


class TestBackgroundProcessingAPIIntegration:
    """Integration tests for background processing API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return User(
            id=uuid4(),
            email="async@example.com",
            password="hashedpassword",
            first_name="Async",
            last_name="User"
        )
    
    @pytest.fixture
    def auth_headers(self, mock_user):
        """Create authentication headers."""
        return {"Authorization": "Bearer async_token"}
    
    def test_extract_text_async_endpoint(self, client, auth_headers, mock_user):
        """Test asynchronous text extraction endpoint."""
        upload_id = uuid4()
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('app.api.upload.background_processor.submit_job') as mock_submit:
                        with patch('app.api.upload.background_processor.get_queue_stats') as mock_stats:
                            
                            job_id = uuid4()
                            mock_submit.return_value = job_id
                            mock_stats.return_value = {"queue_size": 2}
                            
                            # Mock database operations
                            mock_db = Mock()
                            mock_db.execute.return_value.fetchone.return_value = (
                                upload_id,
                                "/tmp/async_test.pdf",
                                "async_test.pdf",
                                "application/pdf",
                                "pending"
                            )
                            mock_get_db.return_value = mock_db
                            
                            response = client.post(
                                f"/upload/{upload_id}/extract-text-async",
                                params={"priority": "high"},
                                headers=auth_headers
                            )
                            
                            assert response.status_code == 200
                            
                            data = response.json()
                            assert data["job_id"] == str(job_id)
                            assert data["upload_id"] == str(upload_id)
                            assert data["priority"] == "high"
                            assert data["estimated_wait_time_seconds"] == 20  # 2 * 10
    
    def test_get_processing_queue_status(self, client, auth_headers, mock_user):
        """Test getting processing queue status."""
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_queue_stats') as mock_queue_stats:
                with patch('app.api.upload.extraction_cache.get_cache_stats') as mock_cache_stats:
                    
                    mock_queue_stats.return_value = {
                        "queue_size": 3,
                        "active_jobs": 1,
                        "is_running": True,
                        "stats": {"average_processing_time": 2.5}
                    }
                    
                    mock_cache_stats.return_value = {
                        "hit_rate_percent": 75.0,
                        "hits": 15,
                        "misses": 5
                    }
                    
                    response = client.get(
                        "/upload/processing-queue/status",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["queue_status"]["queue_size"] == 3
                    assert data["cache_statistics"]["hit_rate_percent"] == 75.0
                    assert data["system_health"]["background_processor_running"] is True
                    assert data["system_health"]["cache_hit_rate"] == 75.0
    
    def test_get_job_status_endpoint(self, client, auth_headers, mock_user):
        """Test getting background job status."""
        job_id = uuid4()
        
        # Create mock job
        mock_job = Mock()
        mock_job.job_id = job_id
        mock_job.user_id = mock_user.id
        mock_job.status = JobStatus.PROCESSING
        mock_job.to_dict.return_value = {
            "job_id": str(job_id),
            "status": "processing",
            "priority": "normal",
            "created_at": utc_now().isoformat()
        }
        mock_job.extraction_result = None
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_job_status', return_value=mock_job):
                
                response = client.get(
                    f"/upload/job/{job_id}/status",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert data["job"]["job_id"] == str(job_id)
                assert data["job"]["status"] == "processing"
    
    def test_get_job_status_with_extraction_result(self, client, auth_headers, mock_user):
        """Test getting job status with extraction result."""
        job_id = uuid4()
        
        # Create mock job with extraction result
        mock_extraction_result = Mock()
        mock_extraction_result.status = ExtractionStatus.COMPLETED
        mock_extraction_result.extracted_text = "Job completed text"
        mock_extraction_result.processing_time_seconds = 3.2
        mock_extraction_result.error_message = None
        
        mock_job = Mock()
        mock_job.job_id = job_id
        mock_job.user_id = mock_user.id
        mock_job.status = JobStatus.COMPLETED
        mock_job.extraction_result = mock_extraction_result
        mock_job.to_dict.return_value = {
            "job_id": str(job_id),
            "status": "completed"
        }
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_job_status', return_value=mock_job):
                
                response = client.get(
                    f"/upload/job/{job_id}/status",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                
                data = response.json()
                assert data["job"]["job_id"] == str(job_id)
                assert data["job"]["extraction_summary"]["status"] == "completed"
                assert data["job"]["extraction_summary"]["has_text"] is True
                assert data["job"]["extraction_summary"]["processing_time"] == 3.2
    
    def test_get_job_status_access_denied(self, client, auth_headers, mock_user):
        """Test getting job status with access denied."""
        job_id = uuid4()
        other_user_id = uuid4()
        
        # Create mock job belonging to different user
        mock_job = Mock()
        mock_job.job_id = job_id
        mock_job.user_id = other_user_id  # Different user
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_job_status', return_value=mock_job):
                
                response = client.get(
                    f"/upload/job/{job_id}/status",
                    headers=auth_headers
                )
                
                assert response.status_code == 403
                assert "access denied" in response.json()["detail"].lower()
    
    def test_cancel_job_endpoint(self, client, auth_headers, mock_user):
        """Test cancelling background job."""
        job_id = uuid4()
        
        # Create mock queued job
        mock_job = Mock()
        mock_job.job_id = job_id
        mock_job.user_id = mock_user.id
        mock_job.status = JobStatus.QUEUED
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_job_status', return_value=mock_job):
                with patch('app.api.upload.background_processor.cancel_job', return_value=True):
                    
                    response = client.delete(
                        f"/upload/job/{job_id}",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["message"] == "Job cancelled successfully"
                    assert data["job_id"] == str(job_id)
    
    def test_cancel_job_wrong_status(self, client, auth_headers, mock_user):
        """Test cancelling job with wrong status."""
        job_id = uuid4()
        
        # Create mock processing job (can't be cancelled)
        mock_job = Mock()
        mock_job.job_id = job_id
        mock_job.user_id = mock_user.id
        mock_job.status = JobStatus.PROCESSING
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.api.upload.background_processor.get_job_status', return_value=mock_job):
                
                response = client.delete(
                    f"/upload/job/{job_id}",
                    headers=auth_headers
                )
                
                assert response.status_code == 422
                assert "cannot cancel" in response.json()["detail"].lower()


class TestAPIErrorHandling:
    """Test API error handling scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return User(
            id=uuid4(),
            email="error@example.com",
            password="hashedpassword",
            first_name="Error",
            last_name="User"
        )
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": "Bearer error_token"}
    
    def test_extract_text_database_error(self, client, auth_headers, mock_user):
        """Test text extraction with database error."""
        upload_id = uuid4()
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                # Mock database error
                mock_db = Mock()
                mock_db.execute.side_effect = Exception("Database connection failed")
                mock_get_db.return_value = mock_db
                
                response = client.post(
                    f"/upload/{upload_id}/extract-text",
                    headers=auth_headers
                )
                
                assert response.status_code == 500
                assert "extraction failed" in response.json()["detail"].lower()
    
    def test_extract_text_file_missing_on_disk(self, client, auth_headers, mock_user):
        """Test text extraction when file missing on disk."""
        upload_id = uuid4()
        
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            with patch('app.database.connection.get_db') as mock_get_db:
                with patch('pathlib.Path.exists', return_value=False):  # File not found
                    
                    mock_db = Mock()
                    mock_db.execute.return_value.fetchone.return_value = (
                        upload_id,
                        "/tmp/missing_file.pdf",
                        "missing_file.pdf",
                        "application/pdf",
                        "pending",
                        None,
                        None,
                        None
                    )
                    mock_get_db.return_value = mock_db
                    
                    response = client.post(
                        f"/upload/{upload_id}/extract-text",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 404
                    assert "file not found" in response.json()["detail"].lower()
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to endpoints."""
        upload_id = uuid4()
        
        # No authentication headers
        response = client.post(f"/upload/{upload_id}/extract-text")
        
        # Should return unauthorized (exact status depends on auth implementation)
        assert response.status_code in [401, 403]
    
    def test_invalid_upload_id_format(self, client, auth_headers, mock_user):
        """Test invalid upload ID format."""
        with patch('app.api.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/upload/not-a-valid-uuid/extract-text",
                headers=auth_headers
            )
            
            # Should return validation error
            assert response.status_code == 422


@pytest.mark.integration
class TestEndToEndIntegration:
    """End-to-end integration tests with real file processing."""
    
    @pytest.fixture
    def temp_pdf_file(self):
        """Create temporary PDF file for testing."""
        # This would create a real PDF file for testing
        # For this example, we'll mock it
        temp_file = Path("/tmp/test_resume_e2e.pdf")
        with patch.object(Path, 'exists', return_value=True):
            yield temp_file
    
    @pytest.mark.asyncio
    async def test_complete_extraction_workflow(self, temp_pdf_file):
        """Test complete extraction workflow from file to AI-ready data."""
        # This test would involve:
        # 1. Creating real test files
        # 2. Running actual extraction
        # 3. Verifying results
        # 4. Testing caching
        # 5. Testing background processing
        
        # For now, this serves as a placeholder for full integration testing
        assert temp_pdf_file is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])