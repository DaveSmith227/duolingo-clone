"""
Role-Based Access Control Package

Provides a clean, service-oriented RBAC system following
the Single Responsibility Principle.
"""

from .permission_manager import PermissionManager, ConfigPermission, FieldPermission
from .role_manager import RoleManager, ConfigRole, RoleDefinition
from .access_control import AccessControlService, AccessDeniedError, require_permission, with_field_filtering

__all__ = [
    "PermissionManager",
    "ConfigPermission", 
    "FieldPermission",
    "RoleManager",
    "ConfigRole",
    "RoleDefinition",
    "AccessControlService",
    "AccessDeniedError",
    "require_permission",
    "with_field_filtering"
]