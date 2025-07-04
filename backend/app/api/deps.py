"""API Dependencies

FastAPI dependency injection utilities for authentication, database sessions,
and other common requirements across API endpoints.
"""

import logging
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_database_session
from app.core.security import verify_access_token, extract_token_from_header

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme for JWT authentication
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Database session
    """
    try:
        db = next(get_database_session())
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Dependency to get current authenticated user ID.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID from validated JWT token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from authorization header
    token = extract_token_from_header(f"Bearer {credentials.credentials}")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify access token
    payload = verify_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Authenticated user: {user_id}")
    return user_id


def get_current_user_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to get current authenticated user's full token payload.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        Full JWT token payload
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from authorization header
    token = extract_token_from_header(f"Bearer {credentials.credentials}")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify access token
    payload = verify_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"Authenticated user payload: {payload.get('sub', 'unknown')}")
    return payload


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Dependency to get current user ID if authenticated, None otherwise.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        # Extract token from authorization header
        token = extract_token_from_header(f"Bearer {credentials.credentials}")
        
        if not token:
            return None
        
        # Verify access token
        payload = verify_access_token(token)
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        logger.debug(f"Optional authenticated user: {user_id}")
        return user_id
    
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


def require_admin_role(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> dict:
    """
    Dependency to require admin role.
    
    Args:
        current_user_payload: Current user's token payload
        
    Returns:
        User payload if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    user_role = current_user_payload.get("role", "user")
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    logger.debug(f"Admin access granted for user: {current_user_payload.get('sub')}")
    return current_user_payload


def require_teacher_role(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> dict:
    """
    Dependency to require teacher role or higher.
    
    Args:
        current_user_payload: Current user's token payload
        
    Returns:
        User payload if teacher or admin
        
    Raises:
        HTTPException: If user is not teacher or admin
    """
    user_role = current_user_payload.get("role", "user")
    
    if user_role not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role or higher required"
        )
    
    logger.debug(f"Teacher access granted for user: {current_user_payload.get('sub')}")
    return current_user_payload


def require_premium_user(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> dict:
    """
    Dependency to require premium user status.
    
    Args:
        current_user_payload: Current user's token payload
        
    Returns:
        User payload if premium user
        
    Raises:
        HTTPException: If user is not premium
    """
    user_role = current_user_payload.get("role", "user")
    is_premium = current_user_payload.get("is_premium", False)
    
    # Admin and teacher users have premium access
    if user_role in ["admin", "teacher"] or is_premium:
        logger.debug(f"Premium access granted for user: {current_user_payload.get('sub')}")
        return current_user_payload
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Premium subscription required"
    )


def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
) -> dict:
    """
    Dependency to get pagination parameters.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Dictionary with pagination parameters
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater"
        )
    
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be 1 or greater"
        )
    
    if page_size > max_page_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size cannot exceed {max_page_size}"
        )
    
    # Calculate offset for database queries
    offset = (page - 1) * page_size
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": offset,
        "limit": page_size
    }


def get_current_settings():
    """
    Dependency to get current application settings.
    
    Returns:
        Application settings
    """
    return get_settings()


def require_development_mode(
    settings = Depends(get_current_settings)
):
    """
    Dependency to require development mode.
    
    Args:
        settings: Application settings
        
    Raises:
        HTTPException: If not in development mode
    """
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in this environment"
        )
    
    return settings


def validate_api_key(api_key: Optional[str] = None) -> bool:
    """
    Dependency to validate API key for external integrations.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    settings = get_settings()
    
    # In a real application, you would validate against a database
    # For now, we'll use a simple check against environment variable
    if api_key != getattr(settings, 'api_key', None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return True


class RateLimitDependency:
    """
    Rate limiting dependency class.
    
    This is a placeholder for implementing rate limiting.
    In a production system, you would integrate with Redis or similar.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def __call__(self, request, user_id: Optional[str] = None):
        """
        Rate limiting check.
        
        Args:
            request: FastAPI request object
            user_id: Optional user ID for user-based rate limiting
            
        Returns:
            True if request is within rate limit
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # TODO: Implement actual rate limiting logic with Redis
        # For now, this is a placeholder that always allows requests
        
        # You would implement logic here to:
        # 1. Get client IP or user ID
        # 2. Check Redis for request count in time window
        # 3. Increment counter
        # 4. Return or raise exception based on limit
        
        return True


# Pre-configured rate limit dependencies
rate_limit_strict = RateLimitDependency(max_requests=10, window_seconds=60)
rate_limit_moderate = RateLimitDependency(max_requests=50, window_seconds=60)
rate_limit_generous = RateLimitDependency(max_requests=100, window_seconds=60)