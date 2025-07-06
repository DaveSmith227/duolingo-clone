"""
Configuration Access Service

Provides controlled access to configuration with RBAC enforcement,
audit logging, and security features.
"""

from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone

from app.core.config import get_settings, Settings
from app.core.config_rbac_compat import (
    get_config_rbac, ConfigPermission, ConfigRole,
    RBACConfigProxy, FieldPermission, RoleDefinition
)
from app.core.audited_config import create_audited_settings
from app.core.audit_logger import get_audit_logger, set_audit_context
from app.models.user import User


class ConfigAccessService:
    """Service for managing configuration access with RBAC."""
    
    def __init__(self):
        self._rbac = get_config_rbac()
        self._audit_logger = get_audit_logger()
        self._settings = get_settings()
    
    def get_user_config(self, user: User) -> RBACConfigProxy:
        """Get configuration proxy with user's permissions."""
        # Set audit context
        set_audit_context(
            user_id=str(user.id),
            user_email=user.email,
            environment=self._settings.environment
        )
        
        # Ensure user has appropriate roles
        self._ensure_user_roles(user)
        
        # Create audited settings
        audited_settings = create_audited_settings(self._settings)
        
        # Wrap with RBAC proxy
        return RBACConfigProxy(
            audited_settings,
            str(user.id),
            self._settings.environment
        )
    
    def _ensure_user_roles(self, user: User):
        """Ensure user has appropriate configuration roles based on their system roles."""
        user_id = str(user.id)
        current_roles = self._rbac.get_user_roles(user_id)
        
        # Map system roles to config roles
        if user.is_super_admin:
            if ConfigRole.SUPER_ADMIN.value not in current_roles:
                self._rbac.assign_role(user_id, ConfigRole.SUPER_ADMIN.value)
        elif user.is_admin:
            if ConfigRole.ADMIN.value not in current_roles:
                self._rbac.assign_role(user_id, ConfigRole.ADMIN.value)
        elif user.role == "developer":
            if ConfigRole.DEVELOPER.value not in current_roles:
                self._rbac.assign_role(user_id, ConfigRole.DEVELOPER.value)
        elif user.role == "operator":
            if ConfigRole.OPERATOR.value not in current_roles:
                self._rbac.assign_role(user_id, ConfigRole.OPERATOR.value)
        else:
            # Default to viewer role
            if ConfigRole.VIEWER.value not in current_roles:
                self._rbac.assign_role(user_id, ConfigRole.VIEWER.value)
    
    def read_config_field(self, user: User, field_name: str) -> Any:
        """Read a specific configuration field."""
        config_proxy = self.get_user_config(user)
        
        try:
            value = getattr(config_proxy, field_name)
            
            # Log successful read
            self._audit_logger.log_config_read(
                field_name=field_name,
                value=value if not self._is_sensitive_field(field_name) else "***",
                success=True,
                metadata={
                    "user_role": user.role,
                    "config_roles": list(self._rbac.get_user_roles(str(user.id)))
                }
            )
            
            return value
            
        except PermissionError as e:
            # Permission denied is already logged by RBAC
            raise
        except AttributeError:
            raise ValueError(f"Configuration field '{field_name}' does not exist")
    
    def write_config_field(self, user: User, field_name: str, value: Any) -> Any:
        """Write a configuration field value."""
        config_proxy = self.get_user_config(user)
        
        # Get old value for audit
        try:
            old_value = getattr(config_proxy._config, field_name)
        except AttributeError:
            old_value = None
        
        # Attempt to write
        try:
            setattr(config_proxy, field_name, value)
            
            # Log successful write
            self._audit_logger.log_config_write(
                field_name=field_name,
                old_value=old_value if not self._is_sensitive_field(field_name) else "***",
                new_value=value if not self._is_sensitive_field(field_name) else "***",
                success=True,
                metadata={
                    "user_role": user.role,
                    "config_roles": list(self._rbac.get_user_roles(str(user.id)))
                }
            )
            
            return value
            
        except PermissionError:
            # Permission denied is already logged by RBAC
            raise
        except Exception as e:
            # Log failed write
            self._audit_logger.log_config_write(
                field_name=field_name,
                old_value=old_value,
                new_value=value,
                success=False,
                error_message=str(e)
            )
            raise
    
    def get_user_permissions(self, user: User) -> Dict[str, Any]:
        """Get the configuration permissions for a user."""
        self._ensure_user_roles(user)
        
        user_id = str(user.id)
        permissions = {
            "user_id": user_id,
            "email": user.email,
            "system_role": user.role,
            "config_roles": list(self._rbac.get_user_roles(user_id)),
            "environment": self._settings.environment,
            "permissions": self._rbac.get_permission_matrix(user_id),
            "readable_fields": list(self._rbac.get_readable_fields(user_id, self._settings.environment))
        }
        
        return permissions
    
    def export_config_for_user(self, user: User, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export configuration based on user's permissions."""
        config_proxy = self.get_user_config(user)
        
        # Check export permission
        if not self._rbac.check_permission(str(user.id), ConfigPermission.EXPORT):
            raise PermissionError("User lacks export permission")
        
        # Get safe config
        config = config_proxy.export_safe()
        
        # Additional filtering for sensitive fields if requested
        if not include_sensitive:
            config = self._filter_sensitive_fields(config)
        
        # Log export
        self._audit_logger.log_config_export(
            export_format="dict",
            include_sensitive=include_sensitive,
            success=True,
            metadata={
                "user_email": user.email,
                "fields_count": len(config),
                "environment": self._settings.environment
            }
        )
        
        return config
    
    def validate_config_for_user(self, user: User, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration updates based on user permissions."""
        # Check validate permission
        if not self._rbac.check_permission(str(user.id), ConfigPermission.VALIDATE):
            raise PermissionError("User lacks validate permission")
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "denied_fields": []
        }
        
        # Check write permissions for each field
        for field_name, new_value in config_updates.items():
            if not self._rbac.check_field_access(
                str(user.id),
                field_name,
                ConfigPermission.WRITE,
                self._settings.environment
            ):
                validation_results["denied_fields"].append(field_name)
                validation_results["valid"] = False
        
        # Log validation attempt
        self._audit_logger.log_config_validation(
            success=validation_results["valid"],
            validation_errors=validation_results.get("errors"),
            metadata={
                "user_email": user.email,
                "fields_attempted": list(config_updates.keys()),
                "denied_fields": validation_results["denied_fields"]
            }
        )
        
        return validation_results
    
    def rotate_secret_for_user(self, user: User, field_name: str) -> bool:
        """Rotate a secret field if user has permission."""
        # Check rotate permission
        if not self._rbac.check_field_access(
            str(user.id),
            field_name,
            ConfigPermission.ROTATE,
            self._settings.environment
        ):
            raise PermissionError(f"User lacks rotate permission for field '{field_name}'")
        
        # Log rotation attempt
        self._audit_logger.log_event(
            action="rotate",
            field_name=field_name,
            success=True,
            metadata={
                "user_email": user.email,
                "field": field_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        # In a real implementation, this would trigger actual secret rotation
        return True
    
    def assign_config_role(self, admin_user: User, target_user_id: str, role: ConfigRole):
        """Assign a configuration role to a user (admin only)."""
        # Check if admin has permission to manage roles
        if not admin_user.is_admin and not admin_user.is_super_admin:
            raise PermissionError("Only admins can assign configuration roles")
        
        # Assign the role
        self._rbac.assign_role(target_user_id, role.value)
        
        # Log role assignment
        self._audit_logger.log_config_write(
            field_name="config_roles",
            old_value=None,
            new_value=f"{target_user_id}:{role.value}",
            success=True,
            metadata={
                "admin_user": admin_user.email,
                "target_user": target_user_id,
                "role_assigned": role.value
            }
        )
    
    def revoke_config_role(self, admin_user: User, target_user_id: str, role: ConfigRole):
        """Revoke a configuration role from a user (admin only)."""
        # Check if admin has permission to manage roles
        if not admin_user.is_admin and not admin_user.is_super_admin:
            raise PermissionError("Only admins can revoke configuration roles")
        
        # Revoke the role
        self._rbac.revoke_role(target_user_id, role.value)
        
        # Log role revocation
        self._audit_logger.log_config_write(
            field_name="config_roles",
            old_value=f"{target_user_id}:{role.value}",
            new_value=None,
            success=True,
            metadata={
                "admin_user": admin_user.email,
                "target_user": target_user_id,
                "role_revoked": role.value
            }
        )
    
    def create_custom_role(
        self,
        admin_user: User,
        role_name: str,
        description: str,
        field_permissions: List[Dict[str, Any]],
        inherits_from: Optional[List[str]] = None
    ):
        """Create a custom configuration role (super admin only)."""
        if not admin_user.is_super_admin:
            raise PermissionError("Only super admins can create custom roles")
        
        # Convert field permissions
        permissions = []
        for perm_dict in field_permissions:
            permissions.append(FieldPermission(
                field_pattern=perm_dict["pattern"],
                permissions={ConfigPermission(p) for p in perm_dict["permissions"]},
                environments=set(perm_dict.get("environments", [])) if perm_dict.get("environments") else None
            ))
        
        # Create role definition
        role = RoleDefinition(
            name=role_name,
            description=description,
            field_permissions=permissions,
            inherits_from=inherits_from
        )
        
        # Register the role
        self._rbac.register_role(role)
        
        # Log role creation
        self._audit_logger.log_config_write(
            field_name="custom_roles",
            old_value=None,
            new_value=role_name,
            success=True,
            metadata={
                "admin_user": admin_user.email,
                "role_name": role_name,
                "description": description,
                "permissions_count": len(permissions)
            }
        )
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field contains sensitive data."""
        sensitive_patterns = [
            "password", "secret", "key", "token", "credential",
            "private", "auth", "jwt", "api", "supabase"
        ]
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)
    
    def _filter_sensitive_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out sensitive fields from configuration."""
        filtered = {}
        for key, value in config.items():
            if self._is_sensitive_field(key):
                filtered[key] = "***REDACTED***" if value else None
            else:
                filtered[key] = value
        return filtered


# Global service instance
_config_access_service: Optional[ConfigAccessService] = None


def get_config_access_service() -> ConfigAccessService:
    """Get or create the global configuration access service."""
    global _config_access_service
    if _config_access_service is None:
        _config_access_service = ConfigAccessService()
    return _config_access_service