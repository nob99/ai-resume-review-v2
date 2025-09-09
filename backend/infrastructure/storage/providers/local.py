"""
Local filesystem storage provider for the new infrastructure layer.
Implements file storage on the local filesystem for development and testing.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO, Dict, Any
from io import BytesIO
import logging
from datetime import datetime

from app.infrastructure.storage.interface import (
    StorageProviderBase,
    StoredFile,
    StorageError
)
from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProviderBase):
    """
    Local filesystem storage provider.
    
    Stores files on the local filesystem, useful for:
    - Development environments
    - Testing
    - Single-server deployments
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the local storage provider.
        
        Args:
            base_path: Base directory for file storage,
                      defaults to settings.LOCAL_STORAGE_PATH
        """
        super().__init__()
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self._ensure_base_path()
    
    def _ensure_base_path(self):
        """Ensure the base storage directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Local storage initialized at: {self.base_path}")
    
    def _get_file_path(self, key: str) -> Path:
        """
        Get the full file path for a storage key.
        
        Args:
            key: Storage key
            
        Returns:
            Full path to the file
        """
        # Ensure the key doesn't contain path traversal attempts
        safe_key = os.path.basename(key)
        return self.base_path / safe_key
    
    async def store(
        self,
        file_content: BinaryIO,
        filename: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StoredFile:
        """
        Store a file on the local filesystem.
        
        Args:
            file_content: Binary content of the file
            filename: Name of the file
            content_type: MIME type of the file
            metadata: Optional metadata to associate with the file
            
        Returns:
            StoredFile object with storage details
            
        Raises:
            StorageError: If the file cannot be stored
        """
        try:
            # Generate unique key
            key = self._generate_key(filename)
            file_path = self._get_file_path(key)
            
            # Read content and get size
            content = file_content.read()
            file_size = len(content)
            
            # Write file to disk
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Store metadata if provided
            if metadata:
                metadata_path = file_path.with_suffix('.metadata.json')
                import json
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            logger.info(f"File stored successfully: {key} ({file_size} bytes)")
            
            return StoredFile(
                key=key,
                original_filename=filename,
                content_type=content_type,
                size=file_size,
                storage_path=str(file_path),
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to store file {filename}: {e}")
            raise StorageError(f"Failed to store file: {e}")
    
    async def retrieve(self, key: str) -> BinaryIO:
        """
        Retrieve a file from the local filesystem.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            Binary content of the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            StorageError: If the file cannot be retrieved
        """
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {key}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            return BytesIO(content)
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve file {key}: {e}")
            raise StorageError(f"Failed to retrieve file: {e}")
    
    async def delete(self, key: str) -> bool:
        """
        Delete a file from the local filesystem.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            True if the file was deleted, False if it didn't exist
            
        Raises:
            StorageError: If the deletion fails
        """
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return False
            
            # Delete the file
            file_path.unlink()
            
            # Delete metadata if it exists
            metadata_path = file_path.with_suffix('.metadata.json')
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"File deleted: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file {key}: {e}")
            raise StorageError(f"Failed to delete file: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists on the local filesystem.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            True if the file exists, False otherwise
        """
        try:
            file_path = self._get_file_path(key)
            return file_path.exists()
        except Exception as e:
            logger.error(f"Failed to check file existence {key}: {e}")
            return False
    
    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a stored file.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            File metadata if the file exists, None otherwise
            
        Raises:
            StorageError: If metadata cannot be retrieved
        """
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            # Check for metadata file
            metadata_path = file_path.with_suffix('.metadata.json')
            if metadata_path.exists():
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Add file system metadata
            stat = file_path.stat()
            metadata.update({
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(file_path)
            })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {key}: {e}")
            raise StorageError(f"Failed to get metadata: {e}")
    
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get a URL for accessing the file.
        
        For local storage, returns a file:// URL.
        In production, this should return an API endpoint URL.
        
        Args:
            key: Unique identifier of the file
            expires_in: URL expiration time (ignored for local storage)
            
        Returns:
            URL for accessing the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            StorageError: If URL cannot be generated
        """
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {key}")
            
            # For local development, return a file URL
            # In production, this should be an API endpoint
            if settings.DEBUG:
                return f"file://{file_path.absolute()}"
            else:
                # Return API endpoint URL
                return f"{settings.API_URL}/api/storage/{key}"
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate URL for {key}: {e}")
            raise StorageError(f"Failed to generate URL: {e}")
    
    async def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up old files from storage.
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.utcnow().timestamp() - (days * 86400)
            
            for file_path in self.base_path.iterdir():
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0