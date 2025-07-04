"""
API Dependencies

FastAPI dependency injection functions for authentication, database sessions,
and other common requirements across API endpoints.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_database_session
from app.core.security import verify_access_token, extract_token_from_header

# HTTP Bearer token security scheme
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.
    
    Yields:
        SQLAlchemy Session instance
    """
    yield from get_database_session()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency to get current authenticated user ID.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID from JWT token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    # Verify the access token
    payload = verify_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    FastAPI dependency to get current user ID if authenticated (optional).
    
    Args:
        credentials: HTTP Bearer token credentials (optional)
        
    Returns:
        User ID from JWT token or None if not authenticated
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    
    # Verify the access token
    payload = verify_access_token(token)
    
    if payload is None:
        return None
    
    return payload.get("sub")


def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency to get full JWT payload of current user.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Full JWT payload dictionary
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    # Verify the access token
    payload = verify_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


def require_admin_role(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> str:
    """
    FastAPI dependency to require admin role.
    
    Args:
        current_user_payload: JWT payload from authenticated user
        
    Returns:
        User ID if user has admin role
        
    Raises:
        HTTPException: If user does not have admin role
    """
    user_roles = current_user_payload.get("roles", [])
    
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user_payload.get("sub")


def require_teacher_role(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> str:
    """
    FastAPI dependency to require teacher role.
    
    Args:
        current_user_payload: JWT payload from authenticated user
        
    Returns:
        User ID if user has teacher role
        
    Raises:
        HTTPException: If user does not have teacher role
    """
    user_roles = current_user_payload.get("roles", [])
    
    if "teacher" not in user_roles and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required"
        )
    
    return current_user_payload.get("sub")


def require_premium_subscription(
    current_user_payload: dict = Depends(get_current_user_payload)
) -> str:
    """
    FastAPI dependency to require premium subscription.
    
    Args:
        current_user_payload: JWT payload from authenticated user
        
    Returns:
        User ID if user has premium subscription
        
    Raises:
        HTTPException: If user does not have premium subscription
    """
    is_premium = current_user_payload.get("is_premium", False)
    
    if not is_premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required"
        )
    
    return current_user_payload.get("sub")


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key for external integrations.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if API key is valid, False otherwise
    """
    # TODO: Implement API key validation logic
    # This could check against database, cache, or external service
    return False


def require_valid_api_key(
    api_key: str = Depends(lambda: None)  # TODO: Extract from header
) -> str:
    """
    FastAPI dependency to require valid API key.
    
    Args:
        api_key: API key from request headers
        
    Returns:
        API key if valid
        
    Raises:
        HTTPException: If API key is invalid
    """
    if not api_key or not validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key


def get_rate_limit_info(
    current_user_id: str = Depends(get_current_user_id)
) -> dict:
    """
    FastAPI dependency to get rate limit information for current user.
    
    Args:
        current_user_id: Current authenticated user ID
        
    Returns:
        Rate limit information dictionary
    """
    # TODO: Implement rate limiting logic
    # This could check Redis cache or database for user's rate limit status
    return {
        "requests_remaining": 1000,
        "reset_time": 3600,  # seconds
        "limit": 1000
    }


def check_rate_limit(
    rate_limit_info: dict = Depends(get_rate_limit_info)
) -> bool:
    """
    FastAPI dependency to check if user has exceeded rate limit.
    
    Args:
        rate_limit_info: Rate limit information for current user
        
    Returns:
        True if within rate limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if rate_limit_info["requests_remaining"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                "X-RateLimit-Remaining": str(rate_limit_info["requests_remaining"]),
                "X-RateLimit-Reset": str(rate_limit_info["reset_time"])
            }
        )
    
    return True


def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
) -> dict:
    """
    FastAPI dependency to get pagination parameters.
    
    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Pagination parameters dictionary
        
    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be greater than 0"
        )
    
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be greater than 0"
        )
    
    if page_size > max_page_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size cannot exceed {max_page_size}"
        )
    
    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "limit": page_size
    }


def get_sorting_params(
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> dict:
    """
    FastAPI dependency to get sorting parameters.
    
    Args:
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')
        
    Returns:
        Sorting parameters dictionary
        
    Raises:
        HTTPException: If sorting parameters are invalid
    """
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sort order must be 'asc' or 'desc'"
        )
    
    return {
        "sort_by": sort_by,
        "sort_order": sort_order
    }


def get_filtering_params(
    status: Optional[str] = None,
    category: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None
) -> dict:
    """
    FastAPI dependency to get filtering parameters.
    
    Args:
        status: Filter by status
        category: Filter by category
        created_after: Filter by creation date (after)
        created_before: Filter by creation date (before)
        
    Returns:
        Filtering parameters dictionary
    """
    filters = {}
    
    if status:
        filters["status"] = status
    if category:
        filters["category"] = category
    if created_after:
        filters["created_after"] = created_after
    if created_before:
        filters["created_before"] = created_before
    
    return filters