"""
Integration Tests for Multi-Environment Configuration System

Tests the complete environment-specific configuration system including
environment detection, inheritance, validation, and hot-reloading.
"""

import os
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from app.core.environment import (
    Environment, EnvironmentDetector, get_environment, reset_detection_cache
)
from app.core.config_inheritance import (
    ConfigurationInheritance, apply_config_inheritance, set_production_baseline
)
from app.core.env_validators import (
    EnvironmentValidationFramework, validate_environment_config, 
    ValidationSeverity, SecurityLevelValidator, URLValidator
)
from app.core.hot_reload import ConfigurationHotReloader
from app.core.config import Settings


class TestEnvironmentDetection:
    """Test environment detection functionality."""
    
    def setup_method(self):
        """Reset environment detection before each test."""
        reset_detection_cache()
    
    def test_environment_detection_from_environment_var(self):
        """Test detection from ENVIRONMENT variable."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            reset_detection_cache()
            assert get_environment() == Environment.PRODUCTION
    
    def test_environment_detection_from_node_env(self):
        """Test detection from NODE_ENV variable."""
        with patch.dict(os.environ, {"NODE_ENV": "staging"}, clear=True):
            reset_detection_cache()
            assert get_environment() == Environment.STAGING
    
    def test_environment_precedence(self):
        """Test that ENVIRONMENT takes precedence over NODE_ENV."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "NODE_ENV": "development"
        }):
            reset_detection_cache()
            assert get_environment() == Environment.PRODUCTION
    
    def test_invalid_environment_value(self):
        """Test handling of invalid environment values."""
        with patch.dict(os.environ, {"ENVIRONMENT": "invalid"}):
            reset_detection_cache()
            # Should fall back to default
            assert get_environment() == Environment.DEVELOPMENT
    
    def test_context_based_detection(self):
        """Test context-based environment detection."""
        detector = EnvironmentDetector()
        
        # Mock pytest context
        with patch('sys.modules', {"pytest": MagicMock()}):
            env = detector.detect_environment()
            assert env == Environment.TEST
    
    def test_environment_consistency_validation(self):
        """Test validation of environment variable consistency."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "NODE_ENV": "development"
        }):
            detector = EnvironmentDetector()
            reset_detection_cache()
            issues = detector.validate_environment_consistency()
            assert len(issues) > 0
            assert "Conflicting environment variables" in issues[0]


class TestConfigurationInheritance:
    """Test configuration inheritance system."""
    
    def test_staging_inherits_from_production(self):
        """Test that staging inherits security settings from production."""
        production_config = {
            "password_min_length": 12,
            "require_email_verification": True,
            "csrf_protection_enabled": True,
            "secret_key": "production-secret-key",
            "debug": False,
        }
        
        staging_config = {
            "password_min_length": 8,  # Should be overridden
            "debug": True,             # Should be kept (override)
            "secret_key": "staging-secret-key",  # Should be kept (excluded)
        }
        
        inheritance = ConfigurationInheritance()
        inheritance.set_production_config(production_config)
        
        result = inheritance.apply_inheritance(staging_config, Environment.STAGING)
        
        # Should inherit security settings
        assert result["password_min_length"] == 12
        assert result["csrf_protection_enabled"] == True
        
        # Should keep excluded fields
        assert result["secret_key"] == "staging-secret-key"
        
        # Should apply overrides (staging has require_email_verification: False as override)
        assert result["debug"] == True
        assert result["require_email_verification"] == False  # Staging override
    
    def test_inheritance_validation(self):
        """Test validation of inheritance application."""
        production_config = {
            "secret_key": "production-secret",
            "password_min_length": 12,
        }
        
        staging_config = {
            "secret_key": "production-secret",  # This should trigger a warning
            "password_min_length": 12,
        }
        
        inheritance = ConfigurationInheritance()
        inheritance.set_production_config(production_config)
        
        issues = inheritance.validate_inheritance(staging_config, Environment.STAGING)
        
        # Should detect sensitive field inheritance
        sensitive_issues = [i for i in issues if "secret_key" in i]
        assert len(sensitive_issues) > 0
    
    def test_no_inheritance_for_development(self):
        """Test that development environment doesn't inherit."""
        production_config = {"password_min_length": 12}
        dev_config = {"password_min_length": 8}
        
        inheritance = ConfigurationInheritance()
        inheritance.set_production_config(production_config)
        
        result = inheritance.apply_inheritance(dev_config, Environment.DEVELOPMENT)
        
        # Should not change development config
        assert result["password_min_length"] == 8


class TestEnvironmentValidation:
    """Test environment-specific validation rules."""
    
    def test_password_length_validation_by_environment(self):
        """Test password length requirements by environment."""
        validator = SecurityLevelValidator("password_min_length", 12, 10, 8)
        
        # Production should require 12
        results = validator.validate(8, Environment.PRODUCTION)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        
        # Staging should require 10
        results = validator.validate(8, Environment.STAGING)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.WARNING
        
        # Development should require 8
        results = validator.validate(8, Environment.DEVELOPMENT)
        assert len(results) == 0
    
    def test_url_validation_by_environment(self):
        """Test URL validation requirements by environment."""
        validator = URLValidator("api_url")
        
        # Production should require HTTPS
        results = validator.validate("http://api.example.com", Environment.PRODUCTION)
        assert len(results) == 1
        assert "HTTPS" in results[0].message
        
        # Development should allow HTTP
        results = validator.validate("http://localhost:8000", Environment.DEVELOPMENT)
        assert len(results) == 0
        
        # Production should reject localhost
        results = validator.validate("https://localhost:8000", Environment.PRODUCTION)
        assert len(results) == 1
        assert "localhost" in results[0].message
    
    def test_comprehensive_config_validation(self):
        """Test complete configuration validation."""
        framework = EnvironmentValidationFramework()
        
        production_config = {
            "password_min_length": 8,  # Too low for production
            "secret_key": "dev-secret-key",  # Weak key
            "supabase_url": "http://localhost:3000",  # HTTP + localhost
            "debug": True,  # Should be False
        }
        
        results = framework.validate_config(production_config, Environment.PRODUCTION)
        
        # Should have multiple errors
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 3
        
        # Check specific validation issues
        field_names = [r.field for r in errors]
        assert "password_min_length" in field_names
        assert "secret_key" in field_names
        assert "supabase_url" in field_names


class TestHotReloading:
    """Test configuration hot-reloading functionality."""
    
    def test_hot_reloader_initialization(self):
        """Test hot-reloader can be initialized."""
        reloader = ConfigurationHotReloader()
        assert not reloader.is_running()
        assert reloader.get_status()["callback_count"] == 0
    
    def test_hot_reloader_callbacks(self):
        """Test adding and removing reload callbacks."""
        reloader = ConfigurationHotReloader()
        
        callback_called = False
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        reloader.add_reload_callback(test_callback)
        assert reloader.get_status()["callback_count"] == 1
        
        # Trigger reload
        reloader._handle_reload()
        assert callback_called
        
        # Remove callback
        reloader.remove_reload_callback(test_callback)
        assert reloader.get_status()["callback_count"] == 0
    
    def test_environment_variable_watching(self):
        """Test environment variable change detection."""
        from app.core.hot_reload import EnvironmentVariableWatcher
        
        callback_called = False
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        watcher = EnvironmentVariableWatcher(test_callback, {"TEST_VAR"})
        
        # Simulate environment variable change
        with patch.dict(os.environ, {"TEST_VAR": "new_value"}):
            watcher._check_variables()
        
        assert callback_called


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    def test_development_environment_setup(self):
        """Test complete development environment configuration."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "SECRET_KEY": "dev-secret-key-that-is-long-enough-for-validation",
            "DATABASE_URL": "sqlite:///dev.db",
        }):
            reset_detection_cache()
            
            # Environment detection should work
            assert get_environment() == Environment.DEVELOPMENT
            
            # Configuration should load without errors
            settings = Settings()
            assert settings.environment == "development"
            assert settings.debug == True
            
            # Validation should pass with warnings only
            framework = EnvironmentValidationFramework()
            results = framework.validate_config(settings.model_dump(), Environment.DEVELOPMENT)
            errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
            assert len(errors) == 0  # No errors in development
    
    def test_staging_environment_with_inheritance(self):
        """Test staging environment with production inheritance."""
        # Setup production baseline
        production_config = {
            "password_min_length": 12,
            "require_email_verification": True,
            "csrf_protection_enabled": True,
            "rate_limiting_enabled": True,
        }
        set_production_baseline(production_config)
        
        with patch.dict(os.environ, {
            "ENVIRONMENT": "staging",
            "SECRET_KEY": "staging-secret-key-with-sufficient-length",
            "DEBUG": "false",
            "SUPABASE_URL": "https://staging.supabase.co",
        }):
            reset_detection_cache()
            
            # Environment detection
            assert get_environment() == Environment.STAGING
            
            # Configuration with inheritance
            base_config = {
                "password_min_length": 8,  # Should be inherited to 12
                "secret_key": "staging-secret-key-with-sufficient-length",
                "debug": False,
                "supabase_url": "https://staging.supabase.co",
            }
            
            inherited_config = apply_config_inheritance(base_config, Environment.STAGING)
            
            # Should inherit production security settings
            assert inherited_config["password_min_length"] == 12
            assert inherited_config["require_email_verification"] == True
            
            # Validation should pass
            framework = EnvironmentValidationFramework()
            results = framework.validate_config(inherited_config, Environment.STAGING)
            errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
            assert len(errors) == 0
    
    def test_production_environment_strict_validation(self):
        """Test production environment with strict validation."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "production-secret-key-that-is-long-enough-and-secure-1234567890",
            "DEBUG": "false",
            "SUPABASE_URL": "https://api.duolingoclone.com",
            "DATABASE_URL": "postgresql://user:pass@prod-db:5432/duolingo",
        }):
            reset_detection_cache()
            
            # Environment detection
            assert get_environment() == Environment.PRODUCTION
            
            # Configuration should meet production standards
            config = {
                "password_min_length": 12,
                "secret_key": "production-secret-key-that-is-long-enough-and-secure-1234567890",
                "debug": False,
                "supabase_url": "https://api.duolingoclone.com",
                "require_email_verification": True,
                "csrf_protection_enabled": True,
                "rate_limiting_enabled": True,
            }
            
            # Validation should pass
            framework = EnvironmentValidationFramework()
            results = framework.validate_config(config, Environment.PRODUCTION)
            errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
            assert len(errors) == 0
    
    def test_configuration_validation_summary(self):
        """Test configuration validation summary functionality."""
        framework = EnvironmentValidationFramework()
        
        # Config with multiple issues
        config = {
            "password_min_length": 6,  # Too low
            "secret_key": "weak",      # Too weak
            "debug": True,             # Wrong for production
        }
        
        results = framework.validate_config(config, Environment.PRODUCTION)
        summary = framework.get_validation_summary(results)
        
        assert summary["total_issues"] > 0
        assert summary["errors"] > 0
        assert not summary["is_valid"]
        assert len(summary["error_fields"]) > 0
        assert "password_min_length" in summary["error_fields"]


class TestEnvironmentTransitions:
    """Test configuration changes when transitioning between environments."""
    
    def test_development_to_production_transition(self):
        """Test configuration issues when moving from dev to production."""
        # Development config
        dev_config = {
            "password_min_length": 8,
            "secret_key": "dev-secret-key",
            "debug": True,
            "supabase_url": "http://localhost:3000",
            "require_email_verification": False,
        }
        
        # Validate as production
        framework = EnvironmentValidationFramework()
        results = framework.validate_config(dev_config, Environment.PRODUCTION)
        
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        
        # Should have multiple errors for production
        assert len(errors) >= 4
        
        # Check specific issues
        field_names = [r.field for r in errors]
        assert "password_min_length" in field_names
        assert "secret_key" in field_names
        assert "debug" in field_names
        assert "supabase_url" in field_names
    
    def test_environment_specific_recommendations(self):
        """Test that validation provides environment-specific recommendations."""
        validator = SecurityLevelValidator("password_min_length", 12, 10, 8)
        
        # Get recommendation for production
        results = validator.validate(8, Environment.PRODUCTION)
        assert results[0].suggestion is not None
        assert "12" in results[0].suggestion
        
        # Get recommendation for staging
        results = validator.validate(6, Environment.STAGING)
        assert results[0].suggestion is not None
        assert "10" in results[0].suggestion


# Integration test fixtures
@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for configuration files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_production_config():
    """Sample production configuration."""
    return {
        "password_min_length": 12,
        "require_email_verification": True,
        "csrf_protection_enabled": True,
        "rate_limiting_enabled": True,
        "secret_key": "production-secret-key-that-is-very-long-and-secure",
        "debug": False,
        "supabase_url": "https://api.duolingoclone.com",
        "database_url": "postgresql://user:pass@prod-db:5432/duolingo",
    }


@pytest.fixture
def sample_staging_config():
    """Sample staging configuration."""
    return {
        "password_min_length": 8,
        "require_email_verification": False,
        "secret_key": "staging-secret-key-that-is-long-enough",
        "debug": True,
        "supabase_url": "https://staging.duolingoclone.com",
        "database_url": "postgresql://user:pass@staging-db:5432/duolingo",
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])