"""
File validation utilities for secure file upload handling.
Implements comprehensive validation for resume files with security checks.
"""

import os
import magic
import hashlib
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel, Field
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Maximum file size (30MB in bytes)
MAX_FILE_SIZE = 30 * 1024 * 1024

# Allowed MIME types for resume files
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# File signatures (magic numbers) for validation
FILE_SIGNATURES = {
    'application/pdf': [
        b'%PDF-'
    ],
    'application/msword': [
        b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # MS Office compound document
        b'\x0d\x44\x4f\x43'  # DOC signature
    ],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
        b'PK\x03\x04',  # ZIP signature (DOCX is a ZIP file)
        b'PK\x05\x06',  # ZIP empty archive
        b'PK\x07\x08'   # ZIP spanned archive
    ]
}


class FileValidationResult(BaseModel):
    """File validation result with detailed information."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    file_info: Dict[str, Any] = Field(default_factory=dict)


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


@dataclass
class FileMetadata:
    """File metadata container."""
    original_filename: str
    file_size: int
    mime_type: str
    file_extension: str
    file_hash: str


class FileValidator:
    """
    Comprehensive file validator for resume uploads.
    
    Implements security-first validation with multiple layers:
    1. File size validation
    2. MIME type validation
    3. File extension validation
    4. Magic number (file signature) validation
    5. Content structure validation
    """
    
    def __init__(self):
        """Initialize file validator."""
        self.magic_detector = magic.Magic(mime=True)
    
    def validate_file_size(self, file_size: int) -> Tuple[bool, List[str]]:
        """
        Validate file size constraints.
        
        Args:
            file_size: Size of file in bytes
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if file_size <= 0:
            errors.append("File is empty")
            return False, errors
        
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            errors.append(f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_mb}MB)")
            return False, errors
        
        return True, errors
    
    def validate_file_extension(self, filename: str) -> Tuple[bool, List[str]]:
        """
        Validate file extension.
        
        Args:
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if not filename:
            errors.append("Filename is required")
            return False, errors
        
        file_ext = Path(filename).suffix.lower()
        
        if not file_ext:
            errors.append("File must have an extension")
            return False, errors
        
        if file_ext not in ALLOWED_EXTENSIONS:
            allowed_list = ', '.join(ALLOWED_EXTENSIONS)
            errors.append(f"File extension '{file_ext}' not allowed. Allowed: {allowed_list}")
            return False, errors
        
        return True, errors
    
    def validate_mime_type(self, file_content: bytes) -> Tuple[bool, List[str], Optional[str]]:
        """
        Validate MIME type using file content analysis.
        
        Args:
            file_content: File content bytes
            
        Returns:
            Tuple of (is_valid, error_messages, detected_mime_type)
        """
        errors = []
        
        try:
            # Detect MIME type from content
            detected_mime = self.magic_detector.from_buffer(file_content)
            
            if detected_mime not in ALLOWED_MIME_TYPES:
                allowed_list = ', '.join(ALLOWED_MIME_TYPES)
                errors.append(f"File type '{detected_mime}' not allowed. Allowed: {allowed_list}")
                return False, errors, detected_mime
            
            return True, errors, detected_mime
            
        except Exception as e:
            logger.error(f"MIME type detection failed: {str(e)}")
            errors.append("Failed to determine file type")
            return False, errors, None
    
    def validate_file_signature(self, file_content: bytes, expected_mime: str) -> Tuple[bool, List[str]]:
        """
        Validate file signature (magic numbers) against expected MIME type.
        
        Args:
            file_content: File content bytes
            expected_mime: Expected MIME type
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if expected_mime not in FILE_SIGNATURES:
            errors.append(f"No signature validation available for MIME type: {expected_mime}")
            return False, errors
        
        # Check file signatures
        expected_signatures = FILE_SIGNATURES[expected_mime]
        signature_match = False
        
        for signature in expected_signatures:
            if file_content.startswith(signature):
                signature_match = True
                break
        
        if not signature_match:
            errors.append("File signature does not match expected format")
            return False, errors
        
        return True, errors
    
    def validate_content_structure(self, file_content: bytes, mime_type: str) -> Tuple[bool, List[str], List[str]]:
        """
        Validate file content structure for basic integrity.
        
        Args:
            file_content: File content bytes
            mime_type: Detected MIME type
            
        Returns:
            Tuple of (is_valid, error_messages, warning_messages)
        """
        errors = []
        warnings = []
        
        try:
            if mime_type == 'application/pdf':
                # Basic PDF structure validation
                if b'%%EOF' not in file_content:
                    warnings.append("PDF file may be truncated or corrupted")
                
                # Check for minimal PDF structure
                if b'/Root' not in file_content and b'/Catalog' not in file_content:
                    errors.append("PDF file appears to be corrupted or invalid")
                    return False, errors, warnings
            
            elif mime_type == 'application/msword':
                # Basic DOC validation - check for OLE compound document structure
                if len(file_content) < 512:
                    errors.append("DOC file too small to be valid")
                    return False, errors, warnings
            
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                # Basic DOCX validation - ensure it's a valid ZIP with required entries
                if b'word/' not in file_content:
                    errors.append("DOCX file missing required Word document structure")
                    return False, errors, warnings
                
                if b'document.xml' not in file_content:
                    warnings.append("DOCX file may be missing main document content")
            
            return True, errors, warnings
            
        except Exception as e:
            logger.error(f"Content structure validation failed: {str(e)}")
            errors.append("Failed to validate file content structure")
            return False, errors, warnings
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """
        Calculate SHA256 hash of file content.
        
        Args:
            file_content: File content bytes
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        return hashlib.sha256(file_content).hexdigest()
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove directory path components
        filename = os.path.basename(filename)
        
        # Replace potentially dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit filename length
        if len(filename) > 255:
            name_part, ext = os.path.splitext(filename)
            max_name_len = 255 - len(ext)
            filename = name_part[:max_name_len] + ext
        
        return filename
    
    def validate_file(self, file_content: bytes, original_filename: str) -> FileValidationResult:
        """
        Perform comprehensive file validation.
        
        Args:
            file_content: File content bytes
            original_filename: Original filename
            
        Returns:
            FileValidationResult with validation results
        """
        try:
            all_errors = []
            all_warnings = []
            file_info = {}
            
            # 1. Validate file size
            file_size = len(file_content)
            size_valid, size_errors = self.validate_file_size(file_size)
            all_errors.extend(size_errors)
            file_info['file_size'] = file_size
            
            if not size_valid:
                return FileValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    warnings=all_warnings,
                    file_info=file_info
                )
            
            # 2. Validate file extension
            ext_valid, ext_errors = self.validate_file_extension(original_filename)
            all_errors.extend(ext_errors)
            
            if not ext_valid:
                return FileValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    warnings=all_warnings,
                    file_info=file_info
                )
            
            # 3. Validate MIME type
            mime_valid, mime_errors, detected_mime = self.validate_mime_type(file_content)
            all_errors.extend(mime_errors)
            
            if not mime_valid or not detected_mime:
                return FileValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    warnings=all_warnings,
                    file_info=file_info
                )
            
            file_info['mime_type'] = detected_mime
            
            # 4. Validate file signature
            sig_valid, sig_errors = self.validate_file_signature(file_content, detected_mime)
            all_errors.extend(sig_errors)
            
            if not sig_valid:
                return FileValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    warnings=all_warnings,
                    file_info=file_info
                )
            
            # 5. Validate content structure
            struct_valid, struct_errors, struct_warnings = self.validate_content_structure(
                file_content, detected_mime
            )
            all_errors.extend(struct_errors)
            all_warnings.extend(struct_warnings)
            
            if not struct_valid:
                return FileValidationResult(
                    is_valid=False,
                    errors=all_errors,
                    warnings=all_warnings,
                    file_info=file_info
                )
            
            # 6. Generate file metadata
            file_hash = self.calculate_file_hash(file_content)
            sanitized_filename = self.sanitize_filename(original_filename)
            
            file_info.update({
                'original_filename': original_filename,
                'sanitized_filename': sanitized_filename,
                'file_extension': Path(original_filename).suffix.lower(),
                'file_hash': file_hash
            })
            
            return FileValidationResult(
                is_valid=True,
                errors=all_errors,
                warnings=all_warnings,
                file_info=file_info
            )
            
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return FileValidationResult(
                is_valid=False,
                errors=[f"Validation failed: {str(e)}"],
                warnings=[],
                file_info={}
            )


# Global validator instance
file_validator = FileValidator()


def validate_uploaded_file(file_content: bytes, filename: str) -> FileValidationResult:
    """
    Convenience function for file validation.
    
    Args:
        file_content: File content bytes
        filename: Original filename
        
    Returns:
        FileValidationResult
    """
    return file_validator.validate_file(file_content, filename)