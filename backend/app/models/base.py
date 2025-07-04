"""
Base Model Classes

SQLAlchemy base model classes with common fields and functionality
for the Duolingo clone backend application.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

# Import the Base from database module
from app.core.database import Base


class UUID(TypeDecorator):
    """
    Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, falls back to CHAR(36) for SQLite.
    """
    
    impl = CHAR
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


class TimestampMixin:
    """
    Mixin to add timestamp fields to models.
    
    Provides created_at and updated_at fields that are automatically
    managed by SQLAlchemy.
    """
    
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality to models.
    
    Provides deleted_at field and is_deleted property for soft deletes.
    """
    
    deleted_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp when the record was soft deleted"
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Mark the record as soft deleted."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self):
        """Restore a soft deleted record."""
        self.deleted_at = None


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields and functionality.
    
    All application models should inherit from this class to ensure
    consistent structure and behavior.
    """
    
    __abstract__ = True
    
    id = Column(
        UUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the record"
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.
        
        Converts CamelCase class names to snake_case table names.
        Example: UserProfile -> user_profiles
        """
        import re
        
        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        
        # Make plural (simple pluralization)
        if name.endswith('y'):
            name = name[:-1] + 'ies'
        elif name.endswith(('s', 'sh', 'ch', 'x', 'z')):
            name = name + 'es'
        else:
            name = name + 's'
            
        return name
    
    def to_dict(self, exclude_fields: set = None) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude_fields: Set of field names to exclude from the dictionary
            
        Returns:
            Dictionary representation of the model
        """
        exclude_fields = exclude_fields or set()
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude_fields:
                value = getattr(self, column.name)
                
                # Handle UUID serialization
                if isinstance(value, uuid.UUID):
                    value = str(value)
                # Handle datetime serialization
                elif isinstance(value, datetime):
                    value = value.isoformat()
                
                result[column.name] = value
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude_fields: set = None):
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary with field names and values
            exclude_fields: Set of field names to exclude from update
        """
        exclude_fields = exclude_fields or {'id', 'created_at'}
        
        for key, value in data.items():
            if (
                key not in exclude_fields and
                hasattr(self, key) and
                key in [c.name for c in self.__table__.columns]
            ):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """
    Base model class with soft delete functionality.
    
    Use this for models that should support soft deletes (marking as deleted
    instead of actually removing from database).
    """
    
    __abstract__ = True


class AuditMixin:
    """
    Mixin to add audit fields to models.
    
    Tracks who created and last modified the record.
    """
    
    created_by = Column(
        UUID(),
        nullable=True,
        doc="ID of the user who created this record"
    )
    
    updated_by = Column(
        UUID(),
        nullable=True,
        doc="ID of the user who last updated this record"
    )


class AuditModel(BaseModel, AuditMixin):
    """
    Base model class with audit trail functionality.
    
    Tracks creation and modification metadata including who performed the actions.
    """
    
    __abstract__ = True


class VersionedMixin:
    """
    Mixin to add optimistic locking to models.
    
    Prevents concurrent modification conflicts using version numbers.
    """
    
    version = Column(
        "version",
        String(36),
        default=lambda: str(uuid.uuid4()),
        nullable=False,
        doc="Version identifier for optimistic locking"
    )
    
    def increment_version(self):
        """Generate a new version identifier."""
        self.version = str(uuid.uuid4())


class VersionedModel(BaseModel, VersionedMixin):
    """
    Base model class with versioning for optimistic locking.
    
    Use this for models that need to prevent concurrent modification conflicts.
    """
    
    __abstract__ = True


class ActiveRecordMixin:
    """
    Mixin to add active record pattern methods to models.
    
    Provides convenient methods for common database operations.
    """
    
    @classmethod
    def create(cls, session, **kwargs):
        """
        Create and save a new instance.
        
        Args:
            session: SQLAlchemy session
            **kwargs: Field values for the new instance
            
        Returns:
            The created instance
        """
        instance = cls(**kwargs)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance
    
    def save(self, session):
        """
        Save the current instance.
        
        Args:
            session: SQLAlchemy session
        """
        session.add(self)
        session.commit()
        session.refresh(self)
    
    def delete(self, session):
        """
        Delete the current instance.
        
        Args:
            session: SQLAlchemy session
        """
        session.delete(self)
        session.commit()
    
    @classmethod
    def get_by_id(cls, session, record_id):
        """
        Get instance by ID.
        
        Args:
            session: SQLAlchemy session
            record_id: The ID to search for
            
        Returns:
            The instance or None if not found
        """
        return session.query(cls).filter(cls.id == record_id).first()
    
    @classmethod
    def get_all(cls, session, limit: int = None, offset: int = None):
        """
        Get all instances with optional pagination.
        
        Args:
            session: SQLAlchemy session
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of instances
        """
        query = session.query(cls)
        
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
            
        return query.all()


class ActiveRecordModel(BaseModel, ActiveRecordMixin):
    """
    Base model class with active record pattern methods.
    
    Provides convenient class and instance methods for database operations.
    """
    
    __abstract__ = True