"""
Database Integration

SQLAlchemy database setup, session management, and connection handling
for the Duolingo clone backend application.
"""

import logging
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Create declarative base for SQLAlchemy models
Base = declarative_base()

# Global variables for database engine and session factory
engine: Optional[object] = None
SessionLocal: Optional[sessionmaker] = None


def create_database_engine():
    """
    Create SQLAlchemy database engine with connection pooling.
    
    Returns:
        SQLAlchemy Engine instance configured for PostgreSQL
    """
    settings = get_settings()
    
    # Engine configuration
    engine_kwargs = {
        "echo": settings.debug,  # Log SQL queries in debug mode
        "pool_pre_ping": True,   # Validate connections before use
        "pool_recycle": 3600,    # Recycle connections every hour
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "connect_args": {
            "connect_timeout": 30,
            "application_name": settings.app_name,
        }
    }
    
    # Use StaticPool for SQLite (testing), NullPool for PostgreSQL with connection pooling
    if settings.database_dsn.startswith("sqlite"):
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,  # Required for SQLite
            }
        })
        # Remove PostgreSQL-specific pool arguments for SQLite
        engine_kwargs.pop("pool_size", None)
        engine_kwargs.pop("max_overflow", None)
    
    try:
        db_engine = create_engine(settings.database_dsn, **engine_kwargs)
        
        # Test the connection
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info(f"Successfully connected to database: {settings.database_dsn.split('@')[-1] if '@' in settings.database_dsn else 'SQLite'}")
        
        return db_engine
    
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating database engine: {e}")
        raise


def init_database():
    """
    Initialize database engine and session factory.
    
    This function should be called once during application startup.
    """
    global engine, SessionLocal
    
    try:
        engine = create_database_engine()
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        SQLAlchemy Session instance
        
    This function is designed to be used with FastAPI's dependency injection system.
    It ensures proper session cleanup even if an exception occurs.
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    db_session = SessionLocal()
    try:
        yield db_session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Yields:
        SQLAlchemy Session instance
        
    Example:
        with get_db_session() as db:
            db.query(User).all()
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    db_session = SessionLocal()
    try:
        yield db_session
        db_session.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


def create_tables():
    """
    Create all database tables defined in models.
    
    This should be called after all models are imported and
    the database engine is initialized.
    """
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_database() first.")
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def drop_tables():
    """
    Drop all database tables.
    
    Warning: This will delete all data! Use only in testing or development.
    """
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_database() first.")
    
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("Cannot drop tables in production environment")
    
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is healthy.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """
    Get database connection information for health checks.
    
    Returns:
        dict: Database connection information
    """
    if engine is None:
        return {"status": "not_initialized"}
    
    try:
        with engine.connect() as conn:
            # Get database version and basic info
            result = conn.execute(text("SELECT version()")).fetchone()
            db_version = result[0] if result else "Unknown"
            
            # Get connection pool info
            pool_info = {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
            }
            
            return {
                "status": "connected",
                "database_version": db_version,
                "pool_info": pool_info,
                "connection_url": engine.url.render_as_string(hide_password=True)
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


# Event listeners for connection pool monitoring
@event.listens_for(pool.Pool, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new database connections."""
    logger.debug("New database connection established")


@event.listens_for(pool.Pool, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkouts from pool."""
    logger.debug("Database connection checked out from pool")


@event.listens_for(pool.Pool, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkins to pool."""
    logger.debug("Database connection returned to pool")