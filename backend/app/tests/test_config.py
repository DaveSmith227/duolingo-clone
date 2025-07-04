"""
Configuration Tests

Test suite for environment configuration management and validation.
Ensures configuration loads correctly and validates required settings.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestSettings:
    """Test configuration settings and validation."""
    
    def test_default_settings(self):
        """Test that default settings load correctly."""
        settings = Settings()
        
        assert settings.app_name == "Duolingo Clone API"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.is_development is True
        assert settings.is_production is False
    
    def test_environment_validation_valid(self):
        """Test valid environment values."""
        valid_environments = ["development", "staging", "production", "test"]
        
        for env in valid_environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                settings = Settings()
                assert settings.environment == env
    
    def test_environment_validation_invalid(self):
        """Test invalid environment value raises error."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Environment must be one of" in str(exc_info.value)
    
    def test_log_level_validation_valid(self):
        """Test valid log level values."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            with patch.dict(os.environ, {"LOG_LEVEL": level.lower()}):
                settings = Settings()
                assert settings.log_level == level.upper()
    
    def test_log_level_validation_invalid(self):
        """Test invalid log level raises error."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "Log level must be one of" in str(exc_info.value)
    
    def test_secret_key_validation_length(self):
        """Test secret key length validation."""
        with patch.dict(os.environ, {"SECRET_KEY": "short"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            
            assert "SECRET_KEY must be at least 32 characters long" in str(exc_info.value)
    
    def test_secret_key_validation_valid(self):
        """Test valid secret key passes validation."""
        valid_key = "a" * 32  # 32 character key
        with patch.dict(os.environ, {"SECRET_KEY": valid_key}):
            settings = Settings()
            assert settings.secret_key == valid_key
    
    def test_cors_origins_environment_override(self):
        """Test CORS origins can be overridden with environment variable."""
        # For simplicity, we'll test with JSON format for list environment variables
        import json
        origins_list = ["http://localhost:3000", "https://example.com"]
        origins_json = json.dumps(origins_list)
        
        with patch.dict(os.environ, {"CORS_ORIGINS": origins_json}):
            settings = Settings()
            assert settings.cors_origins == origins_list
    
    def test_database_dsn_from_url(self):
        """Test database DSN construction from DATABASE_URL."""
        database_url = "postgresql://user:pass@host:5432/dbname"
        
        with patch.dict(os.environ, {"DATABASE_URL": database_url}):
            settings = Settings()
            assert settings.database_dsn == database_url
    
    def test_database_dsn_from_components(self):
        """Test database DSN construction from individual components."""
        env_vars = {
            "DB_HOST": "testhost",
            "DB_PORT": "5433",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            expected_dsn = "postgresql://testuser:testpass@testhost:5433/testdb"
            assert settings.database_dsn == expected_dsn
    
    def test_redis_dsn_from_url(self):
        """Test Redis DSN construction from REDIS_URL."""
        redis_url = "redis://user:pass@host:6379/1"
        
        with patch.dict(os.environ, {"REDIS_URL": redis_url}):
            settings = Settings()
            assert settings.redis_dsn == redis_url
    
    def test_redis_dsn_from_components(self):
        """Test Redis DSN construction from individual components."""
        env_vars = {
            "REDIS_HOST": "testhost",
            "REDIS_PORT": "6380",
            "REDIS_DB": "2"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            expected_dsn = "redis://testhost:6380/2"
            assert settings.redis_dsn == expected_dsn
    
    def test_redis_dsn_with_password(self):
        """Test Redis DSN construction with password."""
        env_vars = {
            "REDIS_HOST": "testhost",
            "REDIS_PORT": "6379",
            "REDIS_PASSWORD": "testpass",
            "REDIS_DB": "0"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            expected_dsn = "redis://:testpass@testhost:6379/0"
            assert settings.redis_dsn == expected_dsn
    
    def test_environment_property_development(self):
        """Test environment property methods for development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False
    
    def test_environment_property_production(self):
        """Test environment property methods for production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is True
            assert settings.is_testing is False
    
    def test_environment_property_test(self):
        """Test environment property methods for test."""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is False
            assert settings.is_testing is True
    
    def test_environment_property_staging(self):
        """Test environment property methods for staging."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is False
            assert settings.is_testing is False


class TestGetSettings:
    """Test the get_settings function."""
    
    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_consistency(self):
        """Test that get_settings returns consistent instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should return the same global instance
        assert settings1 is settings2


class TestConfigurationIntegration:
    """Integration tests for configuration system."""
    
    def test_configuration_loads_in_test_environment(self):
        """Test configuration loads correctly in test environment."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "test",
            "SECRET_KEY": "test-secret-key-32-characters-long",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db"
        }):
            settings = Settings()
            
            assert settings.environment == "test"
            assert settings.is_testing is True
            assert settings.database_dsn == "postgresql://test:test@localhost:5432/test_db"
    
    def test_production_configuration_requirements(self):
        """Test production environment has required security settings."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "production-secret-key-32-chars-long",
            "DEBUG": "false"
        }):
            settings = Settings()
            
            assert settings.environment == "production"
            assert settings.debug is False
            assert settings.is_production is True
            assert len(settings.secret_key) >= 32
    
    def test_env_file_loading(self):
        """Test that .env file loading is configured."""
        settings = Settings()
        
        # Check that model_config has env_file setting
        assert hasattr(settings, 'model_config')
        assert 'env_file' in settings.model_config
    
    @pytest.mark.parametrize("env_var,expected_type", [
        ("PORT", int),
        ("DEBUG", bool),
        ("DB_PORT", int),
        ("REDIS_PORT", int),
        ("JWT_EXPIRATION_HOURS", int),
        ("CORS_ALLOW_CREDENTIALS", bool),
    ])
    def test_type_coercion(self, env_var, expected_type):
        """Test that environment variables are properly type-coerced."""
        # Test with string values that should be converted
        test_values = {
            "PORT": "9000",
            "DEBUG": "true",
            "DB_PORT": "5433",
            "REDIS_PORT": "6380",
            "JWT_EXPIRATION_HOURS": "48",
            "CORS_ALLOW_CREDENTIALS": "false",
        }
        
        with patch.dict(os.environ, {env_var: test_values[env_var]}):
            settings = Settings()
            value = getattr(settings, env_var.lower())
            assert isinstance(value, expected_type)