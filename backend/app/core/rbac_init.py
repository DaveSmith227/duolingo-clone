"""
RBAC Initialization

Initialize default roles and permissions for the application.
This module sets up the basic role-based access control structure.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.rbac import (
    Role, Permission, RoleType, PermissionScope,
    DEFAULT_ROLES, DEFAULT_PERMISSIONS, role_permissions
)
from app.core.database import get_db

logger = logging.getLogger(__name__)


class RBACInitializer:
    """
    RBAC system initializer.
    
    Sets up default roles, permissions, and their associations
    for the Duolingo clone application.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_rbac_system(self) -> None:
        """
        Initialize the complete RBAC system with default roles and permissions.
        """
        try:
            logger.info("Initializing RBAC system...")
            
            # Create default permissions
            permissions = self._create_default_permissions()
            logger.info(f"Created {len(permissions)} permissions")
            
            # Create default roles
            roles = self._create_default_roles()
            logger.info(f"Created {len(roles)} roles")
            
            # Assign permissions to roles
            self._assign_default_role_permissions(roles, permissions)
            logger.info("Assigned permissions to roles")
            
            self.db.commit()
            logger.info("RBAC system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RBAC system: {str(e)}")
            self.db.rollback()
            raise
    
    def _create_default_permissions(self) -> Dict[str, Permission]:
        """
        Create default permissions.
        
        Returns:
            Dictionary mapping permission names to Permission instances
        """
        permissions = {}
        
        for perm_data in DEFAULT_PERMISSIONS:
            # Check if permission already exists
            existing = self.db.query(Permission).filter(
                Permission.name == perm_data['name']
            ).first()
            
            if existing:
                permissions[perm_data['name']] = existing
                continue
            
            # Create new permission
            permission = Permission(
                name=perm_data['name'],
                display_name=perm_data['display_name'],
                description=perm_data.get('description'),
                scope=perm_data['scope'],
                resource_type=perm_data.get('resource_type'),
                metadata=perm_data.get('metadata')
            )
            
            self.db.add(permission)
            permissions[perm_data['name']] = permission
            
            logger.debug(f"Created permission: {perm_data['name']}")
        
        self.db.flush()  # Ensure IDs are available
        return permissions
    
    def _create_default_roles(self) -> Dict[str, Role]:
        """
        Create default roles.
        
        Returns:
            Dictionary mapping role names to Role instances
        """
        roles = {}
        
        for role_data in DEFAULT_ROLES:
            # Check if role already exists
            existing = self.db.query(Role).filter(
                Role.name == role_data['name']
            ).first()
            
            if existing:
                roles[role_data['name']] = existing
                continue
            
            # Create new role
            role = Role(
                name=role_data['name'],
                display_name=role_data['display_name'],
                description=role_data['description'],
                role_type=role_data['role_type'],
                priority=role_data['priority'],
                metadata=role_data.get('metadata')
            )
            
            self.db.add(role)
            roles[role_data['name']] = role
            
            logger.debug(f"Created role: {role_data['name']}")
        
        self.db.flush()  # Ensure IDs are available
        return roles
    
    def _assign_default_role_permissions(self, roles: Dict[str, Role], 
                                       permissions: Dict[str, Permission]) -> None:
        """
        Assign default permissions to roles.
        
        Args:
            roles: Dictionary of role name to Role instance
            permissions: Dictionary of permission name to Permission instance
        """
        # Define role-permission mappings
        role_permission_mappings = {
            'admin': [
                'admin.all',
                'admin.users.manage',
                'admin.roles.manage',
                'admin.system.config',
                'content.courses.create',
                'content.courses.edit',
                'content.courses.delete',
                'content.lessons.create',
                'content.lessons.edit',
                'content.lessons.delete',
                'users.view',
                'users.edit',
                'users.delete',
                'users.suspend',
                'learning.courses.access',
                'learning.lessons.complete',
                'learning.progress.view',
                'profile.view',
                'profile.edit',
                'profile.delete'
            ],
            'moderator': [
                'users.view',
                'users.edit',
                'users.suspend',
                'content.courses.edit',
                'content.lessons.edit',
                'learning.courses.access',
                'learning.lessons.complete',
                'learning.progress.view',
                'profile.view',
                'profile.edit'
            ],
            'instructor': [
                'content.courses.create',
                'content.courses.edit',
                'content.lessons.create',
                'content.lessons.edit',
                'users.view',
                'learning.courses.access',
                'learning.lessons.complete',
                'learning.progress.view',
                'profile.view',
                'profile.edit'
            ],
            'user': [
                'learning.courses.access',
                'learning.lessons.complete',
                'learning.progress.view',
                'profile.view',
                'profile.edit'
            ],
            'guest': [
                'learning.courses.access',
                'profile.view'
            ]
        }
        
        # Assign permissions to roles
        for role_name, permission_names in role_permission_mappings.items():
            if role_name not in roles:
                logger.warning(f"Role {role_name} not found, skipping permission assignment")
                continue
            
            role = roles[role_name]
            
            for perm_name in permission_names:
                if perm_name not in permissions:
                    logger.warning(f"Permission {perm_name} not found, skipping assignment to {role_name}")
                    continue
                
                permission = permissions[perm_name]
                
                # Check if permission already assigned
                if permission not in role.permissions:
                    role.permissions.append(permission)
                    logger.debug(f"Assigned permission {perm_name} to role {role_name}")
    
    def add_custom_role(self, name: str, display_name: str, description: str = None,
                       permission_names: List[str] = None, priority: int = 100) -> Role:
        """
        Add a custom role with specified permissions.
        
        Args:
            name: Role name
            display_name: Human-readable role name
            description: Role description
            permission_names: List of permission names to assign
            priority: Role priority
            
        Returns:
            Created Role instance
        """
        try:
            # Check if role already exists
            existing = self.db.query(Role).filter(Role.name == name).first()
            if existing:
                logger.warning(f"Role {name} already exists")
                return existing
            
            # Create role
            role = Role(
                name=name,
                display_name=display_name,
                description=description,
                role_type=RoleType.CUSTOM,
                priority=priority
            )
            
            self.db.add(role)
            self.db.flush()
            
            # Assign permissions
            if permission_names:
                for perm_name in permission_names:
                    permission = self.db.query(Permission).filter(
                        Permission.name == perm_name
                    ).first()
                    if permission:
                        role.permissions.append(permission)
                    else:
                        logger.warning(f"Permission {perm_name} not found")
            
            self.db.commit()
            logger.info(f"Created custom role: {name}")
            return role
            
        except Exception as e:
            logger.error(f"Failed to create custom role {name}: {str(e)}")
            self.db.rollback()
            raise
    
    def add_custom_permission(self, name: str, display_name: str, description: str = None,
                            scope: PermissionScope = PermissionScope.GLOBAL,
                            resource_type: str = None) -> Permission:
        """
        Add a custom permission.
        
        Args:
            name: Permission name
            display_name: Human-readable permission name
            description: Permission description
            scope: Permission scope
            resource_type: Resource type for scoped permissions
            
        Returns:
            Created Permission instance
        """
        try:
            # Check if permission already exists
            existing = self.db.query(Permission).filter(Permission.name == name).first()
            if existing:
                logger.warning(f"Permission {name} already exists")
                return existing
            
            # Create permission
            permission = Permission(
                name=name,
                display_name=display_name,
                description=description,
                scope=scope,
                resource_type=resource_type
            )
            
            self.db.add(permission)
            self.db.commit()
            
            logger.info(f"Created custom permission: {name}")
            return permission
            
        except Exception as e:
            logger.error(f"Failed to create custom permission {name}: {str(e)}")
            self.db.rollback()
            raise
    
    def verify_rbac_setup(self) -> bool:
        """
        Verify that RBAC system is properly set up.
        
        Returns:
            True if RBAC system is properly configured, False otherwise
        """
        try:
            # Check if all default roles exist
            for role_data in DEFAULT_ROLES:
                role = self.db.query(Role).filter(Role.name == role_data['name']).first()
                if not role:
                    logger.error(f"Default role {role_data['name']} not found")
                    return False
            
            # Check if all default permissions exist
            for perm_data in DEFAULT_PERMISSIONS:
                permission = self.db.query(Permission).filter(
                    Permission.name == perm_data['name']
                ).first()
                if not permission:
                    logger.error(f"Default permission {perm_data['name']} not found")
                    return False
            
            # Check if admin role has admin permissions
            admin_role = self.db.query(Role).filter(Role.name == 'admin').first()
            if not admin_role or not admin_role.has_permission('admin.all'):
                logger.error("Admin role does not have admin.all permission")
                return False
            
            logger.info("RBAC system verification successful")
            return True
            
        except Exception as e:
            logger.error(f"RBAC system verification failed: {str(e)}")
            return False


def initialize_rbac(db: Session = None) -> bool:
    """
    Initialize RBAC system with default roles and permissions.
    
    Args:
        db: Database session (optional)
        
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        if db is None:
            db = next(get_db())
        
        initializer = RBACInitializer(db)
        initializer.initialize_rbac_system()
        
        # Verify setup
        return initializer.verify_rbac_setup()
        
    except Exception as e:
        logger.error(f"RBAC initialization failed: {str(e)}")
        return False


def get_rbac_initializer(db: Session) -> RBACInitializer:
    """
    Get RBACInitializer instance.
    
    Args:
        db: Database session
        
    Returns:
        RBACInitializer instance
    """
    return RBACInitializer(db)