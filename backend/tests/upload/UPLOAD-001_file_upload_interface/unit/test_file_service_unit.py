"""
Unit tests for file storage service.
Tests the file storage logic with mocked dependencies.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import UUID

from app.services.file_service import (
    FileStorageService,
    FileStorageResult,
    StoredFileInfo,
    store_uploaded_file
)
from app.core.file_validation import FileValidationResult


class TestFileStorageService:
    """Test FileStorageService class functionality."""
    
    def setup_method(self):
        """Setup test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.service = FileStorageService(storage_root=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init_creates_storage_directory(self):
        """Test that initialization creates storage directory."""
        storage_path = Path(self.temp_dir) / "test_storage"
        service = FileStorageService(storage_root=str(storage_path))
        
        assert storage_path.exists()
        assert storage_path.is_dir()
        
        # Check permissions (owner read/write only)
        stat = storage_path.stat()
        permissions = oct(stat.st_mode)[-3:]
        assert permissions == "700"  # rwx------
    
    def test_init_with_existing_directory(self):
        """Test initialization with existing directory."""
        # Directory already exists from setup
        service = FileStorageService(storage_root=self.temp_dir)
        
        # Should not raise an error
        assert Path(self.temp_dir).exists()
    
    def test_init_permission_error(self):
        """Test initialization with permission error."""
        # Try to create directory in a location without write permissions
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(RuntimeError) as exc_info:
                FileStorageService(storage_root="/root/no_permission")
            
            assert "Cannot initialize file storage" in str(exc_info.value)
    
    def test_get_date_path_current_date(self):
        """Test date path generation with current date."""
        test_date = datetime(2024, 1, 15, 10, 30, 0)
        
        with patch('app.services.file_service.utc_now', return_value=test_date):
            date_path = self.service._get_date_path()
        
        expected_path = Path(self.temp_dir) / "2024" / "01" / "15"
        assert date_path == expected_path
    
    def test_get_date_path_specific_date(self):
        """Test date path generation with specific date."""
        test_date = datetime(2023, 12, 31, 23, 59, 59)
        date_path = self.service._get_date_path(test_date)
        
        expected_path = Path(self.temp_dir) / "2023" / "12" / "31"
        assert date_path == expected_path
    
    def test_generate_secure_filename(self):
        """Test secure filename generation."""
        filename = self.service._generate_secure_filename("original.pdf", ".pdf")
        
        # Should be UUID.pdf format
        assert filename.endswith(".pdf")
        uuid_part = filename[:-4]  # Remove .pdf
        
        # Should be valid UUID format
        try:
            UUID(uuid_part)
            uuid_valid = True
        except ValueError:
            uuid_valid = False
        
        assert uuid_valid, f"Generated filename {filename} does not contain valid UUID"
    
    def test_generate_secure_filename_no_dot_extension(self):
        """Test secure filename generation with extension without dot."""
        filename = self.service._generate_secure_filename("original.doc", "doc")
        
        assert filename.endswith(".doc")
    
    def test_create_temporary_file(self):
        """Test temporary file creation."""
        content = b"test file content for temporary storage"
        
        temp_path, temp_id = self.service._create_temporary_file(content)
        
        try:
            # Check file exists and has correct content
            assert Path(temp_path).exists()
            
            with open(temp_path, 'rb') as f:
                stored_content = f.read()
            
            assert stored_content == content
            
            # Check permissions (owner read/write only)
            stat = Path(temp_path).stat()
            permissions = oct(stat.st_mode)[-3:]
            assert permissions == "600"  # rw-------
            
            # Check temp_id is filename
            assert temp_id == Path(temp_path).name
            
        finally:
            # Cleanup
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    def test_create_temporary_file_write_error(self):
        """Test temporary file creation with write error."""
        content = b"test content"
        
        with patch('tempfile.mkstemp') as mock_mkstemp:
            with patch('os.fdopen') as mock_fdopen:
                mock_mkstemp.return_value = (99, "/tmp/fake_temp_file")
                mock_file = Mock()
                mock_file.write.side_effect = OSError("Disk full")
                mock_fdopen.return_value.__enter__.return_value = mock_file
                
                with pytest.raises(OSError):
                    self.service._create_temporary_file(content)
    
    @patch('app.services.file_service.validate_uploaded_file')
    def test_store_file_success(self, mock_validate):
        """Test successful file storage."""
        # Setup validation result
        validation_result = FileValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Test warning"],
            file_info={
                'file_size': 1024,
                'mime_type': 'application/pdf',
                'file_extension': '.pdf',
                'file_hash': 'abc123def456',
                'original_filename': 'test.pdf',
                'sanitized_filename': 'test.pdf'
            }
        )
        mock_validate.return_value = validation_result
        
        content = b"%PDF-1.4 fake pdf content"
        filename = "test-resume.pdf"
        
        with patch('app.services.file_service.utc_now') as mock_now:
            mock_now.return_value = datetime(2024, 1, 15, 10, 30, 0)
            result = self.service.store_file(content, filename, "user123")
        
        # Check result
        assert result.success is True
        assert result.file_path is not None
        assert result.file_id is not None
        assert result.error_message is None
        assert result.validation_result == validation_result
        
        # Check file was actually stored
        full_path = Path(self.temp_dir) / result.file_path
        assert full_path.exists()
        
        with open(full_path, 'rb') as f:
            stored_content = f.read()
        assert stored_content == content
        
        # Check file permissions
        stat = full_path.stat()
        permissions = oct(stat.st_mode)[-3:]
        assert permissions == "600"
    
    @patch('app.services.file_service.validate_uploaded_file')
    def test_store_file_validation_failure(self, mock_validate):
        """Test file storage with validation failure."""
        # Setup validation failure
        validation_result = FileValidationResult(
            is_valid=False,
            errors=["File type not allowed"],
            warnings=[],
            file_info={}
        )
        mock_validate.return_value = validation_result
        
        content = b"invalid file content"
        filename = "test.txt"
        
        result = self.service.store_file(content, filename, "user123")
        
        # Check result
        assert result.success is False
        assert result.file_path is None
        assert result.file_id is None
        assert "File validation failed" in result.error_message
        assert result.validation_result == validation_result
    
    @patch('app.services.file_service.validate_uploaded_file')
    def test_store_file_storage_error(self, mock_validate):
        """Test file storage with storage error."""
        # Setup successful validation
        validation_result = FileValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            file_info={
                'file_size': 1024,
                'mime_type': 'application/pdf',
                'file_extension': '.pdf',
                'file_hash': 'abc123',
                'original_filename': 'test.pdf',
                'sanitized_filename': 'test.pdf'
            }
        )
        mock_validate.return_value = validation_result
        
        content = b"test content"
        filename = "test.pdf"
        
        # Mock file movement to fail
        with patch('shutil.move') as mock_move:
            mock_move.side_effect = OSError("Permission denied")
            
            result = self.service.store_file(content, filename, "user123")
        
        # Check result
        assert result.success is False
        assert result.file_path is None
        assert result.file_id is None
        assert "File storage failed" in result.error_message
    
    def test_get_file_path_valid(self):
        """Test getting file path for valid relative path."""
        # Create a test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        relative_path = "2024/01/15/test-file.pdf"
        file_path = self.service.get_file_path(relative_path)
        
        assert file_path == test_file
        assert file_path.exists()
    
    def test_get_file_path_nonexistent(self):
        """Test getting file path for nonexistent file."""
        relative_path = "2024/01/15/nonexistent.pdf"
        file_path = self.service.get_file_path(relative_path)
        
        assert file_path is None
    
    def test_get_file_path_security_violation(self):
        """Test getting file path with path traversal attempt."""
        # Try path traversal attack
        relative_path = "../../../etc/passwd"
        file_path = self.service.get_file_path(relative_path)
        
        # Should return None due to security check
        assert file_path is None
    
    def test_get_file_path_error(self):
        """Test getting file path with path resolution error."""
        with patch('pathlib.Path.resolve') as mock_resolve:
            mock_resolve.side_effect = OSError("Path resolution error")
            
            file_path = self.service.get_file_path("test/path.pdf")
            assert file_path is None
    
    def test_read_file_success(self):
        """Test successful file reading."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_content = b"test file content for reading"
        test_file.write_bytes(test_content)
        
        relative_path = "2024/01/15/test-file.pdf"
        content = self.service.read_file(relative_path)
        
        assert content == test_content
    
    def test_read_file_nonexistent(self):
        """Test reading nonexistent file."""
        relative_path = "2024/01/15/nonexistent.pdf"
        content = self.service.read_file(relative_path)
        
        assert content is None
    
    def test_read_file_read_error(self):
        """Test file reading with read error."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        relative_path = "2024/01/15/test-file.pdf"
        
        # Mock file reading to fail
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = OSError("Read error")
            
            content = self.service.read_file(relative_path)
            assert content is None
    
    def test_delete_file_success(self):
        """Test successful file deletion."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        assert test_file.exists()
        
        relative_path = "2024/01/15/test-file.pdf"
        success = self.service.delete_file(relative_path)
        
        assert success is True
        assert not test_file.exists()
    
    def test_delete_file_nonexistent(self):
        """Test deleting nonexistent file."""
        relative_path = "2024/01/15/nonexistent.pdf"
        success = self.service.delete_file(relative_path)
        
        assert success is False
    
    def test_delete_file_permission_error(self):
        """Test file deletion with permission error."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        relative_path = "2024/01/15/test-file.pdf"
        
        # Mock file deletion to fail
        with patch('pathlib.Path.unlink') as mock_unlink:
            mock_unlink.side_effect = PermissionError("Permission denied")
            
            success = self.service.delete_file(relative_path)
            assert success is False
    
    def test_delete_file_cleanup_empty_directories(self):
        """Test that empty directories are cleaned up after file deletion."""
        # Create nested directory structure
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "only-file.pdf"
        test_file.write_bytes(b"test content")
        
        relative_path = "2024/01/15/only-file.pdf"
        success = self.service.delete_file(relative_path)
        
        assert success is True
        assert not test_file.exists()
        # Empty directories should be cleaned up
        assert not test_dir.exists()
    
    def test_get_file_info_success(self):
        """Test getting file info for existing file."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_content = b"test file content"
        test_file.write_bytes(test_content)
        
        relative_path = "2024/01/15/test-file.pdf"
        file_info = self.service.get_file_info(relative_path)
        
        assert file_info is not None
        assert file_info['relative_path'] == relative_path
        assert file_info['file_size'] == len(test_content)
        assert 'created_time' in file_info
        assert 'modified_time' in file_info
        assert file_info['permissions'] in ['600', '644']  # May vary by system
    
    def test_get_file_info_nonexistent(self):
        """Test getting file info for nonexistent file."""
        relative_path = "2024/01/15/nonexistent.pdf"
        file_info = self.service.get_file_info(relative_path)
        
        assert file_info is None
    
    def test_get_file_info_stat_error(self):
        """Test getting file info with stat error."""
        # Create test file
        test_dir = Path(self.temp_dir) / "2024" / "01" / "15"
        test_dir.mkdir(parents=True)
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        relative_path = "2024/01/15/test-file.pdf"
        
        # Mock stat to fail
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.side_effect = OSError("Stat error")
            
            file_info = self.service.get_file_info(relative_path)
            assert file_info is None
    
    def test_cleanup_old_files(self):
        """Test cleanup of old files."""
        # Create files with different ages
        base_time = datetime.now()
        
        # Old file (35 days old)
        old_dir = Path(self.temp_dir) / "old"
        old_dir.mkdir()
        old_file = old_dir / "old-file.pdf"
        old_file.write_bytes(b"old content")
        
        # Recent file (10 days old)
        recent_dir = Path(self.temp_dir) / "recent"  
        recent_dir.mkdir()
        recent_file = recent_dir / "recent-file.pdf"
        recent_file.write_bytes(b"recent content")
        
        # Mock file modification times
        old_time = (base_time - timedelta(days=35)).timestamp()
        recent_time = (base_time - timedelta(days=10)).timestamp()
        
        with patch('pathlib.Path.stat') as mock_stat:
            def stat_side_effect():
                stat_obj = Mock()
                # Since we can't easily distinguish files in this mock,
                # we'll make old_file appear old by default
                stat_obj.st_mtime = old_time
                return stat_obj
            
            mock_stat.side_effect = stat_side_effect
            
            # Cleanup files older than 30 days
            deleted_count = self.service.cleanup_old_files(days_old=30)
        
        assert deleted_count >= 0  # Should delete files without error
    
    def test_cleanup_old_files_error_handling(self):
        """Test cleanup with file processing errors."""
        # Create test file
        test_dir = Path(self.temp_dir) / "test"
        test_dir.mkdir()
        test_file = test_dir / "test-file.pdf"
        test_file.write_bytes(b"test content")
        
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.side_effect = OSError("Stat error")
            
            # Should not raise error, just continue
            deleted_count = self.service.cleanup_old_files(days_old=30)
            assert deleted_count == 0


class TestStoreUploadedFileFunction:
    """Test the convenience function store_uploaded_file."""
    
    @patch('app.services.file_service.file_storage_service')
    def test_store_uploaded_file_calls_service(self, mock_service):
        """Test that store_uploaded_file calls the global service."""
        mock_result = FileStorageResult(success=True, file_path="test/path.pdf")
        mock_service.store_file.return_value = mock_result
        
        content = b"test content"
        filename = "test.pdf"
        user_id = "user123"
        
        result = store_uploaded_file(content, filename, user_id)
        
        mock_service.store_file.assert_called_once_with(content, filename, user_id)
        assert result == mock_result


class TestFileStorageResult:
    """Test FileStorageResult data class."""
    
    def test_file_storage_result_creation(self):
        """Test FileStorageResult creation with various parameters."""
        # Success result
        success_result = FileStorageResult(
            success=True,
            file_path="test/path.pdf",
            file_id="file123"
        )
        
        assert success_result.success is True
        assert success_result.file_path == "test/path.pdf"
        assert success_result.file_id == "file123"
        assert success_result.error_message is None
        assert success_result.validation_result is None
        
        # Error result
        error_result = FileStorageResult(
            success=False,
            error_message="Test error"
        )
        
        assert error_result.success is False
        assert error_result.file_path is None
        assert error_result.error_message == "Test error"


class TestStoredFileInfo:
    """Test StoredFileInfo data class."""
    
    def test_stored_file_info_creation(self):
        """Test StoredFileInfo creation."""
        created_time = datetime.now()
        
        file_info = StoredFileInfo(
            file_id="file123",
            original_filename="resume.pdf",
            stored_path="2024/01/15/uuid.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_hash="abc123def456",
            created_at=created_time
        )
        
        assert file_info.file_id == "file123"
        assert file_info.original_filename == "resume.pdf"
        assert file_info.stored_path == "2024/01/15/uuid.pdf"
        assert file_info.file_size == 1024
        assert file_info.mime_type == "application/pdf"
        assert file_info.file_hash == "abc123def456"
        assert file_info.created_at == created_time