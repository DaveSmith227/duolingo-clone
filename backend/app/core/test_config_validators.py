"""
Tests for Enhanced Configuration Validators with Business Rules

Tests the custom configuration validators, business rule validators,
and cross-field validation capabilities.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
from pydantic import ValidationError

from app.core.config_validators import (
    DatabaseURLValidator, EmailConfigValidator, CORSOriginsValidator,
    JWTConfigValidator, RateLimitValidator, DatabasePoolValidator,
    SecurityConsistencyValidator, SupabaseConfigValidator,
    ConfigurationBusinessRuleValidator
)
from app.core.env_validators import ValidationSeverity, Environment
from app.core.config import Settings


class TestDatabaseURLValidator:
    """Test database URL validation."""
    
    def test_valid_postgresql_url(self):
        """Test valid PostgreSQL URL."""
        validator = DatabaseURLValidator()
        results = validator.validate(
            "postgresql://user:pass@localhost:5432/dbname",
            Environment.DEVELOPMENT
        )
        assert len(results) == 0
    
    def test_sqlite_not_allowed_in_production(self):
        """Test SQLite is not allowed in production."""
        validator = DatabaseURLValidator()
        results = validator.validate(
            "sqlite:///app.db",
            Environment.PRODUCTION
        )
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("SQLite is not allowed" in r.message for r in errors)
    
    def test_missing_credentials_in_production(self):
        """Test missing credentials in production."""
        validator = DatabaseURLValidator()
        results = validator.validate(
            "postgresql://localhost:5432/dbname",  # No username/password
            Environment.PRODUCTION
        )
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("credentials are required" in r.message for r in errors)
    
    def test_ssl_recommendation_in_production(self):
        """Test SSL recommendation for production."""
        validator = DatabaseURLValidator()
        results = validator.validate(
            "postgresql://user:pass@db.example.com:5432/dbname",
            Environment.PRODUCTION
        )
        # Should have warning about SSL
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 1
        assert "SSL/TLS" in warnings[0].message
    
    def test_ssl_mode_present(self):
        """Test when SSL mode is already present."""
        validator = DatabaseURLValidator()
        results = validator.validate(
            "postgresql://user:pass@db.example.com:5432/dbname?sslmode=require",
            Environment.PRODUCTION
        )
        # Should not have SSL warning
        warnings = [r for r in results if "SSL" in r.message]
        assert len(warnings) == 0


class TestEmailConfigValidator:
    """Test email configuration validation."""
    
    def test_valid_email(self):
        """Test valid email format."""
        validator = EmailConfigValidator()
        results = validator.validate(
            "noreply@production.com",  # Avoid example.com pattern
            Environment.PRODUCTION
        )
        # Should have no errors or warnings
        errors_warnings = [r for r in results if r.severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING]]
        assert len(errors_warnings) == 0
    
    def test_invalid_email_format(self):
        """Test invalid email format."""
        validator = EmailConfigValidator()
        results = validator.validate(
            "not-an-email",
            Environment.PRODUCTION
        )
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "Invalid email format" in results[0].message
    
    def test_development_email_in_production(self):
        """Test development email patterns in production."""
        validator = EmailConfigValidator()
        
        # Test various dev patterns
        dev_emails = [
            "test@example.com",
            "dev@test.com",
            "admin@localhost.com"
        ]
        
        for email in dev_emails:
            results = validator.validate(email, Environment.PRODUCTION)
            errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
            assert len(errors) > 0, f"Expected error for {email}"
            # Check message content - could be about dev pattern or specific pattern like 'test', 'example.com'
            assert any(
                "Development email pattern" in r.message or 
                "development" in r.message.lower() or
                "found in production" in r.message
                for r in errors
            ), f"Unexpected error messages for {email}: {[r.message for r in errors]}"


class TestCORSOriginsValidator:
    """Test CORS origins validation."""
    
    def test_valid_cors_origins_list(self):
        """Test valid CORS origins list."""
        validator = CORSOriginsValidator()
        results = validator.validate(
            ["https://app.example.com", "https://api.example.com"],
            Environment.PRODUCTION
        )
        assert len(results) == 0
    
    def test_valid_cors_origins_string(self):
        """Test valid CORS origins as comma-separated string."""
        validator = CORSOriginsValidator()
        results = validator.validate(
            "https://app.example.com, https://api.example.com",
            Environment.PRODUCTION
        )
        assert len(results) == 0
    
    def test_wildcard_not_allowed_in_production(self):
        """Test wildcard CORS origin not allowed in production."""
        validator = CORSOriginsValidator()
        results = validator.validate(
            ["*"],
            Environment.PRODUCTION
        )
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "Wildcard (*)" in results[0].message
    
    def test_http_not_allowed_in_production(self):
        """Test HTTP origins not allowed in production."""
        validator = CORSOriginsValidator()
        results = validator.validate(
            ["http://app.example.com"],
            Environment.PRODUCTION
        )
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "must use HTTPS" in results[0].message
    
    def test_invalid_origin_format(self):
        """Test invalid origin format."""
        validator = CORSOriginsValidator()
        results = validator.validate(
            ["not-a-url"],
            Environment.PRODUCTION
        )
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "Invalid CORS origin format" in results[0].message


class TestJWTConfigValidator:
    """Test JWT configuration validation."""
    
    def test_valid_jwt_algorithm(self):
        """Test valid JWT algorithm."""
        validator = JWTConfigValidator("jwt_algorithm")
        results = validator.validate("RS256", Environment.PRODUCTION)
        assert len(results) == 0
    
    def test_invalid_jwt_algorithm(self):
        """Test invalid JWT algorithm."""
        validator = JWTConfigValidator("jwt_algorithm")
        results = validator.validate("INVALID", Environment.PRODUCTION)
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("Invalid JWT algorithm" in r.message for r in errors)
    
    def test_symmetric_algorithm_warning_in_production(self):
        """Test warning for symmetric algorithms in production."""
        validator = JWTConfigValidator("jwt_algorithm")
        results = validator.validate("HS256", Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 1
        assert "asymmetric algorithm" in warnings[0].message
    
    def test_access_token_expiration_too_long(self):
        """Test access token expiration too long for production."""
        validator = JWTConfigValidator("access_token_expire_minutes")
        results = validator.validate(120, Environment.PRODUCTION)  # 2 hours
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 1
        assert "long for production" in warnings[0].message
    
    def test_negative_token_expiration(self):
        """Test negative token expiration."""
        validator = JWTConfigValidator("access_token_expire_minutes")
        results = validator.validate(-1, Environment.PRODUCTION)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "must be positive" in results[0].message


class TestRateLimitValidator:
    """Test rate limit configuration validation."""
    
    def test_valid_rate_limit_attempts(self):
        """Test valid rate limit attempts."""
        validator = RateLimitValidator("login_rate_limit_attempts")
        results = validator.validate(5, Environment.PRODUCTION)
        assert len(results) == 0
    
    def test_rate_limit_too_low_for_production(self):
        """Test rate limit too low for production."""
        validator = RateLimitValidator("login_rate_limit_attempts")
        results = validator.validate(2, Environment.PRODUCTION)  # Below minimum of 3
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "too low" in results[0].message
    
    def test_lockout_duration_too_short(self):
        """Test lockout duration too short."""
        validator = RateLimitValidator("lockout_duration_minutes")
        results = validator.validate(5, Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 1
        assert "too short" in warnings[0].message
    
    def test_negative_window_duration(self):
        """Test negative window duration."""
        validator = RateLimitValidator("rate_limit_window_minutes")
        results = validator.validate(-5, Environment.PRODUCTION)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "must be positive" in results[0].message


class TestCrossFieldValidators:
    """Test cross-field validators."""
    
    def test_database_pool_validator(self):
        """Test database pool configuration validation."""
        validator = DatabasePoolValidator()
        
        # Test overflow less than pool size
        config = {
            "db_pool_size": 10,
            "db_max_overflow": 5  # Less than pool size
        }
        results = validator.validate(config, Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) >= 1
        assert any("less than pool size" in r.message for r in warnings)
    
    def test_security_consistency_validator(self):
        """Test security settings consistency."""
        validator = SecurityConsistencyValidator()
        
        # Test email verification without email config
        config = {
            "require_email_verification": True,
            "smtp_host": None,
            "from_email": None
        }
        results = validator.validate(config, Environment.PRODUCTION)
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("email configuration is missing" in r.message for r in errors)
        
        # Test rate limiting without attempts limit
        config = {
            "rate_limiting_enabled": True,
            "login_rate_limit_attempts": None
        }
        results = validator.validate(config, Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) >= 1
        assert any("login attempts limit is not configured" in r.message for r in warnings)
        
        # Test lockout before rate limiting
        config = {
            "login_rate_limit_attempts": 5,
            "lockout_max_failed_attempts": 3  # Less than rate limit
        }
        results = validator.validate(config, Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) >= 1
        assert any("triggers before rate limiting" in r.message for r in warnings)
    
    def test_supabase_config_validator(self):
        """Test Supabase configuration validation."""
        validator = SupabaseConfigValidator()
        
        # Test incomplete Supabase config
        config = {
            "supabase_url": "https://test.supabase.co",
            "supabase_anon_key": None,
            "supabase_service_role_key": None
        }
        results = validator.validate(config, Environment.PRODUCTION)
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "Incomplete Supabase configuration" in results[0].message
        
        # Test mismatched URL and keys
        config = {
            "supabase_url": "https://project1.supabase.co",
            "supabase_anon_key": "project2.anon.key",  # Different project
            "supabase_service_role_key": "service.key"
        }
        results = validator.validate(config, Environment.PRODUCTION)
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        assert len(warnings) == 1
        assert "different projects" in warnings[0].message


class TestConfigurationBusinessRuleValidator:
    """Test the main business rule validator."""
    
    def test_complete_validation(self):
        """Test complete configuration validation."""
        validator = ConfigurationBusinessRuleValidator()
        
        # Create a config with multiple issues
        config = {
            # Database pool issues
            "db_pool_size": 10,
            "db_max_overflow": 5,
            
            # Security consistency issues
            "require_email_verification": True,
            "smtp_host": None,
            
            # Incomplete Supabase
            "supabase_url": "https://test.supabase.co",
            "supabase_anon_key": None,
            "supabase_service_role_key": None
        }
        
        results = validator.validate(config, Environment.PRODUCTION)
        
        # Should have multiple issues
        assert len(results) > 0
        
        # Check for specific issues
        error_fields = [r.field for r in results if r.severity == ValidationSeverity.ERROR]
        assert "require_email_verification" in error_fields
        assert "supabase_config" in error_fields
        
        warning_fields = [r.field for r in results if r.severity == ValidationSeverity.WARNING]
        assert "db_max_overflow" in warning_fields


class TestIntegrationWithSettings:
    """Test integration with Settings class."""
    
    @patch.dict('os.environ', {
        'ENVIRONMENT': 'production',
        'SECRET_KEY': 'production-very-long-random-key-without-weak-patterns-64-chars-minimum',
        'DATABASE_URL': 'postgresql://user:pass@db.example.com/dbname?sslmode=require',
        'SUPABASE_URL': 'https://project.supabase.co',
        'SUPABASE_ANON_KEY': 'project.anon.key',
        'SUPABASE_SERVICE_ROLE_KEY': 'project.service.key',
        'FROM_EMAIL': 'noreply@production.com',
        'SMTP_HOST': 'smtp.example.com',
        'SMTP_PORT': '587',
        'SMTP_USE_TLS': 'true',
        'CORS_ORIGINS': '["https://app.example.com", "https://www.example.com"]',
        'FRONTEND_URL': 'https://www.example.com',
        'DEBUG': 'false',
        'REQUIRE_EMAIL_VERIFICATION': 'true',
        'CSRF_PROTECTION_ENABLED': 'true',
        'RATE_LIMITING_ENABLED': 'true',
        'PASSWORD_MIN_LENGTH': '12',
        'LOGIN_RATE_LIMIT_ATTEMPTS': '5',
        'LOCKOUT_MAX_FAILED_ATTEMPTS': '10'
    })
    def test_production_settings_validation(self):
        """Test production settings pass validation."""
        # This should not raise any errors
        settings = Settings()
        assert settings.environment == "production"
        assert settings.password_min_length == 12
    
    @patch.dict('os.environ', {
        'ENVIRONMENT': 'production',
        'SECRET_KEY': 'weak',  # Too short
        'DATABASE_URL': 'sqlite:///app.db',  # SQLite in production
        'DEBUG': 'true',  # Debug in production
        'REQUIRE_EMAIL_VERIFICATION': 'false',  # Should be true
        'PASSWORD_MIN_LENGTH': '6'  # Too low
    })
    def test_production_settings_validation_failures(self):
        """Test production settings validation failures."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        # Check that we got validation errors
        errors = exc_info.value.errors()
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])