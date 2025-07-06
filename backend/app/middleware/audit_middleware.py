"""
Audit Middleware for FastAPI

Automatically sets audit context for all requests and logs configuration access.
"""

import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.audit_logger import set_audit_context, clear_audit_context, get_audit_logger


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to set audit context for all requests.
    
    Captures request information and user context for audit logging.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.audit_logger = get_audit_logger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and set audit context."""
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Get client IP
        ip_address = request.client.host if request.client else None
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            ip_address = forwarded_for.split(",")[0].strip()
        
        # Get user agent
        user_agent = request.headers.get("User-Agent", "Unknown")
        
        # Get user info from request state (set by auth middleware)
        user_id = None
        user_email = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            user_email = getattr(request.state.user, "email", None)
        
        # Set audit context
        set_audit_context(
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        finally:
            # Clear audit context after request
            clear_audit_context()


def setup_audit_middleware(app):
    """Setup audit middleware on the FastAPI app."""
    app.add_middleware(AuditMiddleware)