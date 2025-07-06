"""
Configuration Health Check Endpoints

Provides endpoints to verify configuration validity, connectivity,
and system health without exposing sensitive configuration data.

Features:
- Configuration validation checks
- External service connectivity tests  
- Database connection verification
- Security configuration validation
- Performance metrics
- Environment-specific health checks
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio
import time
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import redis
import psycopg2
from sqlalchemy import text

from ..core.config import Settings, get_settings
from ..core.database import get_db
from ..core.config_rbac import ConfigRole, get_config_rbac, require_permission, ConfigPermission
from ..services.config_access_service import get_config_access_service
from ..core.audit_logger import get_audit_logger

router = APIRouter(prefix="/config", tags=["configuration"])


class HealthStatus(BaseModel):
    """Health check status model."""
    status: str  # "healthy", "warning", "critical"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    response_time_ms: Optional[float] = None


class ConfigHealthResponse(BaseModel):
    """Configuration health check response."""
    overall_status: str
    environment: str
    checks: Dict[str, HealthStatus]
    summary: Dict[str, int]
    timestamp: datetime
    total_response_time_ms: float


class ServiceHealthResponse(BaseModel):
    """External service health check response."""
    service: str
    status: str
    response_time_ms: float
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


async def check_database_health(settings: Settings) -> HealthStatus:
    """Check database connectivity and basic operations."""
    start_time = time.time()
    
    try:
        # For SQLite, check file access
        if not settings.database_url or "sqlite" in settings.database_url:
            import sqlite3
            import os
            
            db_path = "app.db"  # Default SQLite path
            if os.path.exists(db_path):
                # Try to connect and run a simple query
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                
                status = "healthy"
                message = "SQLite database accessible"
                details = {"type": "sqlite", "path": db_path, "size_mb": round(os.path.getsize(db_path) / 1024 / 1024, 2)}
            else:
                status = "warning"
                message = "SQLite database file not found"
                details = {"type": "sqlite", "path": db_path}
        
        else:
            # For PostgreSQL, check connection
            parsed_url = urlparse(settings.database_url)
            
            conn = psycopg2.connect(
                host=parsed_url.hostname,
                port=parsed_url.port or 5432,
                database=parsed_url.path[1:],  # Remove leading slash
                user=parsed_url.username,
                password=parsed_url.password
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]
            
            conn.close()
            
            status = "healthy"
            message = "PostgreSQL database accessible"
            details = {
                "type": "postgresql",
                "database": db_name,
                "version": version.split()[1] if version else "unknown",
                "host": parsed_url.hostname,
                "port": parsed_url.port or 5432
            }
    
    except Exception as e:
        status = "critical"
        message = f"Database connection failed: {str(e)}"
        details = {"error": str(e), "type": "connection_error"}
    
    response_time = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=status,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=round(response_time, 2)
    )


async def check_redis_health(settings: Settings) -> HealthStatus:
    """Check Redis connectivity and basic operations."""
    start_time = time.time()
    
    try:
        # Build Redis URL
        if hasattr(settings, 'redis_url') and settings.redis_url:
            redis_url = settings.redis_url
        else:
            # Build from individual settings
            redis_host = getattr(settings, 'redis_host', 'localhost')
            redis_port = getattr(settings, 'redis_port', 6379)
            redis_password = getattr(settings, 'redis_password', '')
            redis_db = getattr(settings, 'redis_db', 0)
            
            auth_part = f":{redis_password}@" if redis_password else ""
            redis_url = f"redis://{auth_part}{redis_host}:{redis_port}/{redis_db}"
        
        # Test Redis connection
        redis_client = redis.from_url(redis_url)
        
        # Test basic operations
        test_key = "health_check_test"
        redis_client.set(test_key, "test_value", ex=60)
        value = redis_client.get(test_key)
        redis_client.delete(test_key)
        
        # Get Redis info
        info = redis_client.info()
        
        status = "healthy"
        message = "Redis accessible and functional"
        details = {
            "version": info.get("redis_version", "unknown"),
            "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 1)
        }
        
    except redis.ConnectionError:
        status = "warning"
        message = "Redis connection failed - service may be down"
        details = {"error": "connection_failed", "service": "redis"}
        
    except Exception as e:
        status = "critical"
        message = f"Redis health check failed: {str(e)}"
        details = {"error": str(e), "type": "redis_error"}
    
    response_time = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=status,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=round(response_time, 2)
    )


async def check_configuration_validity(settings: Settings) -> HealthStatus:
    """Check configuration validity and completeness."""
    start_time = time.time()
    
    try:
        issues = []
        warnings = []
        
        # Check required fields based on environment
        if settings.environment == "production":
            # Production-specific checks
            if settings.debug:
                issues.append("DEBUG must be False in production")
            
            if settings.secret_key == "dev-secret-key-change-in-production":
                issues.append("SECRET_KEY must be changed from default value")
            
            if len(settings.secret_key) < 32:
                issues.append("SECRET_KEY must be at least 32 characters")
            
            if not settings.database_url or "sqlite" in settings.database_url:
                warnings.append("Consider using PostgreSQL in production")
            
            if not getattr(settings, 'require_email_verification', False):
                warnings.append("Email verification should be enabled in production")
        
        # Check URL formats
        try:
            if hasattr(settings, 'cors_origins'):
                for origin in settings.cors_origins:
                    if settings.environment == "production" and not origin.startswith("https://"):
                        warnings.append(f"Non-HTTPS CORS origin in production: {origin}")
        except Exception:
            pass
        
        # Check for common misconfigurations
        if hasattr(settings, 'frontend_url'):
            if settings.environment == "production" and settings.frontend_url.startswith("http://"):
                issues.append("Frontend URL should use HTTPS in production")
        
        # Determine status
        if issues:
            status = "critical"
            message = f"Configuration has {len(issues)} critical issues"
            details = {"critical_issues": issues, "warnings": warnings}
        elif warnings:
            status = "warning"
            message = f"Configuration has {len(warnings)} warnings"
            details = {"warnings": warnings}
        else:
            status = "healthy"
            message = "Configuration is valid"
            details = {"environment": settings.environment, "validation": "passed"}
    
    except Exception as e:
        status = "critical"
        message = f"Configuration validation failed: {str(e)}"
        details = {"error": str(e)}
    
    response_time = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=status,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=round(response_time, 2)
    )


async def check_security_configuration(settings: Settings) -> HealthStatus:
    """Check security configuration and compliance."""
    start_time = time.time()
    
    try:
        security_issues = []
        security_warnings = []
        
        # Check password policy
        min_length = getattr(settings, 'password_min_length', 8)
        if min_length < 8:
            security_issues.append("Password minimum length should be at least 8")
        
        # Check session configuration
        if hasattr(settings, 'session_expire_days'):
            if settings.session_expire_days > 90:
                security_warnings.append("Session expiry longer than 90 days")
        
        # Check rate limiting
        if not getattr(settings, 'rate_limiting_enabled', True):
            if settings.environment == "production":
                security_issues.append("Rate limiting should be enabled in production")
            else:
                security_warnings.append("Rate limiting is disabled")
        
        # Check CSRF protection
        if not getattr(settings, 'csrf_protection_enabled', True):
            security_issues.append("CSRF protection should be enabled")
        
        # Check JWT configuration
        if hasattr(settings, 'access_token_expire_minutes'):
            if settings.access_token_expire_minutes > 60:
                security_warnings.append("Access token expiry longer than 60 minutes")
        
        # Determine status
        if security_issues:
            status = "critical"
            message = f"Security configuration has {len(security_issues)} critical issues"
            details = {"critical_issues": security_issues, "warnings": security_warnings}
        elif security_warnings:
            status = "warning"
            message = f"Security configuration has {len(security_warnings)} warnings"
            details = {"warnings": security_warnings}
        else:
            status = "healthy"
            message = "Security configuration is compliant"
            details = {"compliance": "passed"}
    
    except Exception as e:
        status = "critical"
        message = f"Security validation failed: {str(e)}"
        details = {"error": str(e)}
    
    response_time = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=status,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=round(response_time, 2)
    )


async def check_external_services(settings: Settings) -> HealthStatus:
    """Check external service connectivity."""
    start_time = time.time()
    
    services_status = {}
    overall_status = "healthy"
    
    try:
        # Check Supabase connectivity
        if hasattr(settings, 'supabase_url') and settings.supabase_url:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{settings.supabase_url}/rest/v1/", timeout=5.0)
                    if response.status_code in [200, 401]:  # 401 is expected without auth
                        services_status["supabase"] = "healthy"
                    else:
                        services_status["supabase"] = "warning"
                        overall_status = "warning"
            except Exception:
                services_status["supabase"] = "critical"
                overall_status = "critical"
        
        # Check OpenAI connectivity (if configured)
        if hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key != "":
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
                    response = await client.get("https://api.openai.com/v1/models", headers=headers, timeout=5.0)
                    if response.status_code == 200:
                        services_status["openai"] = "healthy"
                    else:
                        services_status["openai"] = "warning"
                        overall_status = "warning"
            except Exception:
                services_status["openai"] = "critical"
                overall_status = "critical"
        
        message = f"External services check completed - {len(services_status)} services tested"
        details = {"services": services_status, "tested_count": len(services_status)}
        
    except Exception as e:
        overall_status = "critical"
        message = f"External services check failed: {str(e)}"
        details = {"error": str(e)}
    
    response_time = (time.time() - start_time) * 1000
    
    return HealthStatus(
        status=overall_status,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc),
        response_time_ms=round(response_time, 2)
    )


@router.get("/health", response_model=ConfigHealthResponse)
async def get_configuration_health(
    settings: Settings = Depends(get_settings)
) -> ConfigHealthResponse:
    """
    Get comprehensive configuration health status.
    
    Performs various health checks including:
    - Configuration validation
    - Database connectivity
    - Redis connectivity
    - Security compliance
    - External service connectivity
    
    Returns detailed health status without exposing sensitive data.
    """
    start_time = time.time()
    
    # Run all health checks concurrently
    health_checks = await asyncio.gather(
        check_configuration_validity(settings),
        check_database_health(settings),
        check_redis_health(settings),
        check_security_configuration(settings),
        check_external_services(settings),
        return_exceptions=True
    )
    
    # Map results
    checks = {
        "configuration": health_checks[0] if not isinstance(health_checks[0], Exception) else 
                        HealthStatus(status="critical", message="Configuration check failed", timestamp=datetime.now(timezone.utc)),
        "database": health_checks[1] if not isinstance(health_checks[1], Exception) else 
                   HealthStatus(status="critical", message="Database check failed", timestamp=datetime.now(timezone.utc)),
        "redis": health_checks[2] if not isinstance(health_checks[2], Exception) else 
               HealthStatus(status="critical", message="Redis check failed", timestamp=datetime.now(timezone.utc)),
        "security": health_checks[3] if not isinstance(health_checks[3], Exception) else 
                   HealthStatus(status="critical", message="Security check failed", timestamp=datetime.now(timezone.utc)),
        "external_services": health_checks[4] if not isinstance(health_checks[4], Exception) else 
                           HealthStatus(status="critical", message="External services check failed", timestamp=datetime.now(timezone.utc))
    }
    
    # Calculate summary
    summary = {"healthy": 0, "warning": 0, "critical": 0}
    for check in checks.values():
        summary[check.status] += 1
    
    # Determine overall status
    if summary["critical"] > 0:
        overall_status = "critical"
    elif summary["warning"] > 0:
        overall_status = "warning"
    else:
        overall_status = "healthy"
    
    total_response_time = (time.time() - start_time) * 1000
    
    return ConfigHealthResponse(
        overall_status=overall_status,
        environment=settings.environment,
        checks=checks,
        summary=summary,
        timestamp=datetime.now(timezone.utc),
        total_response_time_ms=round(total_response_time, 2)
    )


@router.get("/health/quick", response_model=Dict[str, Any])
async def get_quick_health_check(
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Quick health check for load balancers and monitoring systems.
    
    Returns basic health status without detailed checks.
    """
    start_time = time.time()
    
    try:
        # Basic configuration validation
        if not settings:
            raise ValueError("Settings not loaded")
        
        # Check if we can import essential modules
        from ..core.database import get_db
        
        status = "healthy"
        message = "Service is operational"
        
    except Exception as e:
        status = "critical"
        message = f"Service health check failed: {str(e)}"
    
    response_time = (time.time() - start_time) * 1000
    
    return {
        "status": status,
        "message": message,
        "environment": settings.environment if settings else "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_time_ms": round(response_time, 2)
    }


@router.get("/health/services", response_model=List[ServiceHealthResponse])
@require_permission(ConfigPermission.AUDIT_VIEW)
async def get_services_health(
    settings: Settings = Depends(get_settings)
) -> List[ServiceHealthResponse]:
    """
    Detailed health check for individual external services.
    
    Requires admin permissions as it may expose service configuration details.
    """
    services = []
    
    # Database health
    db_health = await check_database_health(settings)
    services.append(ServiceHealthResponse(
        service="database",
        status=db_health.status,
        response_time_ms=db_health.response_time_ms or 0,
        details=db_health.details,
        timestamp=db_health.timestamp
    ))
    
    # Redis health
    redis_health = await check_redis_health(settings)
    services.append(ServiceHealthResponse(
        service="redis",
        status=redis_health.status,
        response_time_ms=redis_health.response_time_ms or 0,
        details=redis_health.details,
        timestamp=redis_health.timestamp
    ))
    
    # External services health
    external_health = await check_external_services(settings)
    services.append(ServiceHealthResponse(
        service="external_apis",
        status=external_health.status,
        response_time_ms=external_health.response_time_ms or 0,
        details=external_health.details,
        timestamp=external_health.timestamp
    ))
    
    return services


@router.get("/health/security", response_model=HealthStatus)
@require_permission(ConfigPermission.AUDIT_VIEW)
async def get_security_health(
    settings: Settings = Depends(get_settings)
) -> HealthStatus:
    """
    Detailed security configuration health check.
    
    Requires admin permissions as it may expose security configuration details.
    """
    return await check_security_configuration(settings)


@router.post("/health/validate", response_model=Dict[str, Any])
@require_permission(ConfigPermission.VALIDATE)
async def validate_configuration_changes(
    config_updates: Dict[str, Any],
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Validate proposed configuration changes without applying them.
    
    Useful for testing configuration changes before deployment.
    """
    start_time = time.time()
    
    try:
        # Create a temporary settings object with proposed changes
        current_config = settings.model_dump()
        
        # Apply proposed changes
        for key, value in config_updates.items():
            if hasattr(settings, key):
                current_config[key] = value
            else:
                raise ValueError(f"Unknown configuration field: {key}")
        
        # Validate the new configuration
        try:
            from ..core.config import Settings
            test_settings = Settings(**current_config)
            
            # Run validation checks on the test configuration
            validation_result = await check_configuration_validity(test_settings)
            security_result = await check_security_configuration(test_settings)
            
            if validation_result.status == "critical" or security_result.status == "critical":
                status = "invalid"
                issues = []
                
                if validation_result.details and "critical_issues" in validation_result.details:
                    issues.extend(validation_result.details["critical_issues"])
                
                if security_result.details and "critical_issues" in security_result.details:
                    issues.extend(security_result.details["critical_issues"])
                
                message = f"Configuration validation failed: {len(issues)} critical issues"
                details = {"issues": issues}
            else:
                status = "valid"
                message = "Configuration changes are valid"
                details = {
                    "validation_warnings": validation_result.details.get("warnings", []) if validation_result.details else [],
                    "security_warnings": security_result.details.get("warnings", []) if security_result.details else []
                }
                
        except Exception as e:
            status = "invalid"
            message = f"Configuration validation error: {str(e)}"
            details = {"error": str(e)}
    
    except Exception as e:
        status = "error"
        message = f"Validation process failed: {str(e)}"
        details = {"error": str(e)}
    
    response_time = (time.time() - start_time) * 1000
    
    return {
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response_time_ms": round(response_time, 2)
    }