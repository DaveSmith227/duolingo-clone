"""
Configuration Management

Environment-based configuration for the Duolingo clone backend application.
Handles environment variables, validation, and settings for different deployment environments.
"""

import os
import json
from typing import Optional, List, Dict, Any, Union
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator, model_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import warnings

from .environment import get_environment, get_environment_name, validate_environment_consistency, Environment
from .config_inheritance import apply_config_inheritance, set_production_baseline
from .env_validators import validate_environment_config, get_config_validation_summary, ValidationSeverity
from .config_validators import ConfigurationBusinessRuleValidator
from .audit_logger import get_audit_logger, set_audit_context, AuditEvent, AuditAction, AuditSeverity
from datetime import datetime, timezone


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Loads configuration from environment variables with fallback defaults
    for development. Validates required settings on application startup.
    """
    
    # Application settings
    app_name: str = Field(default="Duolingo Clone API", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default_factory=get_environment_name)
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # Database settings
    database_url: Optional[str] = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "duolingo_clone"
    db_user: str = "postgres"
    db_password: str = "password"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Security settings
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_expire_hours: int = 1
    
    # Session management settings
    session_expire_days: int = 30
    remember_me_expire_days: int = 30
    max_active_sessions: int = 5
    session_activity_timeout_hours: int = 24 * 30  # 30 days of inactivity
    
    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    
    # Redis settings (for caching and task queue)
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Rate limiting settings
    rate_limiting_enabled: bool = True
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_minutes: int = 15
    login_lockout_duration_minutes: int = 30
    password_reset_rate_limit_attempts: int = 3
    password_reset_rate_limit_window_hours: int = 1
    registration_rate_limit_attempts: int = 3
    registration_rate_limit_window_hours: int = 1
    
    # Password security settings
    password_min_length: int = 8
    password_max_length: int = 128
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special_chars: bool = True
    password_prevent_common: bool = True
    password_history_count: int = 5
    password_expiry_days: Optional[int] = None  # None = no expiry
    csrf_protection_enabled: bool = True
    
    # Email verification settings
    require_email_verification: bool = False  # Set to True in production
    
    # Account lockout settings
    lockout_max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    lockout_progressive_enabled: bool = True
    lockout_max_duration_hours: int = 24
    rapid_fire_threshold_seconds: int = 5
    rapid_fire_max_attempts: int = 3
    multiple_ip_threshold: int = 3
    multiple_ip_window_hours: int = 1
    permanent_lockout_threshold: int = 10
    
    # External API settings
    openai_api_key: Optional[str] = None
    
    # Supabase settings
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    supabase_jwt_secret: Optional[str] = None
    
    # OAuth provider settings
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    apple_client_id: Optional[str] = None
    apple_team_id: Optional[str] = None
    apple_key_id: Optional[str] = None
    apple_private_key_path: Optional[str] = None
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    
    # OAuth redirect settings
    frontend_url: str = "http://localhost:3000"
    oauth_redirect_url: Optional[str] = None
    
    # Email settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str = "noreply@duolingoclone.com"
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment is one of the allowed values."""
        allowed_environments = ["development", "staging", "production", "test"]
        if v not in allowed_environments:
            raise ValueError(f"Environment must be one of: {allowed_environments}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is one of the allowed values."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Validate secret key strength."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        if v == "dev-secret-key-change-in-production":
            warnings.warn(
                "Using default secret key. Please set SECRET_KEY environment variable in production.",
                UserWarning
            )
        return v
    
    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, v):
        """Validate Supabase URL format."""
        if v and not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return v
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins are valid URLs."""
        for origin in v:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"CORS origin must be a valid URL: {origin}")
        return v
    
    @field_validator("redis_host", "db_host")
    @classmethod
    def validate_host(cls, v):
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Host cannot be empty")
        return v
    
    @model_validator(mode="after")
    def validate_environment_specific(self):
        """Apply environment-specific validation rules."""
        # Production environment checks
        if self.environment == "production":
            # Ensure critical security settings
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be changed in production")
            
            if not self.supabase_url or not self.supabase_anon_key:
                raise ValueError("Supabase configuration is required in production")
            
            if self.debug:
                raise ValueError("DEBUG must be False in production")
            
            if "localhost" in str(self.cors_origins) or "127.0.0.1" in str(self.cors_origins):
                warnings.warn("localhost in CORS origins for production environment", UserWarning)
            
            if not self.smtp_host:
                warnings.warn("Email configuration not set for production", UserWarning)
            
            # Ensure strong security settings
            if self.password_min_length < 10:
                raise ValueError("Password minimum length must be at least 10 in production")
            
            if not self.require_email_verification:
                raise ValueError("Email verification must be enabled in production")
            
            if not self.csrf_protection_enabled:
                raise ValueError("CSRF protection must be enabled in production")
        
        # Staging environment checks
        elif self.environment == "staging":
            if self.debug:
                warnings.warn("DEBUG is enabled in staging environment", UserWarning)
            
            if not self.supabase_url:
                warnings.warn("Supabase not configured for staging", UserWarning)
        
        # Development environment defaults
        elif self.environment == "development":
            # Allow relaxed settings for development
            pass
        
        # Test environment checks
        elif self.environment == "test":
            # Ensure test-specific settings
            if self.rate_limiting_enabled:
                warnings.warn("Rate limiting is enabled in test environment", UserWarning)
        
        return self
    
    @model_validator(mode="after")
    def validate_database_configuration(self):
        """Validate database configuration consistency."""
        if not self.database_url and self.environment == "production":
            # Ensure all DB components are provided for production
            required_fields = ["db_host", "db_port", "db_name", "db_user", "db_password"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"Missing database configuration: {', '.join(missing)}")
        return self
    
    @model_validator(mode="after")
    def validate_redis_configuration(self):
        """Validate Redis configuration consistency."""
        if not self.redis_url and self.environment in ["production", "staging"]:
            # Check if Redis components are provided
            if not self.redis_host:
                warnings.warn("Redis not configured for caching and rate limiting", UserWarning)
        return self
    
    @model_validator(mode="after")
    def validate_environment_detection(self):
        """Validate environment detection consistency."""
        # Check for environment variable consistency
        consistency_issues = validate_environment_consistency()
        if consistency_issues:
            for issue in consistency_issues:
                if self.environment == "production":
                    raise ValueError(f"Environment consistency issue: {issue}")
                else:
                    warnings.warn(f"Environment consistency issue: {issue}", UserWarning)
        
        return self
    
    @model_validator(mode="after")
    def validate_environment_specific_rules(self):
        """Apply environment-specific validation rules."""
        current_env = Environment(self.environment)
        config_dict = self.model_dump()
        
        # Run environment-specific validation
        validation_results = validate_environment_config(config_dict, current_env)
        
        # Process validation results
        errors = [r for r in validation_results if r.severity == ValidationSeverity.ERROR]
        warnings_list = [r for r in validation_results if r.severity == ValidationSeverity.WARNING]
        
        # Raise errors for production, warn for others
        if errors and current_env == Environment.PRODUCTION:
            error_messages = [f"{r.field}: {r.message}" for r in errors]
            raise ValueError(f"Environment validation failed: {'; '.join(error_messages)}")
        
        # Log warnings for all environments
        for warning in warnings_list:
            warnings.warn(f"Configuration warning for {warning.field}: {warning.message}", UserWarning)
        
        # Log errors as warnings for non-production environments
        if errors and current_env != Environment.PRODUCTION:
            for error in errors:
                warnings.warn(f"Configuration issue for {error.field}: {error.message}", UserWarning)
        
        return self
    
    @model_validator(mode="after")
    def validate_business_rules(self):
        """Apply business rule validation and cross-field checks."""
        current_env = Environment(self.environment)
        config_dict = self.model_dump()
        
        # Run business rule validation
        business_rule_validator = ConfigurationBusinessRuleValidator()
        validation_results = business_rule_validator.validate(config_dict, current_env)
        
        # Process validation results
        errors = [r for r in validation_results if r.severity == ValidationSeverity.ERROR]
        warnings_list = [r for r in validation_results if r.severity == ValidationSeverity.WARNING]
        
        # Raise errors for production, warn for others
        if errors and current_env == Environment.PRODUCTION:
            error_messages = [f"{r.field}: {r.message}" for r in errors]
            raise ValueError(f"Business rule validation failed: {'; '.join(error_messages)}")
        
        # Log warnings for all environments
        for warning in warnings_list:
            warnings.warn(f"Business rule warning for {warning.field}: {warning.message}", UserWarning)
        
        # Log errors as warnings for non-production environments
        if errors and current_env != Environment.PRODUCTION:
            for error in errors:
                warnings.warn(f"Business rule issue for {error.field}: {error.message}", UserWarning)
        
        return self
    
    
    @property
    def database_dsn(self) -> str:
        """
        Build database connection string.
        
        Returns DATABASE_URL if provided, otherwise constructs from individual components.
        For development environment, defaults to SQLite.
        """
        if self.database_url:
            return self.database_url
        
        # Use SQLite for development, PostgreSQL for production
        if self.is_development or self.is_testing:
            return "sqlite:///./app.db"
        
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def redis_dsn(self) -> str:
        """
        Build Redis connection string.
        
        Returns REDIS_URL if provided, otherwise constructs from individual components.
        """
        if self.redis_url:
            return self.redis_url
        
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.environment == "test"
    
    @property
    def oauth_callback_url(self) -> str:
        """
        Build OAuth callback URL.
        
        Returns configured OAUTH_REDIRECT_URL if provided, otherwise builds from frontend URL.
        """
        if self.oauth_redirect_url:
            return self.oauth_redirect_url
        return f"{self.frontend_url}/auth/callback"
    
    @property
    def has_supabase_config(self) -> bool:
        """Check if Supabase configuration is complete."""
        return all([
            self.supabase_url,
            self.supabase_anon_key,
            self.supabase_service_role_key
        ])
    
    def get_safe_config(self) -> Dict[str, Any]:
        """
        Get configuration suitable for logging/debugging.
        
        Excludes sensitive values like passwords and API keys.
        """
        exclude_fields = {
            "secret_key", "db_password", "redis_password", 
            "supabase_service_role_key", "supabase_anon_key", "supabase_jwt_secret",
            "openai_api_key", "smtp_password",
            "google_client_secret", "apple_private_key_path",
            "facebook_app_secret", "tiktok_client_secret"
        }
        
        config = {}
        for field_name, field_value in self.model_dump().items():
            if field_name in exclude_fields:
                config[field_name] = "***REDACTED***" if field_value else None
            else:
                config[field_name] = field_value
        
        return config
    
    def export_safe(self) -> Dict[str, Any]:
        """Export configuration with audit logging."""
        audit_logger = get_audit_logger()
        
        try:
            safe_config = self.get_safe_config()
            
            # Log the export
            audit_logger.log_config_export(
                export_format="dict",
                include_sensitive=False,
                success=True,
                metadata={
                    "fields_count": len(safe_config),
                    "environment": self.environment
                }
            )
            
            return safe_config
            
        except Exception as e:
            audit_logger.log_config_export(
                export_format="dict",
                include_sensitive=False,
                success=False,
                error_message=str(e)
            )
            raise
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment-specific information for debugging."""
        return {
            "environment": self.environment,
            "is_development": self.is_development,
            "is_production": self.is_production,
            "is_testing": self.is_testing,
            "debug": self.debug,
            "has_supabase": self.has_supabase_config,
            "has_redis": bool(self.redis_url or self.redis_host),
            "has_smtp": bool(self.smtp_host),
            "security_features": {
                "rate_limiting": self.rate_limiting_enabled,
                "csrf_protection": self.csrf_protection_enabled,
                "email_verification": self.require_email_verification,
                "mfa_available": self.has_supabase_config,
            }
        }
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )


# Create settings instance with error handling
def _create_settings() -> Settings:
    """Create settings instance with proper error handling and inheritance."""
    try:
        current_env = get_environment()
        
        # Create initial settings
        base_settings = Settings()
        
        # Apply inheritance if needed
        if current_env == Environment.STAGING:
            # First, we need a production baseline
            # For now, we'll simulate this by creating a production-like config
            # In a real deployment, this would come from a production config file
            production_config = _get_production_baseline()
            if production_config:
                set_production_baseline(production_config)
                
                # Apply inheritance to current config
                current_config = base_settings.model_dump()
                inherited_config = apply_config_inheritance(current_config, current_env)
                
                # Create new settings from inherited config
                base_settings = Settings(**inherited_config)
                print(f"Applied configuration inheritance for {current_env.value} environment")
        
        return base_settings
        
    except ValidationError as e:
        # Log validation errors for debugging
        print("Configuration validation failed:")
        for error in e.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            print(f"  - {field}: {msg}")
        raise
    except Exception as e:
        print(f"Failed to load configuration: {str(e)}")
        raise


def _get_production_baseline() -> Optional[Dict[str, Any]]:
    """Get production configuration baseline for inheritance."""
    # In a real deployment, this would load from a secure config store
    # For now, return a minimal production-like configuration
    baseline_file = Path.home() / '.duolingo_clone' / 'production_baseline.json'
    
    if baseline_file.exists():
        try:
            with baseline_file.open('r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load production baseline: {e}")
    
    # Return minimal baseline if no file exists
    return {
        "password_min_length": 12,
        "require_email_verification": True,
        "csrf_protection_enabled": True,
        "rate_limiting_enabled": True,
        "password_require_uppercase": True,
        "password_require_lowercase": True,
        "password_require_digits": True,
        "password_require_special_chars": True,
        "password_prevent_common": True,
        "password_history_count": 5,
        "login_rate_limit_attempts": 5,
        "login_rate_limit_window_minutes": 15,
        "lockout_max_failed_attempts": 5,
        "lockout_duration_minutes": 30,
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 7,
        "jwt_algorithm": "HS256",
        "app_name": "Duolingo Clone API",
        "app_version": "0.1.0",
    }


# Global settings instance
settings = _create_settings()


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns the global settings instance. Useful for dependency injection
    and testing with override settings.
    """
    return settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.
    
    Useful for testing or when environment variables change.
    """
    global settings
    audit_logger = get_audit_logger()
    
    try:
        # Log reload attempt
        old_env = settings.environment if settings else "unknown"
        
        get_settings.cache_clear()
        settings = _create_settings()
        
        # Log successful reload using the simpler API
        audit_logger.log_config_validation(
            field_name="environment",
            success=True,
            metadata={
                "action": "reload",
                "old_environment": old_env,
                "new_environment": settings.environment,
                "config_version": settings.app_version
            }
        )
        
        return settings
        
    except Exception as e:
        audit_logger.log_config_validation(
            field_name="environment",
            success=False,
            error_message=str(e),
            metadata={
                "action": "reload",
                "error_type": type(e).__name__
            }
        )
        raise


def validate_config_for_environment(env: str) -> List[str]:
    """
    Validate configuration for a specific environment.
    
    Returns a list of validation warnings/errors.
    """
    issues = []
    
    if env == "production":
        if settings.secret_key == "dev-secret-key-change-in-production":
            issues.append("SECRET_KEY is using default value")
        
        if not settings.has_supabase_config:
            issues.append("Supabase configuration is incomplete")
        
        if settings.debug:
            issues.append("DEBUG mode is enabled")
        
        if not settings.smtp_host:
            issues.append("Email server not configured")
        
        if not settings.require_email_verification:
            issues.append("Email verification is disabled")
        
        if any("localhost" in origin for origin in settings.cors_origins):
            issues.append("CORS origins contain localhost")
    
    elif env == "staging":
        if not settings.has_supabase_config:
            issues.append("Supabase configuration is incomplete")
        
        if settings.debug:
            issues.append("DEBUG mode is enabled (warning)")
    
    return issues