"""
Unit tests for AuthRepository and RefreshTokenRepository.
Tests data access layer in isolation with mocked database sessions.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.repository import UserRepository, RefreshTokenRepository
from database.models.auth import User, RefreshToken
from app.features.auth.tests.fixtures.mock_data import (
    MockAuthData,
    MockAuthComponents
)
from app.core.datetime_utils import utc_now


class TestUserRepository:
    """Test suite for UserRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock AsyncSession."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = Mock()
        return session
    
    @pytest.fixture
    def user_repo(self, mock_session):
        """Create UserRepository with mock session."""
        return UserRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repo, mock_session):
        """Test getting user by email."""
        # Arrange
        email = "test@example.com"
        mock_user = MockAuthComponents.create_mock_user()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.get_by_email(email)
        
        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()
        # Verify the query includes the email filter
        call_args = mock_session.execute.call_args[0][0]
        assert hasattr(call_args, 'whereclause')  # Basic check that it's a filtered query
    
    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, user_repo, mock_session):
        """Test getting non-existent user by email."""
        # Arrange
        email = "nonexistent@example.com"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.get_by_email(email)
        
        # Assert
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repo, mock_session):
        """Test getting user by ID."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user = MockAuthComponents.create_mock_user()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.get_by_id(user_id)
        
        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repo, mock_session):
        """Test creating a new user."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "password123",
            "first_name": "New",
            "last_name": "User",
            "role": "consultant"
        }
        
        with pytest.mock.patch('app.features.auth.repository.User') as MockUser:
            mock_user_instance = Mock()
            MockUser.return_value = mock_user_instance
            
            # Act
            result = await user_repo.create(**user_data)
            
            # Assert
            MockUser.assert_called_once_with(**user_data)
            mock_session.add.assert_called_once_with(mock_user_instance)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_user_instance)
            assert result == mock_user_instance
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_repo, mock_session):
        """Test updating user information."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        update_data = {
            "first_name": "Updated",
            "last_login_at": utc_now()
        }
        
        mock_user = MockAuthComponents.create_mock_user()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.update(user_id, **update_data)
        
        # Assert
        # Verify user attributes were updated
        for key, value in update_data.items():
            assert getattr(mock_user, key) == value
        
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_user)
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, user_repo, mock_session):
        """Test updating non-existent user."""
        # Arrange
        user_id = UUID("nonexistent-id")
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.update(user_id, first_name="Updated")
        
        # Assert
        assert result is None
        mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_user(self, user_repo, mock_session):
        """Test soft deleting a user (deactivating)."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_user = MockAuthComponents.create_mock_user()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await user_repo.delete(user_id)
        
        # Assert
        assert result is True
        assert mock_user.is_active is False
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_commit(self, user_repo, mock_session):
        """Test committing transaction."""
        # Act
        await user_repo.commit()
        
        # Assert
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback(self, user_repo, mock_session):
        """Test rolling back transaction."""
        # Act
        await user_repo.rollback()
        
        # Assert
        mock_session.rollback.assert_called_once()


class TestRefreshTokenRepository:
    """Test suite for RefreshTokenRepository."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock AsyncSession."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = Mock()
        return session
    
    @pytest.fixture
    def token_repo(self, mock_session):
        """Create RefreshTokenRepository with mock session."""
        return RefreshTokenRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_create_refresh_token(self, token_repo, mock_session):
        """Test creating a new refresh token."""
        # Arrange
        token_data = {
            "user_id": UUID("550e8400-e29b-41d4-a716-446655440000"),
            "token": "refresh.token.here",
            "session_id": "session-123",
            "device_info": "Test Browser",
            "ip_address": "192.168.1.100"
        }
        
        with pytest.mock.patch('app.features.auth.repository.RefreshToken') as MockToken:
            mock_token_instance = Mock()
            MockToken.return_value = mock_token_instance
            
            # Act
            result = await token_repo.create(**token_data)
            
            # Assert
            MockToken.assert_called_once_with(**token_data)
            mock_session.add.assert_called_once_with(mock_token_instance)
            mock_session.commit.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_token_instance)
            assert result == mock_token_instance
    
    @pytest.mark.asyncio
    async def test_get_by_session(self, token_repo, mock_session):
        """Test getting refresh token by session ID."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        session_id = "session-123"
        
        mock_token = MockAuthComponents.create_mock_refresh_token()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.get_by_session(user_id, session_id)
        
        # Assert
        assert result == mock_token
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_tokens(self, token_repo, mock_session):
        """Test getting all tokens for a user."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        mock_tokens = [
            MockAuthComponents.create_mock_refresh_token(),
            MockAuthComponents.create_mock_refresh_token()
        ]
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_tokens
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.get_user_tokens(user_id)
        
        # Assert
        assert result == mock_tokens
        assert len(result) == 2
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_refresh_token(self, token_repo, mock_session):
        """Test updating refresh token."""
        # Arrange
        token_id = UUID("token-550e-8400-e29b-41d4a716446655440000")
        update_data = {
            "last_used_at": utc_now(),
            "ip_address": "192.168.1.200"
        }
        
        mock_token = MockAuthComponents.create_mock_refresh_token()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.update(token_id, **update_data)
        
        # Assert
        for key, value in update_data.items():
            assert getattr(mock_token, key) == value
        
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_token)
        assert result == mock_token
    
    @pytest.mark.asyncio
    async def test_delete_refresh_token(self, token_repo, mock_session):
        """Test deleting (revoking) a refresh token."""
        # Arrange
        token_id = UUID("token-550e-8400-e29b-41d4a716446655440000")
        mock_token = MockAuthComponents.create_mock_refresh_token()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.delete(token_id)
        
        # Assert
        assert result is True
        assert mock_token.status == "revoked"
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, token_repo, mock_session):
        """Test cleaning up expired tokens."""
        # Arrange
        mock_result = Mock()
        mock_result.rowcount = 5  # 5 tokens were deleted
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.cleanup_expired()
        
        # Assert
        assert result == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_user_sessions(self, token_repo, mock_session):
        """Test revoking all sessions for a user except current."""
        # Arrange
        user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        current_session_id = "current-session"
        
        mock_result = Mock()
        mock_result.rowcount = 3  # 3 sessions were revoked
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await token_repo.revoke_user_sessions(user_id, exclude_session=current_session_id)
        
        # Assert
        assert result == 3
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestRepositoryErrorHandling:
    """Test repository error handling and edge cases."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock AsyncSession that can raise exceptions."""
        session = Mock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.refresh = AsyncMock()
        session.add = Mock()
        return session
    
    @pytest.mark.asyncio
    async def test_user_repo_database_error(self, mock_session):
        """Test repository handling of database errors."""
        # Arrange
        user_repo = UserRepository(mock_session)
        mock_session.execute.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Database connection error"):
            await user_repo.get_by_email("test@example.com")
    
    @pytest.mark.asyncio
    async def test_token_repo_commit_error(self, mock_session):
        """Test repository handling of commit errors."""
        # Arrange
        token_repo = RefreshTokenRepository(mock_session)
        mock_session.commit.side_effect = Exception("Transaction failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Transaction failed"):
            await token_repo.commit()
    
    @pytest.mark.asyncio
    async def test_repository_rollback_on_error(self, mock_session):
        """Test that repositories properly rollback on errors."""
        # Arrange
        user_repo = UserRepository(mock_session)
        mock_session.commit.side_effect = Exception("Commit failed")
        
        # Mock user creation to succeed initially
        with pytest.mock.patch('app.features.auth.repository.User') as MockUser:
            mock_user_instance = Mock()
            MockUser.return_value = mock_user_instance
            
            # Act & Assert
            with pytest.raises(Exception, match="Commit failed"):
                await user_repo.create(email="test@example.com", password="password")
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()