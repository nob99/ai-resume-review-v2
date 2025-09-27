"""
Rate limiting functionality to protect against brute force attacks and DDoS.
Uses Redis for distributed rate limiting across multiple application instances.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_redis_url

# Configure logging
logger = logging.getLogger(__name__)


class RateLimitType(str, Enum):
    """Rate limit types for different endpoints."""
    LOGIN = "login"
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"
    API_GENERAL = "api_general"
    FILE_UPLOAD = "file_upload"
    ANALYSIS = "analysis"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    block_duration: int  # How long to block after limit exceeded (seconds)


class RateLimitConfigs:
    """Default rate limiting configurations."""
    
    LOGIN = RateLimitConfig(
        requests=5,        # 5 login attempts
        window=900,        # per 15 minutes
        block_duration=1800  # block for 30 minutes
    )
    
    REGISTRATION = RateLimitConfig(
        requests=3,        # 3 registration attempts  
        window=3600,       # per hour
        block_duration=3600  # block for 1 hour
    )
    
    PASSWORD_RESET = RateLimitConfig(
        requests=3,        # 3 password reset attempts
        window=3600,       # per hour
        block_duration=1800  # block for 30 minutes
    )
    
    API_GENERAL = RateLimitConfig(
        requests=100,      # 100 API requests
        window=3600,       # per hour
        block_duration=300   # block for 5 minutes
    )
    
    FILE_UPLOAD = RateLimitConfig(
        requests=10,       # 10 file uploads
        window=3600,       # per hour
        block_duration=1800  # block for 30 minutes
    )

    ANALYSIS = RateLimitConfig(
        requests=5,        # 5 analysis requests
        window=300,        # per 5 minutes
        block_duration=600   # block for 10 minutes
    )


class RedisRateLimiter:
    """
    Redis-based distributed rate limiter for protecting against abuse.
    
    Implements sliding window rate limiting with automatic cleanup.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize rate limiter with Redis connection.
        
        Args:
            redis_url: Redis connection URL (optional, defaults to config)
        """
        self.redis_url = redis_url or get_redis_url()
        self.redis_client: Optional[aioredis.Redis] = None
        self.configs = {
            RateLimitType.LOGIN: RateLimitConfigs.LOGIN,
            RateLimitType.REGISTRATION: RateLimitConfigs.REGISTRATION,
            RateLimitType.PASSWORD_RESET: RateLimitConfigs.PASSWORD_RESET,
            RateLimitType.API_GENERAL: RateLimitConfigs.API_GENERAL,
            RateLimitType.FILE_UPLOAD: RateLimitConfigs.FILE_UPLOAD,
            RateLimitType.ANALYSIS: RateLimitConfigs.ANALYSIS,
        }
    
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis rate limiter connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis for rate limiting: {str(e)}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis rate limiter disconnected")
    
    def _get_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"ratelimit:{limit_type.value}:{identifier}"
    
    def _get_block_key(self, limit_type: RateLimitType, identifier: str) -> str:
        """Generate Redis key for blocking."""
        return f"ratelimit:block:{limit_type.value}:{identifier}"
    
    async def is_blocked(self, limit_type: RateLimitType, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier is currently blocked.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            Tuple of (is_blocked, seconds_until_unblock)
        """
        if not self.redis_client:
            return False, None
        
        try:
            block_key = self._get_block_key(limit_type, identifier)
            block_until = await self.redis_client.get(block_key)
            
            if not block_until:
                return False, None
            
            block_until_timestamp = float(block_until)
            current_time = time.time()
            
            if current_time >= block_until_timestamp:
                # Block expired, remove it
                await self.redis_client.delete(block_key)
                return False, None
            
            seconds_remaining = int(block_until_timestamp - current_time)
            return True, seconds_remaining
            
        except Exception as e:
            logger.error(f"Error checking block status: {str(e)}")
            return False, None
    
    async def check_rate_limit(self, limit_type: RateLimitType, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if not self.redis_client:
            # If Redis is not available, allow the request but log warning
            logger.warning("Rate limiting disabled - Redis not available")
            return True, {"redis_available": False}
        
        config = self.configs[limit_type]
        
        # Check if currently blocked
        is_blocked, block_time_remaining = await self.is_blocked(limit_type, identifier)
        if is_blocked:
            return False, {
                "blocked": True,
                "block_time_remaining": block_time_remaining,
                "reason": f"Blocked due to rate limit violation"
            }
        
        try:
            current_time = time.time()
            window_start = current_time - config.window
            key = self._get_key(limit_type, identifier)
            
            # Use pipeline for atomic operations
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Remove old entries outside the window
                await pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current requests in window
                await pipe.zcard(key)
                
                # Add current request
                await pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiry for cleanup
                await pipe.expire(key, config.window + 60)  # Extra buffer for cleanup
                
                results = await pipe.execute()
                
            current_count = results[1]  # Count from zcard
            
            # Check if limit exceeded
            if current_count >= config.requests:
                # Block the identifier
                block_key = self._get_block_key(limit_type, identifier)
                block_until = current_time + config.block_duration
                await self.redis_client.setex(block_key, config.block_duration, str(block_until))
                
                logger.warning(f"Rate limit exceeded for {identifier} on {limit_type.value}")
                
                return False, {
                    "blocked": True,
                    "requests_made": current_count,
                    "requests_allowed": config.requests,
                    "window_seconds": config.window,
                    "block_duration": config.block_duration,
                    "reset_time": current_time + config.window
                }
            
            # Request allowed
            return True, {
                "requests_made": current_count + 1,  # +1 because we just added one
                "requests_allowed": config.requests,
                "window_seconds": config.window,
                "reset_time": current_time + config.window
            }
            
        except Exception as e:
            logger.error(f"Rate limiting error: {str(e)}")
            # On error, allow the request to avoid blocking legitimate traffic
            return True, {"error": str(e)}
    
    async def reset_rate_limit(self, limit_type: RateLimitType, identifier: str) -> bool:
        """
        Reset rate limit for identifier (admin function).
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier to reset
            
        Returns:
            True if successful
        """
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(limit_type, identifier)
            block_key = self._get_block_key(limit_type, identifier)
            
            # Remove both rate limit data and block
            await self.redis_client.delete(key, block_key)
            
            logger.info(f"Rate limit reset for {identifier} on {limit_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limit: {str(e)}")
            return False
    
    async def get_rate_limit_status(self, limit_type: RateLimitType, identifier: str) -> Dict[str, Any]:
        """
        Get current rate limit status for identifier.
        
        Args:
            limit_type: Type of rate limit
            identifier: Unique identifier
            
        Returns:
            Rate limit status information
        """
        if not self.redis_client:
            return {"redis_available": False}
        
        config = self.configs[limit_type]
        
        try:
            # Check block status
            is_blocked, block_time_remaining = await self.is_blocked(limit_type, identifier)
            
            if is_blocked:
                return {
                    "blocked": True,
                    "block_time_remaining": block_time_remaining,
                    "requests_allowed": config.requests,
                    "window_seconds": config.window
                }
            
            # Get current count
            current_time = time.time()
            window_start = current_time - config.window
            key = self._get_key(limit_type, identifier)
            
            # Clean old entries and count
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            current_count = await self.redis_client.zcard(key)
            
            return {
                "blocked": False,
                "requests_made": current_count,
                "requests_allowed": config.requests,
                "requests_remaining": max(0, config.requests - current_count),
                "window_seconds": config.window,
                "reset_time": current_time + config.window
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limit status: {str(e)}")
            return {"error": str(e)}


# Global rate limiter instance
rate_limiter = RedisRateLimiter()

# SlowAPI limiter for simple rate limiting
slowapi_limiter = Limiter(key_func=get_remote_address)


def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.
    
    Uses IP address with X-Forwarded-For header support for proxy/load balancer scenarios.
    """
    # Check for X-Forwarded-For header (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (client IP before any proxies)
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    return get_remote_address(request)


async def check_rate_limit_middleware(
    request: Request, 
    limit_type: RateLimitType,
    identifier: Optional[str] = None
) -> None:
    """
    Middleware function to check rate limits.
    
    Args:
        request: FastAPI request object
        limit_type: Type of rate limit to check
        identifier: Custom identifier (if None, uses IP address)
        
    Raises:
        HTTPException: If rate limit is exceeded
    """
    if identifier is None:
        identifier = get_client_identifier(request)
    
    is_allowed, info = await rate_limiter.check_rate_limit(limit_type, identifier)
    
    if not is_allowed:
        # Add rate limit headers
        headers = {}
        if "block_time_remaining" in info:
            headers["Retry-After"] = str(info["block_time_remaining"])
        if "requests_allowed" in info:
            headers["X-RateLimit-Limit"] = str(info["requests_allowed"])
        if "window_seconds" in info:
            headers["X-RateLimit-Window"] = str(info["window_seconds"])
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests for {limit_type.value}",
                **info
            },
            headers=headers
        )
    
    # Add rate limit info to request state for logging
    if not hasattr(request.state, "rate_limit_info"):
        request.state.rate_limit_info = {}
    request.state.rate_limit_info[limit_type.value] = info


# Utility functions for specific endpoints
async def check_login_rate_limit(request: Request, email: str = None) -> None:
    """Check rate limit for login attempts."""
    identifier = email if email else get_client_identifier(request)
    await check_rate_limit_middleware(request, RateLimitType.LOGIN, identifier)


async def check_registration_rate_limit(request: Request) -> None:
    """Check rate limit for registration attempts."""
    await check_rate_limit_middleware(request, RateLimitType.REGISTRATION)


async def check_password_reset_rate_limit(request: Request, email: str = None) -> None:
    """Check rate limit for password reset attempts."""
    identifier = email if email else get_client_identifier(request)
    await check_rate_limit_middleware(request, RateLimitType.PASSWORD_RESET, identifier)


async def check_api_rate_limit(request: Request) -> None:
    """Check general API rate limit."""
    await check_rate_limit_middleware(request, RateLimitType.API_GENERAL)


async def check_file_upload_rate_limit(request: Request, user_id: str = None) -> None:
    """Check rate limit for file uploads."""
    identifier = user_id if user_id else get_client_identifier(request)
    await check_rate_limit_middleware(request, RateLimitType.FILE_UPLOAD, identifier)