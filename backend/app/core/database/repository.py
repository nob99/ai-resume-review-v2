"""
Base repository class with common CRUD operations.
Provides a foundation for all repository classes in the new architecture.
"""

from typing import Generic, TypeVar, Optional, List, Dict, Any, Type
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

from app.core.datetime_utils import utc_now

T = TypeVar('T', bound=DeclarativeMeta)


class BaseRepository(Generic[T]):
    """
    Base repository with common CRUD operations.
    
    This class provides standard database operations that can be inherited
    by all feature-specific repositories. It follows the repository pattern
    to abstract data access logic from business logic.
    """
    
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        """
        Initialize the repository with a database session and model class.
        
        Args:
            session: The async SQLAlchemy session
            model_class: The SQLAlchemy model class this repository manages
        """
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            id: The UUID of the entity to retrieve
            
        Returns:
            The entity if found, None otherwise
        """
        query = select(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """
        Get all entities with optional pagination and filtering.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Optional dictionary of filters to apply
            
        Returns:
            List of entities matching the criteria
        """
        query = select(self.model_class)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> T:
        """
        Create a new entity.
        
        Args:
            **kwargs: The attributes for the new entity
            
        Returns:
            The created entity
        """
        # Add timestamps if the model has them
        if hasattr(self.model_class, 'created_at'):
            kwargs.setdefault('created_at', utc_now())
        if hasattr(self.model_class, 'updated_at'):
            kwargs.setdefault('updated_at', utc_now())
        
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        await self.session.flush()  # Flush to get the ID without committing
        return entity
    
    async def update(self, id: UUID, **kwargs) -> Optional[T]:
        """
        Update an entity by ID.
        
        Args:
            id: The UUID of the entity to update
            **kwargs: The attributes to update
            
        Returns:
            The updated entity if found, None otherwise
        """
        # Add updated timestamp if the model has it
        if hasattr(self.model_class, 'updated_at'):
            kwargs['updated_at'] = utc_now()
        
        # Build and execute update query
        query = (
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**kwargs)
            .returning(self.model_class)
        )
        
        result = await self.session.execute(query)
        await self.session.flush()
        
        # Return the updated entity
        updated_entity = result.scalar_one_or_none()
        return updated_entity
    
    async def delete(self, id: UUID) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            id: The UUID of the entity to delete
            
        Returns:
            True if the entity was deleted, False if not found
        """
        query = delete(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(query)
        await self.session.flush()
        return result.rowcount > 0
    
    async def exists(self, **kwargs) -> bool:
        """
        Check if an entity exists with the given criteria.
        
        Args:
            **kwargs: The attributes to check
            
        Returns:
            True if an entity exists, False otherwise
        """
        query = select(func.count()).select_from(self.model_class)
        
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                query = query.where(getattr(self.model_class, key) == value)
        
        result = await self.session.execute(query)
        count = result.scalar()
        return count > 0
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities matching the given criteria.
        
        Args:
            filters: Optional dictionary of filters to apply
            
        Returns:
            The count of matching entities
        """
        query = select(func.count()).select_from(self.model_class)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.where(getattr(self.model_class, key) == value)
        
        result = await self.session.execute(query)
        return result.scalar() or 0
    
    async def commit(self):
        """Commit the current transaction."""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback the current transaction."""
        await self.session.rollback()
    
    async def refresh(self, entity: T):
        """
        Refresh an entity from the database.
        
        Args:
            entity: The entity to refresh
        """
        await self.session.refresh(entity)