"""
Unit tests for file validation functionality.
Tests the core file validation logic without external dependencies.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.core.file_validation import (
    FileValidator,
    validate_uploaded_file,
    FileValidationResult,
    FileValidationError,
    MAX_FILE_SIZE,
    ALLOWED_MIME_TYPES,
    ALLOWED_EXTENSIONS
)


class TestFileValidator:
    """Test FileValidator class functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.validator = FileValidator()
    
    def test_validate_file_size_valid(self):
        """Test file size validation with valid sizes."""
        # Test normal file size (1MB)
        file_size = 1024 * 1024
        is_valid, errors = self.validator.validate_file_size(file_size)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_file_size_too_large(self):
        """Test file size validation with oversized files."""
        # Test file larger than 30MB
        file_size = MAX_FILE_SIZE + 1
        is_valid, errors = self.validator.validate_file_size(file_size)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "exceeds maximum allowed size" in errors[0]
    
    def test_validate_file_size_empty(self):
        """Test file size validation with empty files."""
        file_size = 0
        is_valid, errors = self.validator.validate_file_size(file_size)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "File is empty" in errors[0]
    
    def test_validate_file_size_negative(self):
        """Test file size validation with negative sizes."""
        file_size = -1
        is_valid, errors = self.validator.validate_file_size(file_size)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "File is empty" in errors[0]
    
    def test_validate_file_extension_valid(self):
        """Test file extension validation with valid extensions."""
        valid_filenames = [
            "resume.pdf",
            "document.doc", 
            "file.docx",
            "My Resume.PDF",
            "test-file.DOC"
        ]
        
        for filename in valid_filenames:
            is_valid, errors = self.validator.validate_file_extension(filename)
            assert is_valid is True, f"Failed for {filename}"
            assert len(errors) == 0, f"Unexpected errors for {filename}: {errors}"
    
    def test_validate_file_extension_invalid(self):
        """Test file extension validation with invalid extensions."""
        invalid_filenames = [
            "resume.txt",
            "document.jpg",
            "file.png",
            "test.exe",
            "malicious.bat"
        ]
        
        for filename in invalid_filenames:
            is_valid, errors = self.validator.validate_file_extension(filename)
            assert is_valid is False, f"Should have failed for {filename}"
            assert len(errors) == 1, f"Expected one error for {filename}"
            assert "not allowed" in errors[0], f"Wrong error message for {filename}"
    
    def test_validate_file_extension_no_extension(self):
        """Test file extension validation without extension."""
        is_valid, errors = self.validator.validate_file_extension("filename")
        
        assert is_valid is False
        assert len(errors) == 1
        assert "must have an extension" in errors[0]
    
    def test_validate_file_extension_empty_filename(self):
        """Test file extension validation with empty filename."""
        is_valid, errors = self.validator.validate_file_extension("")
        
        assert is_valid is False
        assert len(errors) == 1
        assert "Filename is required" in errors[0]
    
    @patch('app.core.file_validation.magic.Magic')
    def test_validate_mime_type_valid_pdf(self, mock_magic_class):
        """Test MIME type validation for valid PDF."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = 'application/pdf'
        mock_magic_class.return_value = mock_magic
        
        validator = FileValidator()  # Create new instance to use mocked magic
        
        file_content = b"%PDF-1.4 fake pdf content"
        is_valid, errors, detected_mime = validator.validate_mime_type(file_content)
        
        assert is_valid is True
        assert len(errors) == 0
        assert detected_mime == 'application/pdf'
    
    @patch('app.core.file_validation.magic.Magic')
    def test_validate_mime_type_invalid(self, mock_magic_class):
        """Test MIME type validation for invalid types."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = 'text/plain'
        mock_magic_class.return_value = mock_magic
        
        validator = FileValidator()
        
        file_content = b"Just some text content"
        is_valid, errors, detected_mime = validator.validate_mime_type(file_content)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "not allowed" in errors[0]
        assert detected_mime == 'text/plain'
    
    @patch('app.core.file_validation.magic.Magic')
    def test_validate_mime_type_detection_error(self, mock_magic_class):
        """Test MIME type validation when detection fails."""
        mock_magic = Mock()
        mock_magic.from_buffer.side_effect = Exception("Detection failed")
        mock_magic_class.return_value = mock_magic
        
        validator = FileValidator()
        
        file_content = b"some content"
        is_valid, errors, detected_mime = validator.validate_mime_type(file_content)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "Failed to determine file type" in errors[0]
        assert detected_mime is None
    
    def test_validate_file_signature_pdf(self):
        """Test file signature validation for PDF."""
        # Valid PDF signature
        pdf_content = b"%PDF-1.4\n%some pdf content"
        is_valid, errors = self.validator.validate_file_signature(pdf_content, 'application/pdf')
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_file_signature_invalid_pdf(self):
        """Test file signature validation for invalid PDF."""
        # Content without PDF signature
        fake_content = b"fake pdf content"
        is_valid, errors = self.validator.validate_file_signature(fake_content, 'application/pdf')
        
        assert is_valid is False
        assert len(errors) == 1
        assert "does not match expected format" in errors[0]
    
    def test_validate_file_signature_unsupported_mime(self):
        """Test file signature validation for unsupported MIME type."""
        content = b"some content"
        is_valid, errors = self.validator.validate_file_signature(content, 'unsupported/type')
        
        assert is_valid is False
        assert len(errors) == 1
        assert "No signature validation available" in errors[0]
    
    def test_validate_content_structure_pdf_valid(self):
        """Test PDF content structure validation."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        is_valid, errors, warnings = self.validator.validate_content_structure(
            pdf_content, 'application/pdf'
        )
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_content_structure_pdf_truncated(self):
        """Test PDF content structure validation with truncated file."""
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj"  # Missing %%EOF
        is_valid, errors, warnings = self.validator.validate_content_structure(
            pdf_content, 'application/pdf'
        )
        
        assert is_valid is True  # Should still be valid
        assert len(warnings) > 0
        assert "may be truncated" in warnings[0]
    
    def test_validate_content_structure_pdf_corrupted(self):
        """Test PDF content structure validation with corrupted file."""
        pdf_content = b"not a real pdf file"
        is_valid, errors, warnings = self.validator.validate_content_structure(
            pdf_content, 'application/pdf'
        )
        
        assert is_valid is False
        assert len(errors) == 1
        assert "appears to be corrupted" in errors[0]
    
    def test_validate_content_structure_doc_valid(self):
        """Test DOC content structure validation."""
        # DOC files need to be at least 512 bytes for OLE compound document
        doc_content = b"x" * 600  # 600 bytes
        is_valid, errors, warnings = self.validator.validate_content_structure(
            doc_content, 'application/msword'
        )
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_content_structure_doc_too_small(self):
        """Test DOC content structure validation with too small file."""
        doc_content = b"x" * 100  # Too small for valid DOC
        is_valid, errors, warnings = self.validator.validate_content_structure(
            doc_content, 'application/msword'
        )
        
        assert is_valid is False
        assert len(errors) == 1
        assert "too small to be valid" in errors[0]
    
    def test_validate_content_structure_docx_valid(self):
        """Test DOCX content structure validation."""
        # DOCX is a ZIP file with word/ directory and document.xml
        docx_content = b"PK\x03\x04fake zip with word/document.xml content"
        is_valid, errors, warnings = self.validator.validate_content_structure(
            docx_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_content_structure_docx_missing_structure(self):
        """Test DOCX content structure validation without required structure."""
        docx_content = b"PK\x03\x04fake zip without word structure"
        is_valid, errors, warnings = self.validator.validate_content_structure(
            docx_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
        assert is_valid is False
        assert len(errors) == 1
        assert "missing required Word document structure" in errors[0]
    
    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        content = b"test content for hashing"
        hash_value = self.validator.calculate_file_hash(content)
        
        # Should return a valid SHA256 hash (64 hex characters)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)
        
        # Same content should produce same hash
        hash_value2 = self.validator.calculate_file_hash(content)
        assert hash_value == hash_value2
        
        # Different content should produce different hash
        different_content = b"different test content"
        different_hash = self.validator.calculate_file_hash(different_content)
        assert hash_value != different_hash
    
    def test_sanitize_filename_normal(self):
        """Test filename sanitization with normal filenames."""
        test_cases = [
            ("resume.pdf", "resume.pdf"),
            ("My Resume.doc", "My Resume.doc"),
            ("test-file_v2.docx", "test-file_v2.docx")
        ]
        
        for input_name, expected in test_cases:
            result = self.validator.sanitize_filename(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"
    
    def test_sanitize_filename_dangerous_characters(self):
        """Test filename sanitization with dangerous characters."""
        test_cases = [
            ("../../../etc/passwd", "passwd"),  # os.path.basename strips path
            ("resume<script>.pdf", "resume_script_.pdf"),
            ("file|with|pipes.doc", "file_with_pipes.doc"),
            ("test:file.docx", "test_file.docx"),
            ("file\"with\"quotes.pdf", "file_with_quotes.pdf")
        ]
        
        for input_name, expected in test_cases:
            result = self.validator.sanitize_filename(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"
    
    def test_sanitize_filename_path_traversal(self):
        """Test filename sanitization prevents path traversal."""
        dangerous_names = [
            "/etc/passwd",
            "\\windows\\system32\\config",
            "../../../sensitive.txt",
            "..\\..\\..\\secret.doc"
        ]
        
        for dangerous_name in dangerous_names:
            result = self.validator.sanitize_filename(dangerous_name)
            # Should not contain path separators or traversal sequences
            assert "/" not in result, f"Path separator found in sanitized name: {result}"
            assert "\\" not in result, f"Path separator found in sanitized name: {result}"
            assert ".." not in result, f"Path traversal found in sanitized name: {result}"
    
    def test_sanitize_filename_long_filename(self):
        """Test filename sanitization with very long filenames."""
        # Create filename longer than 255 characters
        long_name = "a" * 300 + ".pdf"
        result = self.validator.sanitize_filename(long_name)
        
        # Should be truncated to 255 characters or less
        assert len(result) <= 255
        # Should still have .pdf extension
        assert result.endswith(".pdf")
    
    @patch('app.core.file_validation.magic.Magic')
    def test_validate_file_complete_success(self, mock_magic_class):
        """Test complete file validation with valid file."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = 'application/pdf'
        mock_magic_class.return_value = mock_magic
        
        validator = FileValidator()
        
        # Valid PDF content
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        filename = "test-resume.pdf"
        
        result = validator.validate_file(pdf_content, filename)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.file_info['mime_type'] == 'application/pdf'
        assert result.file_info['file_size'] == len(pdf_content)
        assert 'file_hash' in result.file_info
        assert 'sanitized_filename' in result.file_info
    
    @patch('app.core.file_validation.magic.Magic')
    def test_validate_file_complete_failure(self, mock_magic_class):
        """Test complete file validation with invalid file."""
        mock_magic = Mock()
        mock_magic.from_buffer.return_value = 'text/plain'
        mock_magic_class.return_value = mock_magic
        
        validator = FileValidator()
        
        # Invalid content with wrong MIME type
        content = b"This is just text, not a document"
        filename = "test.txt"  # Invalid extension
        
        result = validator.validate_file(content, filename)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        # Should fail on extension validation
        assert any("not allowed" in error for error in result.errors)
    
    def test_validate_file_size_limit_edge_cases(self):
        """Test file size validation at exact limits."""
        # Exactly at the limit
        max_size = MAX_FILE_SIZE
        is_valid, errors = self.validator.validate_file_size(max_size)
        assert is_valid is True
        assert len(errors) == 0
        
        # Just over the limit  
        over_size = MAX_FILE_SIZE + 1
        is_valid, errors = self.validator.validate_file_size(over_size)
        assert is_valid is False
        assert len(errors) == 1


class TestValidateUploadedFileFunction:
    """Test the convenience function validate_uploaded_file."""
    
    @patch('app.core.file_validation.file_validator')
    def test_validate_uploaded_file_calls_validator(self, mock_validator):
        """Test that validate_uploaded_file calls the global validator."""
        mock_result = FileValidationResult(is_valid=True, errors=[], warnings=[], file_info={})
        mock_validator.validate_file.return_value = mock_result
        
        content = b"test content"
        filename = "test.pdf"
        
        result = validate_uploaded_file(content, filename)
        
        mock_validator.validate_file.assert_called_once_with(content, filename)
        assert result == mock_result


class TestFileValidationConstants:
    """Test file validation constants."""
    
    def test_max_file_size_constant(self):
        """Test that MAX_FILE_SIZE is correct."""
        expected_size = 30 * 1024 * 1024  # 30MB in bytes
        assert MAX_FILE_SIZE == expected_size
    
    def test_allowed_mime_types(self):
        """Test that allowed MIME types are correct."""
        expected_types = {
            'application/pdf',
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        assert ALLOWED_MIME_TYPES == expected_types
    
    def test_allowed_extensions(self):
        """Test that allowed extensions are correct."""
        expected_extensions = {'.pdf', '.doc', '.docx'}
        assert ALLOWED_EXTENSIONS == expected_extensions


class TestFileValidationError:
    """Test FileValidationError exception."""
    
    def test_file_validation_error_creation(self):
        """Test FileValidationError can be created and raised."""
        message = "Test validation error"
        
        with pytest.raises(FileValidationError) as exc_info:
            raise FileValidationError(message)
        
        assert str(exc_info.value) == message
        assert isinstance(exc_info.value, Exception)