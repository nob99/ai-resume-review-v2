"""
Base repository class with common database operations.
Provides consistent patterns for data access across all repositories.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc, func

from app.core.datetime_utils import utc_now

# Type variables for generic repository
T = TypeVar('T')
CreateSchemaType = TypeVar('CreateSchemaType')
UpdateSchemaType = TypeVar('UpdateSchemaType')


class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository with common CRUD operations.
    
    Provides consistent patterns for:
    - Create, read, update, delete operations
    - Query building and filtering
    - Transaction management
    - Error handling
    """
    
    def __init__(self, model: Type[T], db: Session):
        """
        Initialize repository with model and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    def create(self, obj_in: T) -> T:
        """
        Create a new record.
        
        Args:
            obj_in: Object to create
            
        Returns:
            Created object with generated ID and timestamps
            
        Raises:
            IntegrityError: If database constraints are violated
        """
        try:
            self.db.add(obj_in)
            self.db.commit()
            self.db.refresh(obj_in)
            return obj_in
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get record by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            Record if found, None otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[T]:
        """
        Get multiple records with filtering and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field: value filters
            order_by: Field name to order by
            order_desc: Whether to order descending
            
        Returns:
            List of records matching criteria
        """
        query = self.db.query(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, field).in_(value))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_field = getattr(self.model, order_by)
            if order_desc:
                query = query.order_by(desc(order_field))
            else:
                query = query.order_by(asc(order_field))
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters.
        
        Args:
            filters: Dictionary of field: value filters
            
        Returns:
            Number of matching records
        """
        query = self.db.query(func.count(self.model.id))
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, field).in_(value))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        return query.scalar()
    
    def update(self, db_obj: T, obj_in: Dict[str, Any]) -> T:
        """
        Update an existing record.
        
        Args:
            db_obj: Existing database object
            obj_in: Dictionary of fields to update
            
        Returns:
            Updated object
        """
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            # Update timestamp if model has updated_at field
            if hasattr(db_obj, 'updated_at'):
                db_obj.updated_at = utc_now()
            
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            obj = self.db.query(self.model).filter(self.model.id == id).first()
            if obj:
                self.db.delete(obj)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """
        Delete records matching filters.
        
        Args:
            filters: Dictionary of field: value filters
            
        Returns:
            Number of deleted records
        """
        try:
            query = self.db.query(self.model)
            
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            
            deleted_count = query.count()
            query.delete(synchronize_session=False)
            self.db.commit()
            return deleted_count
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def exists(self, id: UUID) -> bool:
        """
        Check if record exists by ID.
        
        Args:
            id: Record UUID
            
        Returns:
            True if exists, False otherwise
        """
        return self.db.query(
            self.db.query(self.model).filter(self.model.id == id).exists()
        ).scalar()
    
    def bulk_create(self, objects: List[T]) -> List[T]:
        """
        Create multiple records in bulk.
        
        Args:
            objects: List of objects to create
            
        Returns:
            List of created objects
        """
        try:
            self.db.add_all(objects)
            self.db.commit()
            for obj in objects:
                self.db.refresh(obj)
            return objects
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e