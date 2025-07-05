"""
Health Check API

FastAPI routes for health monitoring, database connectivity checks,
Redis connectivity checks, and system status endpoints for the Duolingo clone application.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import check_database_connection, get_database_info
from app.api.deps import require_development_mode
from app.core.response_formatter import response_formatter
from app.services.redis_health_service import get_redis_health_service, RedisHealthStatus

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


class RedisHealthResponse(BaseModel):
    """Redis health check response model."""
    status: str
    timestamp: datetime
    redis_status: str
    is_connected: bool
    response_time_ms: float
    memory_usage: Dict[str, Any]
    connection_info: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class CacheHealthResponse(BaseModel):
    """Cache health check response model."""
    status: str
    timestamp: datetime
    cache_status: str
    is_connected: bool
    response_time_ms: float
    performance_metrics: Dict[str, Any]
    memory_info: Dict[str, Any]
    connection_pool_info: Dict[str, Any]


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: datetime
    environment: str
    version: str
    uptime_seconds: float
    database: Dict[str, Any]
    redis: Dict[str, Any]
    services: Dict[str, str]
    system_metrics: Dict[str, Any]


# Track application start time for uptime calculation
_start_time = time.time()


@router.get("/")
async def basic_health_check(request: Request) -> JSONResponse:
    """
    Basic health check endpoint.
    
    Returns basic application status and metadata.
    Useful for load balancers and basic monitoring.
    
    Returns:
        Standardized JSON response with basic health status
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    settings = get_settings()
    
    health_data = HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=time.time() - _start_time
    )
    
    # Create standardized success response
    standard_response = response_formatter.success(
        data=health_data.model_dump(),
        message="Application is healthy",
        metadata={"operation": "health_check", "check_type": "basic"},
        request_id=request_id
    )
    
    return response_formatter.to_json_response(standard_response, status.HTTP_200_OK)


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


@router.get("/cache", response_model=CacheHealthResponse)
async def cache_health_check(request: Request) -> JSONResponse:
    """
    Redis cache health check endpoint.
    
    Returns detailed Redis performance metrics, connection status,
    and cache performance information.
    
    Returns:
        Standardized JSON response with Redis health status
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    redis_service = get_redis_health_service()
    redis_health = redis_service.check_redis_health()
    
    # Determine overall cache status
    if redis_health.status == RedisHealthStatus.HEALTHY:
        cache_status = "healthy"
        overall_status = "healthy"
    elif redis_health.status == RedisHealthStatus.DEGRADED:
        cache_status = "degraded"
        overall_status = "degraded"
    else:
        cache_status = "unhealthy"
        overall_status = "unhealthy"
    
    cache_data = CacheHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        cache_status=cache_status,
        is_connected=redis_health.is_connected,
        response_time_ms=redis_health.response_time_ms,
        performance_metrics=redis_health.performance_metrics or {},
        memory_info=redis_health.memory_usage or {},
        connection_pool_info=redis_health.connection_info or {}
    )
    
    # Create standardized response
    standard_response = response_formatter.success(
        data=cache_data.model_dump(),
        message=f"Redis cache is {cache_status}",
        metadata={
            "operation": "cache_health_check",
            "check_type": "cache",
            "redis_status": redis_health.status.value,
            "error_message": redis_health.error_message
        },
        request_id=request_id
    )
    
    # Use appropriate status code
    status_code = status.HTTP_200_OK if redis_health.is_connected else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return response_formatter.to_json_response(standard_response, status_code)


@router.get("/system", response_model=SystemHealthResponse)
async def system_health_check():
    """
    Comprehensive system health check.
    
    Tests all system components including database, Redis, external services,
    and returns detailed system status.
    
    Returns:
        SystemHealthResponse: Complete system health status
    """
    settings = get_settings()
    
    # Check database
    database_healthy = check_database_connection()
    database_info = get_database_info()
    
    # Check Redis
    redis_service = get_redis_health_service()
    redis_health = redis_service.check_redis_health()
    redis_healthy = redis_health.is_connected and redis_health.status in [
        RedisHealthStatus.HEALTHY, RedisHealthStatus.DEGRADED
    ]
    
    # Check external services
    services_status = {
        "redis": redis_health.status.value,
        "openai": "not_configured" if not settings.openai_api_key else "configured",
    }
    
    # Determine overall system status
    overall_status = "healthy"
    if not database_healthy:
        overall_status = "degraded"
    if not redis_healthy:
        if overall_status == "healthy":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
    
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


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(request: Request) -> JSONResponse:
    """
    Detailed health check with all system components.
    
    Returns comprehensive health status including database, Redis,
    performance metrics, and system information.
    
    Returns:
        Standardized JSON response with detailed health status
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    settings = get_settings()
    
    # Check database
    database_healthy = check_database_connection()
    database_info = get_database_info()
    
    # Check Redis
    redis_service = get_redis_health_service()
    redis_health = redis_service.check_redis_health()
    redis_healthy = redis_health.is_connected and redis_health.status in [
        RedisHealthStatus.HEALTHY, RedisHealthStatus.DEGRADED
    ]
    
    # Check external services
    services_status = {
        "redis": redis_health.status.value,
        "openai": "not_configured" if not settings.openai_api_key else "configured",
        "supabase": "configured" if settings.has_supabase_config else "not_configured"
    }
    
    # System metrics
    uptime = time.time() - _start_time
    system_metrics = {
        "uptime_seconds": uptime,
        "uptime_human": f"{uptime:.0f}s",
        "redis_response_time_ms": redis_health.response_time_ms,
        "memory_info": redis_health.memory_usage or {},
        "connection_pool_info": redis_health.connection_info or {},
        "cache_performance": redis_health.performance_metrics or {}
    }
    
    # Determine overall system status
    overall_status = "healthy"
    if not database_healthy:
        overall_status = "degraded"
    if not redis_healthy:
        if overall_status == "healthy":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
    
    detailed_data = DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        environment=settings.environment,
        version=settings.app_version,
        uptime_seconds=uptime,
        database={
            "healthy": database_healthy,
            "status": database_info.get("status", "unknown"),
            "info": database_info
        },
        redis={
            "healthy": redis_healthy,
            "status": redis_health.status.value,
            "is_connected": redis_health.is_connected,
            "response_time_ms": redis_health.response_time_ms,
            "memory_usage": redis_health.memory_usage or {},
            "connection_info": redis_health.connection_info or {},
            "performance_metrics": redis_health.performance_metrics or {},
            "error_message": redis_health.error_message,
            "last_checked": redis_health.last_checked.isoformat() if redis_health.last_checked else None
        },
        services=services_status,
        system_metrics=system_metrics
    )
    
    # Create standardized response
    standard_response = response_formatter.success(
        data=detailed_data.model_dump(),
        message=f"System status: {overall_status}",
        metadata={
            "operation": "detailed_health_check",
            "check_type": "detailed",
            "components_checked": ["database", "redis", "external_services"],
            "overall_status": overall_status
        },
        request_id=request_id
    )
    
    return response_formatter.to_json_response(standard_response, status.HTTP_200_OK)


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/Docker deployments.
    
    Returns 200 if application is ready to serve traffic,
    503 if not ready (e.g., database or Redis not available).
    
    Returns:
        dict: Simple ready status
        
    Raises:
        HTTPException: If application is not ready
    """
    # Check critical dependencies
    database_healthy = check_database_connection()
    
    # Check Redis (non-critical for basic functionality but important for rate limiting)
    redis_service = get_redis_health_service()
    redis_health = redis_service.check_redis_health()
    redis_healthy = redis_health.is_connected
    
    if not database_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not ready - database unavailable"
        )
    
    # Redis is considered degraded service, not critical for readiness
    # but we include it in the response for monitoring
    return {
        "status": "ready",
        "database": "healthy" if database_healthy else "unhealthy",
        "redis": redis_health.status.value,
        "overall": "ready"
    }


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
    
    Returns application metrics including Redis cache performance.
    In production, you might want to use Prometheus format.
    
    Returns:
        dict: Application metrics
    """
    settings = get_settings()
    database_info = get_database_info()
    uptime = time.time() - _start_time
    
    # Get Redis metrics
    redis_service = get_redis_health_service()
    redis_health = redis_service.check_redis_health()
    
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
        "redis_metrics": {
            "status": redis_health.status.value,
            "is_connected": redis_health.is_connected,
            "response_time_ms": redis_health.response_time_ms,
            "memory_usage": redis_health.memory_usage or {},
            "performance_metrics": redis_health.performance_metrics or {},
            "connection_info": redis_health.connection_info or {}
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