"""
Configuration Validation Service

Orchestrates all configuration validation across different services and environments
following the Single Responsibility Principle.
"""

from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum

from ..environment import Environment


class ValidationSeverity(Enum):
    """Validation result severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Individual validation result."""
    field: str
    message: str
    severity: ValidationSeverity
    service: str  # Which service produced this result
    environment: Optional[str] = None


@dataclass
class ValidationSummary:
    """Summary of all validation results."""
    total_results: int
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    info: List[ValidationResult]
    has_errors: bool
    has_warnings: bool
    
    @classmethod
    def from_results(cls, results: List[ValidationResult]) -> 'ValidationSummary':
        """Create summary from validation results."""
        errors = [r for r in results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        info = [r for r in results if r.severity == ValidationSeverity.INFO]
        
        return cls(
            total_results=len(results),
            errors=errors,
            warnings=warnings,
            info=info,
            has_errors=len(errors) > 0,
            has_warnings=len(warnings) > 0
        )


class ConfigValidator(Protocol):
    """Protocol for configuration validators."""
    
    def validate_for_environment(self, environment: Environment) -> List[ValidationResult]:
        """Validate configuration for specific environment."""
        ...


class ConfigValidationService:
    """
    Service responsible for orchestrating configuration validation.
    
    Responsibilities:
    - Coordinate validation across multiple services
    - Aggregate validation results
    - Apply environment-specific validation rules
    - Generate validation summaries
    """
    
    def __init__(self):
        """Initialize validation service."""
        self._validators: Dict[str, ConfigValidator] = {}
        self._environment_rules: Dict[Environment, List[str]] = {
            Environment.PRODUCTION: ["strict", "security", "performance"],
            Environment.STAGING: ["security", "compatibility"],
            Environment.DEVELOPMENT: ["basic"],
            Environment.TEST: ["minimal"]
        }
    
    def register_validator(self, name: str, validator: ConfigValidator) -> None:
        """
        Register a configuration validator.
        
        Args:
            name: Validator name
            validator: Validator instance
        """
        self._validators[name] = validator
    
    def validate_all(self, environment: Environment) -> ValidationSummary:
        """
        Run all registered validators for the given environment.
        
        Args:
            environment: Environment to validate for
            
        Returns:
            Validation summary with all results
        """
        all_results = []
        
        for validator_name, validator in self._validators.items():
            try:
                results = validator.validate_for_environment(environment)
                # Add service name to results
                for result in results:
                    result.service = validator_name
                    result.environment = environment.value
                all_results.extend(results)
            except Exception as e:
                # If validator fails, record it as an error
                all_results.append(ValidationResult(
                    field=f"{validator_name}_validator",
                    message=f"Validator failed: {str(e)}",
                    severity=ValidationSeverity.ERROR,
                    service="validation_service",
                    environment=environment.value
                ))
        
        return ValidationSummary.from_results(all_results)
    
    def validate_specific(self, validator_names: List[str], environment: Environment) -> ValidationSummary:
        """
        Run specific validators for the given environment.
        
        Args:
            validator_names: List of validator names to run
            environment: Environment to validate for
            
        Returns:
            Validation summary with results from specified validators
        """
        all_results = []
        
        for validator_name in validator_names:
            if validator_name in self._validators:
                validator = self._validators[validator_name]
                try:
                    results = validator.validate_for_environment(environment)
                    for result in results:
                        result.service = validator_name
                        result.environment = environment.value
                    all_results.extend(results)
                except Exception as e:
                    all_results.append(ValidationResult(
                        field=f"{validator_name}_validator",
                        message=f"Validator failed: {str(e)}",
                        severity=ValidationSeverity.ERROR,
                        service="validation_service",
                        environment=environment.value
                    ))
            else:
                all_results.append(ValidationResult(
                    field="validator_registration",
                    message=f"Validator '{validator_name}' not found",
                    severity=ValidationSeverity.ERROR,
                    service="validation_service",
                    environment=environment.value
                ))
        
        return ValidationSummary.from_results(all_results)
    
    def should_fail_on_errors(self, environment: Environment) -> bool:
        """
        Determine if validation errors should cause startup failure.
        
        Args:
            environment: Current environment
            
        Returns:
            True if errors should cause failure
        """
        # Production should always fail on errors
        if environment == Environment.PRODUCTION:
            return True
        
        # Staging should fail on security errors
        if environment == Environment.STAGING:
            return True
        
        # Development and test can continue with warnings
        return False
    
    def get_validation_report(self, summary: ValidationSummary) -> str:
        """
        Generate a human-readable validation report.
        
        Args:
            summary: Validation summary
            
        Returns:
            Formatted validation report
        """
        lines = []
        lines.append(f"Configuration Validation Report")
        lines.append(f"Total issues found: {summary.total_results}")
        lines.append("")
        
        if summary.errors:
            lines.append(f"ERRORS ({len(summary.errors)}):")
            for error in summary.errors:
                lines.append(f"  - {error.field}: {error.message} [{error.service}]")
            lines.append("")
        
        if summary.warnings:
            lines.append(f"WARNINGS ({len(summary.warnings)}):")
            for warning in summary.warnings:
                lines.append(f"  - {warning.field}: {warning.message} [{warning.service}]")
            lines.append("")
        
        if summary.info:
            lines.append(f"INFO ({len(summary.info)}):")
            for info in summary.info:
                lines.append(f"  - {info.field}: {info.message} [{info.service}]")
        
        return "\n".join(lines)
    
    def get_registered_validators(self) -> List[str]:
        """Get list of registered validator names."""
        return list(self._validators.keys())
    
    def clear_validators(self) -> None:
        """Clear all registered validators (useful for testing)."""
        self._validators.clear()


# Adapter classes to make existing services work with the validation protocol
class DatabaseValidatorAdapter:
    """Adapter to make DatabaseConfigService work with validation protocol."""
    
    def __init__(self, database_service):
        self.database_service = database_service
    
    def validate_for_environment(self, environment: Environment) -> List[ValidationResult]:
        """Validate database configuration."""
        db_results = self.database_service.validate_for_environment(environment)
        return [
            ValidationResult(
                field=result.field,
                message=result.message,
                severity=ValidationSeverity(result.severity),
                service="database"
            )
            for result in db_results
        ]


class SecurityValidatorAdapter:
    """Adapter to make SecurityConfigService work with validation protocol."""
    
    def __init__(self, security_service):
        self.security_service = security_service
    
    def validate_for_environment(self, environment: Environment) -> List[ValidationResult]:
        """Validate security configuration."""
        security_results = self.security_service.validate_for_environment(environment)
        return [
            ValidationResult(
                field=result.field,
                message=result.message,
                severity=ValidationSeverity(result.severity),
                service="security"
            )
            for result in security_results
        ]