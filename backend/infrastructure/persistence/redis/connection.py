"""
Redis connection management for the new infrastructure layer.
Provides connection pooling and basic Redis operations.
"""

from typing import Optional, Any
import logging
import json

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class RedisConnection:
    """
    Manages Redis connections with async support.
    
    This class provides:
    - Connection pooling
    - Health checks
    - Graceful shutdown
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the Redis connection manager.
        
        Args:
            redis_url: Optional Redis URL, defaults to settings.REDIS_URL
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """
        Initialize the Redis connection pool and client.
        """
        if self._client is not None:
            logger.warning("Redis client already initialized")
            return
        
        try:
            # Create connection pool
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=True,  # Automatically decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test the connection
            await self._client.ping()
            
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close(self):
        """
        Close the Redis connection and clean up resources.
        
        This should be called during application shutdown.
        """
        if self._client is not None:
            await self._client.close()
            self._client = None
        
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
        
        logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if the Redis connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        if self._client is None:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get the Redis client instance."""
        return self._client
    
    @property
    def is_initialized(self) -> bool:
        """Check if the connection is initialized."""
        return self._client is not None


# Global Redis connection instance
_redis_connection: Optional[RedisConnection] = None


def get_redis_connection() -> RedisConnection:
    """
    Get the global Redis connection instance.
    
    Returns:
        The global RedisConnection instance
    """
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = RedisConnection()
    return _redis_connection


async def init_redis():
    """Initialize the global Redis connection."""
    connection = get_redis_connection()
    await connection.initialize()


async def close_redis():
    """Close the global Redis connection."""
    connection = get_redis_connection()
    await connection.close()


async def get_redis_client() -> redis.Redis:
    """
    Get the Redis client for dependency injection.
    
    Returns:
        The Redis client instance
        
    Raises:
        RuntimeError: If the Redis connection is not initialized
    """
    connection = get_redis_connection()
    if not connection.is_initialized:
        raise RuntimeError("Redis connection not initialized")
    return connection.client