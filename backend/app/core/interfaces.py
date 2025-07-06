"""
Configuration System Interfaces

Defines protocols and interfaces for dependency injection and testability.
"""

from typing import Protocol, Dict, Any, List, Optional
from abc import ABC, abstractmethod

from .environment import Environment


class ConfigProvider(Protocol):
    """Protocol for configuration providers."""
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        ...
    
    def reload(self) -> None:
        """Reload configuration from source."""
        ...
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive data redacted."""
        ...


class DatabaseProvider(Protocol):
    """Protocol for database configuration providers."""
    
    def build_dsn(self, environment: Environment) -> str:
        """Build database connection string."""
        ...
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        ...


class SecurityProvider(Protocol):
    """Protocol for security configuration providers."""
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security configuration summary."""
        ...
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get security config with sensitive data redacted."""
        ...


class ValidationProvider(Protocol):
    """Protocol for configuration validators."""
    
    def validate_all(self, environment: Environment) -> Any:
        """Validate all configuration."""
        ...
    
    def get_validation_report(self, summary: Any) -> str:
        """Get validation report."""
        ...


class AuditProvider(Protocol):
    """Protocol for audit logging providers."""
    
    def log_config_read(self, field_name: str, **kwargs) -> None:
        """Log configuration read access."""
        ...
    
    def log_config_write(self, field_name: str, **kwargs) -> None:
        """Log configuration write access."""
        ...
    
    def log_config_export(self, **kwargs) -> None:
        """Log configuration export."""
        ...


class ConfigServiceInterface(ABC):
    """Abstract base class for configuration services."""
    
    @abstractmethod
    def validate_for_environment(self, environment: Environment) -> List[Any]:
        """Validate configuration for environment."""
        pass
    
    @abstractmethod
    def get_safe_config(self) -> Dict[str, Any]:
        """Get safe configuration export."""
        pass


class AccessControlInterface(ABC):
    """Abstract base class for access control."""
    
    @abstractmethod
    def check_field_access(self, user_id: str, field_name: str, 
                          permission: str, environment: str) -> bool:
        """Check field access permission."""
        pass
    
    @abstractmethod
    def filter_readable_fields(self, user_id: str, config_dict: Dict[str, Any],
                              environment: str) -> Dict[str, Any]:
        """Filter config dict to readable fields."""
        pass


class ConfigurationManagerInterface(ABC):
    """Abstract interface for configuration management."""
    
    @abstractmethod
    def get_database_dsn(self) -> str:
        """Get database connection string."""
        pass
    
    @abstractmethod
    def get_redis_dsn(self) -> str:
        """Get Redis connection string."""
        pass
    
    @abstractmethod
    def is_production(self) -> bool:
        """Check if in production environment."""
        pass
    
    @abstractmethod
    def is_development(self) -> bool:
        """Check if in development environment."""
        pass
    
    @abstractmethod
    def get_safe_config(self) -> Dict[str, Any]:
        """Get safe configuration export."""
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """Reload configuration."""
        pass


# Dependency injection container interface
class DIContainer(Protocol):
    """Protocol for dependency injection containers."""
    
    def register(self, interface: type, implementation: type) -> None:
        """Register an implementation for an interface."""
        ...
    
    def get(self, interface: type) -> Any:
        """Get implementation for interface."""
        ...
    
    def singleton(self, interface: type, implementation: type) -> None:
        """Register singleton implementation."""
        ...


# Simple dependency injection implementation
class SimpleDIContainer:
    """Simple dependency injection container implementation."""
    
    def __init__(self):
        """Initialize container."""
        self._bindings: Dict[type, type] = {}
        self._singletons: Dict[type, Any] = {}
        self._singleton_types: set = set()
    
    def register(self, interface: type, implementation: type) -> None:
        """Register an implementation for an interface."""
        self._bindings[interface] = implementation
    
    def singleton(self, interface: type, implementation: type) -> None:
        """Register singleton implementation."""
        self._bindings[interface] = implementation
        self._singleton_types.add(interface)
    
    def get(self, interface: type) -> Any:
        """Get implementation for interface."""
        if interface in self._singleton_types:
            if interface not in self._singletons:
                implementation = self._bindings[interface]
                self._singletons[interface] = implementation()
            return self._singletons[interface]
        
        if interface in self._bindings:
            implementation = self._bindings[interface]
            return implementation()
        
        raise ValueError(f"No binding found for {interface}")
    
    def clear(self) -> None:
        """Clear all bindings (useful for testing)."""
        self._bindings.clear()
        self._singletons.clear()
        self._singleton_types.clear()


# Global DI container instance
_container = SimpleDIContainer()


def get_container() -> DIContainer:
    """Get the global DI container."""
    return _container


def configure_dependencies():
    """Configure default dependency bindings."""
    from .config.orchestrator import ConfigServiceOrchestrator
    from .config.database_service import DatabaseConfigService
    from .config.security_service import SecurityConfigService
    from .config.validation_service import ConfigValidationService
    from .rbac.role_manager import RoleManager
    from .rbac.permission_manager import PermissionManager
    from .rbac.access_control import AccessControlService
    
    container = get_container()
    
    # Register configuration services
    container.singleton(ConfigurationManagerInterface, ConfigServiceOrchestrator)
    container.register(DatabaseProvider, DatabaseConfigService)
    container.register(SecurityProvider, SecurityConfigService)
    container.register(ValidationProvider, ConfigValidationService)
    
    # Register RBAC services
    container.singleton(RoleManager, RoleManager)
    container.singleton(PermissionManager, PermissionManager)
    container.register(AccessControlInterface, AccessControlService)