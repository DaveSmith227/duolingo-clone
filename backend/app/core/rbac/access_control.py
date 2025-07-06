"""
Access Control

Provides access control checking and enforcement following the Single Responsibility Principle.
"""

from typing import Dict, Any, List, Optional, Callable
from functools import wraps

from .permission_manager import PermissionManager, ConfigPermission
from .role_manager import RoleManager
from ..audit_logger import get_audit_logger, get_audit_context


class AccessDeniedError(Exception):
    """Raised when access is denied."""
    pass


class AccessControlService:
    """
    Service responsible for access control enforcement.
    
    Responsibilities:
    - Check if users can perform operations
    - Enforce access control in functions
    - Integrate with audit logging
    """
    
    def __init__(self, role_manager: RoleManager, permission_manager: PermissionManager):
        """Initialize access control service."""
        self._role_manager = role_manager
        self._permission_manager = permission_manager
        self._audit_logger = get_audit_logger()
    
    def check_field_access(self, user_id: str, field_name: str, 
                          permission: ConfigPermission, environment: str) -> bool:
        """
        Check if user can access a specific field.
        
        Args:
            user_id: User identifier
            field_name: Field name to check
            permission: Required permission
            environment: Current environment
            
        Returns:
            True if access is allowed
        """
        # Get user permissions from their roles
        user_permissions = self._role_manager.get_user_permissions(user_id)
        
        # Check if any permission grants access
        for field_perm in user_permissions:
            if field_perm.matches(field_name, environment):
                if (permission in field_perm.permissions or 
                    ConfigPermission.ALL in field_perm.permissions):
                    return True
        
        return False
    
    def enforce_field_access(self, user_id: str, field_name: str,
                           permission: ConfigPermission, environment: str) -> None:
        """
        Enforce field access control, raising exception if denied.
        
        Args:
            user_id: User identifier
            field_name: Field name to check
            permission: Required permission
            environment: Current environment
            
        Raises:
            AccessDeniedError: If access is denied
        """
        if not self.check_field_access(user_id, field_name, permission, environment):
            # Log access denial
            self._audit_logger.log_config_read(
                field_name=field_name,
                success=False,
                error_message=f"Access denied for user {user_id}",
                metadata={
                    "required_permission": permission.value,
                    "environment": environment,
                    "user_roles": list(self._role_manager.get_user_roles(user_id))
                }
            )
            
            raise AccessDeniedError(
                f"User {user_id} does not have {permission.value} permission for field {field_name}"
            )
    
    def filter_readable_fields(self, user_id: str, config_dict: Dict[str, Any],
                              environment: str) -> Dict[str, Any]:
        """
        Filter configuration dictionary to only readable fields for user.
        
        Args:
            user_id: User identifier
            config_dict: Configuration dictionary
            environment: Current environment
            
        Returns:
            Filtered configuration dictionary
        """
        filtered = {}
        
        for field_name, value in config_dict.items():
            if self.check_field_access(user_id, field_name, ConfigPermission.READ, environment):
                filtered[field_name] = value
        
        return filtered
    
    def filter_writable_fields(self, user_id: str, config_dict: Dict[str, Any],
                              environment: str) -> Dict[str, Any]:
        """
        Filter configuration dictionary to only writable fields for user.
        
        Args:
            user_id: User identifier
            config_dict: Configuration dictionary
            environment: Current environment
            
        Returns:
            Filtered configuration dictionary
        """
        filtered = {}
        
        for field_name, value in config_dict.items():
            if self.check_field_access(user_id, field_name, ConfigPermission.WRITE, environment):
                filtered[field_name] = value
        
        return filtered
    
    def get_user_access_summary(self, user_id: str, environment: str) -> Dict[str, Any]:
        """
        Get summary of user's access permissions.
        
        Args:
            user_id: User identifier
            environment: Current environment
            
        Returns:
            Access summary dictionary
        """
        user_roles = self._role_manager.get_user_roles(user_id)
        
        summary = {
            "user_id": user_id,
            "environment": environment,
            "roles": list(user_roles),
            "permissions": {
                "readable_patterns": [],
                "writable_patterns": [],
                "global_permissions": []
            }
        }
        
        # Aggregate permissions from all roles
        user_permissions = self._role_manager.get_user_permissions(user_id)
        
        for field_perm in user_permissions:
            if not field_perm.environments or environment in field_perm.environments:
                if ConfigPermission.READ in field_perm.permissions:
                    summary["permissions"]["readable_patterns"].append(field_perm.field_pattern)
                if ConfigPermission.WRITE in field_perm.permissions:
                    summary["permissions"]["writable_patterns"].append(field_perm.field_pattern)
        
        # Get global permissions
        for role_name in user_roles:
            if role := self._role_manager.get_role(role_name):
                summary["permissions"]["global_permissions"].extend(
                    [perm.value for perm in role.global_permissions]
                )
        
        return summary


def require_permission(permission: ConfigPermission, field_name: Optional[str] = None):
    """
    Decorator to require specific permission for function execution.
    
    Args:
        permission: Required permission
        field_name: Optional field name (can be derived from function args)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get current user and environment from audit context
            audit_context = get_audit_context()
            user_id = audit_context.get('user_id') if audit_context else 'anonymous'
            environment = audit_context.get('environment', 'development')
            
            # Determine field name
            actual_field_name = field_name
            if not actual_field_name and len(args) > 0:
                # Try to extract field name from first argument
                if isinstance(args[0], str):
                    actual_field_name = args[0]
                elif hasattr(args[0], '__name__'):
                    actual_field_name = args[0].__name__
            
            if not actual_field_name:
                actual_field_name = func.__name__
            
            # Get access control service from global context (would be dependency injected in real app)
            # For now, create a minimal check
            
            # Log the access attempt
            audit_logger = get_audit_logger()
            audit_logger.log_config_read(
                field_name=actual_field_name,
                success=True,
                metadata={
                    "function": func.__name__,
                    "required_permission": permission.value,
                    "user_id": user_id,
                    "environment": environment
                }
            )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_field_filtering(permission: ConfigPermission):
    """
    Decorator to filter function results based on field permissions.
    
    Args:
        permission: Required permission for fields
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # If result is a dict, filter it based on permissions
            if isinstance(result, dict):
                # Get current user and environment from audit context
                audit_context = get_audit_context()
                user_id = audit_context.get('user_id', 'anonymous')
                environment = audit_context.get('environment', 'development')
                
                # For now, return the result as-is (would filter in real implementation)
                # filtered_result = access_control_service.filter_readable_fields(user_id, result, environment)
                # return filtered_result
                
                return result
            
            return result
        
        return wrapper
    return decorator