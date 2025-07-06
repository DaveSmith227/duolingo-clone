"""
RBAC Compatibility Layer

Provides backward compatibility for imports from the old config_rbac.py file.
This file maintains the same API while delegating to the new RBAC services.
"""

import warnings
from typing import Optional, Callable

# Import new RBAC services
from .rbac import (
    ConfigPermission,
    ConfigRole, 
    FieldPermission,
    RoleDefinition,
    PermissionManager,
    RoleManager,
    AccessControlService,
    require_permission,
    with_field_filtering
)

# Global instances for backward compatibility
_role_manager = RoleManager()
_permission_manager = PermissionManager()
_access_control = AccessControlService(_role_manager, _permission_manager)


class ConfigRBAC:
    """
    Backward compatibility wrapper for the old ConfigRBAC class.
    
    Delegates to the new service-oriented RBAC architecture.
    """
    
    def __init__(self):
        """Initialize with deprecation warning."""
        warnings.warn(
            "ConfigRBAC is deprecated. Use the new RBAC services from app.core.rbac instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._role_manager = _role_manager
        self._permission_manager = _permission_manager
        self._access_control = _access_control
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """Assign role to user."""
        return self._role_manager.assign_role_to_user(user_id, role_name)
    
    def revoke_role_from_user(self, user_id: str, role_name: str) -> bool:
        """Revoke role from user."""
        return self._role_manager.revoke_role_from_user(user_id, role_name)
    
    def user_has_role(self, user_id: str, role_name: str) -> bool:
        """Check if user has role."""
        return self._role_manager.user_has_role(user_id, role_name)
    
    def check_field_access(self, user_id: str, field_name: str, permission: ConfigPermission, environment: str) -> bool:
        """Check field access permission."""
        return self._access_control.check_field_access(user_id, field_name, permission, environment)
    
    def filter_config_dict(self, user_id: str, config_dict: dict, permission: ConfigPermission, environment: str) -> dict:
        """Filter config dictionary based on permissions."""
        if permission == ConfigPermission.READ:
            return self._access_control.filter_readable_fields(user_id, config_dict, environment)
        elif permission == ConfigPermission.WRITE:
            return self._access_control.filter_writable_fields(user_id, config_dict, environment)
        else:
            return {}
    
    def register_role(self, role: RoleDefinition) -> None:
        """Register a role."""
        self._role_manager.register_role(role)
    
    def get_role(self, role_name: str) -> Optional[RoleDefinition]:
        """Get role by name."""
        return self._role_manager.get_role(role_name)
    
    def get_user_roles(self, user_id: str) -> set:
        """Get user roles."""
        return self._role_manager.get_user_roles(user_id)


class RBACConfigProxy:
    """
    Backward compatibility wrapper for RBACConfigProxy.
    
    This was used to wrap configuration objects with RBAC enforcement.
    """
    
    def __init__(self, config, user_id: str, environment: str):
        """Initialize proxy with deprecation warning."""
        warnings.warn(
            "RBACConfigProxy is deprecated. Use the new AccessControlService directly.",
            DeprecationWarning,
            stacklevel=2
        )
        self._config = config
        self._user_id = user_id
        self._environment = environment
        self._access_control = _access_control
    
    def __getattr__(self, name: str):
        """Get attribute with access control."""
        # Check read permission
        if self._access_control.check_field_access(
            self._user_id, name, ConfigPermission.READ, self._environment
        ):
            return getattr(self._config, name)
        else:
            raise AttributeError(f"Access denied for field: {name}")
    
    def __setattr__(self, name: str, value):
        """Set attribute with access control."""
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        
        # Check write permission
        if self._access_control.check_field_access(
            self._user_id, name, ConfigPermission.WRITE, self._environment
        ):
            setattr(self._config, name, value)
        else:
            raise AttributeError(f"Write access denied for field: {name}")


# Global instance for backward compatibility
_config_rbac_instance = None


def get_config_rbac() -> ConfigRBAC:
    """
    Get the global ConfigRBAC instance.
    
    This function maintains backward compatibility with the old API.
    """
    global _config_rbac_instance
    if _config_rbac_instance is None:
        _config_rbac_instance = ConfigRBAC()
    return _config_rbac_instance


# Re-export everything for backward compatibility
__all__ = [
    "ConfigPermission",
    "ConfigRole", 
    "FieldPermission",
    "RoleDefinition",
    "ConfigRBAC",
    "RBACConfigProxy",
    "get_config_rbac",
    "require_permission",
    "with_field_filtering"
]