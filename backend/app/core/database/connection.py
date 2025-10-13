"""
PostgreSQL connection management for the new infrastructure layer.
This module provides connection pooling and session management.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class PostgresConnection:
    """
    Manages PostgreSQL database connections with async support.
    
    This class provides:
    - Connection pooling
    - Session factory
    - Health checks
    - Graceful shutdown
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the PostgreSQL connection manager.
        
        Args:
            database_url: Optional database URL, defaults to settings.DATABASE_URL
        """
        self.database_url = database_url or settings.ASYNC_DATABASE_URL
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
    
    async def initialize(self):
        """
        Initialize the database engine and session factory.
        
        This method sets up the async engine with appropriate pooling
        based on the environment (test vs production).
        """
        if self._engine is not None:
            logger.warning("Database engine already initialized")
            return
        
        # Use NullPool for testing to avoid connection issues
        # Use AsyncAdaptedQueuePool for production for better performance
        poolclass = NullPool if settings.TESTING else AsyncAdaptedQueuePool
        
        # Create the async engine
        self._engine = create_async_engine(
            self.database_url,
            poolclass=poolclass,
            echo=settings.DEBUG,  # Log SQL statements in debug mode
            pool_size=settings.DATABASE_POOL_SIZE if not settings.TESTING else 1,
            max_overflow=settings.DATABASE_MAX_OVERFLOW if not settings.TESTING else 0,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 minutes
            connect_args={
                "server_settings": {
                    "application_name": "ai_resume_review_backend",
                    "jit": "off"
                },
                "command_timeout": 60,
                "timeout": 30
            }
        )
        
        # Create session factory
        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Don't auto-flush before queries
            autocommit=False  # Use transactions
        )
        
        logger.info("PostgreSQL connection initialized successfully")
    
    async def close(self):
        """
        Close the database connection and dispose of the engine.
        
        This should be called during application shutdown.
        """
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            logger.info("PostgreSQL connection closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.
        
        Yields:
            An async SQLAlchemy session
            
        Raises:
            RuntimeError: If the connection is not initialized
        """
        if self._sessionmaker is None:
            raise RuntimeError(
                "Database connection not initialized. Call initialize() first."
            )
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    @asynccontextmanager
    async def session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.
        
        This provides an alternative way to get sessions using async context manager.
        
        Yields:
            An async SQLAlchemy session
        """
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def health_check(self) -> bool:
        """
        Check if the database connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        if self._engine is None:
            return False
        
        try:
            async with self._engine.connect() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the async engine instance."""
        return self._engine
    
    @property
    def is_initialized(self) -> bool:
        """Check if the connection is initialized."""
        return self._engine is not None


# Global connection instance
_postgres_connection: Optional[PostgresConnection] = None


def get_postgres_connection() -> PostgresConnection:
    """
    Get the global PostgreSQL connection instance.
    
    Returns:
        The global PostgresConnection instance
    """
    global _postgres_connection
    if _postgres_connection is None:
        _postgres_connection = PostgresConnection()
    return _postgres_connection


async def init_postgres():
    """Initialize the global PostgreSQL connection."""
    connection = get_postgres_connection()
    await connection.initialize()


async def validate_database_environment():
    """
    Critical safety check: Ensure we're connected to the correct database.

    This prevents catastrophic issues like:
    - Staging environment connecting to production database
    - Production environment connecting to staging database

    The check is based on database naming conventions:
    - Staging databases must contain 'staging' in their name
    - Production databases must NOT contain 'staging' in their name

    If a mismatch is detected, the application will immediately shut down
    to prevent data corruption or security issues.

    Raises:
        RuntimeError: If environment doesn't match database
    """
    import os
    from sqlalchemy import text

    expected_env = os.getenv("ENVIRONMENT", "unknown")

    # Skip validation for development environment
    if expected_env in ["development", "dev", "local", "unknown"]:
        logger.info(
            "Skipping database environment validation for development environment",
            extra={"environment": expected_env}
        )
        return

    connection = get_postgres_connection()

    if not connection.is_initialized:
        logger.warning("Database not initialized, cannot validate environment")
        return

    try:
        # Query the actual database name
        async with connection.engine.connect() as conn:
            result = await conn.execute(text("SELECT current_database()"))
            actual_db_name = result.scalar()

        # Validation logic
        if expected_env == "staging":
            if "staging" not in actual_db_name.lower():
                logger.critical(
                    "CRITICAL: Environment mismatch detected!",
                    extra={
                        "expected_environment": expected_env,
                        "actual_database": actual_db_name,
                        "issue": "Staging environment connected to non-staging database",
                        "risk": "HIGH - Could corrupt production data"
                    }
                )
                raise RuntimeError(
                    f"Environment mismatch: Expected {expected_env} environment "
                    f"but connected to database '{actual_db_name}'. "
                    f"This is a critical safety check to prevent data corruption. "
                    f"Shutting down immediately."
                )

        elif expected_env == "production":
            if "staging" in actual_db_name.lower():
                logger.critical(
                    "CRITICAL: Environment mismatch detected!",
                    extra={
                        "expected_environment": expected_env,
                        "actual_database": actual_db_name,
                        "issue": "Production environment connected to staging database",
                        "risk": "HIGH - Production using test data"
                    }
                )
                raise RuntimeError(
                    f"Environment mismatch: Expected {expected_env} environment "
                    f"but connected to database '{actual_db_name}'. "
                    f"This is a critical safety check. Shutting down immediately."
                )

        # Log success
        logger.info(
            "Database environment validated successfully",
            extra={
                "environment": expected_env,
                "database": actual_db_name,
                "status": "VALIDATED"
            }
        )

    except RuntimeError:
        # Re-raise RuntimeError (our validation failures)
        raise
    except Exception as e:
        # Log but don't fail on unexpected errors (e.g., query failures)
        logger.error(
            "Failed to validate database environment",
            extra={
                "error": str(e),
                "environment": expected_env
            }
        )
        # Don't raise - we don't want to block startup on query failures


async def close_postgres():
    """Close the global PostgreSQL connection."""
    connection = get_postgres_connection()
    await connection.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to get database sessions.
    
    This can be used with FastAPI's Depends() for dependency injection.
    
    Yields:
        An async SQLAlchemy session
    """
    connection = get_postgres_connection()
    async for session in connection.get_session():
        yield session