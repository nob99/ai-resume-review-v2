"""
Test configuration and fixtures for the AI Resume Review Platform backend.
"""

import os
import pytest
import asyncio
from typing import Generator
from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment
os.environ["ENVIRONMENT"] = "test"

from app.models.user import Base, User
from app.database.connection import db_manager
from app.core.rate_limiter import rate_limiter
from app.core.config import get_database_url


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine using centralized configuration."""
    # Use centralized database configuration
    database_url = get_database_url()
    
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True
    )
    
    # Test connection
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="session")
def TestSessionLocal(test_engine):
    """Create test session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_db(TestSessionLocal) -> Generator[Session, None, None]:
    """Create test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = Mock()
    mock_redis.ping = Mock(return_value=True)
    mock_redis.get = Mock(return_value=None)
    mock_redis.setex = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=True)
    mock_redis.zremrangebyscore = Mock(return_value=0)
    mock_redis.zcard = Mock(return_value=0)
    mock_redis.zadd = Mock(return_value=True)
    mock_redis.expire = Mock(return_value=True)
    mock_redis.pipeline = Mock()
    
    # Mock pipeline context manager
    pipeline_mock = Mock()
    pipeline_mock.zremrangebyscore = Mock()
    pipeline_mock.zcard = Mock()
    pipeline_mock.zadd = Mock()
    pipeline_mock.expire = Mock()
    pipeline_mock.execute = Mock(return_value=[0, 0, True, True])
    pipeline_mock.__aenter__ = Mock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = Mock(return_value=None)
    
    mock_redis.pipeline.return_value = pipeline_mock
    
    return mock_redis


@pytest.fixture
async def mock_rate_limiter(mock_redis):
    """Mock rate limiter for testing."""
    # Temporarily replace the redis client
    original_client = rate_limiter.redis_client
    rate_limiter.redis_client = mock_redis
    
    yield rate_limiter
    
    # Restore original client
    rate_limiter.redis_client = original_client


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def test_admin_data():
    """Test admin user data."""
    return {
        "email": "admin@example.com", 
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin"
    }


@pytest.fixture
def client():
    """Create FastAPI test client using real app and database."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def create_test_user(test_db):
    """Factory to create test users with cleanup."""
    created_users = []
    
    def _create_user(**kwargs):
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "Test", 
            "last_name": "User"
        }
        user_data.update(kwargs)
        
        user = User(**user_data)
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        created_users.append(user)
        return user
    
    yield _create_user
    
    # Cleanup: remove test users after test completes
    for user in created_users:
        try:
            test_db.delete(user)
            test_db.commit()
        except Exception:
            # If user already deleted, continue
            test_db.rollback()
            pass


@pytest.fixture
def weak_passwords():
    """List of weak passwords for testing."""
    return [
        "123456",
        "password",
        "password123",
        "abc123",
        "qwerty",
        "admin",
        "letmein",
        "welcome"
    ]


@pytest.fixture  
def strong_passwords():
    """List of strong passwords for testing."""
    return [
        "MyStr0ng!Password",
        "C0mplex#Password2023",
        "Secure&Auth!456",
        "D1fficult*Pass789",
        "Random@String123!"
    ]


@pytest.fixture
def invalid_passwords():
    """List of invalid passwords (too short, missing requirements)."""
    return [
        "",           # Empty
        "a",          # Too short
        "1234567",    # No letters
        "password",   # No uppercase, digits, special
        "PASSWORD",   # No lowercase, digits, special  
        "Password",   # No digits, special
        "Password1",  # No special characters
        "password!",  # No uppercase, digits
    ]