"""
Security Configuration Service

Handles security-related configuration, validation, and secret management
following the Single Responsibility Principle.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator

from ..environment import Environment


class SecurityConfig(BaseModel):
    """Security configuration model."""
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_expire_hours: int = 1
    
    # Session management
    session_expire_days: int = 30
    remember_me_expire_days: int = 30
    max_active_sessions: int = 5
    session_activity_timeout_hours: int = 24 * 30
    
    # Password security
    password_min_length: int = 8
    password_max_length: int = 128
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special_chars: bool = True
    password_prevent_common: bool = True
    password_history_count: int = 5
    password_expiry_days: Optional[int] = None
    
    # Security features
    csrf_protection_enabled: bool = True
    require_email_verification: bool = False
    
    # Rate limiting
    rate_limiting_enabled: bool = True
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_minutes: int = 15
    login_lockout_duration_minutes: int = 30
    password_reset_rate_limit_attempts: int = 3
    password_reset_rate_limit_window_hours: int = 1
    registration_rate_limit_attempts: int = 3
    registration_rate_limit_window_hours: int = 1
    
    # Account lockout
    lockout_max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    lockout_progressive_enabled: bool = True
    lockout_max_duration_hours: int = 24
    rapid_fire_threshold_seconds: int = 5
    rapid_fire_max_attempts: int = 3
    multiple_ip_threshold: int = 3
    multiple_ip_window_hours: int = 1
    permanent_lockout_threshold: int = 10
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v):
        """Validate JWT algorithm."""
        allowed_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        if v not in allowed_algorithms:
            raise ValueError(f"JWT algorithm must be one of: {allowed_algorithms}")
        return v


class SecurityValidationResult(BaseModel):
    """Security validation result."""
    field: str
    message: str
    severity: str  # "error", "warning", "info"


class SecurityConfigService:
    """
    Service responsible for security configuration management.
    
    Responsibilities:
    - Security settings validation
    - Password policy enforcement
    - Session and token configuration
    - Security feature toggles
    """
    
    def __init__(self, config_dict: Dict[str, Any]):
        """Initialize with configuration dictionary."""
        # Extract security-related fields
        security_fields = [
            'secret_key', 'jwt_algorithm', 'access_token_expire_minutes',
            'refresh_token_expire_days', 'password_reset_expire_hours',
            'session_expire_days', 'remember_me_expire_days', 'max_active_sessions',
            'session_activity_timeout_hours', 'password_min_length', 'password_max_length',
            'password_require_uppercase', 'password_require_lowercase', 'password_require_digits',
            'password_require_special_chars', 'password_prevent_common', 'password_history_count',
            'password_expiry_days', 'csrf_protection_enabled', 'require_email_verification',
            'rate_limiting_enabled', 'login_rate_limit_attempts', 'login_rate_limit_window_minutes',
            'login_lockout_duration_minutes', 'password_reset_rate_limit_attempts',
            'password_reset_rate_limit_window_hours', 'registration_rate_limit_attempts',
            'registration_rate_limit_window_hours', 'lockout_max_failed_attempts',
            'lockout_duration_minutes', 'lockout_progressive_enabled', 'lockout_max_duration_hours',
            'rapid_fire_threshold_seconds', 'rapid_fire_max_attempts', 'multiple_ip_threshold',
            'multiple_ip_window_hours', 'permanent_lockout_threshold'
        ]
        
        security_config = {
            field: config_dict.get(field)
            for field in security_fields
            if config_dict.get(field) is not None
        }
        
        self.config = SecurityConfig(**security_config)
    
    def validate_for_environment(self, environment: Environment) -> List[SecurityValidationResult]:
        """
        Validate security configuration for specific environment.
        
        Args:
            environment: Environment to validate for
            
        Returns:
            List of validation results
        """
        results = []
        
        if environment == Environment.PRODUCTION:
            results.extend(self._validate_production_security())
        elif environment == Environment.STAGING:
            results.extend(self._validate_staging_security())
        elif environment == Environment.DEVELOPMENT:
            results.extend(self._validate_development_security())
        elif environment == Environment.TEST:
            results.extend(self._validate_test_security())
        
        return results
    
    def _validate_production_security(self) -> List[SecurityValidationResult]:
        """Validate production security requirements."""
        results = []
        
        # Secret key validation
        if self.config.secret_key == "dev-secret-key-change-in-production":
            results.append(SecurityValidationResult(
                field="secret_key",
                message="SECRET_KEY must be changed in production",
                severity="error"
            ))
        
        # Password policy
        if self.config.password_min_length < 10:
            results.append(SecurityValidationResult(
                field="password_min_length",
                message="Password minimum length must be at least 10 in production",
                severity="error"
            ))
        
        # Email verification
        if not self.config.require_email_verification:
            results.append(SecurityValidationResult(
                field="require_email_verification",
                message="Email verification must be enabled in production",
                severity="error"
            ))
        
        # CSRF protection
        if not self.config.csrf_protection_enabled:
            results.append(SecurityValidationResult(
                field="csrf_protection_enabled",
                message="CSRF protection must be enabled in production",
                severity="error"
            ))
        
        # Session timeout
        if self.config.session_activity_timeout_hours > 24 * 7:  # More than a week
            results.append(SecurityValidationResult(
                field="session_activity_timeout_hours",
                message="Session timeout should be shorter in production",
                severity="warning"
            ))
        
        return results
    
    def _validate_staging_security(self) -> List[SecurityValidationResult]:
        """Validate staging security requirements."""
        results = []
        
        # Less strict than production, but still secure
        if self.config.password_min_length < 8:
            results.append(SecurityValidationResult(
                field="password_min_length",
                message="Password minimum length should be at least 8 in staging",
                severity="warning"
            ))
        
        if self.config.secret_key == "dev-secret-key-change-in-production":
            results.append(SecurityValidationResult(
                field="secret_key",
                message="Consider using a staging-specific secret key",
                severity="warning"
            ))
        
        return results
    
    def _validate_development_security(self) -> List[SecurityValidationResult]:
        """Validate development security requirements."""
        results = []
        
        # More lenient for development
        if self.config.password_min_length < 6:
            results.append(SecurityValidationResult(
                field="password_min_length",
                message="Password minimum length should be at least 6 in development",
                severity="warning"
            ))
        
        if self.config.rate_limiting_enabled:
            results.append(SecurityValidationResult(
                field="rate_limiting_enabled",
                message="Rate limiting may slow development, consider disabling",
                severity="info"
            ))
        
        return results
    
    def _validate_test_security(self) -> List[SecurityValidationResult]:
        """Validate test security requirements."""
        results = []
        
        # Test environment specific checks
        if self.config.rate_limiting_enabled:
            results.append(SecurityValidationResult(
                field="rate_limiting_enabled",
                message="Rate limiting should be disabled in test environment",
                severity="warning"
            ))
        
        if self.config.lockout_max_failed_attempts < 10:
            results.append(SecurityValidationResult(
                field="lockout_max_failed_attempts",
                message="Lockout threshold should be higher in test environment",
                severity="warning"
            ))
        
        return results
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get security configuration with sensitive data redacted."""
        config_dict = self.config.model_dump()
        
        # Redact sensitive fields
        config_dict["secret_key"] = "***REDACTED***" if config_dict["secret_key"] else None
        
        return config_dict
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security configuration summary."""
        return {
            "password_policy": {
                "min_length": self.config.password_min_length,
                "max_length": self.config.password_max_length,
                "require_uppercase": self.config.password_require_uppercase,
                "require_lowercase": self.config.password_require_lowercase,
                "require_digits": self.config.password_require_digits,
                "require_special_chars": self.config.password_require_special_chars,
                "prevent_common": self.config.password_prevent_common,
                "history_count": self.config.password_history_count
            },
            "session_management": {
                "expire_days": self.config.session_expire_days,
                "remember_me_days": self.config.remember_me_expire_days,
                "max_active": self.config.max_active_sessions,
                "activity_timeout_hours": self.config.session_activity_timeout_hours
            },
            "security_features": {
                "csrf_protection": self.config.csrf_protection_enabled,
                "email_verification": self.config.require_email_verification,
                "rate_limiting": self.config.rate_limiting_enabled
            },
            "token_settings": {
                "access_token_minutes": self.config.access_token_expire_minutes,
                "refresh_token_days": self.config.refresh_token_expire_days,
                "jwt_algorithm": self.config.jwt_algorithm
            }
        }