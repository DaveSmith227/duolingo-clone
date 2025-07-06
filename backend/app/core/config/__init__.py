"""
Configuration Package

Provides a clean, service-oriented configuration system following
the Single Responsibility Principle.
"""

from .orchestrator import ConfigServiceOrchestrator
from .database_service import DatabaseConfigService, DatabaseConfig
from .security_service import SecurityConfigService, SecurityConfig
from .validation_service import ConfigValidationService, ValidationSummary, ValidationResult

# Import backward compatibility layer
import sys
import importlib.util

# Load the new config module and expose its exports for backward compatibility
spec = importlib.util.spec_from_file_location(
    "config_new", 
    str(__file__).replace("config/__init__.py", "config_new.py")
)
config_new = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_new)

# Export backward compatible interfaces
Settings = config_new.Settings
get_settings = config_new.get_settings
reload_settings = config_new.reload_settings
validate_config_for_environment = config_new.validate_config_for_environment
settings = config_new.settings
_create_settings = config_new._create_settings

__all__ = [
    "ConfigServiceOrchestrator",
    "DatabaseConfigService", 
    "DatabaseConfig",
    "SecurityConfigService",
    "SecurityConfig", 
    "ConfigValidationService",
    "ValidationSummary",
    "ValidationResult",
    # Backward compatibility
    "Settings",
    "get_settings", 
    "reload_settings",
    "validate_config_for_environment",
    "settings",
    "_create_settings"
]