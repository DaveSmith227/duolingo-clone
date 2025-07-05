"""
Health Check API

FastAPI routes for health monitoring, database connectivity checks,
and system status endpoints for the Duolingo clone application.
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import check_database_connection, get_database_info
from app.api.deps import require_development_mode

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    environment: str
    version: str
    uptime_seconds: float


class DatabaseHealthResponse(BaseModel):
    """Database health check response model."""
    status: str
    timestamp: datetime
    database_status: str
    database_info: Dict[str, Any]
    connection_healthy: bool


class SystemHealthResponse(BaseModel):
    """System health check response model."""
    status: str
    timestamp: datetime
    environment: str
    version: str
    uptime_seconds: float
    database: Dict[str, Any]
    services: Dict[str, str]


# Track application start time for uptime calculation
_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def basic_health_check():
    """
    Basic health check endpoint.
    
    Returns basic application status and metadata.
    Useful for load balancers and basic monitoring.
    
    Returns:
        HealthResponse: Basic health status
    """
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=time.time() - _start_time
    )


@router.get("/database", response_model=DatabaseHealthResponse)
async def database_health_check():
    """
    Database connectivity health check.
    
    Tests database connection and returns detailed database status.
    
    Returns:
        DatabaseHealthResponse: Database health status
        
    Raises:
        HTTPException: If database connection fails
    """
    connection_healthy = check_database_connection()
    database_info = get_database_info()
    
    if not connection_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    
    return DatabaseHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        database_status=database_info.get("status", "unknown"),
        database_info=database_info,
        connection_healthy=connection_healthy
    )


@router.get("/system", response_model=SystemHealthResponse)
async def system_health_check():
    """
    Comprehensive system health check.
    
    Tests all system components including database, external services,
    and returns detailed system status.
    
    Returns:
        SystemHealthResponse: Complete system health status
    """
    settings = get_settings()
    
    # Check database
    database_healthy = check_database_connection()
    database_info = get_database_info()
    
    # Check external services (placeholder for future integrations)
    services_status = {
        "redis": "not_configured",  # Placeholder
        "openai": "not_configured" if not settings.openai_api_key else "configured",
    }
    
    # Determine overall system status
    overall_status = "healthy"
    if not database_healthy:
        overall_status = "degraded"
    
    return SystemHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=time.time() - _start_time,
        database={
            "healthy": database_healthy,
            "status": database_info.get("status", "unknown"),
            "info": database_info
        },
        services=services_status
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/Docker deployments.
    
    Returns 200 if application is ready to serve traffic,
    503 if not ready (e.g., database not available).
    
    Returns:
        dict: Simple ready status
        
    Raises:
        HTTPException: If application is not ready
    """
    # Check critical dependencies
    database_healthy = check_database_connection()
    
    if not database_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready - database unavailable"
        )
    
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/Docker deployments.
    
    Returns 200 if application is alive (basic functionality working).
    Should only fail if application needs to be restarted.
    
    Returns:
        dict: Simple alive status
    """
    return {"status": "alive"}


@router.get("/metrics")
async def metrics_endpoint():
    """
    Basic metrics endpoint.
    
    Returns application metrics in a simple format.
    In production, you might want to use Prometheus format.
    
    Returns:
        dict: Application metrics
    """
    settings = get_settings()
    database_info = get_database_info()
    uptime = time.time() - _start_time
    
    return {
        "application_info": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_seconds": uptime
        },
        "database_metrics": {
            "status": database_info.get("status", "unknown"),
            "pool_info": database_info.get("pool_info", {})
        },
        "system_metrics": {
            "timestamp": datetime.utcnow().isoformat(),
            "memory_usage": "not_implemented",  # Placeholder
            "cpu_usage": "not_implemented"      # Placeholder
        }
    }


@router.get("/debug", dependencies=[Depends(require_development_mode)])
async def debug_info():
    """
    Debug information endpoint (development only).
    
    Returns detailed debug information for development purposes.
    Only available in development environment.
    
    Returns:
        dict: Debug information
    """
    settings = get_settings()
    database_info = get_database_info()
    
    return {
        "environment": settings.environment,
        "debug_mode": settings.debug,
        "settings": {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "database_dsn": settings.database_dsn,
            "cors_origins": settings.cors_origins,
            "log_level": settings.log_level
        },
        "database": database_info,
        "uptime_seconds": time.time() - _start_time,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/test-database")
async def test_database_operations():
    """
    Test basic database operations.
    
    Performs basic database operations to verify functionality.
    Useful for integration testing and diagnostics.
    
    Returns:
        dict: Test results
        
    Raises:
        HTTPException: If database operations fail
    """
    try:
        from sqlalchemy import text, create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import get_settings
        from app.core.database import SessionLocal, init_database
        
        # Initialize database if needed
        if SessionLocal is None:
            init_database()
        
        # If still None, create a session directly
        if SessionLocal is None:
            settings = get_settings()
            engine = create_engine(
                settings.database_dsn,
                connect_args={"check_same_thread": False} if settings.database_dsn.startswith("sqlite") else {}
            )
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test database operations
        db = SessionLocal()
        try:
            # Test basic query
            result = db.execute(text("SELECT 1 as test_value")).fetchone()
            test_value = result[0] if result else None
            
            # Test table existence (check if languages table exists)
            table_check = db.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='languages'"
            )).fetchone()
            
            # Count some records
            language_count = db.execute(text("SELECT COUNT(*) FROM languages")).fetchone()
            exercise_type_count = db.execute(text("SELECT COUNT(*) FROM exercise_types")).fetchone()
            achievement_count = db.execute(text("SELECT COUNT(*) FROM achievements")).fetchone()
            
            return {
                "status": "success",
                "test_query": test_value,
                "tables_exist": table_check is not None,
                "record_counts": {
                    "languages": language_count[0] if language_count else 0,
                    "exercise_types": exercise_type_count[0] if exercise_type_count else 0,
                    "achievements": achievement_count[0] if achievement_count else 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database test failed: {str(e)}"
        )