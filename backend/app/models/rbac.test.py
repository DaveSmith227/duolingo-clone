"""
Tests for Role-Based Access Control Models

Unit tests for RBAC models including roles, permissions,
and user role assignments.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from app.models.rbac import (
    Role, Permission, UserRoleAssignment, RoleType, PermissionScope
)
from app.models.user import User


class TestRole:
    """Test cases for Role model."""
    
    def test_create_role(self, db_session):
        """Test creating a role."""
        role = Role(
            name='test_role',
            display_name='Test Role',
            description='A test role',
            role_type=RoleType.CUSTOM,
            priority=100
        )
        
        db_session.add(role)
        db_session.commit()
        
        assert role.id is not None
        assert role.name == 'test_role'
        assert role.display_name == 'Test Role'
        assert role.role_type == RoleType.CUSTOM
        assert role.is_active is True
        assert role.priority == 100
    
    def test_role_unique_constraint(self, db_session):
        """Test unique constraint on role name."""
        # Create first role
        role1 = Role(
            name='duplicate_role',
            display_name='Role 1',
            role_type=RoleType.CUSTOM
        )
        db_session.add(role1)
        db_session.commit()
        
        # Create second role with same name
        role2 = Role(
            name='duplicate_role',
            display_name='Role 2',
            role_type=RoleType.CUSTOM
        )
        db_session.add(role2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_validate_role_name(self, db_session):
        """Test role name validation."""
        role = Role(
            display_name='Test Role',
            role_type=RoleType.CUSTOM
        )
        
        # Valid names
        valid_names = ['admin', 'user_role', 'test-role', 'role123']
        for name in valid_names:
            role.name = name
            assert role.name == name.lower()
        
        # Invalid names
        with pytest.raises(ValueError, match="Role name is required"):
            role.name = ''
        
        with pytest.raises(ValueError, match="Role name can only contain"):
            role.name = 'Invalid Role!'
    
    def test_validate_reserved_names(self, db_session):
        """Test validation of reserved role names."""
        # System role with reserved name should work
        system_role = Role(
            name='admin',
            display_name='Administrator',
            role_type=RoleType.SYSTEM
        )
        assert system_role.name == 'admin'
        
        # Custom role with reserved name should fail
        custom_role = Role(
            display_name='Custom Admin',
            role_type=RoleType.CUSTOM
        )
        
        with pytest.raises(ValueError, match="Role name 'admin' is reserved"):
            custom_role.name = 'admin'
    
    def test_validate_priority(self, db_session):
        """Test role priority validation."""
        role = Role(
            name='test_role',
            display_name='Test Role',
            role_type=RoleType.CUSTOM
        )
        
        # Valid priorities
        role.priority = 0
        assert role.priority == 0
        
        role.priority = 500
        assert role.priority == 500
        
        role.priority = 1000
        assert role.priority == 1000
        
        # Invalid priorities
        with pytest.raises(ValueError, match="Role priority must be between 0 and 1000"):
            role.priority = -1
        
        with pytest.raises(ValueError, match="Role priority must be between 0 and 1000"):
            role.priority = 1001
    
    def test_has_permission(self, db_session, sample_permission):
        """Test role permission checking."""
        role = Role(
            name='test_role',
            display_name='Test Role',
            role_type=RoleType.CUSTOM
        )
        
        # Add permission to role
        role.permissions.append(sample_permission)
        
        # Test permission check
        assert role.has_permission(sample_permission.name) is True
        assert role.has_permission('non_existent_permission') is False
    
    def test_get_jwt_claims(self, db_session, sample_permission):
        """Test JWT claims generation."""
        role = Role(
            name='test_role',
            display_name='Test Role',
            description='A test role',
            role_type=RoleType.CUSTOM,
            priority=100,
            metadata={'custom_field': 'custom_value'}
        )
        
        role.permissions.append(sample_permission)
        
        claims = role.get_jwt_claims()
        
        assert claims['role'] == 'test_role'
        assert claims['role_display_name'] == 'Test Role'
        assert claims['role_type'] == 'custom'
        assert claims['role_priority'] == 100
        assert sample_permission.name in claims['permissions']
        assert claims['role_metadata']['custom_field'] == 'custom_value'


class TestPermission:
    """Test cases for Permission model."""
    
    def test_create_permission(self, db_session):
        """Test creating a permission."""
        permission = Permission(
            name='test.permission',
            display_name='Test Permission',
            description='A test permission',
            scope=PermissionScope.GLOBAL,
            resource_type='test'
        )
        
        db_session.add(permission)
        db_session.commit()
        
        assert permission.id is not None
        assert permission.name == 'test.permission'
        assert permission.display_name == 'Test Permission'
        assert permission.scope == PermissionScope.GLOBAL
        assert permission.is_active is True
    
    def test_permission_unique_constraint(self, db_session):
        """Test unique constraint on permission name."""
        # Create first permission
        perm1 = Permission(
            name='duplicate.permission',
            display_name='Permission 1',
            scope=PermissionScope.GLOBAL
        )
        db_session.add(perm1)
        db_session.commit()
        
        # Create second permission with same name
        perm2 = Permission(
            name='duplicate.permission',
            display_name='Permission 2',
            scope=PermissionScope.GLOBAL
        )
        db_session.add(perm2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_validate_permission_name(self, db_session):
        """Test permission name validation."""
        permission = Permission(
            display_name='Test Permission',
            scope=PermissionScope.GLOBAL
        )
        
        # Valid names
        valid_names = ['admin.all', 'users:view', 'content.create', 'test_permission']
        for name in valid_names:
            permission.name = name
            assert permission.name == name.lower()
        
        # Invalid names
        with pytest.raises(ValueError, match="Permission name is required"):
            permission.name = ''
        
        with pytest.raises(ValueError, match="Permission name can only contain"):
            permission.name = 'Invalid Permission!'


class TestUserRoleAssignment:
    """Test cases for UserRoleAssignment model."""
    
    def test_create_assignment(self, db_session, sample_user, sample_role):
        """Test creating a user role assignment."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        
        assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            assigned_by=sample_user.id,
            expires_at=expires_at,
            context={'reason': 'test_assignment'}
        )
        
        db_session.add(assignment)
        db_session.commit()
        
        assert assignment.id is not None
        assert assignment.user_id == sample_user.id
        assert assignment.role_id == sample_role.id
        assert assignment.is_active is True
        assert assignment.assigned_at is not None
        assert assignment.context['reason'] == 'test_assignment'
    
    def test_is_expired_property(self, db_session, sample_user, sample_role):
        """Test assignment expiration check."""
        # Expired assignment
        expired_assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        # Valid assignment
        valid_assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        # Never-expiring assignment
        never_expires = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            expires_at=None
        )
        
        assert expired_assignment.is_expired is True
        assert valid_assignment.is_expired is False
        assert never_expires.is_expired is False
    
    def test_is_valid_property(self, db_session, sample_user, sample_role):
        """Test assignment validity check."""
        # Valid assignment
        valid_assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        # Inactive assignment
        inactive_assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            is_active=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        # Expired assignment
        expired_assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        assert valid_assignment.is_valid is True
        assert inactive_assignment.is_valid is False
        assert expired_assignment.is_valid is False
    
    def test_extend_expiration(self, db_session, sample_user, sample_role):
        """Test extending assignment expiration."""
        original_expires = datetime.now(timezone.utc) + timedelta(days=30)
        assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            expires_at=original_expires
        )
        
        assignment.extend_expiration(10)  # Extend by 10 days
        
        expected_expires = original_expires + timedelta(days=10)
        assert assignment.expires_at.date() == expected_expires.date()
    
    def test_extend_expiration_never_expires(self, db_session, sample_user, sample_role):
        """Test extending expiration on never-expiring assignment."""
        assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            expires_at=None
        )
        
        assignment.extend_expiration(30)
        
        assert assignment.expires_at is not None
        expected_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
        assert assignment.expires_at.date() == expected_date
    
    def test_revoke_assignment(self, db_session, sample_user, sample_role):
        """Test revoking a role assignment."""
        assignment = UserRoleAssignment(
            user_id=sample_user.id,
            role_id=sample_role.id,
            is_active=True
        )
        
        revoked_by = 'admin_user_id'
        assignment.revoke(revoked_by)
        
        assert assignment.is_active is False
        assert assignment.context['revoked_by'] == revoked_by
        assert 'revoked_at' in assignment.context


class TestRolePermissionRelationships:
    """Test cases for role-permission relationships."""
    
    def test_role_permission_association(self, db_session, sample_role, sample_permission):
        """Test many-to-many relationship between roles and permissions."""
        # Associate permission with role
        sample_role.permissions.append(sample_permission)
        
        db_session.add(sample_role)
        db_session.commit()
        
        # Test relationship from role side
        assert sample_permission in sample_role.permissions
        
        # Test relationship from permission side
        assert sample_role in sample_permission.roles
    
    def test_multiple_permissions_per_role(self, db_session, sample_role):
        """Test role with multiple permissions."""
        permissions = []
        for i in range(3):
            perm = Permission(
                name=f'test.permission.{i}',
                display_name=f'Test Permission {i}',
                scope=PermissionScope.GLOBAL
            )
            permissions.append(perm)
            sample_role.permissions.append(perm)
        
        db_session.add(sample_role)
        db_session.commit()
        
        assert len(sample_role.permissions) == 3
        for perm in permissions:
            assert perm in sample_role.permissions
    
    def test_permission_across_multiple_roles(self, db_session, sample_permission):
        """Test permission assigned to multiple roles."""
        roles = []
        for i in range(3):
            role = Role(
                name=f'test_role_{i}',
                display_name=f'Test Role {i}',
                role_type=RoleType.CUSTOM
            )
            role.permissions.append(sample_permission)
            roles.append(role)
            db_session.add(role)
        
        db_session.commit()
        
        assert len(sample_permission.roles) == 3
        for role in roles:
            assert role in sample_permission.roles


class TestDefaultRolesAndPermissions:
    """Test cases for default roles and permissions."""
    
    def test_default_roles_structure(self):
        """Test that default roles have required structure."""
        from app.models.rbac import DEFAULT_ROLES
        
        required_fields = ['name', 'display_name', 'description', 'role_type', 'priority']
        
        for role_data in DEFAULT_ROLES:
            for field in required_fields:
                assert field in role_data, f"Default role missing field: {field}"
            
            # Validate role types
            assert role_data['role_type'] == RoleType.SYSTEM
            
            # Validate priority range
            assert 0 <= role_data['priority'] <= 1000
    
    def test_default_permissions_structure(self):
        """Test that default permissions have required structure."""
        from app.models.rbac import DEFAULT_PERMISSIONS
        
        required_fields = ['name', 'display_name', 'scope']
        
        for perm_data in DEFAULT_PERMISSIONS:
            for field in required_fields:
                assert field in perm_data, f"Default permission missing field: {field}"
            
            # Validate scopes
            assert isinstance(perm_data['scope'], PermissionScope)
            
            # Validate naming convention
            assert '.' in perm_data['name'] or ':' in perm_data['name'], \
                f"Permission name should follow namespacing convention: {perm_data['name']}"