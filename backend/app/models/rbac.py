"""
Role-Based Access Control Models

SQLAlchemy models for role and permission management
with custom JWT claims integration.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import enum

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, Enum, JSON, Table
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    BaseModel.metadata,
    Column('role_id', String(36), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', String(36), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    BaseModel.metadata,
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', String(36), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('assigned_at', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('assigned_by', String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
)


class RoleType(enum.Enum):
    """Enumeration for role types."""
    SYSTEM = "system"       # System-defined roles
    CUSTOM = "custom"       # User-defined roles
    TEMPORARY = "temporary" # Temporary roles with expiration


class PermissionScope(enum.Enum):
    """Enumeration for permission scopes."""
    GLOBAL = "global"       # Global permissions
    COURSE = "course"       # Course-specific permissions
    LESSON = "lesson"       # Lesson-specific permissions
    USER = "user"          # User-specific permissions


class Role(BaseModel):
    """
    Role model for role-based access control.
    
    Defines roles that can be assigned to users with associated permissions.
    Supports both system-defined and custom roles.
    """
    
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique role name"
    )
    
    display_name = Column(
        String(255),
        nullable=False,
        doc="Human-readable role name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Role description"
    )
    
    role_type = Column(
        Enum(RoleType),
        default=RoleType.CUSTOM,
        nullable=False,
        doc="Type of role (system, custom, temporary)"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether role is active and can be assigned"
    )
    
    priority = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Role priority for conflict resolution (higher = more priority)"
    )
    
    role_metadata = Column(
        JSON,
        nullable=True,
        doc="Additional role metadata"
    )
    
    # Relationships
    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        doc="Permissions associated with this role"
    )
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate role name."""
        if not name or not name.strip():
            raise ValueError("Role name is required")
        
        name = name.strip().lower()
        
        # Check for reserved role names
        reserved_names = ['admin', 'user', 'guest', 'moderator', 'instructor']
        if name in reserved_names and self.role_type != RoleType.SYSTEM:
            raise ValueError(f"Role name '{name}' is reserved for system roles")
        
        # Validate format (alphanumeric, underscore, hyphen)
        import re
        if not re.match(r'^[a-z0-9_-]+$', name):
            raise ValueError("Role name can only contain lowercase letters, numbers, underscores, and hyphens")
        
        return name
    
    @validates('priority')
    def validate_priority(self, key, priority):
        """Validate role priority."""
        if priority < 0 or priority > 1000:
            raise ValueError("Role priority must be between 0 and 1000")
        return priority
    
    def has_permission(self, permission_name: str, scope: str = None, resource_id: str = None) -> bool:
        """
        Check if role has a specific permission.
        
        Args:
            permission_name: Name of the permission to check
            scope: Permission scope (optional)
            resource_id: Resource ID for scoped permissions (optional)
            
        Returns:
            True if role has the permission, False otherwise
        """
        for permission in self.permissions:
            if permission.name == permission_name:
                # Check scope if provided
                if scope and permission.scope.value != scope:
                    continue
                
                # For scoped permissions, check resource access
                if resource_id and permission.scope != PermissionScope.GLOBAL:
                    # This would need additional logic for resource-specific checks
                    # For now, we'll allow if the permission exists
                    pass
                
                return True
        
        return False
    
    def get_jwt_claims(self) -> Dict[str, Any]:
        """
        Get JWT claims for this role.
        
        Returns:
            Dictionary of claims to include in JWT tokens
        """
        return {
            'role': self.name,
            'role_display_name': self.display_name,
            'role_type': self.role_type.value,
            'role_priority': self.priority,
            'permissions': [perm.name for perm in self.permissions],
            'role_metadata': self.role_metadata or {}
        }
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name}, type={self.role_type.value})>"


class Permission(BaseModel):
    """
    Permission model for fine-grained access control.
    
    Defines specific permissions that can be granted to roles.
    Supports different scopes and resource-specific permissions.
    """
    
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique permission name"
    )
    
    display_name = Column(
        String(255),
        nullable=False,
        doc="Human-readable permission name"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Permission description"
    )
    
    scope = Column(
        Enum(PermissionScope),
        default=PermissionScope.GLOBAL,
        nullable=False,
        doc="Permission scope (global, course, lesson, user)"
    )
    
    resource_type = Column(
        String(50),
        nullable=True,
        doc="Type of resource this permission applies to"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether permission is active"
    )
    
    permission_metadata = Column(
        JSON,
        nullable=True,
        doc="Additional permission metadata"
    )
    
    # Relationships
    roles = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
        doc="Roles that have this permission"
    )
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate permission name."""
        if not name or not name.strip():
            raise ValueError("Permission name is required")
        
        name = name.strip().lower()
        
        # Validate format (alphanumeric, underscore, dot, colon)
        import re
        if not re.match(r'^[a-z0-9_.:]+$', name):
            raise ValueError("Permission name can only contain lowercase letters, numbers, underscores, dots, and colons")
        
        return name
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, scope={self.scope.value})>"


class UserRoleAssignment(BaseModel):
    """
    User role assignment model for tracking role assignments.
    
    Provides audit trail and additional context for role assignments
    including expiration and assignment metadata.
    """
    
    user_id = Column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="User ID"
    )
    
    role_id = Column(
        String(36),
        ForeignKey('roles.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Role ID"
    )
    
    assigned_by = Column(
        String(36),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        doc="User ID of who assigned this role"
    )
    
    assigned_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="When the role was assigned"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the role assignment expires (null = never)"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether role assignment is active"
    )
    
    context = Column(
        JSON,
        nullable=True,
        doc="Additional context for the role assignment"
    )
    
    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        doc="User who has this role"
    )
    
    role = relationship(
        "Role",
        doc="Role that is assigned"
    )
    
    assigned_by_user = relationship(
        "User",
        foreign_keys=[assigned_by],
        doc="User who assigned this role"
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if role assignment has expired."""
        if not self.expires_at:
            return False
        return self.expires_at <= datetime.now(timezone.utc)
    
    @property
    def is_valid(self) -> bool:
        """Check if role assignment is valid and active."""
        return self.is_active and not self.is_expired
    
    def extend_expiration(self, days: int):
        """
        Extend role assignment expiration.
        
        Args:
            days: Number of days to extend the assignment
        """
        from datetime import timedelta
        
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    
    def revoke(self, revoked_by: str = None):
        """
        Revoke role assignment.
        
        Args:
            revoked_by: User ID of who revoked the assignment
        """
        self.is_active = False
        if revoked_by:
            self.context = self.context or {}
            self.context['revoked_by'] = revoked_by
            self.context['revoked_at'] = datetime.now(timezone.utc).isoformat()
    
    def __repr__(self) -> str:
        return f"<UserRoleAssignment(id={self.id}, user_id={self.user_id}, role_id={self.role_id})>"


# Default system roles and permissions
DEFAULT_ROLES = [
    {
        'name': 'admin',
        'display_name': 'Administrator',
        'description': 'Full system administration access',
        'role_type': RoleType.SYSTEM,
        'priority': 1000
    },
    {
        'name': 'moderator',
        'display_name': 'Moderator',
        'description': 'Content moderation and user management',
        'role_type': RoleType.SYSTEM,
        'priority': 800
    },
    {
        'name': 'instructor',
        'display_name': 'Instructor',
        'description': 'Course and lesson management',
        'role_type': RoleType.SYSTEM,
        'priority': 600
    },
    {
        'name': 'user',
        'display_name': 'User',
        'description': 'Standard user access',
        'role_type': RoleType.SYSTEM,
        'priority': 100
    },
    {
        'name': 'guest',
        'display_name': 'Guest',
        'description': 'Limited guest access',
        'role_type': RoleType.SYSTEM,
        'priority': 0
    }
]

DEFAULT_PERMISSIONS = [
    # Admin permissions
    {'name': 'admin.all', 'display_name': 'Full Admin Access', 'scope': PermissionScope.GLOBAL},
    {'name': 'admin.users.manage', 'display_name': 'Manage Users', 'scope': PermissionScope.GLOBAL},
    {'name': 'admin.roles.manage', 'display_name': 'Manage Roles', 'scope': PermissionScope.GLOBAL},
    {'name': 'admin.system.config', 'display_name': 'System Configuration', 'scope': PermissionScope.GLOBAL},
    
    # Content management permissions
    {'name': 'content.courses.create', 'display_name': 'Create Courses', 'scope': PermissionScope.GLOBAL},
    {'name': 'content.courses.edit', 'display_name': 'Edit Courses', 'scope': PermissionScope.COURSE},
    {'name': 'content.courses.delete', 'display_name': 'Delete Courses', 'scope': PermissionScope.COURSE},
    {'name': 'content.lessons.create', 'display_name': 'Create Lessons', 'scope': PermissionScope.COURSE},
    {'name': 'content.lessons.edit', 'display_name': 'Edit Lessons', 'scope': PermissionScope.LESSON},
    {'name': 'content.lessons.delete', 'display_name': 'Delete Lessons', 'scope': PermissionScope.LESSON},
    
    # User management permissions
    {'name': 'users.view', 'display_name': 'View Users', 'scope': PermissionScope.GLOBAL},
    {'name': 'users.edit', 'display_name': 'Edit Users', 'scope': PermissionScope.USER},
    {'name': 'users.delete', 'display_name': 'Delete Users', 'scope': PermissionScope.USER},
    {'name': 'users.suspend', 'display_name': 'Suspend Users', 'scope': PermissionScope.USER},
    
    # Learning permissions
    {'name': 'learning.courses.access', 'display_name': 'Access Courses', 'scope': PermissionScope.COURSE},
    {'name': 'learning.lessons.complete', 'display_name': 'Complete Lessons', 'scope': PermissionScope.LESSON},
    {'name': 'learning.progress.view', 'display_name': 'View Progress', 'scope': PermissionScope.USER},
    
    # Profile permissions
    {'name': 'profile.view', 'display_name': 'View Profile', 'scope': PermissionScope.USER},
    {'name': 'profile.edit', 'display_name': 'Edit Profile', 'scope': PermissionScope.USER},
    {'name': 'profile.delete', 'display_name': 'Delete Profile', 'scope': PermissionScope.USER}
]