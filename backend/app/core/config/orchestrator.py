"""
Configuration Service Orchestrator

Coordinates all configuration services and provides a clean interface
to replace the monolithic Settings class, following the Single Responsibility Principle.
"""

import os
import warnings
from typing import Dict, Any, List, Optional
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..environment import Environment, get_environment
from .database_service import DatabaseConfigService
from .security_service import SecurityConfigService  
from .validation_service import (
    ConfigValidationService, 
    DatabaseValidatorAdapter,
    SecurityValidatorAdapter,
    ValidationSummary
)


class BaseConfigModel(BaseSettings):
    """Base configuration model for non-service specific settings."""
    
    # Application settings
    app_name: str = Field(default="Duolingo Clone API", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default_factory=lambda: get_environment().value)
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # External API settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
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
    
    # CORS settings
    cors_origins: List[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])
    cors_allow_credentials: bool = True
    
    # Redis settings (for caching and task queue)
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )


class ConfigServiceOrchestrator:
    """
    Coordinates configuration services - replaces monolithic Settings class.
    
    This class is much smaller and focused on orchestration rather than
    containing all configuration logic itself.
    """
    
    def __init__(self):
        """Initialize the configuration orchestrator."""
        self._base_config: Optional[BaseConfigModel] = None
        self._database_service: Optional[DatabaseConfigService] = None
        self._security_service: Optional[SecurityConfigService] = None
        self._validation_service: Optional[ConfigValidationService] = None
        self._environment: Optional[Environment] = None
        
        # Initialize all services
        self._load_configuration()
        self._initialize_services()
        self._setup_validation()
        self._validate_configuration()
    
    def _load_configuration(self) -> None:
        """Load base configuration from environment."""
        try:
            self._base_config = BaseConfigModel()
            self._environment = Environment(self._base_config.environment)
        except Exception as e:
            raise ValueError(f"Failed to load base configuration: {e}")
    
    def _initialize_services(self) -> None:
        """Initialize all configuration services."""
        if not self._base_config:
            raise RuntimeError("Base configuration not loaded")
        
        # Convert to dict for service initialization
        config_dict = self._base_config.model_dump()
        
        # Initialize services
        self._database_service = DatabaseConfigService(config_dict)
        self._security_service = SecurityConfigService(config_dict)
        self._validation_service = ConfigValidationService()
    
    def _setup_validation(self) -> None:
        """Setup validation service with all validators."""
        if not self._validation_service:
            raise RuntimeError("Validation service not initialized")
        
        # Register validators
        self._validation_service.register_validator(
            "database",
            DatabaseValidatorAdapter(self._database_service)
        )
        self._validation_service.register_validator(
            "security", 
            SecurityValidatorAdapter(self._security_service)
        )
    
    def _validate_configuration(self) -> None:
        """Validate all configuration and handle results."""
        if not self._validation_service or not self._environment:
            raise RuntimeError("Services not properly initialized")
        
        validation_summary = self._validation_service.validate_all(self._environment)
        
        # Handle validation results based on environment
        if validation_summary.has_errors:
            if self._validation_service.should_fail_on_errors(self._environment):
                error_messages = [f"{r.field}: {r.message}" for r in validation_summary.errors]
                raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")
            else:
                # Log errors as warnings for non-production
                for error in validation_summary.errors:
                    warnings.warn(f"Configuration error for {error.field}: {error.message}", UserWarning)
        
        # Always log warnings
        for warning in validation_summary.warnings:
            warnings.warn(f"Configuration warning for {warning.field}: {warning.message}", UserWarning)
    
    @property
    def environment(self) -> str:
        """Get current environment."""
        return self._base_config.environment if self._base_config else "unknown"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self._environment == Environment.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._environment == Environment.PRODUCTION
    
    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self._environment == Environment.TEST
    
    @property
    def database_dsn(self) -> str:
        """Get database connection string."""
        if not self._database_service or not self._environment:
            raise RuntimeError("Services not initialized")
        return self._database_service.build_dsn(self._environment)
    
    @property
    def redis_dsn(self) -> str:
        """Get Redis connection string."""
        if not self._base_config:
            raise RuntimeError("Configuration not loaded")
        
        if self._base_config.redis_url:
            return self._base_config.redis_url
        
        password_part = f":{self._base_config.redis_password}@" if self._base_config.redis_password else ""
        return f"redis://{password_part}{self._base_config.redis_host}:{self._base_config.redis_port}/{self._base_config.redis_db}"
    
    @property
    def oauth_callback_url(self) -> str:
        """Get OAuth callback URL."""
        if not self._base_config:
            raise RuntimeError("Configuration not loaded")
        
        if self._base_config.oauth_redirect_url:
            return self._base_config.oauth_redirect_url
        return f"{self._base_config.frontend_url}/auth/callback"
    
    @property
    def has_supabase_config(self) -> bool:
        """Check if Supabase configuration is complete."""
        if not self._base_config:
            return False
        
        return all([
            self._base_config.supabase_url,
            self._base_config.supabase_anon_key,
            self._base_config.supabase_service_role_key
        ])
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get configuration suitable for logging/debugging."""
        if not self._base_config:
            raise RuntimeError("Configuration not loaded")
        
        # Get base config
        safe_config = {}
        base_dict = self._base_config.model_dump()
        
        # Define sensitive fields
        sensitive_fields = {
            "openai_api_key", "supabase_service_role_key", "supabase_anon_key", 
            "supabase_jwt_secret", "google_client_secret", "apple_private_key_path",
            "facebook_app_secret", "tiktok_client_secret", "smtp_password",
            "redis_password"
        }
        
        for field_name, field_value in base_dict.items():
            if field_name in sensitive_fields:
                safe_config[field_name] = "***REDACTED***" if field_value else None
            else:
                safe_config[field_name] = field_value
        
        # Add service configs
        if self._database_service:
            safe_config.update(self._database_service.get_safe_config())
        
        if self._security_service:
            safe_config.update(self._security_service.get_safe_config())
        
        return safe_config
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment-specific information for debugging."""
        if not self._base_config:
            raise RuntimeError("Configuration not loaded")
        
        info = {
            "environment": self.environment,
            "is_development": self.is_development,
            "is_production": self.is_production,
            "is_testing": self.is_testing,
            "debug": self._base_config.debug,
            "has_supabase": self.has_supabase_config,
            "has_redis": bool(self._base_config.redis_url or self._base_config.redis_host),
            "has_smtp": bool(self._base_config.smtp_host),
        }
        
        # Add security features info
        if self._security_service:
            security_summary = self._security_service.get_security_summary()
            info["security_features"] = security_summary["security_features"]
        
        return info
    
    def reload(self) -> None:
        """Reload configuration from environment."""
        self._load_configuration()
        self._initialize_services()
        self._setup_validation()
        self._validate_configuration()
    
    def get_validation_report(self) -> str:
        """Get detailed validation report."""
        if not self._validation_service or not self._environment:
            return "Validation service not available"
        
        summary = self._validation_service.validate_all(self._environment)
        return self._validation_service.get_validation_report(summary)
    
    # Compatibility methods for existing code
    def model_dump(self) -> Dict[str, Any]:
        """Compatibility method - return all configuration."""
        if not self._base_config:
            raise RuntimeError("Configuration not loaded")
        
        config = self._base_config.model_dump()
        
        # Add derived properties
        config["database_dsn"] = self.database_dsn
        config["redis_dsn"] = self.redis_dsn
        config["oauth_callback_url"] = self.oauth_callback_url
        config["has_supabase_config"] = self.has_supabase_config
        
        return config
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to base config and services for compatibility."""
        # First try base config
        if self._base_config and hasattr(self._base_config, name):
            return getattr(self._base_config, name)
        
        # Try security service for security-related fields
        if self._security_service and hasattr(self._security_service.config, name):
            return getattr(self._security_service.config, name)
        
        # Try database service for database-related fields  
        if self._database_service and hasattr(self._database_service.config, name):
            return getattr(self._database_service.config, name)
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")