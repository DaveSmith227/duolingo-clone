"""
Standardized Response Formatter

Provides consistent JSON response structure across all API endpoints
with proper error handling, request tracking, and metadata inclusion.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.exceptions import (
    AppException,
    AuthenticationError, 
    AuthorizationError,
    ValidationError,
    NotFoundError,
    RateLimitExceededError,
    ServiceUnavailableError
)


class StandardResponse(BaseModel):
    """Standard response model for all API endpoints."""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable message")
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ResponseFormatter:
    """
    Response formatter utility for creating standardized API responses.
    
    Provides methods for success and error responses with consistent structure,
    proper error code mapping, and metadata inclusion.
    """
    
    # HTTP status code to error code mapping
    ERROR_CODE_MAPPING = {
        400: "bad_request",
        401: "unauthorized", 
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        502: "bad_gateway",
        503: "service_unavailable",
        504: "gateway_timeout"
    }
    
    # Exception to HTTP status code mapping
    EXCEPTION_STATUS_MAPPING = {
        AuthenticationError: status.HTTP_401_UNAUTHORIZED,
        AuthorizationError: status.HTTP_403_FORBIDDEN,
        ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
        NotFoundError: status.HTTP_404_NOT_FOUND,
        RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
        ServiceUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    # User-friendly error messages
    USER_FRIENDLY_MESSAGES = {
        "bad_request": "The request was invalid. Please check your input and try again.",
        "unauthorized": "Authentication required. Please log in to continue.",
        "forbidden": "You don't have permission to access this resource.",
        "not_found": "The requested resource was not found.",
        "conflict": "This resource already exists or conflicts with existing data.",
        "validation_error": "The provided data is invalid. Please check the required fields.",
        "rate_limit_exceeded": "Too many requests. Please wait before trying again.",
        "internal_server_error": "An unexpected error occurred. Please try again later.",
        "service_unavailable": "Service temporarily unavailable. Please try again later."
    }

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """
        Create a standardized success response.
        
        Args:
            data: Response data payload
            message: Optional success message
            metadata: Additional metadata
            request_id: Optional request ID
            
        Returns:
            StandardResponse: Formatted success response
        """
        response_metadata = metadata or {}
        
        # Add response metrics
        response_metadata.update({
            "response_type": "success",
            "api_version": "v1"
        })
        
        return StandardResponse(
            success=True,
            data=data,
            message=message,
            metadata=response_metadata,
            request_id=request_id or str(uuid.uuid4())
        )
    
    @classmethod
    def error(
        cls,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        errors: Optional[List[ErrorDetail]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """
        Create a standardized error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Specific error code
            errors: List of error details
            metadata: Additional metadata
            request_id: Optional request ID
            
        Returns:
            StandardResponse: Formatted error response
        """
        # Determine error code if not provided
        if not error_code:
            error_code = cls.ERROR_CODE_MAPPING.get(status_code, "unknown_error")
        
        # Use user-friendly message if available
        user_message = cls.USER_FRIENDLY_MESSAGES.get(error_code, message)
        
        response_metadata = metadata or {}
        response_metadata.update({
            "response_type": "error",
            "api_version": "v1",
            "status_code": status_code,
            "error_code": error_code
        })
        
        # Format errors
        formatted_errors = None
        if errors:
            formatted_errors = [error.model_dump() if isinstance(error, ErrorDetail) else error for error in errors]
        
        return StandardResponse(
            success=False,
            message=user_message,
            errors=formatted_errors,
            metadata=response_metadata,
            request_id=request_id or str(uuid.uuid4())
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        request_id: Optional[str] = None,
        include_traceback: bool = False
    ) -> StandardResponse:
        """
        Create an error response from an exception.
        
        Args:
            exception: The exception to format
            request_id: Optional request ID
            include_traceback: Whether to include traceback in metadata
            
        Returns:
            StandardResponse: Formatted error response
        """
        # Determine status code based on exception type
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        if isinstance(exception, HTTPException):
            status_code = exception.status_code
            message = exception.detail
        elif type(exception) in cls.EXCEPTION_STATUS_MAPPING:
            status_code = cls.EXCEPTION_STATUS_MAPPING[type(exception)]
            message = str(exception)
        else:
            message = "An unexpected error occurred"
        
        # Determine error code
        error_code = cls.ERROR_CODE_MAPPING.get(status_code, "unknown_error")
        
        # Create metadata
        metadata = {
            "exception_type": type(exception).__name__
        }
        
        if include_traceback:
            import traceback
            metadata["traceback"] = traceback.format_exc()
        
        return cls.error(
            message=message,
            status_code=status_code,
            error_code=error_code,
            metadata=metadata,
            request_id=request_id
        )
    
    @classmethod
    def validation_error(
        cls,
        field_errors: Dict[str, str],
        message: str = "Validation failed",
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """
        Create a validation error response.
        
        Args:
            field_errors: Dictionary of field names to error messages
            message: Overall validation error message
            request_id: Optional request ID
            
        Returns:
            StandardResponse: Formatted validation error response
        """
        errors = [
            ErrorDetail(
                code="validation_error",
                message=error_msg,
                field=field_name
            )
            for field_name, error_msg in field_errors.items()
        ]
        
        return cls.error(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_error",
            errors=errors,
            request_id=request_id
        )
    
    @classmethod
    def paginated_response(
        cls,
        items: List[Any],
        total_count: int,
        page: int,
        page_size: int,
        request_id: Optional[str] = None
    ) -> StandardResponse:
        """
        Create a paginated response.
        
        Args:
            items: List of items for current page
            total_count: Total number of items
            page: Current page number
            page_size: Number of items per page
            request_id: Optional request ID
            
        Returns:
            StandardResponse: Formatted paginated response
        """
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        pagination_metadata = {
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": page + 1 if has_next else None,
                "previous_page": page - 1 if has_previous else None
            }
        }
        
        return cls.success(
            data=items,
            metadata=pagination_metadata,
            request_id=request_id
        )
    
    @classmethod
    def to_json_response(
        cls,
        response: StandardResponse,
        status_code: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """
        Convert StandardResponse to FastAPI JSONResponse.
        
        Args:
            response: StandardResponse to convert
            status_code: HTTP status code
            
        Returns:
            JSONResponse: FastAPI JSON response
        """
        return JSONResponse(
            content=response.model_dump(mode='json'),
            status_code=status_code,
            headers={
                "X-Request-ID": response.request_id,
                "X-Timestamp": response.timestamp.isoformat(),
                "X-API-Version": response.metadata.get("api_version", "v1")
            }
        )


def create_error_handler(formatter: ResponseFormatter):
    """
    Create a FastAPI error handler using the response formatter.
    
    Args:
        formatter: ResponseFormatter instance
        
    Returns:
        Callable error handler function
    """
    async def handle_error(request, exc: Exception):
        """Handle exceptions and return standardized error responses."""
        response = formatter.from_exception(exc)
        
        # Determine status code from metadata
        status_code = response.metadata.get("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return formatter.to_json_response(response, status_code)
    
    return handle_error


# Create default formatter instance
response_formatter = ResponseFormatter()