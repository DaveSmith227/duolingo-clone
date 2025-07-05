"""
Security Middleware

FastAPI middleware for security headers, CSRF protection, and authentication security.
"""

import logging
import secrets
from typing import Callable, Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.services.cookie_manager import get_cookie_manager

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses.
    
    Adds standard security headers including HSTS, CSP, X-Frame-Options, etc.
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        try:
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        headers = self._get_security_headers()
        
        for header, value in headers.items():
            response.headers[header] = value
    
    def _get_security_headers(self) -> dict:
        """Get security headers based on environment."""
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            
            # Content Security Policy
            "Content-Security-Policy": self._get_csp_header(),
        }
        
        # Add HSTS in production
        if self.settings.is_production:
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return headers
    
    def _get_csp_header(self) -> str:
        """Get Content Security Policy header."""
        if self.settings.is_development:
            # More permissive CSP for development
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' ws: wss:; "
                "font-src 'self' data:; "
                "frame-ancestors 'none';"
            )
        else:
            # Strict CSP for production
            return (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self';"
            )


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware for authentication endpoints.
    
    Validates CSRF tokens for state-changing requests to authentication endpoints.
    """
    
    PROTECTED_PATHS = [
        "/api/auth/login",
        "/api/auth/register", 
        "/api/auth/logout",
        "/api/auth/refresh",
        "/api/auth/password-reset",
        "/api/auth/password-change",
        "/api/auth/profile",
    ]
    
    SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"]
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
        self.cookie_manager = get_cookie_manager()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token for protected endpoints."""
        try:
            # Skip CSRF validation for safe methods
            if request.method in self.SAFE_METHODS:
                return await call_next(request)
            
            # Skip CSRF validation for non-protected paths
            if not self._is_protected_path(request.url.path):
                return await call_next(request)
            
            # Skip CSRF validation in development if disabled
            if self.settings.is_development and not getattr(self.settings, 'csrf_protection_enabled', True):
                return await call_next(request)
            
            # Validate CSRF token
            if not self.cookie_manager.validate_csrf_token(request):
                logger.warning(f"CSRF validation failed for {request.url.path} from {request.client.host}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token validation failed"
                )
            
            return await call_next(request)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"CSRF middleware error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    def _is_protected_path(self, path: str) -> bool:
        """Check if path requires CSRF protection."""
        return any(path.startswith(protected_path) for protected_path in self.PROTECTED_PATHS)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for authentication endpoints.
    
    Applies rate limiting to authentication endpoints based on IP address and user.
    """
    
    RATE_LIMITED_PATHS = {
        "/api/auth/login": "login_attempts",
        "/api/auth/register": "registration", 
        "/api/auth/password-reset": "password_reset",
        "/api/auth/refresh": "token_refresh",
    }
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
        
        # Import here to avoid circular imports
        from app.services.rate_limiter import get_rate_limiter
        self.rate_limiter = get_rate_limiter() if self.settings.rate_limiting_enabled else None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to protected endpoints."""
        try:
            # Skip if rate limiting is disabled
            if not self.rate_limiter:
                return await call_next(request)
            
            # Check if path needs rate limiting
            rule_name = self._get_rate_limit_rule(request.url.path)
            if not rule_name:
                return await call_next(request)
            
            # Get identifier (IP address)
            identifier = self._get_client_identifier(request)
            
            # Check rate limit
            rate_limit_info = self.rate_limiter.check_rate_limit(identifier, rule_name)
            
            # Add rate limit headers to response
            response = await call_next(request)
            self._add_rate_limit_headers(response, rate_limit_info)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}")
            # Continue processing if rate limiting fails
            return await call_next(request)
    
    def _get_rate_limit_rule(self, path: str) -> Optional[str]:
        """Get rate limit rule for path."""
        for rate_limited_path, rule_name in self.RATE_LIMITED_PATHS.items():
            if path.startswith(rate_limited_path):
                return rule_name
        return None
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_info) -> None:
        """Add rate limit headers to response."""
        from app.services.rate_limiter import RateLimitResult
        
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_info.reset_time.timestamp()))
        
        if rate_limit_info.result == RateLimitResult.RATE_LIMITED:
            response.headers["Retry-After"] = str(rate_limit_info.retry_after or 0)
        
        if rate_limit_info.result == RateLimitResult.BLOCKED:
            response.headers["X-RateLimit-Blocked"] = "true"
            if rate_limit_info.retry_after:
                response.headers["Retry-After"] = str(rate_limit_info.retry_after)


class AuthenticationSecurityMiddleware(BaseHTTPMiddleware):
    """
    Authentication security middleware.
    
    Handles authentication security features like session validation,
    suspicious activity detection, and security logging.
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process authentication security."""
        try:
            # Add request timestamp for audit logging
            request.state.request_start_time = datetime.now(timezone.utc)
            
            # Add client information
            request.state.client_ip = self._get_client_ip(request)
            request.state.user_agent = request.headers.get("User-Agent", "")
            
            # Process request
            response = await call_next(request)
            
            # Log authentication events if needed
            await self._log_authentication_event(request, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Authentication security middleware error: {str(e)}")
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_authentication_event(self, request: Request, response: Response) -> None:
        """Log authentication events for audit trail."""
        # Only log authentication-related endpoints
        if not request.url.path.startswith("/api/auth/"):
            return
        
        # Don't log successful GET requests (they're not security events)
        if request.method == "GET" and response.status_code < 400:
            return
        
        event_data = {
            "timestamp": getattr(request.state, "request_start_time", datetime.now(timezone.utc)),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": getattr(request.state, "client_ip", "unknown"),
            "user_agent": getattr(request.state, "user_agent", ""),
            "success": response.status_code < 400
        }
        
        # Log based on severity
        if response.status_code >= 400:
            logger.warning(f"Authentication event: {event_data}")
        else:
            logger.info(f"Authentication event: {event_data}")


def add_security_middleware(app: FastAPI) -> None:
    """
    Add all security middleware to FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Add middleware in reverse order (last added runs first)
    
    # Authentication security (runs last, closest to route)
    app.add_middleware(AuthenticationSecurityMiddleware)
    
    # Rate limiting
    app.add_middleware(RateLimitMiddleware)
    
    # CSRF protection  
    app.add_middleware(CSRFProtectionMiddleware)
    
    # Security headers (runs first, outermost)
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info("Security middleware added to application")


# Utility functions for manual security checks

def validate_origin(request: Request, allowed_origins: Optional[List[str]] = None) -> bool:
    """
    Validate request origin against allowed origins.
    
    Args:
        request: FastAPI Request object
        allowed_origins: List of allowed origins (defaults to CORS settings)
        
    Returns:
        True if origin is allowed
    """
    if not allowed_origins:
        settings = get_settings()
        allowed_origins = settings.cors_origins
    
    origin = request.headers.get("Origin") or request.headers.get("Referer", "")
    
    if not origin:
        return False
    
    # Extract domain from origin
    if "://" in origin:
        origin = origin.split("://", 1)[1]
    if "/" in origin:
        origin = origin.split("/", 1)[0]
    
    return any(
        allowed_origin in origin or origin in allowed_origin
        for allowed_origin in allowed_origins
    )


def generate_csrf_token() -> str:
    """
    Generate a secure CSRF token.
    
    Returns:
        URL-safe CSRF token
    """
    return secrets.token_urlsafe(32)


def is_secure_context(request: Request) -> bool:
    """
    Check if request is in a secure context (HTTPS).
    
    Args:
        request: FastAPI Request object
        
    Returns:
        True if request is secure
    """
    # Check if connection is HTTPS
    if request.url.scheme == "https":
        return True
    
    # Check for proxy headers indicating HTTPS
    if request.headers.get("X-Forwarded-Proto") == "https":
        return True
    
    if request.headers.get("X-Forwarded-SSL") == "on":
        return True
    
    # Allow insecure in development
    settings = get_settings()
    if settings.is_development:
        return True
    
    return False