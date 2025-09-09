"""Unit tests for file upload service."""

import io
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
import uuid

from app.features.file_upload.service import FileUploadService
from app.features.file_upload.models import FileStatus, FileType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def file_service(mock_db):
    """Create file upload service with mock DB."""
    return FileUploadService(mock_db)


@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF upload file."""
    content = b"%PDF-1.4\n%Test PDF content\n"
    file = Mock(spec=UploadFile)
    file.filename = "test_resume.pdf"
    file.content_type = "application/pdf"
    file.size = len(content)
    file.read = AsyncMock(return_value=content)
    return file


@pytest.fixture
def mock_txt_file():
    """Create a mock text upload file."""
    content = b"John Doe\nSoftware Engineer\nExperience: 5 years"
    file = Mock(spec=UploadFile)
    file.filename = "test_resume.txt"
    file.content_type = "text/plain"
    file.size = len(content)
    file.read = AsyncMock(return_value=content)
    return file


class TestFileUploadService:
    """Test file upload service functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self, file_service, mock_pdf_file):
        """Test successful file validation."""
        # Should not raise any exception
        await file_service._validate_file(mock_pdf_file)
    
    @pytest.mark.asyncio
    async def test_validate_file_invalid_extension(self, file_service):
        """Test validation fails for invalid file extension."""
        file = Mock(spec=UploadFile)
        file.filename = "test.exe"
        file.content_type = "application/x-msdownload"
        file.size = 1000
        
        with pytest.raises(ValueError, match="File type not supported"):
            await file_service._validate_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, file_service):
        """Test validation fails for oversized file."""
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        file.content_type = "application/pdf"
        file.size = 11 * 1024 * 1024  # 11MB
        
        with pytest.raises(ValueError, match="File too large"):
            await file_service._validate_file(file)
    
    @pytest.mark.asyncio
    async def test_validate_content_too_small(self, file_service):
        """Test content validation fails for too small file."""
        content = b"abc"  # Very small content
        
        with pytest.raises(ValueError, match="File too small"):
            await file_service._validate_content(content)
    
    def test_extract_text_from_txt(self, file_service):
        """Test text extraction from TXT file."""
        content = b"Test resume content\nWith multiple lines"
        
        result = file_service._extract_text(content, '.txt')
        
        assert result == "Test resume content\nWith multiple lines"
    
    def test_calculate_metadata(self, file_service):
        """Test metadata calculation."""
        text = "John Doe\njohn@example.com\n123-456-7890\nSoftware Engineer"
        content = text.encode()
        
        metadata = file_service._calculate_metadata(text, content)
        
        assert metadata["line_count"] == 4
        assert metadata["word_count"] == 5
        assert metadata["has_email"] == True
        assert metadata["has_phone"] == True
    
    def test_get_file_type(self, file_service):
        """Test file type mapping."""
        assert file_service._get_file_type(".pdf") == FileType.PDF
        assert file_service._get_file_type(".docx") == FileType.DOCX
        assert file_service._get_file_type(".doc") == FileType.DOC
        assert file_service._get_file_type(".txt") == FileType.TXT
        assert file_service._get_file_type(".unknown") == FileType.TXT  # Default
    
    @pytest.mark.asyncio
    async def test_process_upload_success(self, file_service, mock_txt_file):
        """Test successful file upload processing."""
        user_id = uuid.uuid4()
        
        # Mock repository methods
        mock_upload = Mock()
        mock_upload.id = uuid.uuid4()
        mock_upload.original_filename = "test_resume.txt"
        mock_upload.file_size = 50
        mock_upload.file_type = "txt"
        mock_upload.status = FileStatus.COMPLETED
        mock_upload.error_message = None
        mock_upload.created_at = Mock()
        mock_upload.created_at.timestamp = Mock(return_value=1234567890)
        mock_upload.upload_started_at = Mock()
        mock_upload.upload_started_at.timestamp = Mock(return_value=1234567890)
        mock_upload.upload_completed_at = Mock()
        mock_upload.upload_completed_at.timestamp = Mock(return_value=1234567891)
        mock_upload.processing_time_ms = 1000
        
        file_service.repository.create_upload = AsyncMock(return_value=mock_upload)
        file_service.repository.update_status = AsyncMock(return_value=mock_upload)
        file_service.repository.update_extracted_text = AsyncMock(return_value=mock_upload)
        
        # Process upload
        result = await file_service.process_upload(mock_txt_file, user_id)
        
        # Verify result
        assert result.id == str(mock_upload.id)
        assert result.status == FileStatus.COMPLETED
        assert result.extractedText is not None
        assert result.error is None
        
        # Verify repository calls
        file_service.repository.create_upload.assert_called_once()
        assert file_service.repository.update_status.call_count >= 2  # At least validating and completed
        file_service.repository.update_extracted_text.assert_called_once()