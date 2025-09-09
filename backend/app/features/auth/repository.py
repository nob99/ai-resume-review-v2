"""
Repository for auth feature using the new infrastructure layer.
Implements data access patterns for User and RefreshToken models.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.postgres.base import BaseRepository
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from database.models.auth import User, RefreshToken, SessionStatus


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User if found, None otherwise
        """
        # Make email lookup case-insensitive
        query = select(User).where(User.email.ilike(email.lower()))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def email_exists(self, email: str, exclude_user_id: Optional[UUID] = None) -> bool:
        """
        Check if email already exists in the system.
        
        Args:
            email: Email to check
            exclude_user_id: Optional user ID to exclude from check (for updates)
            
        Returns:
            True if email exists, False otherwise
        """
        query = select(User).where(User.email.ilike(email.lower()))
        
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all active users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active users
        """
        query = (
            select(User)
            .where(User.is_active == True)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Search users by email, first name, or last name.
        
        Args:
            search_term: Term to search for
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching users
        """
        search_pattern = f"%{search_term.lower()}%"
        
        query = (
            select(User)
            .where(
                or_(
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            )
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate a user account.
        
        Args:
            user_id: ID of the user to deactivate
            
        Returns:
            True if user was deactivated, False if not found
        """
        updated_user = await self.update(user_id, is_active=False)
        return updated_user is not None


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for RefreshToken model operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RefreshToken)
    
    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Get refresh token by token hash.
        
        Args:
            token_hash: SHA-256 hash of the token
            
        Returns:
            RefreshToken if found, None otherwise
        """
        query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_session_id(self, session_id: str) -> Optional[RefreshToken]:
        """
        Get refresh token by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            RefreshToken if found, None otherwise
        """
        query = select(RefreshToken).where(RefreshToken.session_id == session_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_sessions(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[RefreshToken]:
        """
        Get all refresh tokens for a user.
        
        Args:
            user_id: User ID
            active_only: If True, only return active tokens
            
        Returns:
            List of refresh tokens
        """
        query = select(RefreshToken).where(RefreshToken.user_id == user_id)
        
        if active_only:
            query = query.where(RefreshToken.status == SessionStatus.ACTIVE.value)
        
        query = query.order_by(RefreshToken.last_used_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def revoke_user_sessions(
        self,
        user_id: UUID,
        exclude_session_id: Optional[str] = None
    ) -> int:
        """
        Revoke all active sessions for a user.
        
        Args:
            user_id: User ID
            exclude_session_id: Optional session ID to exclude from revocation
            
        Returns:
            Number of sessions revoked
        """
        # Get active tokens for this user
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.status == SessionStatus.ACTIVE.value
            )
        )
        
        if exclude_session_id:
            query = query.where(RefreshToken.session_id != exclude_session_id)
        
        result = await self.session.execute(query)
        tokens = list(result.scalars().all())
        
        # Revoke each token
        for token in tokens:
            token.revoke()
        
        await self.session.flush()
        return len(tokens)
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired refresh tokens from the database.
        
        Returns:
            Number of tokens cleaned up
        """
        # Find expired tokens
        from app.core.datetime_utils import utc_now
        
        query = select(RefreshToken).where(
            or_(
                RefreshToken.expires_at < utc_now(),
                RefreshToken.status == SessionStatus.EXPIRED.value
            )
        )
        
        result = await self.session.execute(query)
        expired_tokens = list(result.scalars().all())
        
        # Delete expired tokens
        for token in expired_tokens:
            await self.session.delete(token)
        
        await self.session.flush()
        return len(expired_tokens)
    
    async def get_session_count_for_user(self, user_id: UUID) -> int:
        """
        Get count of active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of active sessions
        """
        return await self.count({
            "user_id": user_id,
            "status": SessionStatus.ACTIVE.value
        })