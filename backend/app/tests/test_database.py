"""
Database Integration Tests

Test suite for database connection, session management, and model functionality.
Tests both SQLite (for testing) and PostgreSQL connection handling.
"""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import Column, String, Integer, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.core.database import (
    create_database_engine,
    init_database,
    get_database_session,
    get_db_session,
    create_tables,
    drop_tables,
    check_database_connection,
    get_database_info,
    Base,
    engine,
    SessionLocal
)
from app.models.base import BaseModel, TimestampMixin, SoftDeleteMixin, SoftDeleteModel


class DatabaseTestModel(BaseModel):
    """Test model for database testing."""
    __tablename__ = "test_models"
    
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)


class DatabaseTestSoftDeleteModel(SoftDeleteModel):
    """Test model with soft delete for testing."""
    __tablename__ = "test_soft_delete_models"
    
    name = Column(String(100), nullable=False)


@pytest.fixture
def sqlite_database_url():
    """Provide SQLite database URL for testing."""
    return "sqlite:///test_database.db"


@pytest.fixture
def test_engine(sqlite_database_url):
    """Create test database engine."""
    test_db_engine = create_engine(
        sqlite_database_url,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables for testing
    Base.metadata.create_all(bind=test_db_engine)
    
    yield test_db_engine
    
    # Cleanup
    Base.metadata.drop_all(bind=test_db_engine)
    if os.path.exists("test_database.db"):
        os.remove("test_database.db")


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    TestSessionLocal = sessionmaker(bind=test_engine)
    session = TestSessionLocal()
    
    yield session
    
    session.close()


class TestDatabaseEngine:
    """Test database engine creation and configuration."""
    
    @patch('app.core.database.get_settings')
    def test_create_sqlite_engine(self, mock_get_settings):
        """Test SQLite engine creation."""
        mock_settings = MagicMock()
        mock_settings.database_dsn = "sqlite:///test.db"
        mock_settings.debug = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        engine = create_database_engine()
        
        assert engine is not None
        assert "sqlite" in str(engine.url)
    
    @patch('app.core.database.get_settings')
    def test_create_postgresql_engine_connection_failure(self, mock_get_settings):
        """Test PostgreSQL engine creation with connection failure."""
        mock_settings = MagicMock()
        mock_settings.database_dsn = "postgresql://user:pass@nonexistent:5432/db"
        mock_settings.debug = False
        mock_settings.db_pool_size = 5
        mock_settings.db_max_overflow = 10
        mock_settings.app_name = "Test App"
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(OperationalError):
            create_database_engine()


class TestDatabaseInitialization:
    """Test database initialization functions."""
    
    @patch('app.core.database.create_database_engine')
    def test_init_database_success(self, mock_create_engine):
        """Test successful database initialization."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        # Reset global variables
        import app.core.database as db_module
        db_module.engine = None
        db_module.SessionLocal = None
        
        init_database()
        
        assert db_module.engine is not None
        assert db_module.SessionLocal is not None
    
    @patch('app.core.database.create_database_engine')
    def test_init_database_failure(self, mock_create_engine):
        """Test database initialization failure."""
        mock_create_engine.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception) as exc_info:
            init_database()
        
        assert "Connection failed" in str(exc_info.value)


class TestDatabaseSession:
    """Test database session management."""
    
    def test_get_database_session_not_initialized(self):
        """Test getting session when database not initialized."""
        import app.core.database as db_module
        db_module.SessionLocal = None
        
        session_generator = get_database_session()
        
        with pytest.raises(RuntimeError) as exc_info:
            next(session_generator)
        
        assert "Database not initialized" in str(exc_info.value)
    
    @patch('app.core.database.SessionLocal')
    def test_get_database_session_success(self, mock_session_local):
        """Test successful session creation and cleanup."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        session_generator = get_database_session()
        session = next(session_generator)
        
        assert session == mock_session
        
        # Test cleanup
        try:
            next(session_generator)
        except StopIteration:
            pass
        
        mock_session.close.assert_called_once()
    
    @patch('app.core.database.SessionLocal')
    def test_get_database_session_with_exception(self, mock_session_local):
        """Test session cleanup when exception occurs."""
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session
        
        session_generator = get_database_session()
        session = next(session_generator)
        
        # Simulate exception
        try:
            session_generator.throw(Exception("Test error"))
        except Exception:
            pass
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
    
    def test_get_db_session_context_manager_not_initialized(self):
        """Test context manager when database not initialized."""
        import app.core.database as db_module
        db_module.SessionLocal = None
        
        with pytest.raises(RuntimeError) as exc_info:
            with get_db_session():
                pass
        
        assert "Database not initialized" in str(exc_info.value)


class TestDatabaseOperations:
    """Test database table operations."""
    
    @patch('app.core.database.engine')
    @patch('app.core.database.Base')
    def test_create_tables_success(self, mock_base, mock_engine):
        """Test successful table creation."""
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        create_tables()
        
        mock_metadata.create_all.assert_called_once_with(bind=mock_engine)
    
    def test_create_tables_not_initialized(self):
        """Test table creation when engine not initialized."""
        import app.core.database as db_module
        db_module.engine = None
        
        with pytest.raises(RuntimeError) as exc_info:
            create_tables()
        
        assert "Database engine not initialized" in str(exc_info.value)
    
    @patch('app.core.database.get_settings')
    @patch('app.core.database.engine')
    @patch('app.core.database.Base')
    def test_drop_tables_development(self, mock_base, mock_engine, mock_get_settings):
        """Test table dropping in development environment."""
        mock_settings = MagicMock()
        mock_settings.is_production = False
        mock_get_settings.return_value = mock_settings
        
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        drop_tables()
        
        mock_metadata.drop_all.assert_called_once_with(bind=mock_engine)
    
    @patch('app.core.database.get_settings')
    @patch('app.core.database.engine')
    def test_drop_tables_production_error(self, mock_engine, mock_get_settings):
        """Test table dropping prevention in production."""
        mock_settings = MagicMock()
        mock_settings.is_production = True
        mock_get_settings.return_value = mock_settings
        
        with pytest.raises(RuntimeError) as exc_info:
            drop_tables()
        
        assert "Cannot drop tables in production" in str(exc_info.value)


class TestDatabaseHealthChecks:
    """Test database health check functions."""
    
    def test_check_database_connection_not_initialized(self):
        """Test connection check when engine not initialized."""
        import app.core.database as db_module
        original_engine = db_module.engine
        db_module.engine = None
        
        try:
            result = check_database_connection()
            assert result is False
        finally:
            db_module.engine = original_engine
    
    @patch('app.core.database.engine')
    def test_check_database_connection_success(self, mock_engine):
        """Test successful connection check."""
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        
        result = check_database_connection()
        
        assert result is True
        mock_connection.execute.assert_called_once()
    
    @patch('app.core.database.engine')
    def test_check_database_connection_failure(self, mock_engine):
        """Test connection check failure."""
        mock_engine.connect.side_effect = Exception("Connection failed")
        
        result = check_database_connection()
        
        assert result is False
    
    def test_get_database_info_not_initialized(self):
        """Test getting database info when not initialized."""
        import app.core.database as db_module
        db_module.engine = None
        
        result = get_database_info()
        
        assert result["status"] == "not_initialized"
    
    @patch('app.core.database.engine')
    def test_get_database_info_success(self, mock_engine):
        """Test successful database info retrieval."""
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.__getitem__.return_value = "PostgreSQL 13.0"
        mock_connection.execute.return_value.fetchone.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        
        # Mock pool info
        mock_pool = MagicMock()
        mock_pool.size.return_value = 10
        mock_pool.checkedin.return_value = 8
        mock_pool.checkedout.return_value = 2
        mock_pool.overflow.return_value = 0
        mock_engine.pool = mock_pool
        
        # Mock URL
        mock_url = MagicMock()
        mock_url.render_as_string.return_value = "postgresql://user:***@localhost:5432/db"
        mock_engine.url = mock_url
        
        result = get_database_info()
        
        assert result["status"] == "connected"
        assert "PostgreSQL 13.0" in result["database_version"]
        assert "pool_info" in result
        assert result["pool_info"]["pool_size"] == 10


class TestBaseModelFunctionality:
    """Test base model classes and mixins."""
    
    def test_timestamp_mixin_fields(self, test_session):
        """Test that TimestampMixin adds timestamp fields."""
        test_model = DatabaseTestModel(name="test", value=42)
        test_session.add(test_model)
        test_session.commit()
        
        assert test_model.created_at is not None
        assert test_model.updated_at is not None
        # Allow small time difference between creation and update timestamps
        time_diff = abs((test_model.updated_at - test_model.created_at).total_seconds())
        assert time_diff < 1.0  # Less than 1 second difference
    
    def test_base_model_to_dict(self, test_session):
        """Test BaseModel to_dict method."""
        test_model = DatabaseTestModel(name="test", value=42)
        test_session.add(test_model)
        test_session.commit()
        
        model_dict = test_model.to_dict()
        
        assert "id" in model_dict
        assert model_dict["name"] == "test"
        assert model_dict["value"] == 42
        assert "created_at" in model_dict
        assert "updated_at" in model_dict
    
    def test_base_model_to_dict_exclude_fields(self, test_session):
        """Test BaseModel to_dict with excluded fields."""
        test_model = DatabaseTestModel(name="test", value=42)
        test_session.add(test_model)
        test_session.commit()
        
        model_dict = test_model.to_dict(exclude_fields={"value", "created_at"})
        
        assert "value" not in model_dict
        assert "created_at" not in model_dict
        assert "name" in model_dict
    
    def test_base_model_update_from_dict(self, test_session):
        """Test BaseModel update_from_dict method."""
        test_model = DatabaseTestModel(name="test", value=42)
        test_session.add(test_model)
        test_session.commit()
        
        update_data = {"name": "updated", "value": 100}
        test_model.update_from_dict(update_data)
        
        assert test_model.name == "updated"
        assert test_model.value == 100
    
    def test_soft_delete_mixin(self, test_session):
        """Test SoftDeleteMixin functionality."""
        test_model = DatabaseTestSoftDeleteModel(name="test")
        test_session.add(test_model)
        test_session.commit()
        
        # Initially not deleted
        assert not test_model.is_deleted
        assert test_model.deleted_at is None
        
        # Soft delete
        test_model.soft_delete()
        assert test_model.is_deleted
        assert test_model.deleted_at is not None
        
        # Restore
        test_model.restore()
        assert not test_model.is_deleted
        assert test_model.deleted_at is None
    
    def test_base_model_repr(self, test_session):
        """Test BaseModel string representation."""
        test_model = DatabaseTestModel(name="test", value=42)
        test_session.add(test_model)
        test_session.commit()
        
        repr_str = repr(test_model)
        
        assert "DatabaseTestModel" in repr_str
        assert str(test_model.id) in repr_str
    
    def test_tablename_generation(self):
        """Test automatic table name generation."""
        assert DatabaseTestModel.__tablename__ == "test_models"
        assert DatabaseTestSoftDeleteModel.__tablename__ == "test_soft_delete_models"


class TestDatabaseIntegration:
    """Integration tests for database functionality."""
    
    def test_full_database_workflow_sqlite(self, sqlite_database_url):
        """Test complete database workflow with SQLite."""
        with patch('app.core.database.get_settings') as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.database_dsn = sqlite_database_url
            mock_settings.debug = False
            mock_settings.db_pool_size = 5
            mock_settings.db_max_overflow = 10
            mock_settings.app_name = "Test App"
            mock_get_settings.return_value = mock_settings
            
            # Initialize database
            init_database()
            
            # Create tables
            create_tables()
            
            # Check connection
            assert check_database_connection() is True
            
            # Test session
            session_gen = get_database_session()
            session = next(session_gen)
            
            # Create test record
            test_model = DatabaseTestModel(name="integration_test", value=999)
            session.add(test_model)
            session.commit()
            
            # Verify record
            retrieved = session.query(DatabaseTestModel).filter(DatabaseTestModel.name == "integration_test").first()
            assert retrieved is not None
            assert retrieved.value == 999
            
            # Cleanup session
            session.close()