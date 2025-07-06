"""
Tests for Configuration Management

Comprehensive test suite for the configuration module including
environment validation, error handling, and security checks.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.core.config import (
    Settings, 
    get_settings, 
    reload_settings,
    validate_config_for_environment,
    _create_settings
)


@pytest.fixture(autouse=True)
def isolate_environment():
    """Isolate environment variables for each test."""
    # Clear environment variables that affect configuration
    env_vars_to_clear = [
        'ENVIRONMENT', 'NODE_ENV', 'APP_ENV', 'DEPLOY_ENV',
        'DEBUG', 'SECRET_KEY', 'DATABASE_URL'
    ]
    
    original_env = {}
    for var in env_vars_to_clear:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original environment
    for var, value in original_env.items():
        os.environ[var] = value


def get_valid_production_config():
    """Get a valid production configuration for testing."""
    return {
        "ENVIRONMENT": "production",
        "SECRET_KEY": "a" * 32,
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "DEBUG": "false",
        "PASSWORD_MIN_LENGTH": "12",
        "REQUIRE_EMAIL_VERIFICATION": "true",
        "CSRF_PROTECTION_ENABLED": "true",
        "CORS_ORIGINS": "https://myapp.com",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db"
    }


class TestSettings:
    """Test the Settings class configuration loading and validation."""
    
    def test_default_settings(self):
        """Test default settings are loaded correctly."""
        # Explicitly set development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings(_env_file=None)
            assert settings.app_name == "Duolingo Clone API"
            assert settings.app_version == "0.1.0"
            assert settings.environment == "development"
            assert settings.debug is False
            assert settings.secret_key == "dev-secret-key-change-in-production"
    
    def test_environment_validation(self):
        """Test environment validation."""
        # Valid environments
        for env in ["development", "staging", "production", "test"]:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                settings = Settings(_env_file=None)
                assert settings.environment == env
        
        # Invalid environment
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Environment must be one of" in str(exc_info.value)
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid log levels (case insensitive)
        for level in ["debug", "INFO", "Warning", "ERROR", "CRITICAL"]:
            with patch.dict(os.environ, {"LOG_LEVEL": level}):
                settings = Settings(_env_file=None)
                assert settings.log_level == level.upper()
        
        # Invalid log level
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Log level must be one of" in str(exc_info.value)
    
    def test_secret_key_validation(self):
        """Test secret key validation."""
        # Valid secret key
        with patch.dict(os.environ, {"SECRET_KEY": "a" * 32}):
            settings = Settings(_env_file=None)
            assert len(settings.secret_key) == 32
        
        # Too short secret key
        with patch.dict(os.environ, {"SECRET_KEY": "short"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "at least 32 characters" in str(exc_info.value)
    
    def test_supabase_url_validation(self):
        """Test Supabase URL validation."""
        # Valid HTTPS URL
        with patch.dict(os.environ, {"SUPABASE_URL": "https://project.supabase.co"}):
            settings = Settings(_env_file=None)
            assert settings.supabase_url == "https://project.supabase.co"
        
        # Invalid HTTP URL
        with patch.dict(os.environ, {"SUPABASE_URL": "http://project.supabase.co"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "must start with https://" in str(exc_info.value)
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation."""
        # Valid origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,https://example.com"}):
            settings = Settings(_env_file=None)
            assert len(settings.cors_origins) == 2
        
        # Invalid origin
        with patch.dict(os.environ, {"CORS_ORIGINS": "invalid-url"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "CORS origin must be a valid URL" in str(exc_info.value)
    
    def test_host_validation(self):
        """Test host validation."""
        # Valid hosts
        with patch.dict(os.environ, {"REDIS_HOST": "localhost", "DB_HOST": "192.168.1.1"}):
            settings = Settings(_env_file=None)
            assert settings.redis_host == "localhost"
            assert settings.db_host == "192.168.1.1"
        
        # Empty host
        with patch.dict(os.environ, {"REDIS_HOST": ""}):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Host cannot be empty" in str(exc_info.value)


class TestEnvironmentSpecificValidation:
    """Test environment-specific validation rules."""
    
    def test_production_validation(self):
        """Test production environment validation."""
        # Invalid production config (using defaults)
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "dev-secret-key-change-in-production"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "SECRET_KEY must be changed in production" in str(exc_info.value)
        
        # Missing Supabase config
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Supabase configuration is required" in str(exc_info.value)
        
        # Debug enabled in production
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-key",
            "DEBUG": "true"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "DEBUG must be False in production" in str(exc_info.value)
        
        # Weak password settings
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "a" * 32,
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-key",
            "PASSWORD_MIN_LENGTH": "6"
        }):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Password minimum length must be at least 10" in str(exc_info.value)
        
        # Email verification disabled
        config = get_valid_production_config()
        config["REQUIRE_EMAIL_VERIFICATION"] = "false"
        with patch.dict(os.environ, config):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Email verification must be enabled" in str(exc_info.value)
        
        # CSRF disabled
        config = get_valid_production_config()
        config["CSRF_PROTECTION_ENABLED"] = "false"
        with patch.dict(os.environ, config):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "CSRF protection must be enabled" in str(exc_info.value)
    
    def test_staging_warnings(self):
        """Test staging environment warnings."""
        # Should not raise, but log warnings
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "SECRET_KEY": "staging-key-32-chars-minimum-test",
            "DEBUG": "true"  # This should trigger warning
        }):
            settings = Settings(_env_file=None)
            assert settings.environment == "staging"
            assert settings.debug is True
    
    def test_development_relaxed_rules(self):
        """Test development environment allows relaxed settings."""
        # All of these should be allowed in development
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "dev-secret-key-change-in-production",
            "DEBUG": "true",
            "REQUIRE_EMAIL_VERIFICATION": "false",
            "PASSWORD_MIN_LENGTH": "6",
            "CSRF_PROTECTION_ENABLED": "false"
        }):
            settings = Settings(_env_file=None)
            assert settings.environment == "development"
            assert settings.debug is True
    
    def test_test_environment(self):
        """Test test environment configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "RATE_LIMITING_ENABLED": "true"  # Should trigger warning
        }):
            settings = Settings(_env_file=None)
            assert settings.environment == "test"


class TestDatabaseConfiguration:
    """Test database configuration validation."""
    
    def test_database_dsn_with_url(self):
        """Test database DSN when DATABASE_URL is provided."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            settings = Settings(_env_file=None)
            assert settings.database_dsn == "postgresql://user:pass@host:5432/db"
    
    def test_database_dsn_development(self):
        """Test database DSN defaults to SQLite in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings(_env_file=None)
            assert settings.database_dsn == "sqlite:///./app.db"
    
    def test_database_dsn_production(self):
        """Test database DSN construction for production."""
        config = get_valid_production_config()
        config.update({
            "DB_HOST": "prod-db",
            "DB_PORT": "5432",
            "DB_NAME": "prod_db", 
            "DB_USER": "prod_user",
            "DB_PASSWORD": "prod_pass"
        })
        # Remove DATABASE_URL to test construction
        if "DATABASE_URL" in config:
            del config["DATABASE_URL"]
            
        with patch.dict(os.environ, config):
            settings = Settings(_env_file=None)
            expected = "postgresql://prod_user:prod_pass@prod-db:5432/prod_db"
            assert settings.database_dsn == expected
    
    def test_production_missing_db_config(self):
        """Test production validation with missing database config."""
        # Should raise validation error
        config = get_valid_production_config()
        # Remove DATABASE_URL and DB_PASSWORD to trigger validation error
        if "DATABASE_URL" in config:
            del config["DATABASE_URL"]
        config["DB_PASSWORD"] = ""
        
        with patch.dict(os.environ, config):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)
            assert "Missing database configuration" in str(exc_info.value)


class TestRedisConfiguration:
    """Test Redis configuration."""
    
    def test_redis_dsn_with_url(self):
        """Test Redis DSN when REDIS_URL is provided."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://user:pass@host:6379/0"}):
            settings = Settings(_env_file=None)
            assert settings.redis_dsn == "redis://user:pass@host:6379/0"
    
    def test_redis_dsn_construction(self):
        """Test Redis DSN construction from components."""
        with patch.dict(os.environ, {
            "REDIS_HOST": "redis-server",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "secret",
            "REDIS_DB": "2"
        }):
            settings = Settings(_env_file=None)
            assert settings.redis_dsn == "redis://:secret@redis-server:6380/2"
    
    def test_redis_dsn_no_password(self):
        """Test Redis DSN without password."""
        with patch.dict(os.environ, {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "0"
        }):
            settings = Settings(_env_file=None)
            assert settings.redis_dsn == "redis://localhost:6379/0"


class TestConfigurationHelpers:
    """Test configuration helper methods."""
    
    def test_is_environment_properties(self):
        """Test environment property helpers."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            dev_settings = Settings(_env_file=None)
            assert dev_settings.is_development is True
            assert dev_settings.is_production is False
            assert dev_settings.is_testing is False
        
        config = get_valid_production_config()
        with patch.dict(os.environ, config):
            prod_settings = Settings(_env_file=None)
            assert prod_settings.is_development is False
            assert prod_settings.is_production is True
            assert prod_settings.is_testing is False
    
    def test_oauth_callback_url(self):
        """Test OAuth callback URL construction."""
        # Default callback
        with patch.dict(os.environ, {"FRONTEND_URL": "https://example.com"}):
            settings = Settings(_env_file=None)
            assert settings.oauth_callback_url == "https://example.com/auth/callback"
        
        # Custom callback
        with patch.dict(os.environ, {
            "FRONTEND_URL": "https://example.com",
            "OAUTH_REDIRECT_URL": "https://custom.com/oauth"
        }):
            settings = Settings(_env_file=None)
            assert settings.oauth_callback_url == "https://custom.com/oauth"
    
    def test_has_supabase_config(self):
        """Test Supabase configuration check."""
        # Missing config
        settings = Settings(_env_file=None)
        assert settings.has_supabase_config is False
        
        # Complete config
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key"
        }):
            settings = Settings(_env_file=None)
            assert settings.has_supabase_config is True
    
    def test_get_safe_config(self):
        """Test safe configuration export."""
        with patch.dict(os.environ, {
            "SECRET_KEY": "super-secret-key-32-chars-minimum",
            "DB_PASSWORD": "password123",
            "OPENAI_API_KEY": "sk-test",
            "APP_NAME": "Test App"
        }):
            settings = Settings(_env_file=None)
        
        safe_config = settings.get_safe_config()
        
        # Sensitive fields should be redacted
        assert safe_config["secret_key"] == "***REDACTED***"
        assert safe_config["db_password"] == "***REDACTED***"
        assert safe_config["openai_api_key"] == "***REDACTED***"
        
        # Non-sensitive fields should be visible
        assert safe_config["app_name"] == "Test App"
        assert safe_config["environment"] == "development"
    
    def test_get_environment_info(self):
        """Test environment info export."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "DEBUG": "true",
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "key",
            "SUPABASE_SERVICE_ROLE_KEY": "service-key",
            "REDIS_HOST": "localhost"
        }):
            settings = Settings(_env_file=None)
        
        info = settings.get_environment_info()
        
        assert info["environment"] == "staging"
        assert info["is_development"] is False
        assert info["is_production"] is False
        assert info["debug"] is True
        assert info["has_supabase"] is True
        assert info["has_redis"] is True
        assert info["security_features"]["rate_limiting"] is True


class TestConfigurationLoading:
    """Test configuration loading and error handling."""
    
    @patch.dict(os.environ, {"SECRET_KEY": "env-secret-key-32-chars-minimum!"})
    def test_env_loading(self):
        """Test loading configuration from environment variables."""
        settings = Settings(_env_file=None)
        assert settings.secret_key == "env-secret-key-32-chars-minimum!"
    
    def test_create_settings_validation_error(self):
        """Test _create_settings handles validation errors."""
        # Force a validation error by setting invalid environment
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValidationError):
                _create_settings()
    
    @patch("app.core.config.Settings")
    def test_create_settings_generic_error(self, mock_settings):
        """Test _create_settings handles generic errors."""
        mock_settings.side_effect = Exception("Generic error")
        
        with pytest.raises(Exception) as exc_info:
            _create_settings()
        assert "Generic error" in str(exc_info.value)
    
    def test_get_settings(self):
        """Test get_settings returns singleton."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
    
    def test_reload_settings(self):
        """Test reload_settings updates configuration."""
        # Set initial environment
        with patch.dict(os.environ, {"APP_NAME": "Original"}):
            original_settings = get_settings()
            assert original_settings.app_name == "Original"
        
        # Change environment and reload
        with patch.dict(os.environ, {"APP_NAME": "Updated"}):
            new_settings = reload_settings()
            assert new_settings.app_name == "Updated"
            
            # Verify singleton is updated
            assert get_settings().app_name == "Updated"


class TestValidateConfigForEnvironment:
    """Test environment-specific configuration validation."""
    
    @patch("app.core.config.settings")
    def test_validate_production_issues(self, mock_settings):
        """Test validation issues for production environment."""
        mock_settings.secret_key = "dev-secret-key-change-in-production"
        mock_settings.has_supabase_config = False
        mock_settings.debug = True
        mock_settings.smtp_host = None
        mock_settings.require_email_verification = False
        mock_settings.cors_origins = ["http://localhost:3000"]
        
        issues = validate_config_for_environment("production")
        
        assert "SECRET_KEY is using default value" in issues
        assert "Supabase configuration is incomplete" in issues
        assert "DEBUG mode is enabled" in issues
        assert "Email server not configured" in issues
        assert "Email verification is disabled" in issues
        assert "CORS origins contain localhost" in issues
    
    @patch("app.core.config.settings")
    def test_validate_staging_issues(self, mock_settings):
        """Test validation issues for staging environment."""
        mock_settings.has_supabase_config = False
        mock_settings.debug = True
        
        issues = validate_config_for_environment("staging")
        
        assert "Supabase configuration is incomplete" in issues
        assert "DEBUG mode is enabled (warning)" in issues
    
    @patch("app.core.config.settings")
    def test_validate_development_no_issues(self, mock_settings):
        """Test development environment has no validation issues."""
        # Development should have no required validations
        issues = validate_config_for_environment("development")
        assert len(issues) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])