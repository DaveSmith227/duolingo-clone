"""
Role-Based Access Control for Configuration Management

Provides fine-grained access control for configuration operations,
allowing different roles to have different permissions for reading,
writing, and managing configuration values.
"""

from typing import Dict, List, Set, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import re

from .audit_logger import get_audit_logger, get_audit_context


class ConfigPermission(Enum):
    """Configuration permissions that can be granted."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"
    ROTATE = "rotate"
    VALIDATE = "validate"
    AUDIT_VIEW = "audit_view"
    AUDIT_EXPORT = "audit_export"
    ALL = "all"


class ConfigRole(Enum):
    """Pre-defined configuration access roles."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SECURITY_ADMIN = "security_admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class FieldPermission:
    """Permission definition for a specific field or pattern."""
    field_pattern: str  # Regex pattern for field names
    permissions: Set[ConfigPermission]
    environments: Optional[Set[str]] = None  # None means all environments
    
    def __post_init__(self):
        # Compile regex pattern
        self._pattern = re.compile(self.field_pattern)
    
    def matches(self, field_name: str, environment: str) -> bool:
        """Check if this permission applies to the given field and environment."""
        # Check field pattern
        if not self._pattern.match(field_name):
            return False
        
        # Check environment restriction
        if self.environments and environment not in self.environments:
            return False
        
        return True


@dataclass
class RoleDefinition:
    """Definition of a configuration role with its permissions."""
    name: str
    description: str
    field_permissions: List[FieldPermission] = field(default_factory=list)
    global_permissions: Set[ConfigPermission] = field(default_factory=set)
    inherits_from: Optional[List[str]] = None
    
    def get_all_permissions(self, role_registry: Dict[str, 'RoleDefinition']) -> List[FieldPermission]:
        """Get all permissions including inherited ones."""
        all_permissions = list(self.field_permissions)
        
        if self.inherits_from:
            for parent_role_name in self.inherits_from:
                if parent_role := role_registry.get(parent_role_name):
                    all_permissions.extend(parent_role.get_all_permissions(role_registry))
        
        return all_permissions


class ConfigRBAC:
    """Main RBAC system for configuration management."""
    
    def __init__(self):
        self._roles: Dict[str, RoleDefinition] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._audit_logger = get_audit_logger()
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize default role definitions."""
        # Viewer - read-only access to non-sensitive fields
        self._roles[ConfigRole.VIEWER.value] = RoleDefinition(
            name=ConfigRole.VIEWER.value,
            description="Read-only access to non-sensitive configuration",
            field_permissions=[
                FieldPermission(
                    field_pattern=r"^(app_name|app_version|environment|debug|host|port|log_level)$",
                    permissions={ConfigPermission.READ}
                ),
                FieldPermission(
                    field_pattern=r"^(?!.*(?:password|secret|key|token|credential|private|auth|supabase)).*$",
                    permissions={ConfigPermission.READ}
                )
            ]
        )
        
        # Operator - can read all, write non-sensitive
        self._roles[ConfigRole.OPERATOR.value] = RoleDefinition(
            name=ConfigRole.OPERATOR.value,
            description="Read all, write non-sensitive configuration",
            inherits_from=[ConfigRole.VIEWER.value],
            field_permissions=[
                FieldPermission(
                    field_pattern=r"^(log_level|rate_limit.*|cors_.*|frontend_url)$",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE}
                ),
                FieldPermission(
                    field_pattern=r".*",  # Read everything
                    permissions={ConfigPermission.READ}
                )
            ],
            global_permissions={ConfigPermission.VALIDATE, ConfigPermission.EXPORT}
        )
        
        # Developer - full access in dev/staging, limited in production
        self._roles[ConfigRole.DEVELOPER.value] = RoleDefinition(
            name=ConfigRole.DEVELOPER.value,
            description="Full access in dev/staging, limited in production",
            inherits_from=None,  # Don't inherit operator's broad read permissions
            field_permissions=[
                # Development/staging permissions
                FieldPermission(
                    field_pattern=r".*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE},
                    environments={"development", "test", "staging"}
                ),
                # Production permissions - only non-sensitive fields
                FieldPermission(
                    field_pattern=r"^(?!.*(?:secret_key|supabase_.*_key|jwt_secret|password|token|credential|auth|private)).*$",
                    permissions={ConfigPermission.READ},
                    environments={"production"}
                ),
                # Can write some non-sensitive fields in all environments
                FieldPermission(
                    field_pattern=r"^(log_level|rate_limit.*|cors_.*|frontend_url)$",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE}
                )
            ],
            global_permissions={ConfigPermission.EXPORT, ConfigPermission.VALIDATE}
        )
        
        # Admin - full configuration access, limited audit access
        self._roles[ConfigRole.ADMIN.value] = RoleDefinition(
            name=ConfigRole.ADMIN.value,
            description="Full configuration access with audit viewing",
            field_permissions=[
                FieldPermission(
                    field_pattern=r".*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE, ConfigPermission.DELETE}
                )
            ],
            global_permissions={
                ConfigPermission.EXPORT,
                ConfigPermission.VALIDATE,
                ConfigPermission.AUDIT_VIEW
            }
        )
        
        # Security Admin - focus on security-related configuration
        self._roles[ConfigRole.SECURITY_ADMIN.value] = RoleDefinition(
            name=ConfigRole.SECURITY_ADMIN.value,
            description="Security configuration and audit management",
            inherits_from=[ConfigRole.ADMIN.value],
            field_permissions=[
                FieldPermission(
                    field_pattern=r".*(password|secret|key|token|credential|auth|security|csrf|rate_limit).*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE, ConfigPermission.ROTATE}
                )
            ],
            global_permissions={
                ConfigPermission.EXPORT,
                ConfigPermission.ROTATE,
                ConfigPermission.AUDIT_VIEW,
                ConfigPermission.AUDIT_EXPORT
            }
        )
        
        # Super Admin - unrestricted access
        self._roles[ConfigRole.SUPER_ADMIN.value] = RoleDefinition(
            name=ConfigRole.SUPER_ADMIN.value,
            description="Unrestricted configuration access",
            field_permissions=[
                FieldPermission(
                    field_pattern=r".*",
                    permissions={ConfigPermission.ALL}
                )
            ],
            global_permissions={ConfigPermission.ALL}
        )
    
    def register_role(self, role: RoleDefinition):
        """Register a custom role definition."""
        self._roles[role.name] = role
    
    def assign_role(self, user_id: str, role_name: str):
        """Assign a role to a user."""
        if role_name not in self._roles:
            raise ValueError(f"Unknown role: {role_name}")
        
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role_name)
        
        # Log role assignment
        self._audit_logger.log_config_write(
            field_name="user_roles",
            old_value=None,
            new_value=f"{user_id}:{role_name}",
            success=True,
            metadata={
                "operation": "role_assignment",
                "user_id": user_id,
                "role": role_name
            }
        )
    
    def revoke_role(self, user_id: str, role_name: str):
        """Revoke a role from a user."""
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role_name)
            
            # Log role revocation
            self._audit_logger.log_config_write(
                field_name="user_roles",
                old_value=f"{user_id}:{role_name}",
                new_value=None,
                success=True,
                metadata={
                    "operation": "role_revocation",
                    "user_id": user_id,
                    "role": role_name
                }
            )
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles assigned to a user."""
        return self._user_roles.get(user_id, set())
    
    def check_permission(
        self,
        user_id: str,
        permission: ConfigPermission,
        field_name: Optional[str] = None,
        environment: str = "development"
    ) -> bool:
        """Check if a user has a specific permission."""
        user_roles = self.get_user_roles(user_id)
        
        # Check each role
        for role_name in user_roles:
            if role := self._roles.get(role_name):
                # Check global permissions
                if permission in role.global_permissions or ConfigPermission.ALL in role.global_permissions:
                    return True
                
                # Check field-specific permissions if field_name provided
                if field_name:
                    all_permissions = role.get_all_permissions(self._roles)
                    for field_perm in all_permissions:
                        if field_perm.matches(field_name, environment):
                            if permission in field_perm.permissions or ConfigPermission.ALL in field_perm.permissions:
                                return True
        
        return False
    
    def check_field_access(
        self,
        user_id: str,
        field_name: str,
        permission: ConfigPermission,
        environment: str = "development"
    ) -> bool:
        """Check if a user can access a specific field with given permission."""
        has_access = self.check_permission(user_id, permission, field_name, environment)
        
        # Log access attempt
        if not has_access:
            self._audit_logger.log_access_denied(
                action=permission.value,
                resource=f"config.{field_name}",
                reason=f"User {user_id} lacks {permission.value} permission for {field_name}",
                metadata={
                    "user_id": user_id,
                    "field": field_name,
                    "environment": environment,
                    "required_permission": permission.value
                }
            )
        
        return has_access
    
    def get_readable_fields(self, user_id: str, environment: str = "development") -> Set[str]:
        """Get all fields a user can read in the given environment."""
        readable_fields = set()
        user_roles = self.get_user_roles(user_id)
        
        # This is a simplified version - in practice, you'd check against actual field names
        for role_name in user_roles:
            if role := self._roles.get(role_name):
                all_permissions = role.get_all_permissions(self._roles)
                for field_perm in all_permissions:
                    if ConfigPermission.READ in field_perm.permissions or ConfigPermission.ALL in field_perm.permissions:
                        # Add pattern indicator
                        readable_fields.add(f"pattern:{field_perm.field_pattern}")
        
        return readable_fields
    
    def filter_config_dict(
        self,
        config_dict: Dict[str, Any],
        user_id: str,
        environment: str = "development"
    ) -> Dict[str, Any]:
        """Filter a configuration dictionary based on user permissions."""
        filtered = {}
        
        for field_name, value in config_dict.items():
            if self.check_field_access(user_id, field_name, ConfigPermission.READ, environment):
                filtered[field_name] = value
        
        return filtered
    
    def enforce_write_permission(
        self,
        user_id: str,
        field_name: str,
        environment: str = "development"
    ):
        """Enforce write permission, raising exception if denied."""
        if not self.check_field_access(user_id, field_name, ConfigPermission.WRITE, environment):
            raise PermissionError(
                f"User {user_id} does not have write permission for field '{field_name}' in {environment}"
            )
    
    def get_permission_matrix(self, user_id: str) -> Dict[str, Dict[str, bool]]:
        """Get a matrix of all permissions for a user."""
        matrix = {}
        user_roles = self.get_user_roles(user_id)
        
        # Get all permissions
        all_permissions = list(ConfigPermission)
        
        # Check global permissions
        matrix["_global"] = {}
        for perm in all_permissions:
            matrix["_global"][perm.value] = self.check_permission(user_id, perm)
        
        # Add role information
        matrix["_roles"] = list(user_roles)
        
        return matrix


# Global RBAC instance
_config_rbac: Optional[ConfigRBAC] = None


def get_config_rbac() -> ConfigRBAC:
    """Get or create the global RBAC instance."""
    global _config_rbac
    if _config_rbac is None:
        _config_rbac = ConfigRBAC()
    return _config_rbac


def require_permission(permission: ConfigPermission, field_name: Optional[str] = None):
    """Decorator to enforce permission requirements on functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get current user from audit context
            context = get_audit_context()
            user_id = context.user_id
            
            if not user_id:
                raise PermissionError("No user context available")
            
            # Check permission
            rbac = get_config_rbac()
            environment = context.environment
            
            if not rbac.check_permission(user_id, permission, field_name, environment):
                raise PermissionError(
                    f"User {user_id} lacks {permission.value} permission"
                    + (f" for field {field_name}" if field_name else "")
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_field_filtering(func: Callable) -> Callable:
    """Decorator to automatically filter configuration based on permissions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # If result is a dict, filter it
        if isinstance(result, dict):
            context = get_audit_context()
            if context.user_id:
                rbac = get_config_rbac()
                result = rbac.filter_config_dict(
                    result,
                    context.user_id,
                    context.environment
                )
        
        return result
    
    return wrapper


class RBACConfigProxy:
    """Proxy class that enforces RBAC on configuration access."""
    
    def __init__(self, config: Any, user_id: str, environment: str = "development"):
        self._config = config
        self._user_id = user_id
        self._environment = environment
        self._rbac = get_config_rbac()
        self._audit_logger = get_audit_logger()
    
    def __getattribute__(self, name: str) -> Any:
        # Handle internal attributes
        if name.startswith('_') or name in ['get_safe_config', 'export_safe']:
            return object.__getattribute__(self, name)
        
        # Check read permission
        if name != '__dict__':
            rbac = object.__getattribute__(self, '_rbac')
            user_id = object.__getattribute__(self, '_user_id')
            environment = object.__getattribute__(self, '_environment')
            
            if not rbac.check_field_access(user_id, name, ConfigPermission.READ, environment):
                raise PermissionError(f"Access denied to field '{name}'")
        
        # Get the actual value
        config = object.__getattribute__(self, '_config')
        return getattr(config, name)
    
    def __setattr__(self, name: str, value: Any):
        # Handle internal attributes
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        
        # Check write permission
        self._rbac.enforce_write_permission(self._user_id, name, self._environment)
        
        # Set the value
        setattr(self._config, name, value)
    
    def get_safe_config(self) -> Dict[str, Any]:
        """Get filtered configuration based on permissions."""
        all_config = self._config.get_safe_config() if hasattr(self._config, 'get_safe_config') else {}
        return self._rbac.filter_config_dict(all_config, self._user_id, self._environment)
    
    def export_safe(self) -> Dict[str, Any]:
        """Export configuration with RBAC filtering."""
        # Check export permission
        if not self._rbac.check_permission(self._user_id, ConfigPermission.EXPORT):
            raise PermissionError("User lacks export permission")
        
        return self.get_safe_config()