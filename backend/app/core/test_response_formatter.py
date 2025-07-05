"""
Unit Tests for Response Formatter

Comprehensive test suite for the standardized response formatting utility
covering success responses, error handling, validation, and edge cases.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.core.response_formatter import (
    ResponseFormatter,
    StandardResponse,
    ErrorDetail,
    response_formatter,
    create_error_handler
)
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    NotFoundError,
    RateLimitExceededError,
    ServiceUnavailableError
)


class TestStandardResponse:
    """Test StandardResponse model."""
    
    def test_standard_response_creation(self):
        """Test basic StandardResponse creation."""
        response = StandardResponse(
            success=True,
            data={"test": "data"},
            message="Test message"
        )
        
        assert response.success is True
        assert response.data == {"test": "data"}
        assert response.message == "Test message"
        assert response.errors is None
        assert isinstance(response.metadata, dict)
        assert isinstance(response.timestamp, datetime)
        assert isinstance(response.request_id, str)
    
    def test_standard_response_with_errors(self):
        """Test StandardResponse with error details."""
        errors = [{"code": "test_error", "message": "Test error message"}]
        
        response = StandardResponse(
            success=False,
            errors=errors,
            message="Validation failed"
        )
        
        assert response.success is False
        assert response.errors == errors
        assert response.message == "Validation failed"
        assert response.data is None


class TestErrorDetail:
    """Test ErrorDetail model."""
    
    def test_error_detail_creation(self):
        """Test ErrorDetail creation with all fields."""
        error = ErrorDetail(
            code="validation_error",
            message="Field is required",
            field="email",
            details={"constraint": "not_null"}
        )
        
        assert error.code == "validation_error"
        assert error.message == "Field is required"
        assert error.field == "email"
        assert error.details == {"constraint": "not_null"}
    
    def test_error_detail_minimal(self):
        """Test ErrorDetail with minimal required fields."""
        error = ErrorDetail(
            code="general_error",
            message="Something went wrong"
        )
        
        assert error.code == "general_error"
        assert error.message == "Something went wrong"
        assert error.field is None
        assert error.details is None


class TestResponseFormatter:
    """Test ResponseFormatter utility methods."""
    
    @pytest.fixture
    def formatter(self):
        """Create ResponseFormatter instance."""
        return ResponseFormatter()
    
    def test_success_response_basic(self, formatter):
        """Test basic success response creation."""
        response = formatter.success(
            data={"user_id": "123", "name": "Test User"},
            message="User retrieved successfully"
        )
        
        assert response.success is True
        assert response.data == {"user_id": "123", "name": "Test User"}
        assert response.message == "User retrieved successfully"
        assert response.errors is None
        assert "response_type" in response.metadata
        assert response.metadata["response_type"] == "success"
        assert "api_version" in response.metadata
        assert isinstance(response.timestamp, datetime)
        assert isinstance(response.request_id, str)
    
    def test_success_response_with_metadata(self, formatter):
        """Test success response with custom metadata."""
        custom_metadata = {"operation": "user_creation", "user_id": "456"}
        
        response = formatter.success(
            data={"created": True},
            message="User created successfully",
            metadata=custom_metadata
        )
        
        assert response.success is True
        assert response.data == {"created": True}
        assert response.metadata["operation"] == "user_creation"
        assert response.metadata["user_id"] == "456"
        assert response.metadata["response_type"] == "success"
        assert response.metadata["api_version"] == "v1"
    
    def test_success_response_with_custom_request_id(self, formatter):
        """Test success response with custom request ID."""
        custom_request_id = "custom-req-123"
        
        response = formatter.success(
            data={"test": "data"},
            request_id=custom_request_id
        )
        
        assert response.success is True
        assert response.request_id == custom_request_id
    
    def test_error_response_basic(self, formatter):
        """Test basic error response creation."""
        response = formatter.error(
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
        
        assert response.success is False
        assert response.message == "The requested resource was not found."  # User-friendly message
        assert response.data is None
        assert "error_code" in response.metadata
        assert response.metadata["error_code"] == "not_found"
        assert response.metadata["status_code"] == 404
        assert response.metadata["response_type"] == "error"
    
    def test_error_response_with_custom_code(self, formatter):
        """Test error response with custom error code."""
        response = formatter.error(
            message="Invalid user data",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="invalid_user_data"
        )
        
        assert response.success is False
        assert response.metadata["error_code"] == "invalid_user_data"
        assert response.metadata["status_code"] == 400
    
    def test_error_response_with_errors_list(self, formatter):
        """Test error response with detailed errors."""
        errors = [
            ErrorDetail(
                code="validation_error",
                message="Email is required",
                field="email"
            ),
            ErrorDetail(
                code="validation_error", 
                message="Password must be at least 8 characters",
                field="password"
            )
        ]
        
        response = formatter.error(
            message="Validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=errors
        )
        
        assert response.success is False
        assert len(response.errors) == 2
        assert response.errors[0]["code"] == "validation_error"
        assert response.errors[0]["field"] == "email"
        assert response.errors[1]["field"] == "password"
    
    def test_from_exception_http_exception(self, formatter):
        """Test error response creation from HTTPException."""
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
        
        response = formatter.from_exception(exception)
        
        assert response.success is False
        assert response.message == "Authentication required. Please log in to continue."  # User-friendly
        assert response.metadata["status_code"] == 401
        assert response.metadata["error_code"] == "unauthorized"
        assert response.metadata["exception_type"] == "HTTPException"
    
    def test_from_exception_custom_exceptions(self, formatter):
        """Test error response creation from custom exceptions."""
        # Test AuthenticationError
        auth_error = AuthenticationError("Invalid credentials")
        response = formatter.from_exception(auth_error)
        
        assert response.success is False
        assert response.metadata["status_code"] == 401
        assert response.metadata["error_code"] == "unauthorized"
        
        # Test ValidationError
        validation_error = ValidationError("Invalid input data")
        response = formatter.from_exception(validation_error)
        
        assert response.success is False
        assert response.metadata["status_code"] == 422
        assert response.metadata["error_code"] == "validation_error"
        
        # Test NotFoundError
        not_found_error = NotFoundError("Resource not found")
        response = formatter.from_exception(not_found_error)
        
        assert response.success is False
        assert response.metadata["status_code"] == 404
        assert response.metadata["error_code"] == "not_found"
    
    def test_from_exception_unknown_exception(self, formatter):
        """Test error response creation from unknown exception."""
        exception = RuntimeError("Unexpected error")
        
        response = formatter.from_exception(exception)
        
        assert response.success is False
        assert response.message == "An unexpected error occurred. Please try again later."
        assert response.metadata["status_code"] == 500
        assert response.metadata["error_code"] == "internal_server_error"
        assert response.metadata["exception_type"] == "RuntimeError"
    
    def test_validation_error_response(self, formatter):
        """Test validation error response creation."""
        field_errors = {
            "email": "Email format is invalid",
            "password": "Password is too short",
            "age": "Age must be a positive number"
        }
        
        response = formatter.validation_error(
            field_errors=field_errors,
            message="Input validation failed"
        )
        
        assert response.success is False
        assert response.message == "The provided data is invalid. Please check the required fields."
        assert len(response.errors) == 3
        
        # Check that all field errors are included
        error_fields = [error["field"] for error in response.errors]
        assert "email" in error_fields
        assert "password" in error_fields
        assert "age" in error_fields
        
        # Verify error structure
        email_error = next(error for error in response.errors if error["field"] == "email")
        assert email_error["code"] == "validation_error"
        assert email_error["message"] == "Email format is invalid"
    
    def test_paginated_response(self, formatter):
        """Test paginated response creation."""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        
        response = formatter.paginated_response(
            items=items,
            total_count=50,
            page=2,
            page_size=10
        )
        
        assert response.success is True
        assert response.data == items
        assert "pagination" in response.metadata
        
        pagination = response.metadata["pagination"]
        assert pagination["current_page"] == 2
        assert pagination["page_size"] == 10
        assert pagination["total_count"] == 50
        assert pagination["total_pages"] == 5
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is True
        assert pagination["next_page"] == 3
        assert pagination["previous_page"] == 1
    
    def test_paginated_response_first_page(self, formatter):
        """Test paginated response for first page."""
        items = [{"id": 1}, {"id": 2}]
        
        response = formatter.paginated_response(
            items=items,
            total_count=25,
            page=1,
            page_size=10
        )
        
        pagination = response.metadata["pagination"]
        assert pagination["current_page"] == 1
        assert pagination["has_previous"] is False
        assert pagination["previous_page"] is None
        assert pagination["has_next"] is True
        assert pagination["next_page"] == 2
    
    def test_paginated_response_last_page(self, formatter):
        """Test paginated response for last page."""
        items = [{"id": 21}, {"id": 22}]
        
        response = formatter.paginated_response(
            items=items,
            total_count=22,
            page=3,
            page_size=10
        )
        
        pagination = response.metadata["pagination"]
        assert pagination["current_page"] == 3
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is False
        assert pagination["next_page"] is None
        assert pagination["has_previous"] is True
        assert pagination["previous_page"] == 2
    
    def test_to_json_response(self, formatter):
        """Test conversion to FastAPI JSONResponse."""
        standard_response = formatter.success(
            data={"test": "data"},
            message="Success"
        )
        
        json_response = formatter.to_json_response(
            standard_response,
            status.HTTP_200_OK
        )
        
        assert isinstance(json_response, JSONResponse)
        assert json_response.status_code == 200
        
        # Check headers
        assert "X-Request-ID" in json_response.headers
        assert "X-Timestamp" in json_response.headers
        assert "X-API-Version" in json_response.headers
        assert json_response.headers["X-Request-ID"] == standard_response.request_id
        assert json_response.headers["X-API-Version"] == "v1"
    
    def test_error_code_mapping(self, formatter):
        """Test error code mapping functionality."""
        # Test various HTTP status codes
        test_cases = [
            (400, "bad_request"),
            (401, "unauthorized"),
            (403, "forbidden"),
            (404, "not_found"),
            (409, "conflict"),
            (422, "validation_error"),
            (429, "rate_limit_exceeded"),
            (500, "internal_server_error"),
            (503, "service_unavailable")
        ]
        
        for status_code, expected_error_code in test_cases:
            response = formatter.error(
                message="Test error",
                status_code=status_code
            )
            assert response.metadata["error_code"] == expected_error_code
    
    def test_user_friendly_messages(self, formatter):
        """Test user-friendly error messages."""
        test_cases = [
            ("bad_request", "The request was invalid. Please check your input and try again."),
            ("unauthorized", "Authentication required. Please log in to continue."),
            ("forbidden", "You don't have permission to access this resource."),
            ("not_found", "The requested resource was not found."),
            ("validation_error", "The provided data is invalid. Please check the required fields."),
            ("rate_limit_exceeded", "Too many requests. Please wait before trying again."),
            ("internal_server_error", "An unexpected error occurred. Please try again later.")
        ]
        
        for error_code, expected_message in test_cases:
            response = formatter.error(
                message="Original message",
                status_code=500,  # Will be overridden by error_code
                error_code=error_code
            )
            assert response.message == expected_message


class TestExceptionHandling:
    """Test exception handling functionality."""
    
    def test_exception_status_mapping(self):
        """Test exception to status code mapping."""
        test_cases = [
            (AuthenticationError("test"), 401),
            (AuthorizationError("test"), 403),
            (ValidationError("test"), 422),
            (NotFoundError("test"), 404),
            (RateLimitExceededError("test"), 429),
            (ServiceUnavailableError("test"), 503)
        ]
        
        for exception, expected_status in test_cases:
            response = response_formatter.from_exception(exception)
            assert response.metadata["status_code"] == expected_status
    
    def test_create_error_handler(self):
        """Test error handler creation."""
        formatter = ResponseFormatter()
        error_handler = create_error_handler(formatter)
        
        # Mock request
        mock_request = MagicMock()
        
        # Test with HTTPException
        exception = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad request"
        )
        
        # The handler should be an async function
        import asyncio
        
        async def test_handler():
            return await error_handler(mock_request, exception)
        
        # Run the handler
        result = asyncio.run(test_handler())
        
        assert isinstance(result, JSONResponse)
        assert result.status_code == 400


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_data_success_response(self):
        """Test success response with empty/None data."""
        response = response_formatter.success(data=None)
        
        assert response.success is True
        assert response.data is None
    
    def test_large_metadata(self):
        """Test response with large metadata."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        response = response_formatter.success(
            data={"test": "data"},
            metadata=large_metadata
        )
        
        assert response.success is True
        assert len(response.metadata) >= 100  # Should include custom + default metadata
    
    def test_unicode_handling(self):
        """Test handling of unicode characters in messages and data."""
        unicode_data = {"message": "Testing unicode: 你好, こんにちは, 🚀"}
        unicode_message = "Unicode test: café, naïve, résumé"
        
        response = response_formatter.success(
            data=unicode_data,
            message=unicode_message
        )
        
        assert response.success is True
        assert response.data == unicode_data
        assert response.message == unicode_message
    
    def test_invalid_status_code(self):
        """Test handling of unknown status codes."""
        response = response_formatter.error(
            message="Unknown error",
            status_code=999  # Invalid status code
        )
        
        assert response.success is False
        assert response.metadata["error_code"] == "unknown_error"
        assert response.metadata["status_code"] == 999
    
    def test_timestamp_consistency(self):
        """Test that timestamps are properly set and recent."""
        response = response_formatter.success(data={"test": "data"})
        
        # Check that timestamp is recent (within last few seconds)
        now = datetime.now(timezone.utc)
        time_diff = (now - response.timestamp).total_seconds()
        assert time_diff < 5  # Should be within 5 seconds
    
    def test_request_id_uniqueness(self):
        """Test that request IDs are unique."""
        response1 = response_formatter.success(data={"test": "data1"})
        response2 = response_formatter.success(data={"test": "data2"})
        
        assert response1.request_id != response2.request_id
        
        # Test with custom request ID
        custom_id = "custom-123"
        response3 = response_formatter.success(
            data={"test": "data3"},
            request_id=custom_id
        )
        
        assert response3.request_id == custom_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])