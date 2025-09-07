"""
Storage interface for the new infrastructure layer.
Defines the contract that all storage providers must implement.
"""

from typing import Protocol, Optional, BinaryIO, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class StoredFile:
    """
    Represents a file stored in the storage system.
    
    Attributes:
        key: Unique identifier for the file in storage
        original_filename: Original name of the uploaded file
        content_type: MIME type of the file
        size: File size in bytes
        storage_path: Path or URL where the file is stored
        metadata: Optional metadata associated with the file
        created_at: Timestamp when the file was stored
    """
    key: str
    original_filename: str
    content_type: str
    size: int
    storage_path: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class StorageProvider(Protocol):
    """
    Protocol defining the interface for storage providers.
    
    All storage providers (local, GCS, S3, etc.) must implement this interface.
    This ensures consistent behavior across different storage backends.
    """
    
    async def store(
        self,
        file_content: BinaryIO,
        filename: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StoredFile:
        """
        Store a file in the storage system.
        
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
        ...
    
    async def retrieve(self, key: str) -> BinaryIO:
        """
        Retrieve a file from the storage system.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            Binary content of the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            StorageError: If the file cannot be retrieved
        """
        ...
    
    async def delete(self, key: str) -> bool:
        """
        Delete a file from the storage system.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            True if the file was deleted, False if it didn't exist
            
        Raises:
            StorageError: If the deletion fails
        """
        ...
    
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists in the storage system.
        
        Args:
            key: Unique identifier of the file
            
        Returns:
            True if the file exists, False otherwise
        """
        ...
    
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
        ...
    
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Get a URL for accessing the file.
        
        For cloud storage, this might be a signed URL.
        For local storage, this might be a file:// URL or API endpoint.
        
        Args:
            key: Unique identifier of the file
            expires_in: URL expiration time in seconds (for signed URLs)
            
        Returns:
            URL for accessing the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            StorageError: If URL cannot be generated
        """
        ...


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class StorageProviderBase(ABC):
    """
    Abstract base class for storage providers.
    
    Provides common functionality and ensures all providers
    implement the required methods.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the storage provider.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config or {}
    
    @abstractmethod
    async def store(
        self,
        file_content: BinaryIO,
        filename: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> StoredFile:
        """Store a file in the storage system."""
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> BinaryIO:
        """Retrieve a file from the storage system."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a file from the storage system."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists in the storage system."""
        pass
    
    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a stored file."""
        pass
    
    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a URL for accessing the file."""
        pass
    
    def _generate_key(self, filename: str) -> str:
        """
        Generate a unique storage key for a file.
        
        Args:
            filename: Original filename
            
        Returns:
            Unique storage key
        """
        from uuid import uuid4
        from pathlib import Path
        
        # Get file extension
        path = Path(filename)
        extension = path.suffix
        
        # Generate unique key with timestamp and UUID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        
        return f"{timestamp}_{unique_id}{extension}"