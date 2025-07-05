"""
Rate Limiting Middleware

FastAPI middleware for applying rate limits to API endpoints with 
Redis-based tracking and configurable limits per endpoint type.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Tuple
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.rate_limiter import get_rate_limiter, RateLimitRule, RateLimitResult
from app.core.response_formatter import response_formatter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that applies different limits based on endpoint types.
    
    Tracks requests by IP address and user ID (when authenticated) with 
    configurable rate limits per endpoint category.
    """
    
    # Rate limit configurations per endpoint type as specified in PRD
    ENDPOINT_RULES = {
        # Authentication endpoints: 5 requests per minute
        "auth": RateLimitRule(
            key_prefix="rate_limit:api_auth",
            max_attempts=5,
            window_seconds=60,
            lockout_seconds=300,  # 5 minute lockout
            exponential_backoff=False
        ),
        
        # User management endpoints: 60 requests per minute
        "user": RateLimitRule(
            key_prefix="rate_limit:api_user",
            max_attempts=60,
            window_seconds=60,
            lockout_seconds=None,  # No lockout for user endpoints
            exponential_backoff=False
        ),
        
        # Analytics endpoints: 100 requests per minute
        "analytics": RateLimitRule(
            key_prefix="rate_limit:api_analytics",
            max_attempts=100,
            window_seconds=60,
            lockout_seconds=None,  # No lockout for analytics endpoints
            exponential_backoff=False
        ),
        
        # Health check endpoints: 30 requests per minute (reasonable for monitoring)
        "health": RateLimitRule(
            key_prefix="rate_limit:api_health",
            max_attempts=30,
            window_seconds=60,
            lockout_seconds=None,
            exponential_backoff=False
        ),
        
        # General API endpoints: 120 requests per minute (higher default)
        "general": RateLimitRule(
            key_prefix="rate_limit:api_general",
            max_attempts=120,
            window_seconds=60,
            lockout_seconds=None,
            exponential_backoff=False
        )
    }
    
    # Endpoint path to rule mapping
    ENDPOINT_PATTERNS = {
        # Authentication endpoints
        "/api/auth/": "auth",
        "/api/login": "auth",
        "/api/logout": "auth",
        "/api/register": "auth",
        "/api/token": "auth",
        "/api/refresh": "auth",
        "/api/password/": "auth",
        "/api/verify/": "auth",
        "/api/mfa/": "auth",
        
        # User management endpoints
        "/api/users/": "user",
        "/api/profile/": "user",
        "/api/preferences/": "user",
        "/api/avatar/": "user",
        
        # Analytics endpoints
        "/api/analytics/": "analytics",
        "/api/events/": "analytics",
        "/api/progress/": "analytics",
        "/api/metrics/": "analytics",
        
        # Health check endpoints
        "/api/health/": "health",
        "/health": "health",
        
        # Admin endpoints (use auth limits due to sensitivity)
        "/api/admin/": "auth",
        "/api/privacy/": "auth"
    }
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            excluded_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = get_rate_limiter()
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/favicon.ico"
        ]
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response with rate limit headers or error response
        """
        # Skip rate limiting for excluded paths
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Determine endpoint type and get rate limit rule
        endpoint_type = self._get_endpoint_type(request.url.path)
        rule = self.ENDPOINT_RULES.get(endpoint_type, self.ENDPOINT_RULES["general"])
        
        # Get client identifier (IP + user if authenticated)
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        rate_limit_info = self.rate_limiter.check_rate_limit(
            identifier=client_id,
            rule_name=f"api_{endpoint_type}",
            custom_rule=rule
        )
        
        # Handle rate limit exceeded
        if rate_limit_info.result in [RateLimitResult.RATE_LIMITED, RateLimitResult.BLOCKED]:
            return self._create_rate_limit_response(
                rate_limit_info, rule, request
            )
        
        # Record the attempt (for tracking purposes)
        try:
            # Process the request
            start_time = time.time()
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Record successful attempt
            self.rate_limiter.record_attempt(
                identifier=client_id,
                rule_name=f"api_{endpoint_type}",
                success=True,
                custom_rule=rule
            )
            
            # Add rate limit headers to response
            self._add_rate_limit_headers(response, rate_limit_info, rule)
            
            # Add processing time header for monitoring
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}s"
            
            return response
            
        except Exception as e:
            # Record failed attempt on exception
            self.rate_limiter.record_attempt(
                identifier=client_id,
                rule_name=f"api_{endpoint_type}",
                success=False,
                custom_rule=rule
            )
            raise
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Check if request should skip rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if should skip rate limiting
        """
        path = request.url.path
        
        # Skip excluded paths
        if any(excluded in path for excluded in self.excluded_paths):
            return True
        
        # Skip static files
        if path.startswith("/static/") or path.endswith((".css", ".js", ".png", ".jpg", ".ico")):
            return True
        
        return False
    
    def _get_endpoint_type(self, path: str) -> str:
        """
        Determine endpoint type from request path.
        
        Args:
            path: Request path
            
        Returns:
            Endpoint type string
        """
        # Check specific patterns first (most specific to least specific)
        for pattern, endpoint_type in self.ENDPOINT_PATTERNS.items():
            if path.startswith(pattern):
                return endpoint_type
        
        # Default to general for unmatched paths
        return "general"
    
    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique client identifier for rate limiting.
        
        Combines IP address with user ID when available for more accurate tracking.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Unique client identifier string
        """
        # Get IP address (check for forwarded headers)
        ip_address = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP") or
            request.client.host if request.client else "unknown"
        )
        
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        
        if user_id:
            return f"ip:{ip_address}:user:{user_id}"
        else:
            return f"ip:{ip_address}"
    
    def _create_rate_limit_response(
        self, 
        rate_limit_info, 
        rule: RateLimitRule, 
        request: Request
    ) -> JSONResponse:
        """
        Create rate limit exceeded response.
        
        Args:
            rate_limit_info: Rate limit information
            rule: Rate limit rule that was exceeded
            request: FastAPI request object
            
        Returns:
            JSONResponse with rate limit error
        """
        # Extract request ID if available
        request_id = request.headers.get("X-Request-ID")
        
        # Determine error message based on result type
        if rate_limit_info.result == RateLimitResult.BLOCKED:
            message = "Account temporarily blocked due to too many requests"
            error_code = "account_blocked"
        else:
            message = "Rate limit exceeded"
            error_code = "rate_limit_exceeded"
        
        # Create standardized error response
        error_response = response_formatter.error(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=error_code,
            metadata={
                "operation": "rate_limit_check",
                "endpoint_type": self._get_endpoint_type(request.url.path),
                "client_id": self._get_client_identifier(request),
                "rate_limit": {
                    "limit": rule.max_attempts,
                    "window_seconds": rule.window_seconds,
                    "remaining": rate_limit_info.remaining,
                    "reset_time": rate_limit_info.reset_time.isoformat(),
                    "total_attempts": rate_limit_info.total_attempts
                }
            },
            request_id=request_id
        )
        
        # Convert to JSON response
        json_response = response_formatter.to_json_response(
            error_response, 
            status.HTTP_429_TOO_MANY_REQUESTS
        )
        
        # Add rate limit headers
        self._add_rate_limit_headers(json_response, rate_limit_info, rule)
        
        # Add Retry-After header
        if rate_limit_info.retry_after:
            json_response.headers["Retry-After"] = str(rate_limit_info.retry_after)
        
        return json_response
    
    def _add_rate_limit_headers(
        self, 
        response: Response, 
        rate_limit_info, 
        rule: RateLimitRule
    ):
        """
        Add rate limit headers to response.
        
        Args:
            response: Response object to modify
            rate_limit_info: Current rate limit information
            rule: Rate limit rule being applied
        """
        # Standard rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rule.max_attempts)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = str(int(rate_limit_info.reset_time.timestamp()))
        response.headers["X-RateLimit-Window"] = str(rule.window_seconds)
        
        # Additional headers for debugging
        response.headers["X-RateLimit-Type"] = rule.key_prefix.split(":")[-1]
        
        if rate_limit_info.retry_after:
            response.headers["X-RateLimit-Retry-After"] = str(rate_limit_info.retry_after)


def create_rate_limit_middleware(
    excluded_paths: Optional[list] = None
) -> RateLimitMiddleware:
    """
    Create rate limiting middleware with optional configuration.
    
    Args:
        excluded_paths: List of paths to exclude from rate limiting
        
    Returns:
        Configured RateLimitMiddleware instance
    """
    return lambda app: RateLimitMiddleware(app, excluded_paths)