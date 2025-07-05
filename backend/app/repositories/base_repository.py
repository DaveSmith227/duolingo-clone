"""
Base Repository Pattern Implementation

Provides common database operations for all repositories.
"""
from typing import TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    
    This class provides standard database operations that can be
    inherited by specific model repositories.
    """
    
    def __init__(self, model: type[ModelType], db: Session):
        """
        Initialize repository with model and database session.
        
        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    async def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Get entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get all entities with optional filtering and pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field filters
            
        Returns:
            List of entities
        """
        query = self.db.query(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        
        return query.offset(skip).limit(limit).all()
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create new entity.
        
        Args:
            **kwargs: Entity attributes
            
        Returns:
            Created entity
        """
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    async def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """
        Update entity by ID.
        
        Args:
            id: Entity ID
            **kwargs: Attributes to update
            
        Returns:
            Updated entity or None if not found
        """
        entity = await self.get_by_id(id)
        if not entity:
            return None
        
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        self.db.commit()
        self.db.refresh(entity)
        return entity
    
    async def delete(self, id: str) -> bool:
        """
        Delete entity by ID.
        
        Args:
            id: Entity ID
            
        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(id)
        if not entity:
            return False
        
        self.db.delete(entity)
        self.db.commit()
        return True
    
    async def exists(self, **kwargs) -> bool:
        """
        Check if entity exists with given attributes.
        
        Args:
            **kwargs: Attributes to check
            
        Returns:
            True if exists, False otherwise
        """
        query = self.db.query(self.model)
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.first() is not None
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities with optional filtering.
        
        Args:
            filters: Dictionary of field filters
            
        Returns:
            Count of entities
        """
        query = self.db.query(self.model)
        
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
        
        return query.count()
    
    async def find_one(self, **kwargs) -> Optional[ModelType]:
        """
        Find single entity by attributes.
        
        Args:
            **kwargs: Attributes to match
            
        Returns:
            Entity or None if not found
        """
        query = self.db.query(self.model)
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.first()
    
    async def find_many(self, **kwargs) -> List[ModelType]:
        """
        Find multiple entities by attributes.
        
        Args:
            **kwargs: Attributes to match
            
        Returns:
            List of matching entities
        """
        query = self.db.query(self.model)
        
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.all()
    
    def save(self) -> None:
        """Save pending changes to database."""
        self.db.commit()
    
    def refresh(self, entity: ModelType) -> None:
        """Refresh entity from database."""
        self.db.refresh(entity)