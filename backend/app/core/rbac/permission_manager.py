"""
Permission Manager

Handles permission definitions and checking following the Single Responsibility Principle.
"""

from typing import Set, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
import re


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


@dataclass
class FieldPermission:
    """Permission definition for a specific field or pattern."""
    field_pattern: str  # Regex pattern for field names
    permissions: Set[ConfigPermission]
    environments: Set[str] = None  # None means all environments
    
    def __post_init__(self):
        # Compile regex pattern
        self._pattern = re.compile(self.field_pattern)
        if self.environments is None:
            self.environments = set()
    
    def matches(self, field_name: str, environment: str) -> bool:
        """Check if this permission applies to the given field and environment."""
        # Check field pattern
        if not self._pattern.match(field_name):
            return False
        
        # Check environment restriction (empty set means all environments)
        if self.environments and environment not in self.environments:
            return False
        
        return True


class PermissionManager:
    """
    Manages permissions and permission checking.
    
    Responsibilities:
    - Define field-level permissions
    - Check if operations are allowed
    - Manage permission inheritance
    """
    
    def __init__(self):
        """Initialize permission manager."""
        self._field_permissions: List[FieldPermission] = []
    
    def add_field_permission(self, permission: FieldPermission) -> None:
        """Add a field permission."""
        self._field_permissions.append(permission)
    
    def has_permission(self, field_name: str, permission: ConfigPermission, 
                      environment: str) -> bool:
        """
        Check if a field operation is permitted.
        
        Args:
            field_name: Name of the field
            permission: Required permission
            environment: Current environment
            
        Returns:
            True if permission is granted
        """
        # Check if any field permission grants this access
        for field_perm in self._field_permissions:
            if field_perm.matches(field_name, environment):
                if (permission in field_perm.permissions or 
                    ConfigPermission.ALL in field_perm.permissions):
                    return True
        
        return False
    
    def get_allowed_fields(self, permission: ConfigPermission, environment: str,
                          field_names: List[str]) -> List[str]:
        """
        Get list of fields that allow the specified permission.
        
        Args:
            permission: Required permission
            environment: Current environment  
            field_names: List of field names to check
            
        Returns:
            List of allowed field names
        """
        allowed = []
        for field_name in field_names:
            if self.has_permission(field_name, permission, environment):
                allowed.append(field_name)
        return allowed
    
    def filter_config_dict(self, config_dict: Dict[str, Any], 
                          permission: ConfigPermission, environment: str) -> Dict[str, Any]:
        """
        Filter configuration dictionary based on permissions.
        
        Args:
            config_dict: Configuration dictionary
            permission: Required permission
            environment: Current environment
            
        Returns:
            Filtered configuration dictionary
        """
        filtered = {}
        for field_name, value in config_dict.items():
            if self.has_permission(field_name, permission, environment):
                filtered[field_name] = value
        return filtered
    
    def get_permission_summary(self, environment: str) -> Dict[str, List[str]]:
        """
        Get summary of permissions for an environment.
        
        Args:
            environment: Environment to summarize
            
        Returns:
            Dictionary mapping permission types to field patterns
        """
        summary = {}
        
        for permission in ConfigPermission:
            if permission == ConfigPermission.ALL:
                continue
                
            patterns = []
            for field_perm in self._field_permissions:
                if (not field_perm.environments or environment in field_perm.environments):
                    if (permission in field_perm.permissions or 
                        ConfigPermission.ALL in field_perm.permissions):
                        patterns.append(field_perm.field_pattern)
            
            summary[permission.value] = patterns
        
        return summary
    
    def clear_permissions(self) -> None:
        """Clear all permissions (useful for testing)."""
        self._field_permissions.clear()
    
    def get_permissions_count(self) -> int:
        """Get total number of field permissions."""
        return len(self._field_permissions)