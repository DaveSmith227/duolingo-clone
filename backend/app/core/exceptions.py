"""
Custom exceptions for the application.
"""


class AppException(Exception):
    """Base exception for application."""
    pass


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(AppException):
    """Raised when authorization fails."""
    pass


class UserNotFoundError(AppException):
    """Raised when user is not found."""
    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid or expired."""
    pass


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""
    pass


class ValidationError(AppException):
    """Raised when validation fails."""
    pass


class DuplicateError(AppException):
    """Raised when trying to create duplicate resource."""
    pass


class NotFoundError(AppException):
    """Raised when resource is not found."""
    pass


class PermissionDeniedError(AuthorizationError):
    """Raised when user lacks required permissions."""
    pass


class ServiceUnavailableError(AppException):
    """Raised when external service is unavailable."""
    pass


class ServiceError(AppException):
    """Raised when a service operation fails."""
    pass