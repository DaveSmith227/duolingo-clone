"""
Authentication Service Interface

Defines the contract for authentication services to ensure consistent
implementation across different auth providers and testing scenarios.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, Tuple
from datetime import datetime

from app.models.user import User


class IAuthService(Protocol):
    """
    Protocol for authentication service implementations.
    
    This interface defines the core authentication operations that any
    auth service implementation must provide.
    """
    
    @abstractmethod
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        client_info: Dict[str, Any]
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Register a new user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            first_name: User's first name
            last_name: User's last name
            client_info: Client information (IP, user agent, etc.)
            
        Returns:
            Tuple of (User, session_data)
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            ValueError: If validation fails
        """
        ...
    
    @abstractmethod
    async def login_user(
        self,
        email: str,
        password: str,
        client_info: Dict[str, Any],
        remember_me: bool = False
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email
            password: User's password
            client_info: Client information
            remember_me: Whether to create long-lived session
            
        Returns:
            Tuple of (User, session_data or mfa_challenge)
            
        Raises:
            AuthenticationError: If authentication fails
            AccountLockedError: If account is locked
            RateLimitExceededError: If rate limit exceeded
        """
        ...
    
    @abstractmethod
    async def verify_mfa(
        self,
        challenge_token: str,
        mfa_code: str,
        method: str,
        client_info: Dict[str, Any]
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Verify MFA code and complete login.
        
        Args:
            challenge_token: MFA challenge token
            mfa_code: User-provided MFA code
            method: MFA method (totp or backup_code)
            client_info: Client information
            
        Returns:
            Tuple of (User, session_data)
            
        Raises:
            InvalidTokenError: If challenge token invalid
            AuthenticationError: If MFA code invalid
        """
        ...
    
    @abstractmethod
    async def logout_user(
        self,
        session_id: str,
        user_id: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Logout user and invalidate session.
        
        Args:
            session_id: Session to invalidate
            user_id: User ID for logging
            client_info: Client information
        """
        ...
    
    @abstractmethod
    async def request_password_reset(
        self,
        email: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Request password reset for user.
        
        Args:
            email: User's email
            client_info: Client information
        """
        ...
    
    @abstractmethod
    async def reset_password(
        self,
        token: str,
        new_password: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Reset user password with token.
        
        Args:
            token: Password reset token
            new_password: New password
            client_info: Client information
            
        Raises:
            InvalidTokenError: If token invalid
            ValueError: If password invalid
        """
        ...


class AuthServiceConfig:
    """Configuration type for authentication service."""
    
    def __init__(
        self,
        max_login_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        password_reset_token_expiry_hours: int = 1,
        session_timeout_minutes: int = 30,
        remember_me_days: int = 30
    ):
        self.max_login_attempts = max_login_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        self.password_reset_token_expiry_hours = password_reset_token_expiry_hours
        self.session_timeout_minutes = session_timeout_minutes
        self.remember_me_days = remember_me_days


class AuthenticationResult:
    """Result type for authentication operations."""
    
    def __init__(
        self,
        success: bool,
        user: Optional[User] = None,
        session_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        requires_mfa: bool = False,
        mfa_challenge_token: Optional[str] = None
    ):
        self.success = success
        self.user = user
        self.session_data = session_data
        self.error_code = error_code
        self.error_message = error_message
        self.requires_mfa = requires_mfa
        self.mfa_challenge_token = mfa_challenge_token
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "success": self.success,
            "user": self.user.to_dict() if self.user else None,
            "session_data": self.session_data,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "requires_mfa": self.requires_mfa,
            "mfa_challenge_token": self.mfa_challenge_token
        }