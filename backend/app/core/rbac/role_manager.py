"""
Role Manager

Handles role definitions and role-based access control following the Single Responsibility Principle.
"""

from typing import Dict, List, Set, Optional
from enum import Enum
from dataclasses import dataclass, field

from .permission_manager import FieldPermission, ConfigPermission


class ConfigRole(Enum):
    """Pre-defined configuration access roles."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SECURITY_ADMIN = "security_admin"
    SUPER_ADMIN = "super_admin"


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


class RoleManager:
    """
    Manages roles and role assignments.
    
    Responsibilities:
    - Define and manage roles
    - Assign roles to users
    - Handle role inheritance
    - Provide role-based permission lookup
    """
    
    def __init__(self):
        """Initialize role manager."""
        self._roles: Dict[str, RoleDefinition] = {}
        self._user_roles: Dict[str, Set[str]] = {}
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
                    field_pattern=r"^(log_level|debug|frontend_url|cors_origins)$",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE}
                )
            ],
            global_permissions={ConfigPermission.VALIDATE, ConfigPermission.EXPORT}
        )
        
        # Admin - full access except security-specific operations
        self._roles[ConfigRole.ADMIN.value] = RoleDefinition(
            name=ConfigRole.ADMIN.value,
            description="Full configuration access with audit viewing",
            field_permissions=[
                FieldPermission(
                    field_pattern=r".*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE, ConfigPermission.EXPORT}
                )
            ],
            global_permissions={
                ConfigPermission.VALIDATE, ConfigPermission.EXPORT, 
                ConfigPermission.AUDIT_VIEW
            }
        )
        
        # Security Admin - security configuration and audit management
        self._roles[ConfigRole.SECURITY_ADMIN.value] = RoleDefinition(
            name=ConfigRole.SECURITY_ADMIN.value,
            description="Security configuration and audit management",
            inherits_from=[ConfigRole.ADMIN.value],
            field_permissions=[
                FieldPermission(
                    field_pattern=r".*(?:secret|key|token|credential|auth|password|security|csrf|rate_limit|lockout).*",
                    permissions={ConfigPermission.ALL}
                )
            ],
            global_permissions={
                ConfigPermission.ROTATE, ConfigPermission.AUDIT_VIEW, 
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
    
    def register_role(self, role: RoleDefinition) -> None:
        """Register a custom role."""
        self._roles[role.name] = role
    
    def get_role(self, role_name: str) -> Optional[RoleDefinition]:
        """Get role definition by name."""
        return self._roles.get(role_name)
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User identifier
            role_name: Name of role to assign
            
        Returns:
            True if role was assigned successfully
        """
        if role_name not in self._roles:
            return False
        
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        
        self._user_roles[user_id].add(role_name)
        return True
    
    def revoke_role_from_user(self, user_id: str, role_name: str) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_id: User identifier
            role_name: Name of role to revoke
            
        Returns:
            True if role was revoked successfully
        """
        if user_id in self._user_roles:
            self._user_roles[user_id].discard(role_name)
            return True
        return False
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles assigned to a user."""
        return self._user_roles.get(user_id, set())
    
    def get_user_permissions(self, user_id: str) -> List[FieldPermission]:
        """Get all permissions for a user from their assigned roles."""
        all_permissions = []
        user_roles = self.get_user_roles(user_id)
        
        for role_name in user_roles:
            if role := self._roles.get(role_name):
                all_permissions.extend(role.get_all_permissions(self._roles))
        
        return all_permissions
    
    def user_has_role(self, user_id: str, role_name: str) -> bool:
        """Check if user has a specific role."""
        return role_name in self.get_user_roles(user_id)
    
    def get_all_roles(self) -> Dict[str, RoleDefinition]:
        """Get all registered roles."""
        return dict(self._roles)
    
    def get_role_hierarchy(self) -> Dict[str, List[str]]:
        """Get role inheritance hierarchy."""
        hierarchy = {}
        for role_name, role_def in self._roles.items():
            hierarchy[role_name] = role_def.inherits_from or []
        return hierarchy
    
    def clear_user_roles(self, user_id: str) -> None:
        """Clear all roles for a user."""
        if user_id in self._user_roles:
            del self._user_roles[user_id]
    
    def clear_all_assignments(self) -> None:
        """Clear all role assignments (useful for testing)."""
        self._user_roles.clear()
    
    def get_users_with_role(self, role_name: str) -> List[str]:
        """Get all users that have a specific role."""
        users = []
        for user_id, roles in self._user_roles.items():
            if role_name in roles:
                users.append(user_id)
        return users