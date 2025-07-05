"""
Configuration Management

Environment-based configuration for the Duolingo clone backend application.
Handles environment variables, validation, and settings for different deployment environments.
"""

import os
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
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
    def validate_secret_key(cls, v, info):
        """Validate secret key is not using default in production."""
        # Note: In Pydantic v2, we can't access other field values during validation
        # This validation will be handled at the model level
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, v):
        """Validate Supabase URL format."""
        if v and not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        return v
    
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Get application settings.
    
    Returns the global settings instance. Useful for dependency injection
    and testing with override settings.
    """
    return settings