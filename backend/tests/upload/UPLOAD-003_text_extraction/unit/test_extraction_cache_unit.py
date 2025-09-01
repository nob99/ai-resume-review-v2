"""
Unit tests for ExtractionCache (UPLOAD-003)

Tests caching system functionality including:
- Redis and memory-based caching
- File hash-based deduplication
- TTL management and cache statistics
- Cache warming and performance optimization
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import json
import hashlib
from datetime import datetime, timedelta

from app.core.extraction_cache import (
    ExtractionCache,
    CacheEntry,
    extraction_cache
)
from app.services.text_extraction_service import ExtractionResult, ExtractionStatus


class TestCacheEntry:
    """Test CacheEntry data class functionality."""
    
    def test_cache_entry_creation(self):
        """Test creating CacheEntry instance."""
        now = datetime.now()
        entry = CacheEntry(
            file_hash="abc123",
            file_size=1000,
            mime_type="application/pdf",
            extraction_result={"status": "completed", "text": "content"},
            created_at=now,
            last_accessed=now,
            access_count=5
        )
        
        assert entry.file_hash == "abc123"
        assert entry.file_size == 1000
        assert entry.mime_type == "application/pdf"
        assert entry.access_count == 5
        assert entry.created_at == now
        assert entry.last_accessed == now
    
    def test_cache_entry_to_dict(self):
        """Test converting CacheEntry to dictionary."""
        now = datetime.now()
        entry = CacheEntry(
            file_hash="abc123",
            file_size=1000,
            mime_type="application/pdf",
            extraction_result={"status": "completed"},
            created_at=now,
            last_accessed=now,
            access_count=3
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["file_hash"] == "abc123"
        assert entry_dict["file_size"] == 1000
        assert entry_dict["mime_type"] == "application/pdf"
        assert entry_dict["access_count"] == 3
        assert entry_dict["created_at"] == now.isoformat()
        assert entry_dict["last_accessed"] == now.isoformat()
    
    def test_cache_entry_from_dict(self):
        """Test creating CacheEntry from dictionary."""
        now = datetime.now()
        entry_dict = {
            "file_hash": "def456",
            "file_size": 2000,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "extraction_result": {"status": "completed", "text": "docx content"},
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
            "access_count": 1
        }
        
        entry = CacheEntry.from_dict(entry_dict)
        
        assert entry.file_hash == "def456"
        assert entry.file_size == 2000
        assert entry.access_count == 1
        assert isinstance(entry.created_at, (str, datetime))
        assert isinstance(entry.last_accessed, (str, datetime))


class TestExtractionCache:
    """Test ExtractionCache functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis connection."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.keys.return_value = []
        return mock_redis
    
    @pytest.fixture
    def cache_with_redis(self, mock_redis):
        """Create cache instance with mocked Redis."""
        with patch('redis.from_url', return_value=mock_redis):
            return ExtractionCache(
                redis_url="redis://localhost:6379/1",
                default_ttl_hours=24,
                max_cache_size_mb=50
            )
    
    @pytest.fixture
    def cache_memory_only(self):
        """Create cache instance with memory fallback."""
        with patch('redis.from_url', side_effect=ConnectionError("Redis not available")):
            return ExtractionCache()
    
    def test_cache_initialization_with_redis(self, mock_redis):
        """Test cache initialization with Redis connection."""
        with patch('redis.from_url', return_value=mock_redis):
            cache = ExtractionCache()
            
            assert cache.redis is not None
            assert cache.default_ttl_hours == 24 * 7  # Default 7 days
            assert cache.max_cache_size_mb == 100
    
    def test_cache_initialization_redis_failure(self):
        """Test cache initialization with Redis connection failure."""
        with patch('redis.from_url', side_effect=ConnectionError("Connection failed")):
            cache = ExtractionCache()
            
            assert cache.redis is None
            assert hasattr(cache, '_memory_cache')
            assert isinstance(cache._memory_cache, dict)
    
    def test_generate_file_hash(self, cache_with_redis):
        """Test file hash generation."""
        test_content = b"Test file content for hashing"
        
        with patch('builtins.open', mock_open(read_data=test_content)):
            file_hash = cache_with_redis._generate_file_hash(Path("/tmp/test.pdf"))
            
            expected_hash = hashlib.sha256(test_content).hexdigest()
            assert file_hash == expected_hash
    
    def test_generate_file_hash_fallback(self, cache_with_redis):
        """Test file hash generation fallback when file can't be read."""
        test_file = Path("/tmp/test.pdf")
        
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value = Mock(st_size=1000, st_mtime=1234567890)
                
                file_hash = cache_with_redis._generate_file_hash(test_file)
                
                # Should return a hash based on path + size + mtime
                assert len(file_hash) == 64  # SHA256 hex length
                assert file_hash != ""
    
    def test_get_cache_key(self, cache_with_redis):
        """Test cache key generation."""
        file_hash = "abc123def456"
        cache_key = cache_with_redis._get_cache_key(file_hash)
        
        assert cache_key == f"{cache_with_redis.key_prefix}:{file_hash}"
    
    @pytest.mark.asyncio
    async def test_get_cache_miss_redis(self, cache_with_redis):
        """Test cache miss with Redis backend."""
        test_file = Path("/tmp/nonexistent.pdf")
        
        with patch.object(cache_with_redis, '_generate_file_hash', return_value="abc123"):
            result = await cache_with_redis.get(test_file, "application/pdf")
            
            assert result is None
            assert cache_with_redis._stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_get_cache_hit_redis(self, cache_with_redis):
        """Test cache hit with Redis backend."""
        test_file = Path("/tmp/test.pdf")
        file_hash = "abc123"
        
        # Mock file stats
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1000)
            
            # Mock Redis response
            cache_entry = CacheEntry(
                file_hash=file_hash,
                file_size=1000,
                mime_type="application/pdf",
                extraction_result={
                    "status": "completed",
                    "extracted_text": "Test content",
                    "processing_time_seconds": 1.5
                },
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0
            )
            
            cache_with_redis.redis.get.return_value = json.dumps(cache_entry.to_dict())
            
            with patch.object(cache_with_redis, '_generate_file_hash', return_value=file_hash):
                result = await cache_with_redis.get(test_file, "application/pdf")
                
                assert result is not None
                assert isinstance(result, ExtractionResult)
                assert result.status == ExtractionStatus.COMPLETED
                assert result.extracted_text == "Test content"
                assert cache_with_redis._stats["hits"] == 1
    
    @pytest.mark.asyncio
    async def test_get_cache_hit_mime_type_mismatch(self, cache_with_redis):
        """Test cache miss due to MIME type mismatch."""
        test_file = Path("/tmp/test.pdf")
        file_hash = "abc123"
        
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1000)
            
            # Cache entry with different MIME type
            cache_entry = CacheEntry(
                file_hash=file_hash,
                file_size=1000,
                mime_type="application/msword",  # Different MIME type
                extraction_result={"status": "completed"},
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0
            )
            
            cache_with_redis.redis.get.return_value = json.dumps(cache_entry.to_dict())
            
            with patch.object(cache_with_redis, '_generate_file_hash', return_value=file_hash):
                with patch.object(cache_with_redis, '_invalidate') as mock_invalidate:
                    result = await cache_with_redis.get(test_file, "application/pdf")
                    
                    assert result is None
                    assert cache_with_redis._stats["misses"] == 1
                    mock_invalidate.assert_called_once_with(file_hash)
    
    @pytest.mark.asyncio
    async def test_get_cache_hit_size_mismatch(self, cache_with_redis):
        """Test cache miss due to file size mismatch."""
        test_file = Path("/tmp/test.pdf")
        file_hash = "abc123"
        
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=2000)  # Different size
            
            cache_entry = CacheEntry(
                file_hash=file_hash,
                file_size=1000,  # Cached size
                mime_type="application/pdf",
                extraction_result={"status": "completed"},
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0
            )
            
            cache_with_redis.redis.get.return_value = json.dumps(cache_entry.to_dict())
            
            with patch.object(cache_with_redis, '_generate_file_hash', return_value=file_hash):
                with patch.object(cache_with_redis, '_invalidate') as mock_invalidate:
                    result = await cache_with_redis.get(test_file, "application/pdf")
                    
                    assert result is None
                    assert cache_with_redis._stats["misses"] == 1
                    mock_invalidate.assert_called_once_with(file_hash)
    
    @pytest.mark.asyncio
    async def test_store_successful_extraction_redis(self, cache_with_redis):
        """Test storing successful extraction result in Redis."""
        test_file = Path("/tmp/test.pdf")
        
        extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Test resume content",
            processing_time_seconds=2.0,
            metadata={"extraction_method": "pdfplumber"}
        )
        
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1000)
            
            with patch.object(cache_with_redis, '_generate_file_hash', return_value="abc123"):
                success = await cache_with_redis.store(
                    test_file, 
                    "application/pdf", 
                    extraction_result
                )
                
                assert success is True
                assert cache_with_redis._stats["stores"] == 1
                cache_with_redis.redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_failed_extraction_not_cached(self, cache_with_redis):
        """Test that failed extractions are not cached."""
        test_file = Path("/tmp/test.pdf")
        
        extraction_result = ExtractionResult(
            status=ExtractionStatus.FAILED,
            error_message="Extraction failed"
        )
        
        success = await cache_with_redis.store(test_file, "application/pdf", extraction_result)
        
        assert success is False
        assert cache_with_redis._stats["stores"] == 0
    
    @pytest.mark.asyncio
    async def test_get_memory_cache(self, cache_memory_only):
        """Test cache operations with memory backend."""
        test_file = Path("/tmp/test.pdf")
        file_hash = "memory123"
        
        # First, test cache miss
        with patch.object(cache_memory_only, '_generate_file_hash', return_value=file_hash):
            result = await cache_memory_only.get(test_file, "application/pdf")
            assert result is None
        
        # Store something in memory cache
        extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Memory cached content"
        )
        
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1500)
            
            with patch.object(cache_memory_only, '_generate_file_hash', return_value=file_hash):
                success = await cache_memory_only.store(test_file, "application/pdf", extraction_result)
                assert success is True
        
        # Now test cache hit
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1500)
            
            with patch.object(cache_memory_only, '_generate_file_hash', return_value=file_hash):
                result = await cache_memory_only.get(test_file, "application/pdf")
                
                assert result is not None
                assert result.extracted_text == "Memory cached content"
                assert cache_memory_only._stats["hits"] == 1
    
    @pytest.mark.asyncio
    async def test_memory_cache_size_management(self, cache_memory_only):
        """Test memory cache size management and eviction."""
        # Fill cache beyond limit
        for i in range(1100):  # More than the 1000 limit
            cache_key = f"test_key_{i}"
            cache_entry = CacheEntry(
                file_hash=f"hash_{i}",
                file_size=1000,
                mime_type="application/pdf",
                extraction_result={"status": "completed"},
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            cache_memory_only._memory_cache[cache_key] = cache_entry
        
        # Store one more item to trigger cleanup
        test_file = Path("/tmp/trigger_cleanup.pdf")
        extraction_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Cleanup trigger"
        )
        
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value = Mock(st_size=1000)
            
            with patch.object(cache_memory_only, '_generate_file_hash', return_value="cleanup_hash"):
                await cache_memory_only.store(test_file, "application/pdf", extraction_result)
        
        # Should have triggered eviction
        assert cache_memory_only._stats["evictions"] > 0
        assert len(cache_memory_only._memory_cache) < 1100
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_entry_redis(self, cache_with_redis):
        """Test cache entry invalidation with Redis."""
        file_hash = "invalidate_test"
        
        success = await cache_with_redis._invalidate(file_hash)
        
        assert success is True
        cache_with_redis.redis.delete.assert_called_once_with(f"{cache_with_redis.key_prefix}:{file_hash}")
    
    @pytest.mark.asyncio
    async def test_invalidate_cache_entry_memory(self, cache_memory_only):
        """Test cache entry invalidation with memory backend."""
        file_hash = "memory_invalidate"
        cache_key = f"{cache_memory_only.key_prefix}:{file_hash}"
        
        # Add entry to memory cache
        cache_memory_only._memory_cache[cache_key] = Mock()
        assert cache_key in cache_memory_only._memory_cache
        
        success = await cache_memory_only._invalidate(file_hash)
        
        assert success is True
        assert cache_key not in cache_memory_only._memory_cache
    
    @pytest.mark.asyncio
    async def test_clear_cache_redis(self, cache_with_redis):
        """Test clearing all cache entries with Redis."""
        cache_with_redis.redis.keys.return_value = ["key1", "key2", "key3"]
        cache_with_redis.redis.delete.return_value = 3
        
        cleared_count = await cache_with_redis.clear_cache()
        
        assert cleared_count == 3
        cache_with_redis.redis.keys.assert_called_once()
        cache_with_redis.redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_clear_cache_memory(self, cache_memory_only):
        """Test clearing all cache entries with memory backend."""
        # Add some entries
        cache_memory_only._memory_cache["key1"] = Mock()
        cache_memory_only._memory_cache["key2"] = Mock()
        
        cleared_count = await cache_memory_only.clear_cache()
        
        assert cleared_count == 2
        assert len(cache_memory_only._memory_cache) == 0
    
    def test_get_cache_stats_basic(self, cache_with_redis):
        """Test basic cache statistics."""
        # Set some stats
        cache_with_redis._stats["hits"] = 10
        cache_with_redis._stats["misses"] = 5
        cache_with_redis._stats["stores"] = 8
        
        stats = cache_with_redis.get_cache_stats()
        
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["stores"] == 8
        assert stats["hit_rate_percent"] == 66.67  # 10/(10+5) * 100
        assert stats["total_requests"] == 15
        assert stats["using_redis"] is True
    
    def test_get_cache_stats_memory(self, cache_memory_only):
        """Test cache statistics with memory backend."""
        stats = cache_memory_only.get_cache_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "cache_entries" in stats
        assert "estimated_size_mb" in stats
        assert stats["using_redis"] is False
    
    @pytest.mark.asyncio
    async def test_warm_cache_success(self, cache_with_redis):
        """Test cache warming with successful extractions."""
        test_files = [Path("/tmp/resume1.pdf"), Path("/tmp/resume2.pdf")]
        mime_types = ["application/pdf", "application/pdf"]
        
        with patch('app.core.extraction_cache.text_extraction_service') as mock_service:
            with patch('app.core.extraction_cache.get_file_info') as mock_file_info:
                
                mock_service.extract_text_from_file.return_value = ExtractionResult(
                    status=ExtractionStatus.COMPLETED,
                    extracted_text="Warmed content"
                )
                mock_file_info.return_value = Mock()
                
                with patch.object(cache_with_redis, 'get', return_value=None):  # Cache miss
                    with patch.object(cache_with_redis, 'store', return_value=True):
                        
                        results = await cache_with_redis.warm_cache(test_files, mime_types)
                        
                        assert results["requested"] == 2
                        assert results["newly_cached"] == 2
                        assert results["already_cached"] == 0
                        assert results["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_already_cached(self, cache_with_redis):
        """Test cache warming with already cached files."""
        test_files = [Path("/tmp/cached.pdf")]
        mime_types = ["application/pdf"]
        
        cached_result = ExtractionResult(
            status=ExtractionStatus.COMPLETED,
            extracted_text="Already cached"
        )
        
        with patch.object(cache_with_redis, 'get', return_value=cached_result):
            results = await cache_with_redis.warm_cache(test_files, mime_types)
            
            assert results["requested"] == 1
            assert results["already_cached"] == 1
            assert results["newly_cached"] == 0
    
    @pytest.mark.asyncio
    async def test_warm_cache_failed_extraction(self, cache_with_redis):
        """Test cache warming with failed extractions."""
        test_files = [Path("/tmp/corrupted.pdf")]
        mime_types = ["application/pdf"]
        
        with patch('app.core.extraction_cache.text_extraction_service') as mock_service:
            with patch('app.core.extraction_cache.get_file_info') as mock_file_info:
                
                mock_service.extract_text_from_file.return_value = ExtractionResult(
                    status=ExtractionStatus.FAILED,
                    error_message="Corrupted file"
                )
                mock_file_info.return_value = Mock()
                
                with patch.object(cache_with_redis, 'get', return_value=None):
                    results = await cache_with_redis.warm_cache(test_files, mime_types)
                    
                    assert results["requested"] == 1
                    assert results["failed"] == 1
                    assert results["newly_cached"] == 0
                    assert len(results["errors"]) == 1
                    assert "Corrupted file" in results["errors"][0]
    
    def test_warm_cache_mismatched_lengths(self, cache_with_redis):
        """Test cache warming with mismatched file and mime type lists."""
        test_files = [Path("/tmp/file1.pdf"), Path("/tmp/file2.pdf")]
        mime_types = ["application/pdf"]  # Only one MIME type for two files
        
        with pytest.raises(ValueError, match="must have same length"):
            asyncio.run(cache_with_redis.warm_cache(test_files, mime_types))


class TestGlobalCacheInstance:
    """Test the global extraction_cache instance."""
    
    def test_global_cache_exists(self):
        """Test that global cache instance exists."""
        assert extraction_cache is not None
        assert isinstance(extraction_cache, ExtractionCache)
    
    def test_global_cache_configuration(self):
        """Test global cache configuration."""
        assert extraction_cache.default_ttl_hours == 24 * 7  # 7 days
        assert extraction_cache.max_cache_size_mb == 100
        assert extraction_cache.key_prefix == "resume_extraction"


@pytest.mark.performance
class TestCachePerformance:
    """Test cache performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, cache_memory_only):
        """Test concurrent cache get/set operations."""
        test_files = [Path(f"/tmp/concurrent_{i}.pdf") for i in range(10)]
        
        async def cache_operation(file_path, index):
            # Try to get from cache
            result = await cache_memory_only.get(file_path, "application/pdf")
            
            if result is None:
                # Store in cache
                extraction_result = ExtractionResult(
                    status=ExtractionStatus.COMPLETED,
                    extracted_text=f"Concurrent content {index}"
                )
                
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value = Mock(st_size=1000)
                    with patch.object(cache_memory_only, '_generate_file_hash', return_value=f"hash_{index}"):
                        await cache_memory_only.store(file_path, "application/pdf", extraction_result)
            
            return index
        
        # Run concurrent operations
        tasks = [cache_operation(file_path, i) for i, file_path in enumerate(test_files)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(isinstance(r, int) for r in results)
        
        # All operations should have completed without errors
        # Some cache hits and misses are expected
        total_requests = cache_memory_only._stats["hits"] + cache_memory_only._stats["misses"]
        assert total_requests == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])