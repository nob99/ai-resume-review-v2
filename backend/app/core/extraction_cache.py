"""
Extraction Cache System for UPLOAD-003

Implements intelligent caching for text extraction results to improve performance.
Uses Redis-based caching with file hash-based keys for deduplication.
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path

import redis
from app.core.datetime_utils import utc_now
from app.services.text_extraction_service import ExtractionResult, ExtractionStatus


@dataclass
class CacheEntry:
    """Cache entry for extraction results."""
    file_hash: str
    file_size: int
    mime_type: str
    extraction_result: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    
    def __post_init__(self):
        """Initialize cache entry."""
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        if isinstance(self.last_accessed, str):
            self.last_accessed = datetime.fromisoformat(self.last_accessed.replace('Z', '+00:00'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "extraction_result": self.extraction_result,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Create cache entry from dictionary."""
        return cls(
            file_hash=data["file_hash"],
            file_size=data["file_size"],
            mime_type=data["mime_type"],
            extraction_result=data["extraction_result"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            access_count=data.get("access_count", 0)
        )


class ExtractionCache:
    """
    Redis-based cache for text extraction results.
    
    Features:
    - File hash-based deduplication
    - TTL-based expiration
    - Access tracking and statistics
    - Memory-efficient storage
    - Cache warming and preloading
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl_hours: int = 24 * 7,  # 7 days
        max_cache_size_mb: int = 100,
        key_prefix: str = "extraction_cache"
    ):
        """
        Initialize extraction cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl_hours: Default time-to-live in hours
            max_cache_size_mb: Maximum cache size in MB
            key_prefix: Prefix for cache keys
        """
        self.logger = logging.getLogger(__name__)
        self.default_ttl_hours = default_ttl_hours
        self.max_cache_size_mb = max_cache_size_mb
        self.key_prefix = key_prefix
        
        # Initialize Redis connection
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            self.logger.info(f"Connected to Redis for extraction caching: {redis_url}")
        except (redis.RedisError, ConnectionError) as e:
            self.logger.warning(f"Redis connection failed, using memory fallback: {str(e)}")
            self.redis = None
            # Fallback to in-memory cache
            self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "evictions": 0,
            "errors": 0
        }
    
    def _generate_file_hash(self, file_path: Path) -> str:
        """Generate SHA256 hash of file contents."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating file hash for {file_path}: {str(e)}")
            # Fallback to path + size + mtime hash
            stat = file_path.stat()
            fallback_data = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.sha256(fallback_data.encode()).hexdigest()
    
    def _get_cache_key(self, file_hash: str) -> str:
        """Generate cache key for file hash."""
        return f"{self.key_prefix}:{file_hash}"
    
    def _get_stats_key(self) -> str:
        """Get key for cache statistics."""
        return f"{self.key_prefix}:stats"
    
    async def get(self, file_path: Path, mime_type: str) -> Optional[ExtractionResult]:
        """
        Get cached extraction result for file.
        
        Args:
            file_path: Path to the file
            mime_type: File MIME type
            
        Returns:
            Cached ExtractionResult or None if not found
        """
        try:
            file_hash = self._generate_file_hash(file_path)
            cache_key = self._get_cache_key(file_hash)
            
            # Get from cache (Redis or memory)
            cached_data = None
            if self.redis:
                cached_json = self.redis.get(cache_key)
                if cached_json:
                    cached_data = json.loads(cached_json)
            else:
                cached_entry = self._memory_cache.get(cache_key)
                if cached_entry:
                    cached_data = cached_entry.to_dict()
            
            if not cached_data:
                self._stats["misses"] += 1
                return None
            
            # Verify cache entry is still valid
            cache_entry = CacheEntry.from_dict(cached_data)
            
            # Check if MIME type matches (file might have changed)
            if cache_entry.mime_type != mime_type:
                self.logger.debug(f"Cache miss: MIME type changed for {file_path}")
                await self._invalidate(file_hash)
                self._stats["misses"] += 1
                return None
            
            # Check if file size matches (file might have changed)
            current_size = file_path.stat().st_size
            if cache_entry.file_size != current_size:
                self.logger.debug(f"Cache miss: File size changed for {file_path}")
                await self._invalidate(file_hash)
                self._stats["misses"] += 1
                return None
            
            # Update access statistics
            cache_entry.last_accessed = utc_now()
            cache_entry.access_count += 1
            
            # Update cache with new access stats
            if self.redis:
                self.redis.setex(
                    cache_key,
                    self.default_ttl_hours * 3600,
                    json.dumps(cache_entry.to_dict())
                )
            else:
                self._memory_cache[cache_key] = cache_entry
            
            # Convert back to ExtractionResult
            result_data = cache_entry.extraction_result
            extraction_result = ExtractionResult(
                status=ExtractionStatus(result_data["status"]),
                extracted_text=result_data.get("extracted_text"),
                metadata=result_data.get("metadata", {}),
                error_message=result_data.get("error_message"),
                processing_time_seconds=result_data.get("processing_time_seconds")
            )
            
            self._stats["hits"] += 1
            self.logger.debug(f"Cache hit for {file_path} (hash: {file_hash[:8]}...)")
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Error getting cached extraction for {file_path}: {str(e)}")
            self._stats["errors"] += 1
            return None
    
    async def store(
        self, 
        file_path: Path, 
        mime_type: str, 
        extraction_result: ExtractionResult,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """
        Store extraction result in cache.
        
        Args:
            file_path: Path to the processed file
            mime_type: File MIME type
            extraction_result: Extraction result to cache
            ttl_hours: Time-to-live in hours (uses default if None)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Only cache successful extractions
            if not extraction_result.is_success:
                return False
            
            file_hash = self._generate_file_hash(file_path)
            cache_key = self._get_cache_key(file_hash)
            file_size = file_path.stat().st_size
            
            # Create cache entry
            cache_entry = CacheEntry(
                file_hash=file_hash,
                file_size=file_size,
                mime_type=mime_type,
                extraction_result={
                    "status": extraction_result.status.value,
                    "extracted_text": extraction_result.extracted_text,
                    "metadata": extraction_result.metadata,
                    "error_message": extraction_result.error_message,
                    "processing_time_seconds": extraction_result.processing_time_seconds
                },
                created_at=utc_now(),
                last_accessed=utc_now(),
                access_count=0
            )
            
            # Store in cache
            ttl_seconds = (ttl_hours or self.default_ttl_hours) * 3600
            
            if self.redis:
                self.redis.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(cache_entry.to_dict())
                )
            else:
                # Memory cache with simple size management
                if len(self._memory_cache) > 1000:  # Prevent memory bloat
                    # Remove oldest entries
                    oldest_keys = sorted(
                        self._memory_cache.keys(),
                        key=lambda k: self._memory_cache[k].last_accessed
                    )[:100]
                    for old_key in oldest_keys:
                        del self._memory_cache[old_key]
                        self._stats["evictions"] += 1
                
                self._memory_cache[cache_key] = cache_entry
            
            self._stats["stores"] += 1
            self.logger.debug(f"Cached extraction for {file_path} (hash: {file_hash[:8]}...)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing extraction cache for {file_path}: {str(e)}")
            self._stats["errors"] += 1
            return False
    
    async def _invalidate(self, file_hash: str) -> bool:
        """Invalidate cache entry by file hash."""
        try:
            cache_key = self._get_cache_key(file_hash)
            
            if self.redis:
                self.redis.delete(cache_key)
            else:
                self._memory_cache.pop(cache_key, None)
            
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating cache for hash {file_hash}: {str(e)}")
            return False
    
    async def clear_cache(self) -> int:
        """Clear all cache entries."""
        try:
            if self.redis:
                keys = self.redis.keys(f"{self.key_prefix}:*")
                if keys:
                    deleted = self.redis.delete(*keys)
                    self.logger.info(f"Cleared {deleted} cache entries from Redis")
                    return deleted
            else:
                count = len(self._memory_cache)
                self._memory_cache.clear()
                self.logger.info(f"Cleared {count} cache entries from memory")
                return count
            
            return 0
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and metrics."""
        try:
            # Calculate hit rate
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            # Get cache size info
            cache_size = 0
            entry_count = 0
            
            if self.redis:
                try:
                    cache_keys = self.redis.keys(f"{self.key_prefix}:*")
                    entry_count = len([k for k in cache_keys if not k.endswith(":stats")])
                    # Estimate size (Redis doesn't provide easy way to get exact size)
                    cache_size = entry_count * 50 * 1024  # Rough estimate: 50KB per entry
                except Exception:
                    pass
            else:
                entry_count = len(self._memory_cache)
                # Estimate memory usage
                for entry in self._memory_cache.values():
                    if entry.extraction_result.get("extracted_text"):
                        cache_size += len(entry.extraction_result["extracted_text"]) * 2  # Unicode overhead
                    cache_size += 1024  # Overhead for metadata
            
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "stores": self._stats["stores"],
                "evictions": self._stats["evictions"],
                "errors": self._stats["errors"],
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "cache_entries": entry_count,
                "estimated_size_bytes": cache_size,
                "estimated_size_mb": round(cache_size / 1024 / 1024, 2),
                "max_size_mb": self.max_cache_size_mb,
                "default_ttl_hours": self.default_ttl_hours,
                "using_redis": self.redis is not None
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def warm_cache(self, file_paths: List[Path], mime_types: List[str]) -> Dict[str, Any]:
        """
        Pre-warm cache with commonly accessed files.
        
        Args:
            file_paths: List of file paths to pre-process
            mime_types: Corresponding MIME types
            
        Returns:
            Warming results and statistics
        """
        if len(file_paths) != len(mime_types):
            raise ValueError("file_paths and mime_types must have same length")
        
        results = {
            "requested": len(file_paths),
            "already_cached": 0,
            "newly_cached": 0,
            "failed": 0,
            "errors": []
        }
        
        from app.services.text_extraction_service import text_extraction_service
        from app.core.file_validation import get_file_info
        
        for file_path, mime_type in zip(file_paths, mime_types):
            try:
                # Check if already cached
                cached_result = await self.get(file_path, mime_type)
                if cached_result:
                    results["already_cached"] += 1
                    continue
                
                # Extract and cache
                file_info = get_file_info(file_path, file_path.name)
                extraction_result = await text_extraction_service.extract_text_from_file(
                    file_path, file_info, timeout_seconds=60
                )
                
                if extraction_result.is_success:
                    await self.store(file_path, mime_type, extraction_result)
                    results["newly_cached"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{file_path.name}: {extraction_result.error_message}")
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{file_path.name}: {str(e)}")
        
        self.logger.info(f"Cache warming completed: {results}")
        return results


# Global cache instance
extraction_cache = ExtractionCache(
    redis_url="redis://localhost:6379/1",  # Use database 1 for extraction cache
    default_ttl_hours=24 * 7,  # Cache for 1 week
    max_cache_size_mb=100,
    key_prefix="resume_extraction"
)