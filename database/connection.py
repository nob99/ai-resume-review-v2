"""
Database connection and session management for PostgreSQL.
Handles connection pooling, environment configuration, and session lifecycle.
"""

import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

# Import centralized configuration  
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from backend.app.core.config import get_database_url, app_config

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration management."""
    
    def __init__(self):
        """Initialize database configuration from centralized config."""
        self.database_url = get_database_url()
        self.echo_sql = os.getenv("DB_ECHO", "false").lower() == "true"
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
        self.pool_pre_ping = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
        
        # Add SSL configuration for production
        if app_config.ENVIRONMENT in ["staging", "prod"]:
            self.database_url += "?sslmode=require"
    
    def get_engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration."""
        return {
            "echo": self.echo_sql,
            "poolclass": QueuePool,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "connect_args": {
                "connect_timeout": 10,
                "application_name": "ai-resume-review-backend"
            }
        }


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self):
        """Initialize database manager."""
        self.config = DatabaseConfig()
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._initialized:
            return
        
        try:
            # Create engine
            self.engine = create_engine(
                self.config.database_url,
                **self.config.get_engine_kwargs()
            )
            
            # Add connection event listeners
            self._setup_event_listeners()
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Test connection
            self._test_connection()
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set connection-specific settings."""
            # This is for PostgreSQL, so we don't need SQLite pragmas
            # But we can set PostgreSQL-specific settings here if needed
            pass
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log database connection checkout."""
            logger.debug("Database connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log database connection checkin."""
            logger.debug("Database connection returned to pool")
    
    def _test_connection(self) -> None:
        """Test database connection."""
        try:
            from sqlalchemy import text
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """
        Get database session.
        
        Returns:
            SQLAlchemy session
        """
        if not self._initialized:
            self.initialize()
        
        return self.SessionLocal()
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """
        Get database session with context management.
        
        Yields:
            SQLAlchemy session
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")
    
    def get_connection_info(self) -> dict:
        """
        Get database connection information (for debugging).
        
        Returns:
            Connection information (passwords masked)
        """
        if not self.engine:
            return {"status": "not_initialized"}
        
        pool = self.engine.pool
        
        return {
            "status": "initialized",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "url_masked": str(self.engine.url).replace(
                f":{self.engine.url.password}@", ":***@"
            ) if self.engine.url.password else str(self.engine.url)
        }


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        SQLAlchemy session
    """
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


async def get_async_db() -> Generator[Session, None, None]:
    """
    Async version of get_db dependency.
    
    Yields:
        SQLAlchemy session
    """
    # For now, we're using sync SQLAlchemy
    # In future sprints, we might migrate to async SQLAlchemy
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    """Initialize database connection on application startup."""
    try:
        db_manager.initialize()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


def close_database() -> None:
    """Close database connections on application shutdown."""
    try:
        db_manager.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")


def get_db_health() -> dict:
    """
    Get database health status.
    
    Returns:
        Database health information
    """
    try:
        with db_manager.get_session_context() as session:
            # Simple health check query
            from sqlalchemy import text
            result = session.execute(text("SELECT 1 as health_check, NOW() as timestamp"))
            row = result.fetchone()
            
            return {
                "status": "healthy",
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "connection_info": db_manager.get_connection_info()
            }
            
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_info": db_manager.get_connection_info()
        }
    except Exception as e:
        logger.error(f"Database health check error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }