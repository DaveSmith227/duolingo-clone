"""
Enhanced Configuration Validators with Business Rules

Extends the environment validation framework with domain-specific validators,
business rule validators, and cross-field validation capabilities.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from urllib.parse import urlparse
from pathlib import Path
from dataclasses import dataclass

from .env_validators import (
    EnvironmentValidator, ValidationResult, ValidationSeverity, 
    Environment, get_validation_framework, URLValidator
)
from .environment import get_environment

logger = logging.getLogger(__name__)


class DatabaseURLValidator(EnvironmentValidator):
    """Validates database connection URLs with environment-specific rules."""
    
    def __init__(self, field_name: str = "database_url"):
        super().__init__(field_name)
        self.supported_schemes = {
            "postgresql": True,
            "postgres": True,  # Common alias
            "sqlite": False,  # Only in development/test
            "mysql": True,
            "mssql": True,
        }
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not value:
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} is required",
                value=value
            ))
            return results
        
        if not isinstance(value, str):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a string",
                value=value
            ))
            return results
        
        try:
            parsed = urlparse(value)
            scheme = parsed.scheme
            
            # Check if scheme is supported
            if scheme not in self.supported_schemes:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Unsupported database scheme '{scheme}'",
                    value=value,
                    suggestion=f"Use one of: {', '.join(self.supported_schemes.keys())}"
                ))
                return results
            
            # SQLite only allowed in development/test
            if scheme == "sqlite" and environment in [Environment.PRODUCTION, Environment.STAGING]:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"SQLite is not allowed in {environment.value}",
                    value=value,
                    suggestion="Use PostgreSQL or another production database"
                ))
            
            # Check for missing credentials in production
            if environment == Environment.PRODUCTION:
                if not parsed.username or not parsed.password:
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message="Database credentials are required in production",
                        value="***REDACTED***",
                        suggestion="Include username and password in the database URL"
                    ))
                
                # Check for SSL requirement
                if parsed.scheme in ["postgresql", "postgres", "mysql"]:
                    query_params = dict(param.split('=') for param in (parsed.query or '').split('&') if '=' in param)
                    ssl_params = ["sslmode", "ssl", "sslrequire", "require_secure_transport"]
                    
                    has_ssl = any(param in query_params for param in ssl_params)
                    if not has_ssl:
                        results.append(ValidationResult(
                            field=self.field_name,
                            severity=ValidationSeverity.WARNING,
                            message="SSL/TLS connection should be enforced in production",
                            value="***REDACTED***",
                            suggestion="Add ?sslmode=require to the database URL"
                        ))
            
        except Exception as e:
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid database URL format: {str(e)}",
                value=value
            ))
        
        return results


class EmailConfigValidator(EnvironmentValidator):
    """Validates email configuration settings."""
    
    def __init__(self, field_name: str = "from_email"):
        super().__init__(field_name)
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not value:
            severity = ValidationSeverity.ERROR if environment == Environment.PRODUCTION else ValidationSeverity.WARNING
            results.append(ValidationResult(
                field=self.field_name,
                severity=severity,
                message=f"{self.field_name} is required for email functionality",
                value=value
            ))
            return results
        
        if not isinstance(value, str):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a string",
                value=value
            ))
            return results
        
        # Email regex pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid email format for {self.field_name}",
                value=value,
                suggestion="Use a valid email address format"
            ))
            return results
        
        # Check for noreply pattern in production
        if environment == Environment.PRODUCTION and "noreply" not in value.lower():
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.INFO,
                message="Consider using a noreply email address for system emails",
                value=value,
                suggestion="Use format like noreply@yourdomain.com"
            ))
        
        # Check for test/dev emails in production
        dev_patterns = ["test", "dev", "example.com", "localhost"]
        if environment == Environment.PRODUCTION:
            for pattern in dev_patterns:
                if pattern in value.lower():
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Development email pattern '{pattern}' found in production",
                        value=value,
                        suggestion="Use a production email address"
                    ))
                    break
        
        return results


class CORSOriginsValidator(EnvironmentValidator):
    """Validates CORS origins configuration."""
    
    def __init__(self, field_name: str = "cors_origins"):
        super().__init__(field_name)
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if value is None:
            return results  # CORS origins can be optional
        
        # Accept both string and list formats
        origins = []
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        elif isinstance(value, list):
            origins = value
        else:
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a string or list",
                value=value
            ))
            return results
        
        # Check each origin
        for origin in origins:
            if not isinstance(origin, str):
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Each CORS origin must be a string, got {type(origin).__name__}",
                    value=origin
                ))
                continue
            
            # Wildcard check
            if origin == "*":
                if environment == Environment.PRODUCTION:
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message="Wildcard (*) CORS origin is not allowed in production",
                        value=origin,
                        suggestion="Specify exact allowed origins"
                    ))
                else:
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.WARNING,
                        message="Wildcard (*) CORS origin is insecure",
                        value=origin,
                        suggestion="Consider specifying exact origins"
                    ))
                continue
            
            # Validate URL format
            try:
                parsed = urlparse(origin)
                if not parsed.scheme or not parsed.netloc:
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid CORS origin format: {origin}",
                        value=origin,
                        suggestion="Use full URL format (e.g., https://example.com)"
                    ))
                    continue
                
                # HTTPS requirement in production
                if environment == Environment.PRODUCTION and parsed.scheme != "https":
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"CORS origin must use HTTPS in production: {origin}",
                        value=origin,
                        suggestion="Change protocol to https://"
                    ))
                
            except Exception as e:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid CORS origin: {str(e)}",
                    value=origin
                ))
        
        return results


class JWTConfigValidator(EnvironmentValidator):
    """Validates JWT configuration settings."""
    
    def __init__(self, field_name: str):
        super().__init__(field_name)
        self.secure_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        self.acceptable_algorithms = ["HS256", "HS384", "HS512"] + self.secure_algorithms
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if self.field_name == "jwt_algorithm":
            if value not in self.acceptable_algorithms:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid JWT algorithm: {value}",
                    value=value,
                    suggestion=f"Use one of: {', '.join(self.acceptable_algorithms)}"
                ))
            
            # Recommend asymmetric algorithms for production
            if environment == Environment.PRODUCTION and value not in self.secure_algorithms:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.WARNING,
                    message="Consider using asymmetric algorithm (RS256, ES256) in production",
                    value=value,
                    suggestion="Use RS256 or ES256 for better security"
                ))
        
        elif self.field_name == "access_token_expire_minutes":
            if not isinstance(value, (int, float)):
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"{self.field_name} must be a number",
                    value=value
                ))
                return results
            
            # Token expiration recommendations
            if environment == Environment.PRODUCTION:
                if value > 60:  # More than 1 hour
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.WARNING,
                        message=f"Access token expiration ({value} minutes) is long for production",
                        value=value,
                        suggestion="Consider 15-30 minutes for access tokens"
                    ))
            
            if value <= 0:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message="Access token expiration must be positive",
                    value=value
                ))
        
        return results


class RateLimitValidator(EnvironmentValidator):
    """Validates rate limiting configuration with business rules."""
    
    def __init__(self, field_name: str):
        super().__init__(field_name)
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not isinstance(value, (int, float)):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a number",
                value=value
            ))
            return results
        
        # Field-specific validation
        if "attempts" in self.field_name:
            min_values = {
                Environment.PRODUCTION: 3,
                Environment.STAGING: 5,
                Environment.DEVELOPMENT: 10,
                Environment.TEST: 100,
            }
            
            min_val = min_values.get(environment, 5)
            if value < min_val:
                severity = ValidationSeverity.ERROR if environment == Environment.PRODUCTION else ValidationSeverity.WARNING
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=severity,
                    message=f"{self.field_name} ({value}) is too low for {environment.value}",
                    value=value,
                    suggestion=f"Set to at least {min_val} attempts"
                ))
        
        elif "window" in self.field_name or "duration" in self.field_name:
            # Window/duration in minutes
            if value <= 0:
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"{self.field_name} must be positive",
                    value=value
                ))
            
            # Check for reasonable values
            if "lockout" in self.field_name and environment == Environment.PRODUCTION:
                if value < 15:
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.WARNING,
                        message=f"Lockout duration ({value} minutes) may be too short",
                        value=value,
                        suggestion="Consider 15-30 minutes for account lockout"
                    ))
        
        return results


class CrossFieldValidator:
    """Base class for validators that check relationships between multiple fields."""
    
    def __init__(self, name: str, fields: List[str]):
        self.name = name
        self.fields = fields
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationResult]:
        """Validate relationships between fields."""
        raise NotImplementedError


class DatabasePoolValidator(CrossFieldValidator):
    """Validates database connection pool settings consistency."""
    
    def __init__(self):
        super().__init__(
            "database_pool_config",
            ["db_pool_size", "db_max_overflow", "db_pool_timeout"]
        )
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationResult]:
        results = []
        
        pool_size = config.get("db_pool_size", 5)
        max_overflow = config.get("db_max_overflow", 10)
        
        # Validate relationship between pool size and overflow
        if max_overflow < pool_size:
            results.append(ValidationResult(
                field="db_max_overflow",
                severity=ValidationSeverity.WARNING,
                message=f"Max overflow ({max_overflow}) is less than pool size ({pool_size})",
                value=max_overflow,
                suggestion="Set max_overflow >= db_pool_size for better scaling"
            ))
        
        # Environment-specific recommendations
        if environment == Environment.PRODUCTION:
            total_connections = pool_size + max_overflow
            if total_connections < 20:
                results.append(ValidationResult(
                    field="database_pool_config",
                    severity=ValidationSeverity.INFO,
                    message=f"Total connection pool ({total_connections}) may be low for production",
                    value={"pool_size": pool_size, "max_overflow": max_overflow},
                    suggestion="Consider increasing pool_size and max_overflow for production load"
                ))
        
        return results


class SecurityConsistencyValidator(CrossFieldValidator):
    """Validates consistency of security-related settings."""
    
    def __init__(self):
        super().__init__(
            "security_consistency",
            [
                "require_email_verification", "smtp_host", "from_email",
                "csrf_protection_enabled", "rate_limiting_enabled",
                "login_rate_limit_attempts", "lockout_max_failed_attempts"
            ]
        )
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationResult]:
        results = []
        
        # Email verification requires email configuration
        if config.get("require_email_verification", False):
            if not config.get("smtp_host") or not config.get("from_email"):
                results.append(ValidationResult(
                    field="require_email_verification",
                    severity=ValidationSeverity.ERROR,
                    message="Email verification is enabled but email configuration is missing",
                    value=True,
                    suggestion="Configure smtp_host and from_email or disable email verification"
                ))
        
        # Rate limiting consistency
        if config.get("rate_limiting_enabled", False):
            if not config.get("login_rate_limit_attempts"):
                results.append(ValidationResult(
                    field="rate_limiting_enabled",
                    severity=ValidationSeverity.WARNING,
                    message="Rate limiting is enabled but login attempts limit is not configured",
                    value=True,
                    suggestion="Set login_rate_limit_attempts"
                ))
        
        # Lockout should be less restrictive than rate limiting
        rate_limit = config.get("login_rate_limit_attempts")
        lockout_limit = config.get("lockout_max_failed_attempts")
        
        if rate_limit is not None and lockout_limit is not None and lockout_limit < rate_limit:
            results.append(ValidationResult(
                field="lockout_max_failed_attempts",
                severity=ValidationSeverity.WARNING,
                message=f"Account lockout ({lockout_limit}) triggers before rate limiting ({rate_limit})",
                value=lockout_limit,
                suggestion="Set lockout_max_failed_attempts >= login_rate_limit_attempts"
            ))
        
        return results


class SupabaseConfigValidator(CrossFieldValidator):
    """Validates Supabase-specific configuration."""
    
    def __init__(self):
        super().__init__(
            "supabase_config",
            ["supabase_url", "supabase_anon_key", "supabase_service_role_key"]
        )
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationResult]:
        results = []
        
        url = config.get("supabase_url")
        anon_key = config.get("supabase_anon_key")
        service_key = config.get("supabase_service_role_key")
        
        # All or nothing validation
        supabase_fields = [url, anon_key, service_key]
        configured_count = sum(1 for field in supabase_fields if field)
        
        if 0 < configured_count < 3:
            results.append(ValidationResult(
                field="supabase_config",
                severity=ValidationSeverity.ERROR,
                message="Incomplete Supabase configuration",
                value={"url": bool(url), "anon_key": bool(anon_key), "service_key": bool(service_key)},
                suggestion="Configure all Supabase fields or none"
            ))
        
        # Check for matching URL and keys
        if url and anon_key:
            # Extract project ref from URL
            match = re.search(r'https://([a-z0-9]+)\.supabase\.co', url)
            if match:
                project_ref = match.group(1)
                # Anon keys often contain the project reference
                if project_ref not in anon_key:
                    results.append(ValidationResult(
                        field="supabase_anon_key",
                        severity=ValidationSeverity.WARNING,
                        message="Supabase URL and anon key may be from different projects",
                        value="***REDACTED***",
                        suggestion="Verify keys match the Supabase project URL"
                    ))
        
        return results


class ConfigurationBusinessRuleValidator:
    """Main validator for business rules and cross-field validation."""
    
    def __init__(self):
        self.cross_field_validators = [
            DatabasePoolValidator(),
            SecurityConsistencyValidator(),
            SupabaseConfigValidator(),
        ]
    
    def validate(self, config: Dict[str, Any], environment: Environment) -> List[ValidationResult]:
        """Run all cross-field validators."""
        results = []
        
        for validator in self.cross_field_validators:
            try:
                validator_results = validator.validate(config, environment)
                results.extend(validator_results)
            except Exception as e:
                logger.error(f"Cross-field validator {validator.name} failed: {e}")
                results.append(ValidationResult(
                    field=validator.name,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation error in {validator.name}: {str(e)}",
                    value=None
                ))
        
        return results


def register_config_validators():
    """Register all custom configuration validators with the global framework."""
    framework = get_validation_framework()
    
    # Database validators
    framework.add_validator("database_url", DatabaseURLValidator())
    
    # Email validators
    framework.add_validator("from_email", EmailConfigValidator())
    # Note: smtp_host is not a URL, it's just a hostname like smtp.gmail.com
    
    # CORS validator
    framework.add_validator("cors_origins", CORSOriginsValidator())
    
    # JWT validators
    framework.add_validator("jwt_algorithm", JWTConfigValidator("jwt_algorithm"))
    framework.add_validator("access_token_expire_minutes", JWTConfigValidator("access_token_expire_minutes"))
    
    # Rate limiting validators
    framework.add_validator("login_rate_limit_attempts", RateLimitValidator("login_rate_limit_attempts"))
    framework.add_validator("login_rate_limit_window_minutes", RateLimitValidator("login_rate_limit_window_minutes"))
    framework.add_validator("lockout_max_failed_attempts", RateLimitValidator("lockout_max_failed_attempts"))
    framework.add_validator("lockout_duration_minutes", RateLimitValidator("lockout_duration_minutes"))
    
    logger.info("Registered custom configuration validators")


# Auto-register validators on import
register_config_validators()