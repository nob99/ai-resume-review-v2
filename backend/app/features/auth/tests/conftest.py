"""
Pytest configuration for auth feature tests.
Provides shared fixtures and configuration for auth testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient

from app.main import app
from app.features.auth.service import AuthService
from app.features.auth.repository import UserRepository, RefreshTokenRepository
from app.features.auth.tests.fixtures.mock_data import MockAuthComponents


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client_with_new_auth() -> TestClient:
    """Create test client with new auth feature enabled."""
    with patch.dict('os.environ', {'USE_NEW_AUTH': 'true'}):
        return TestClient(app)


@pytest.fixture
def client_with_old_auth() -> TestClient:
    """Create test client with old auth feature enabled."""
    with patch.dict('os.environ', {'USE_NEW_AUTH': 'false'}):
        return TestClient(app)


@pytest.fixture
def mock_user_repository():
    """Create mock UserRepository."""
    return MockAuthComponents.create_mock_repository()


@pytest.fixture
def mock_token_repository():
    """Create mock RefreshTokenRepository."""
    return MockAuthComponents.create_mock_token_repository()


@pytest.fixture
def mock_auth_service(mock_user_repository, mock_token_repository):
    """Create mock AuthService with mocked repositories."""
    service = Mock(spec=AuthService)
    service.user_repo = mock_user_repository
    service.token_repo = mock_token_repository
    
    # Mock service methods
    service.login = AsyncMock()
    service.register_user = AsyncMock()
    service.logout = AsyncMock()
    service.refresh_token = AsyncMock()
    service.change_password = AsyncMock()
    service.get_user_sessions = AsyncMock()
    service.revoke_session = AsyncMock()
    service.cleanup_expired_tokens = AsyncMock()
    
    return service


@pytest.fixture
def auth_headers():
    """Create authorization headers with mock JWT token."""
    return {"Authorization": "Bearer mock.jwt.token.here"}


@pytest.fixture
def invalid_auth_headers():
    """Create invalid authorization headers."""
    return {"Authorization": "Bearer invalid.jwt.token"}


@pytest.fixture
def admin_auth_headers():
    """Create authorization headers for admin user."""
    return {"Authorization": "Bearer mock.admin.jwt.token"}


# Mark integration tests for easy filtering
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as auth-related"
    )


# Auto-mark auth tests
def pytest_collection_modifyitems(config, items):
    """Automatically mark auth feature tests."""
    for item in items:
        # Mark all tests in auth feature as auth tests
        if "features/auth/tests" in str(item.fspath):
            item.add_marker(pytest.mark.auth)
        
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# Skip integration tests if database not available
@pytest.fixture(scope="session", autouse=True)
def check_database_connection():
    """Check if database is available for integration tests."""
    import os
    
    # Skip database-dependent tests if not in test environment
    if os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true":
        pytest.skip("Integration tests skipped - database not available", allow_module_level=True)


# Cleanup after tests
@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    
    # Here you could add cleanup logic if needed
    # For example, remove test users created during tests
    # This is especially important for integration tests
    pass