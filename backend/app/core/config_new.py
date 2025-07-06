"""
Configuration Management - Refactored

Clean configuration interface using the new service-oriented architecture.
This replaces the monolithic Settings class with a much smaller, focused interface.
"""

from functools import lru_cache
from typing import Dict, Any, List

from app.core.config.orchestrator import ConfigServiceOrchestrator
from app.core.audit_logger import get_audit_logger


# Global configuration instance
_config_orchestrator: ConfigServiceOrchestrator = None


def _create_settings() -> ConfigServiceOrchestrator:
    """Create configuration orchestrator with proper error handling."""
    try:
        return ConfigServiceOrchestrator()
    except Exception as e:
        print(f"Failed to create configuration: {str(e)}")
        raise


def _get_orchestrator() -> ConfigServiceOrchestrator:
    """Get or create the global configuration orchestrator."""
    global _config_orchestrator
    if _config_orchestrator is None:
        _config_orchestrator = _create_settings()
    return _config_orchestrator


# Compatibility class for existing code
class Settings:
    """
    Compatibility wrapper for the original Settings class.
    
    This class is now much smaller (< 50 lines) and delegates
    all work to the ConfigServiceOrchestrator.
    """
    
    def __init__(self, _env_file=None):
        """Initialize settings - mostly for test compatibility."""
        self._orchestrator = _create_settings()
    
    def __getattr__(self, name: str):
        """Delegate all attribute access to orchestrator."""
        return getattr(self._orchestrator, name)
    
    def model_dump(self) -> Dict[str, Any]:
        """Compatibility method for Pydantic model_dump."""
        return self._orchestrator.model_dump()
    
    def export_safe(self) -> Dict[str, Any]:
        """Export configuration with audit logging."""
        audit_logger = get_audit_logger()
        
        try:
            safe_config = self._orchestrator.get_safe_config()
            
            # Log the export
            audit_logger.log_config_export(
                export_format="dict",
                include_sensitive=False,
                success=True,
                metadata={
                    "fields_count": len(safe_config),
                    "environment": self._orchestrator.environment
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


# Global settings instance for compatibility
settings = Settings()


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
    global settings, _config_orchestrator
    
    audit_logger = get_audit_logger()
    
    try:
        # Log reload attempt
        old_env = settings.environment if settings else "unknown"
        
        get_settings.cache_clear()
        _config_orchestrator = None  # Clear global orchestrator
        settings = Settings()
        
        # Log successful reload
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
    orchestrator = _get_orchestrator()
    
    # Use the new validation system
    report = orchestrator.get_validation_report()
    
    # Extract issues for compatibility
    issues = []
    for line in report.split('\n'):
        if line.strip() and not line.startswith('Configuration') and not line.startswith('Total'):
            issues.append(line.strip())
    
    return issues