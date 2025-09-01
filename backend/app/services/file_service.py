"""
File storage service for secure handling of uploaded resume files.
Implements UUID-based naming, secure directory structure, and cleanup mechanisms.
"""

import os
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import logging
import tempfile

from app.core.config import get_settings
from app.core.file_validation import FileValidationResult, validate_uploaded_file
from app.core.datetime_utils import utc_now

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class FileStorageResult:
    """Result of file storage operation."""
    success: bool
    file_path: Optional[str] = None
    file_id: Optional[str] = None
    error_message: Optional[str] = None
    validation_result: Optional[FileValidationResult] = None


@dataclass
class StoredFileInfo:
    """Information about a stored file."""
    file_id: str
    original_filename: str
    stored_path: str
    file_size: int
    mime_type: str
    file_hash: str
    created_at: datetime


class FileStorageService:
    """
    Secure file storage service for resume uploads.
    
    Features:
    - UUID-based file naming for security
    - Organized directory structure by date
    - Automatic cleanup of temporary files
    - File validation integration
    - Secure file permissions
    """
    
    def __init__(self, storage_root: Optional[str] = None):
        """
        Initialize file storage service.
        
        Args:
            storage_root: Root directory for file storage (optional, uses config default)
        """
        settings = get_settings()
        self.storage_root = Path(storage_root or settings.file_storage_path or "storage/uploads")
        
        # Ensure storage directory exists with proper permissions
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self) -> None:
        """Ensure storage directory exists with proper permissions."""
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
            
            # Set secure permissions (owner read/write only)
            os.chmod(self.storage_root, 0o700)
            
            logger.info(f"File storage initialized at: {self.storage_root}")
            
        except Exception as e:
            logger.error(f"Failed to create storage directory: {str(e)}")
            raise RuntimeError(f"Cannot initialize file storage: {str(e)}")
    
    def _get_date_path(self, date: Optional[datetime] = None) -> Path:
        """
        Generate date-based directory path for organizing files.
        
        Args:
            date: Date to use for path (defaults to current UTC time)
            
        Returns:
            Path object for date-based directory
        """
        if date is None:
            date = utc_now()
        
        # Create path like: storage/uploads/2024/01/15/
        return self.storage_root / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"
    
    def _generate_secure_filename(self, original_filename: str, file_extension: str) -> str:
        """
        Generate secure filename using UUID.
        
        Args:
            original_filename: Original filename (for logging)
            file_extension: File extension to preserve
            
        Returns:
            Secure UUID-based filename
        """
        # Generate UUID for unique filename
        file_uuid = str(uuid.uuid4())
        
        # Ensure extension starts with dot
        if not file_extension.startswith('.'):
            file_extension = f'.{file_extension}'
        
        return f"{file_uuid}{file_extension}"
    
    def _create_temporary_file(self, file_content: bytes) -> Tuple[str, str]:
        """
        Create temporary file for processing.
        
        Args:
            file_content: File content bytes
            
        Returns:
            Tuple of (temp_file_path, temp_file_id)
        """
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(prefix="resume_upload_", suffix=".tmp")
        
        try:
            # Write content to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(file_content)
            
            # Set secure permissions on temporary file
            os.chmod(temp_path, 0o600)
            
            return temp_path, os.path.basename(temp_path)
            
        except Exception:
            # Clean up on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise
    
    def store_file(
        self, 
        file_content: bytes, 
        original_filename: str,
        user_id: Optional[str] = None
    ) -> FileStorageResult:
        """
        Store uploaded file with validation and security checks.
        
        Args:
            file_content: File content bytes
            original_filename: Original filename from upload
            user_id: Optional user ID for logging and organization
            
        Returns:
            FileStorageResult with operation status and details
        """
        temp_path = None
        
        try:
            # 1. Validate file
            logger.info(f"Validating file upload: {original_filename} ({len(file_content)} bytes)")
            
            validation_result = validate_uploaded_file(file_content, original_filename)
            
            if not validation_result.is_valid:
                logger.warning(f"File validation failed for {original_filename}: {validation_result.errors}")
                return FileStorageResult(
                    success=False,
                    error_message=f"File validation failed: {'; '.join(validation_result.errors)}",
                    validation_result=validation_result
                )
            
            # 2. Create temporary file for processing
            temp_path, temp_id = self._create_temporary_file(file_content)
            
            # 3. Generate secure storage path
            current_time = utc_now()
            date_path = self._get_date_path(current_time)
            
            # Ensure date directory exists
            date_path.mkdir(parents=True, exist_ok=True)
            os.chmod(date_path, 0o700)
            
            # Generate secure filename
            file_extension = validation_result.file_info.get('file_extension', '')
            secure_filename = self._generate_secure_filename(original_filename, file_extension)
            final_path = date_path / secure_filename
            
            # 4. Move file to final location
            shutil.move(temp_path, final_path)
            temp_path = None  # Mark as moved
            
            # Set secure permissions on final file
            os.chmod(final_path, 0o600)
            
            # 5. Generate file ID and relative path for database storage
            file_id = str(uuid.uuid4())
            relative_path = str(final_path.relative_to(self.storage_root))
            
            logger.info(
                f"File stored successfully: {original_filename} -> {secure_filename} "
                f"(user: {user_id or 'anonymous'})"
            )
            
            return FileStorageResult(
                success=True,
                file_path=relative_path,
                file_id=file_id,
                validation_result=validation_result
            )
            
        except Exception as e:
            logger.error(f"File storage failed for {original_filename}: {str(e)}")
            
            # Clean up temporary file on error
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            return FileStorageResult(
                success=False,
                error_message=f"File storage failed: {str(e)}"
            )
    
    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Get full file path from relative path.
        
        Args:
            relative_path: Relative path from database
            
        Returns:
            Full Path object or None if file doesn't exist
        """
        try:
            full_path = self.storage_root / relative_path
            
            # Security check: ensure path is within storage root
            full_path.resolve().relative_to(self.storage_root.resolve())
            
            if full_path.exists() and full_path.is_file():
                return full_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving file path {relative_path}: {str(e)}")
            return None
    
    def read_file(self, relative_path: str) -> Optional[bytes]:
        """
        Read file content from storage.
        
        Args:
            relative_path: Relative path from database
            
        Returns:
            File content bytes or None if file doesn't exist
        """
        try:
            file_path = self.get_file_path(relative_path)
            
            if not file_path:
                logger.warning(f"File not found: {relative_path}")
                return None
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.debug(f"File read successfully: {relative_path} ({len(content)} bytes)")
            return content
            
        except Exception as e:
            logger.error(f"Error reading file {relative_path}: {str(e)}")
            return None
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            relative_path: Relative path from database
            
        Returns:
            True if file was deleted successfully
        """
        try:
            file_path = self.get_file_path(relative_path)
            
            if not file_path:
                logger.warning(f"File not found for deletion: {relative_path}")
                return False
            
            file_path.unlink()
            
            # Try to remove empty parent directories
            try:
                parent = file_path.parent
                while parent != self.storage_root:
                    if not any(parent.iterdir()):  # Directory is empty
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
            except:
                pass  # Ignore errors when cleaning up directories
            
            logger.info(f"File deleted successfully: {relative_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {relative_path}: {str(e)}")
            return False
    
    def get_file_info(self, relative_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information without reading content.
        
        Args:
            relative_path: Relative path from database
            
        Returns:
            Dictionary with file information or None
        """
        try:
            file_path = self.get_file_path(relative_path)
            
            if not file_path:
                return None
            
            stat = file_path.stat()
            
            return {
                'file_path': str(file_path),
                'relative_path': relative_path,
                'file_size': stat.st_size,
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'permissions': oct(stat.st_mode)[-3:]
            }
            
        except Exception as e:
            logger.error(f"Error getting file info {relative_path}: {str(e)}")
            return None
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Clean up files older than specified days.
        
        Args:
            days_old: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            cutoff_date = utc_now() - timedelta(days=days_old)
            deleted_count = 0
            
            # Walk through storage directory
            for file_path in self.storage_root.rglob("*"):
                if file_path.is_file():
                    try:
                        # Check file modification time
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Deleted old file: {file_path}")
                    
                    except Exception as e:
                        logger.warning(f"Error processing file {file_path} during cleanup: {str(e)}")
            
            logger.info(f"Cleanup completed: {deleted_count} files deleted (older than {days_old} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")
            return 0


# Global file storage service instance
file_storage_service = FileStorageService()


def store_uploaded_file(
    file_content: bytes, 
    original_filename: str, 
    user_id: Optional[str] = None
) -> FileStorageResult:
    """
    Convenience function for storing uploaded files.
    
    Args:
        file_content: File content bytes
        original_filename: Original filename
        user_id: Optional user ID
        
    Returns:
        FileStorageResult
    """
    return file_storage_service.store_file(file_content, original_filename, user_id)