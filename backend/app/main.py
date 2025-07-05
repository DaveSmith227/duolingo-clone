"""FastAPI Application Entry Point

Main application module that configures and initializes the FastAPI application
for the Duolingo clone backend with comprehensive middleware, error handling,
and monitoring capabilities.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import engine, get_database_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Path: {request.url.path}"
        )
        
        # Add processing time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    try:
        from app.core.database import init_database
        init_database()
        logger.info("Database initialized successfully")
        
        # Test database connection
        db_info = get_database_info()
        logger.info(f"Database connection successful: {db_info.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"Database initialization/connection failed: {e}")
        if settings.is_production:
            raise
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    
    # Close database connections
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Initialize FastAPI application
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI instance
    app = FastAPI(
        title=settings.app_name,
        description="Backend API for the Duolingo clone language learning platform",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Configure middleware
    setup_middleware(app, settings)
    
    # Configure exception handlers
    setup_exception_handlers(app)
    
    # Add routes
    setup_routes(app)
    
    return app


def setup_middleware(app: FastAPI, settings) -> None:
    """Configure application middleware."""
    # Security middleware
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure with actual allowed hosts in production
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ],
        expose_headers=["X-Process-Time"],
    )
    
    # Request logging middleware
    if settings.debug or settings.is_development:
        app.add_middleware(RequestLoggingMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url.path)
                }
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle Starlette HTTP exceptions."""
        logger.warning(
            f"Starlette HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url.path)
                }
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(
            f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "validation_error",
                    "code": 422,
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "path": str(request.url.path)
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(
            f"Unexpected error on {request.method} {request.url.path}: {exc}",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "internal_error",
                    "code": 500,
                    "message": "An unexpected error occurred",
                    "path": str(request.url.path)
                }
            }
        )


def setup_routes(app: FastAPI) -> None:
    """Configure application routes."""
    
    # Include health check router
    from app.api.health import router as health_router
    app.include_router(health_router)
    
    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, Any]:
        """Root endpoint providing basic API information."""
        settings = get_settings()
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "environment": settings.environment,
            "docs_url": "/docs" if settings.debug else None,
            "status": "running"
        }
    
    @app.get("/info", tags=["Info"])
    async def app_info() -> Dict[str, Any]:
        """Application information endpoint."""
        settings = get_settings()
        
        return {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug,
            "python_version": "3.11+",
            "framework": "FastAPI",
            "database": "PostgreSQL/SQLite",
            "features": [
                "JWT Authentication",
                "Password Hashing",
                "Database ORM",
                "API Documentation",
                "Health Monitoring",
                "CORS Support",
                "Request Logging"
            ]
        }


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=settings.debug
    )