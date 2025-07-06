"""
Environment-Specific Validation Rules

Provides validation rules that are enforced differently based on the
deployment environment (development, staging, production, test).
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from .environment import Environment, get_environment

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Fails validation, stops application
    WARNING = "warning"  # Logs warning, continues
    INFO = "info"       # Informational only


@dataclass
class ValidationResult:
    """Result of a validation check."""
    field: str
    severity: ValidationSeverity
    message: str
    value: Any = None
    suggestion: Optional[str] = None


class EnvironmentValidator(ABC):
    """Base class for environment-specific validators."""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
    
    @abstractmethod
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        """Validate a field value for a specific environment."""
        pass


class SecurityLevelValidator(EnvironmentValidator):
    """Validates security-related settings based on environment."""
    
    def __init__(self, field_name: str, 
                 min_production: int = 10,
                 min_staging: int = 8,
                 min_development: int = 6):
        super().__init__(field_name)
        self.requirements = {
            Environment.PRODUCTION: min_production,
            Environment.STAGING: min_staging,
            Environment.DEVELOPMENT: min_development,
            Environment.TEST: min_development,
        }
    
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
        
        required_min = self.requirements.get(environment, 8)
        
        if value < required_min:
            severity = ValidationSeverity.ERROR if environment == Environment.PRODUCTION else ValidationSeverity.WARNING
            results.append(ValidationResult(
                field=self.field_name,
                severity=severity,
                message=f"{self.field_name} is {value}, but {environment.value} environment requires minimum {required_min}",
                value=value,
                suggestion=f"Set {self.field_name} to at least {required_min}"
            ))
        
        return results


class SecretKeyValidator(EnvironmentValidator):
    """Validates secret key strength based on environment."""
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not isinstance(value, str):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a string",
                value=value
            ))
            return results
        
        # Check for default/weak keys
        weak_patterns = [
            "dev-",
            "development",
            "test",
            "change-me",
            "default",
            "password",
            "secret",
            "key123",
        ]
        
        value_lower = value.lower()
        for pattern in weak_patterns:
            if pattern in value_lower:
                severity = ValidationSeverity.ERROR if environment == Environment.PRODUCTION else ValidationSeverity.WARNING
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=severity,
                    message=f"{self.field_name} appears to contain weak pattern '{pattern}'",
                    value="***REDACTED***",
                    suggestion="Use a cryptographically secure random key"
                ))
                break
        
        # Check length requirements
        min_lengths = {
            Environment.PRODUCTION: 64,
            Environment.STAGING: 32,
            Environment.DEVELOPMENT: 16,
            Environment.TEST: 16,
        }
        
        required_length = min_lengths.get(environment, 32)
        if len(value) < required_length:
            severity = ValidationSeverity.ERROR if environment == Environment.PRODUCTION else ValidationSeverity.WARNING
            results.append(ValidationResult(
                field=self.field_name,
                severity=severity,
                message=f"{self.field_name} is {len(value)} characters, but {environment.value} requires {required_length}",
                value="***REDACTED***",
                suggestion=f"Generate a key with at least {required_length} characters"
            ))
        
        return results


class URLValidator(EnvironmentValidator):
    """Validates URLs based on environment security requirements."""
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not value:  # Allow None/empty for optional URLs
            return results
        
        if not isinstance(value, str):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a string",
                value=value
            ))
            return results
        
        # Check protocol requirements
        if environment == Environment.PRODUCTION:
            if not value.startswith("https://"):
                results.append(ValidationResult(
                    field=self.field_name,
                    severity=ValidationSeverity.ERROR,
                    message=f"{self.field_name} must use HTTPS in production",
                    value=value,
                    suggestion="Change protocol to https://"
                ))
        
        # Check for localhost/development URLs in production
        dev_patterns = ["localhost", "127.0.0.1", "0.0.0.0", ".local"]
        if environment == Environment.PRODUCTION:
            for pattern in dev_patterns:
                if pattern in value.lower():
                    results.append(ValidationResult(
                        field=self.field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"{self.field_name} contains development hostname '{pattern}' in production",
                        value=value,
                        suggestion="Use production domain name"
                    ))
        
        return results


class BooleanSecurityValidator(EnvironmentValidator):
    """Validates boolean security settings based on environment."""
    
    def __init__(self, field_name: str, required_production: bool = True,
                 required_staging: Optional[bool] = None):
        super().__init__(field_name)
        self.required_production = required_production
        self.required_staging = required_staging
    
    def validate(self, value: Any, environment: Environment) -> List[ValidationResult]:
        results = []
        
        if not isinstance(value, bool):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be a boolean",
                value=value
            ))
            return results
        
        # Check production requirements
        if environment == Environment.PRODUCTION and value != self.required_production:
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.ERROR,
                message=f"{self.field_name} must be {self.required_production} in production",
                value=value,
                suggestion=f"Set {self.field_name} to {self.required_production}"
            ))
        
        # Check staging requirements
        if (environment == Environment.STAGING and 
            self.required_staging is not None and
            value != self.required_staging):
            results.append(ValidationResult(
                field=self.field_name,
                severity=ValidationSeverity.WARNING,
                message=f"{self.field_name} should be {self.required_staging} in staging",
                value=value,
                suggestion=f"Consider setting {self.field_name} to {self.required_staging}"
            ))
        
        return results


class EnvironmentValidationFramework:
    """Framework for applying environment-specific validation rules."""
    
    def __init__(self):
        self.validators: Dict[str, EnvironmentValidator] = {}
        self._setup_default_validators()
    
    def _setup_default_validators(self):
        """Setup default validation rules."""
        # Security-related validators
        self.add_validator("password_min_length", SecurityLevelValidator(
            "password_min_length", min_production=12, min_staging=10, min_development=8
        ))
        
        self.add_validator("secret_key", SecretKeyValidator("secret_key"))
        
        self.add_validator("require_email_verification", BooleanSecurityValidator(
            "require_email_verification", required_production=True, required_staging=False
        ))
        
        self.add_validator("csrf_protection_enabled", BooleanSecurityValidator(
            "csrf_protection_enabled", required_production=True, required_staging=True
        ))
        
        self.add_validator("rate_limiting_enabled", BooleanSecurityValidator(
            "rate_limiting_enabled", required_production=True, required_staging=True
        ))
        
        self.add_validator("debug", BooleanSecurityValidator(
            "debug", required_production=False, required_staging=False
        ))
        
        # URL validators
        self.add_validator("supabase_url", URLValidator("supabase_url"))
        self.add_validator("database_url", URLValidator("database_url"))
        self.add_validator("redis_url", URLValidator("redis_url"))
        self.add_validator("frontend_url", URLValidator("frontend_url"))
        
        # Rate limiting validators
        self.add_validator("login_rate_limit_attempts", SecurityLevelValidator(
            "login_rate_limit_attempts", min_production=3, min_staging=5, min_development=10
        ))
        
        self.add_validator("lockout_max_failed_attempts", SecurityLevelValidator(
            "lockout_max_failed_attempts", min_production=3, min_staging=5, min_development=10
        ))
    
    def add_validator(self, field_name: str, validator: EnvironmentValidator):
        """Add a custom validator for a field."""
        self.validators[field_name] = validator
        logger.debug(f"Added validator for field '{field_name}'")
    
    def remove_validator(self, field_name: str):
        """Remove a validator for a field."""
        if field_name in self.validators:
            del self.validators[field_name]
            logger.debug(f"Removed validator for field '{field_name}'")
    
    def validate_config(self, config: Dict[str, Any], 
                       environment: Optional[Environment] = None) -> List[ValidationResult]:
        """
        Validate configuration against environment-specific rules.
        
        Args:
            config: Configuration dictionary
            environment: Target environment (auto-detected if None)
            
        Returns:
            List of validation results
        """
        if environment is None:
            environment = get_environment()
        
        all_results = []
        
        logger.info(f"Validating configuration for {environment.value} environment")
        
        for field_name, validator in self.validators.items():
            if field_name in config:
                try:
                    results = validator.validate(config[field_name], environment)
                    all_results.extend(results)
                except Exception as e:
                    logger.error(f"Validation failed for field '{field_name}': {e}")
                    all_results.append(ValidationResult(
                        field=field_name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Validation error: {str(e)}",
                        value=config[field_name]
                    ))
        
        # Log validation summary
        error_count = sum(1 for r in all_results if r.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for r in all_results if r.severity == ValidationSeverity.WARNING)
        
        logger.info(
            f"Validation complete: {error_count} errors, {warning_count} warnings"
        )
        
        return all_results
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Get a summary of validation results."""
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        infos = [r for r in results if r.severity == ValidationSeverity.INFO]
        
        return {
            "total_issues": len(results),
            "errors": len(errors),
            "warnings": len(warnings),
            "infos": len(infos),
            "is_valid": len(errors) == 0,
            "error_fields": [r.field for r in errors],
            "warning_fields": [r.field for r in warnings],
            "details": {
                "errors": [{"field": r.field, "message": r.message, "suggestion": r.suggestion} for r in errors],
                "warnings": [{"field": r.field, "message": r.message, "suggestion": r.suggestion} for r in warnings],
            }
        }


# Global validation framework instance
_validation_framework: Optional[EnvironmentValidationFramework] = None


def get_validation_framework() -> EnvironmentValidationFramework:
    """Get or create the global validation framework."""
    global _validation_framework
    
    if _validation_framework is None:
        _validation_framework = EnvironmentValidationFramework()
    
    return _validation_framework


def validate_environment_config(config: Dict[str, Any], 
                               environment: Optional[Environment] = None) -> List[ValidationResult]:
    """Validate configuration for environment-specific rules."""
    framework = get_validation_framework()
    return framework.validate_config(config, environment)


def get_config_validation_summary(config: Dict[str, Any], 
                                 environment: Optional[Environment] = None) -> Dict[str, Any]:
    """Get validation summary for configuration."""
    framework = get_validation_framework()
    results = framework.validate_config(config, environment)
    return framework.get_validation_summary(results)


def add_custom_validator(field_name: str, validator: EnvironmentValidator):
    """Add a custom validator to the global framework."""
    framework = get_validation_framework()
    framework.add_validator(field_name, validator)