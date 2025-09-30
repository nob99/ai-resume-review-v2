"""
Cache service for the new infrastructure layer.
Provides caching functionality with TTL support and JSON serialization.
"""

from typing import Optional, Any, Union
import json
import logging
from datetime import timedelta

import redis.asyncio as redis

from app.core.cache.connection import get_redis_client

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for caching data in Redis.
    
    This service provides:
    - Key-value caching with TTL
    - JSON serialization for complex objects
    - Cache invalidation
    - Namespace support for cache keys
    """
    
    def __init__(self, namespace: str = "cache", client: Optional[redis.Redis] = None):
        """
        Initialize the cache service.
        
        Args:
            namespace: Namespace prefix for all cache keys
            client: Optional Redis client, will use global client if not provided
        """
        self.namespace = namespace
        self._client = client
    
    async def _get_client(self) -> redis.Redis:
        """Get the Redis client, using the provided one or the global one."""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client
    
    def _make_key(self, key: str) -> str:
        """
        Create a namespaced cache key.
        
        Args:
            key: The cache key
            
        Returns:
            The namespaced key
        """
        return f"{self.namespace}:{key}"
    
    async def get(
        self,
        key: str,
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            default: Default value if key not found
            deserialize: Whether to deserialize JSON values
            
        Returns:
            The cached value or default
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            value = await client.get(full_key)
            
            if value is None:
                return default
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live (seconds or timedelta)
            serialize: Whether to serialize the value as JSON
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            
            # Serialize value if needed
            if serialize and not isinstance(value, str):
                value = json.dumps(value)
            
            # Convert timedelta to seconds
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            # Set the value with optional TTL
            if ttl:
                await client.setex(full_key, ttl, value)
            else:
                await client.set(full_key, value)
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was deleted, False otherwise
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            result = await client.delete(full_key)
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key exists, False otherwise
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            return await client.exists(full_key) > 0
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def clear_namespace(self) -> int:
        """
        Clear all keys in this cache's namespace.
        
        Returns:
            The number of keys deleted
        """
        try:
            client = await self._get_client()
            pattern = f"{self.namespace}:*"
            
            # Find all keys matching the pattern
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            # Delete all found keys
            if keys:
                return await client.delete(*keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear namespace error: {e}")
            return 0
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the TTL (time to live) of a key.
        
        Args:
            key: The cache key
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no TTL
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            ttl = await client.ttl(full_key)
            
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but has no TTL
                return None
            else:
                return ttl
                
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return None
    
    async def extend_ttl(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """
        Extend the TTL of an existing key.
        
        Args:
            key: The cache key
            ttl: New TTL (seconds or timedelta)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            full_key = self._make_key(key)
            
            # Convert timedelta to seconds
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            
            return await client.expire(full_key, ttl)
            
        except Exception as e:
            logger.error(f"Cache extend TTL error for key {key}: {e}")
            return False


# Convenience function for creating cache services
def create_cache_service(namespace: str) -> CacheService:
    """
    Create a cache service with a specific namespace.
    
    Args:
        namespace: The cache namespace
        
    Returns:
        A configured CacheService instance
    """
    return CacheService(namespace=namespace)