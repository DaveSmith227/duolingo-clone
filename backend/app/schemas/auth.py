"""
Authentication Schemas

Pydantic models for authentication API requests and responses,
including registration, login, password reset, and token management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegistrationRequest(BaseModel):
    """User registration request schema."""
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        example="user@example.com"
    )
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)",
        example="SecurePass123!"
    )
    
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User first name",
        example="John"
    )
    
    last_name: Optional[str] = Field(
        None,
        max_length=100,
        description="User last name",
        example="Doe"
    )
    
    language_code: Optional[str] = Field(
        "en",
        min_length=2,
        max_length=5,
        description="Preferred language code (ISO 639-1)",
        example="en"
    )
    
    marketing_consent: bool = Field(
        False,
        description="Consent to receive marketing communications"
    )
    
    terms_accepted: bool = Field(
        ...,
        description="User accepts terms of service"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if len(v) > 128:
            raise ValueError('Password must be no more than 128 characters long')
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        # Check for at least one digit
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        
        return v
    
    @field_validator('terms_accepted')
    @classmethod
    def validate_terms_accepted(cls, v):
        """Ensure terms are accepted."""
        if not v:
            raise ValueError('Terms of service must be accepted')
        return v
    
    @field_validator('language_code')
    @classmethod
    def validate_language_code(cls, v):
        """Validate language code format."""
        if v and not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', v):
            raise ValueError('Language code must be in ISO 639-1 format (e.g., en, en-US)')
        return v


class LoginRequest(BaseModel):
    """User login request schema."""
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        example="user@example.com"
    )
    
    password: str = Field(
        ...,
        description="User password",
        example="SecurePass123!"
    )
    
    remember_me: bool = Field(
        False,
        description="Extend session duration (30 days instead of default)"
    )
    
    device_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Device name for session tracking",
        example="iPhone 14"
    )


class SocialAuthRequest(BaseModel):
    """Social authentication request schema."""
    
    provider: str = Field(
        ...,
        description="OAuth provider name",
        example="google"
    )
    
    access_token: str = Field(
        ...,
        description="OAuth access token from provider"
    )
    
    device_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Device name for session tracking",
        example="iPhone 14"
    )
    
    marketing_consent: bool = Field(
        False,
        description="Consent to receive marketing communications"
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        """Validate OAuth provider."""
        allowed_providers = ['google', 'apple', 'facebook', 'github', 'twitter']
        if v.lower() not in allowed_providers:
            raise ValueError(f'Provider must be one of: {", ".join(allowed_providers)}')
        return v.lower()


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        example="user@example.com"
    )


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    
    token: str = Field(
        ...,
        description="Password reset token from email"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
        example="NewSecurePass123!"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        # Reuse the same validation logic as registration
        return UserRegistrationRequest.validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    
    current_password: str = Field(
        ...,
        description="Current password"
    )
    
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
        example="NewSecurePass123!"
    )
    
    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password meets security requirements."""
        return UserRegistrationRequest.validate_password_strength(v)


class TokenResponse(BaseModel):
    """Authentication token response schema."""
    
    access_token: str = Field(
        ...,
        description="JWT access token"
    )
    
    refresh_token: str = Field(
        ...,
        description="JWT refresh token"
    )
    
    token_type: str = Field(
        "bearer",
        description="Token type"
    )
    
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds"
    )
    
    refresh_expires_in: int = Field(
        ...,
        description="Refresh token expiration time in seconds"
    )


class UserResponse(BaseModel):
    """User information response schema."""
    
    id: str = Field(
        ...,
        description="User ID"
    )
    
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    
    first_name: str = Field(
        ...,
        description="User first name"
    )
    
    last_name: Optional[str] = Field(
        None,
        description="User last name"
    )
    
    display_name: str = Field(
        ...,
        description="User display name"
    )
    
    avatar_url: Optional[str] = Field(
        None,
        description="User avatar URL"
    )
    
    language_code: str = Field(
        ...,
        description="User preferred language"
    )
    
    is_verified: bool = Field(
        ...,
        description="Email verification status"
    )
    
    is_premium: bool = Field(
        ...,
        description="Premium subscription status"
    )
    
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp"
    )
    
    last_login_at: Optional[datetime] = Field(
        None,
        description="Last login timestamp"
    )
    
    streak_count: int = Field(
        0,
        description="Current learning streak"
    )
    
    total_xp: int = Field(
        0,
        description="Total experience points"
    )


class AuthenticationResponse(BaseModel):
    """Complete authentication response schema."""
    
    user: UserResponse = Field(
        ...,
        description="User information"
    )
    
    tokens: TokenResponse = Field(
        ...,
        description="Authentication tokens"
    )
    
    session_id: str = Field(
        ...,
        description="Session identifier"
    )
    
    remember_me: bool = Field(
        False,
        description="Whether session has extended duration"
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )


class LogoutRequest(BaseModel):
    """Logout request schema."""
    
    logout_all_devices: bool = Field(
        False,
        description="Logout from all devices"
    )


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(
        ...,
        description="Error type"
    )
    
    message: str = Field(
        ...,
        description="Error message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    
    code: int = Field(
        ...,
        description="HTTP status code"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""
    
    error: str = Field(
        "validation_error",
        description="Error type"
    )
    
    message: str = Field(
        "Request validation failed",
        description="Error message"
    )
    
    details: List[Dict[str, Any]] = Field(
        ...,
        description="Validation error details"
    )
    
    code: int = Field(
        422,
        description="HTTP status code"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )


class RateLimitErrorResponse(BaseModel):
    """Rate limit error response schema."""
    
    error: str = Field(
        "rate_limit_exceeded",
        description="Error type"
    )
    
    message: str = Field(
        "Rate limit exceeded",
        description="Error message"
    )
    
    retry_after: int = Field(
        ...,
        description="Seconds to wait before retry"
    )
    
    limit: int = Field(
        ...,
        description="Rate limit threshold"
    )
    
    window: int = Field(
        ...,
        description="Rate limit window in seconds"
    )
    
    code: int = Field(
        429,
        description="HTTP status code"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )


class SessionInfo(BaseModel):
    """Session information schema."""
    
    session_id: str = Field(
        ...,
        description="Session identifier"
    )
    
    device_name: Optional[str] = Field(
        None,
        description="Device name"
    )
    
    ip_address: Optional[str] = Field(
        None,
        description="IP address"
    )
    
    user_agent: Optional[str] = Field(
        None,
        description="User agent string"
    )
    
    created_at: datetime = Field(
        ...,
        description="Session creation time"
    )
    
    last_activity: datetime = Field(
        ...,
        description="Last activity time"
    )
    
    expires_at: datetime = Field(
        ...,
        description="Session expiration time"
    )
    
    is_current: bool = Field(
        ...,
        description="Whether this is the current session"
    )


class UserSessionsResponse(BaseModel):
    """User sessions response schema."""
    
    sessions: List[SessionInfo] = Field(
        ...,
        description="List of active sessions"
    )
    
    total_count: int = Field(
        ...,
        description="Total number of sessions"
    )


class AccountLockoutInfo(BaseModel):
    """Account lockout information schema."""
    
    is_locked: bool = Field(
        ...,
        description="Whether account is locked"
    )
    
    lockout_reason: Optional[str] = Field(
        None,
        description="Reason for lockout"
    )
    
    locked_at: Optional[datetime] = Field(
        None,
        description="Lockout timestamp"
    )
    
    unlock_at: Optional[datetime] = Field(
        None,
        description="Automatic unlock timestamp"
    )
    
    attempt_count: int = Field(
        0,
        description="Failed attempt count"
    )
    
    can_retry_at: Optional[datetime] = Field(
        None,
        description="Next retry allowed timestamp"
    )


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""
    
    token: str = Field(
        ...,
        description="Email verification token"
    )


class ResendVerificationRequest(BaseModel):
    """Resend email verification request schema."""
    
    email: EmailStr = Field(
        ...,
        description="User email address",
        example="user@example.com"
    )


class AccountDeletionRequest(BaseModel):
    """Account deletion request schema."""
    
    confirmation: str = Field(
        ...,
        description="Confirmation phrase 'DELETE MY ACCOUNT'",
        example="DELETE MY ACCOUNT"
    )
    
    password: Optional[str] = Field(
        None,
        description="User password for verification (if not OAuth-only)",
        min_length=8,
        max_length=128
    )
    
    reason: Optional[str] = Field(
        None,
        description="Reason for account deletion",
        max_length=500
    )


class AccountDeletionResponse(BaseModel):
    """Account deletion response schema."""
    
    message: str = Field(
        ...,
        description="Deletion confirmation message"
    )
    
    user_id: str = Field(
        ...,
        description="ID of deleted user"
    )
    
    email: str = Field(
        ...,
        description="Email of deleted user"
    )
    
    deleted_at: datetime = Field(
        ...,
        description="Deletion timestamp"
    )
    
    records_deleted: int = Field(
        ...,
        description="Total number of records deleted"
    )
    
    supabase_auth_deleted: bool = Field(
        ...,
        description="Whether Supabase Auth account was deleted"
    )


class DataExportRequest(BaseModel):
    """Data export request schema."""
    
    format: str = Field(
        "json",
        description="Export format (json only for now)",
        example="json"
    )
    
    include_sections: Optional[List[str]] = Field(
        None,
        description="Specific sections to include (all if not specified)",
        example=["personal_data", "learning_data", "gamification_data"]
    )


class DataExportResponse(BaseModel):
    """Data export response schema."""
    
    export_info: Dict[str, Any] = Field(
        ...,
        description="Export metadata"
    )
    
    personal_data: Dict[str, Any] = Field(
        ...,
        description="User personal data"
    )
    
    learning_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Learning progress data"
    )
    
    gamification_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Gamification and achievement data"
    )
    
    access_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Access control and role data"
    )