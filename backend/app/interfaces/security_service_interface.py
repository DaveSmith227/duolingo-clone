"""
Security Service Interfaces

Defines contracts for various security-related services including
password security, rate limiting, and audit logging.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, List
from enum import Enum


class SecurityEventType(Enum):
    """Security event types for audit logging."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    REGISTRATION = "registration"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKED = "account_locked"
    MFA_ENABLED = "mfa_enabled"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class ThreatLevel(Enum):
    """Threat level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IPasswordSecurity(Protocol):
    """
    Protocol for password security services.
    """
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """
        Hash a password using secure algorithm.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        ...
    
    @abstractmethod
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            password_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        ...
    
    @abstractmethod
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength against policy.
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results and score
        """
        ...
    
    @abstractmethod
    async def check_password_history(self, user_id: str, password: str) -> bool:
        """
        Check if password was used before by user.
        
        Args:
            user_id: User ID
            password: Password to check
            
        Returns:
            True if password is in history, False otherwise
        """
        ...


class IRateLimiter(Protocol):
    """
    Protocol for rate limiting services.
    """
    
    @abstractmethod
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if request is within rate limits.
        
        Args:
            key: Rate limit key (e.g., 'login', 'register')
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            identifier: Optional identifier (IP, user ID)
            
        Returns:
            Dictionary with rate limit status
        """
        ...
    
    @abstractmethod
    async def record_request(
        self,
        key: str,
        identifier: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Record a request for rate limiting.
        
        Args:
            key: Rate limit key
            identifier: Optional identifier
            success: Whether request was successful
        """
        ...
    
    @abstractmethod
    async def get_rate_limit_status(
        self,
        key: str,
        identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Args:
            key: Rate limit key
            identifier: Optional identifier
            
        Returns:
            Dictionary with current status
        """
        ...


class ISecurityService(Protocol):
    """
    Protocol for general security services.
    """
    
    @abstractmethod
    async def log_security_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a security event for audit purposes.
        
        Args:
            event_type: Type of security event
            user_id: User ID (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether event was successful
            metadata: Additional event metadata
        """
        ...
    
    @abstractmethod
    async def assess_threat_level(
        self,
        user_id: Optional[str],
        ip_address: str,
        event_type: SecurityEventType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ThreatLevel:
        """
        Assess threat level for security event.
        
        Args:
            user_id: User ID (if applicable)
            ip_address: Client IP address
            event_type: Type of security event
            metadata: Additional context
            
        Returns:
            Assessed threat level
        """
        ...
    
    @abstractmethod
    async def should_block_request(
        self,
        ip_address: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Determine if request should be blocked based on security rules.
        
        Args:
            ip_address: Client IP address
            user_id: User ID (if applicable)
            
        Returns:
            True if request should be blocked
        """
        ...


class SecurityConfig:
    """Configuration for security services."""
    
    def __init__(
        self,
        password_min_length: int = 8,
        password_require_uppercase: bool = True,
        password_require_lowercase: bool = True,
        password_require_numbers: bool = True,
        password_require_symbols: bool = True,
        password_history_count: int = 5,
        max_failed_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        rate_limit_window_seconds: int = 300,
        suspicious_activity_threshold: int = 10
    ):
        self.password_min_length = password_min_length
        self.password_require_uppercase = password_require_uppercase
        self.password_require_lowercase = password_require_lowercase
        self.password_require_numbers = password_require_numbers
        self.password_require_symbols = password_require_symbols
        self.password_history_count = password_history_count
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.suspicious_activity_threshold = suspicious_activity_threshold


class RateLimitResult:
    """Result type for rate limiting operations."""
    
    def __init__(
        self,
        allowed: bool,
        remaining_requests: int,
        reset_time: int,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.remaining_requests = remaining_requests
        self.reset_time = reset_time
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "allowed": self.allowed,
            "remaining_requests": self.remaining_requests,
            "reset_time": self.reset_time,
            "retry_after": self.retry_after
        }