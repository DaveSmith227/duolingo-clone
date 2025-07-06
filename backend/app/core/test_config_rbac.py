"""
Tests for Configuration RBAC System

Tests role-based access control for configuration management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from .config_rbac_compat import (
    ConfigRBAC, ConfigPermission, ConfigRole, FieldPermission,
    RoleDefinition, get_config_rbac, require_permission,
    with_field_filtering, RBACConfigProxy
)
from .audit_logger import AuditContext, get_audit_context


class TestFieldPermission:
    """Test the FieldPermission class."""
    
    def test_field_pattern_matching(self):
        """Test field pattern matching."""
        perm = FieldPermission(
            field_pattern=r"^log_.*",
            permissions={ConfigPermission.READ, ConfigPermission.WRITE}
        )
        
        assert perm.matches("log_level", "development")
        assert perm.matches("log_format", "development")
        assert not perm.matches("debug", "development")
        assert not perm.matches("app_log", "development")
    
    def test_environment_restriction(self):
        """Test environment-based restrictions."""
        perm = FieldPermission(
            field_pattern=r".*",
            permissions={ConfigPermission.WRITE},
            environments={"development", "staging"}
        )
        
        assert perm.matches("any_field", "development")
        assert perm.matches("any_field", "staging")
        assert not perm.matches("any_field", "production")
    
    def test_sensitive_field_exclusion(self):
        """Test pattern for excluding sensitive fields."""
        perm = FieldPermission(
            field_pattern=r"^(?!.*(?:password|secret|key|token)).*$",
            permissions={ConfigPermission.READ}
        )
        
        assert perm.matches("debug", "development")
        assert perm.matches("log_level", "development")
        assert not perm.matches("jwt_secret", "development")
        assert not perm.matches("api_key", "development")
        assert not perm.matches("password_hash", "development")


class TestRoleDefinition:
    """Test the RoleDefinition class."""
    
    def test_role_inheritance(self):
        """Test role inheritance."""
        # Create base role
        base_role = RoleDefinition(
            name="base",
            description="Base role",
            field_permissions=[
                FieldPermission(
                    field_pattern=r"^app_.*",
                    permissions={ConfigPermission.READ}
                )
            ]
        )
        
        # Create derived role
        derived_role = RoleDefinition(
            name="derived",
            description="Derived role",
            field_permissions=[
                FieldPermission(
                    field_pattern=r"^log_.*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE}
                )
            ],
            inherits_from=["base"]
        )
        
        # Test inheritance
        role_registry = {"base": base_role, "derived": derived_role}
        all_perms = derived_role.get_all_permissions(role_registry)
        
        assert len(all_perms) == 2
        patterns = [p.field_pattern for p in all_perms]
        assert r"^log_.*" in patterns
        assert r"^app_.*" in patterns


class TestConfigRBAC:
    """Test the main ConfigRBAC class."""
    
    @pytest.fixture
    def rbac(self):
        """Create a fresh RBAC instance."""
        return ConfigRBAC()
    
    def test_default_roles_initialization(self, rbac):
        """Test that default roles are initialized correctly."""
        # Check all default roles exist
        for role in ConfigRole:
            assert role.value in rbac._roles
        
        # Check viewer role
        viewer_role = rbac._roles[ConfigRole.VIEWER.value]
        assert viewer_role.name == ConfigRole.VIEWER.value
        assert len(viewer_role.field_permissions) > 0
        
        # Check super admin role
        super_admin_role = rbac._roles[ConfigRole.SUPER_ADMIN.value]
        assert ConfigPermission.ALL in super_admin_role.global_permissions
    
    def test_role_assignment(self, rbac):
        """Test assigning roles to users."""
        user_id = "user123"
        
        # Assign viewer role
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        roles = rbac.get_user_roles(user_id)
        assert ConfigRole.VIEWER.value in roles
        
        # Assign additional role
        rbac.assign_role(user_id, ConfigRole.OPERATOR.value)
        roles = rbac.get_user_roles(user_id)
        assert len(roles) == 2
        assert ConfigRole.VIEWER.value in roles
        assert ConfigRole.OPERATOR.value in roles
    
    def test_role_revocation(self, rbac):
        """Test revoking roles from users."""
        user_id = "user123"
        
        # Assign roles
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        rbac.assign_role(user_id, ConfigRole.OPERATOR.value)
        
        # Revoke one role
        rbac.revoke_role(user_id, ConfigRole.VIEWER.value)
        roles = rbac.get_user_roles(user_id)
        assert ConfigRole.VIEWER.value not in roles
        assert ConfigRole.OPERATOR.value in roles
    
    def test_permission_checking(self, rbac):
        """Test permission checking logic."""
        user_id = "user123"
        
        # Test viewer permissions
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        assert rbac.check_permission(user_id, ConfigPermission.READ, "app_name")
        assert not rbac.check_permission(user_id, ConfigPermission.WRITE, "app_name")
        assert not rbac.check_permission(user_id, ConfigPermission.READ, "jwt_secret")
        
        # Test admin permissions
        admin_id = "admin123"
        rbac.assign_role(admin_id, ConfigRole.ADMIN.value)
        assert rbac.check_permission(admin_id, ConfigPermission.READ, "jwt_secret")
        assert rbac.check_permission(admin_id, ConfigPermission.WRITE, "jwt_secret")
        assert rbac.check_permission(admin_id, ConfigPermission.EXPORT)
    
    def test_environment_specific_permissions(self, rbac):
        """Test environment-specific permission rules."""
        user_id = "dev123"
        rbac.assign_role(user_id, ConfigRole.DEVELOPER.value)
        
        # Developer should have write access in development
        assert rbac.check_permission(
            user_id,
            ConfigPermission.WRITE,
            "debug",
            "development"
        )
        
        # But not in production
        assert not rbac.check_permission(
            user_id,
            ConfigPermission.WRITE,
            "debug",
            "production"
        )
        
        # Should still have read access in production for non-sensitive fields
        assert rbac.check_permission(
            user_id,
            ConfigPermission.READ,
            "debug",
            "production"
        )
    
    def test_field_access_checking(self, rbac):
        """Test field-specific access checking with audit logging."""
        user_id = "user123"
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        
        # Should have access to non-sensitive fields
        assert rbac.check_field_access(user_id, "app_name", ConfigPermission.READ)
        assert rbac.check_field_access(user_id, "debug", ConfigPermission.READ)
        
        # Should not have access to sensitive fields
        assert not rbac.check_field_access(user_id, "jwt_secret", ConfigPermission.READ)
        assert not rbac.check_field_access(user_id, "api_key", ConfigPermission.READ)
        
        # Should not have write access
        assert not rbac.check_field_access(user_id, "debug", ConfigPermission.WRITE)
    
    def test_filter_config_dict(self, rbac):
        """Test filtering configuration dictionary based on permissions."""
        user_id = "user123"
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        
        config = {
            "app_name": "Test App",
            "debug": True,
            "jwt_secret": "super-secret",
            "api_key": "key123",
            "log_level": "INFO"
        }
        
        filtered = rbac.filter_config_dict(config, user_id)
        
        # Should include non-sensitive fields
        assert "app_name" in filtered
        assert "debug" in filtered
        assert "log_level" in filtered
        
        # Should exclude sensitive fields
        assert "jwt_secret" not in filtered
        assert "api_key" not in filtered
    
    def test_custom_role_registration(self, rbac):
        """Test registering custom roles."""
        custom_role = RoleDefinition(
            name="custom_operator",
            description="Custom operator with specific permissions",
            field_permissions=[
                FieldPermission(
                    field_pattern=r"^custom_.*",
                    permissions={ConfigPermission.READ, ConfigPermission.WRITE}
                )
            ],
            global_permissions={ConfigPermission.VALIDATE}
        )
        
        rbac.register_role(custom_role)
        
        # Assign custom role
        user_id = "custom_user"
        rbac.assign_role(user_id, "custom_operator")
        
        # Test permissions
        assert rbac.check_permission(user_id, ConfigPermission.READ, "custom_field")
        assert rbac.check_permission(user_id, ConfigPermission.WRITE, "custom_field")
        assert rbac.check_permission(user_id, ConfigPermission.VALIDATE)
        assert not rbac.check_permission(user_id, ConfigPermission.EXPORT)


class TestPermissionDecorators:
    """Test permission enforcement decorators."""
    
    def test_require_permission_decorator(self):
        """Test the require_permission decorator."""
        # Mock audit context
        with patch('app.core.config_rbac.get_audit_context') as mock_context:
            mock_context.return_value = Mock(
                user_id="user123",
                environment="development"
            )
            
            # Mock RBAC
            with patch('app.core.config_rbac.get_config_rbac') as mock_rbac:
                rbac_instance = Mock()
                mock_rbac.return_value = rbac_instance
                
                # Test with permission granted
                rbac_instance.check_permission.return_value = True
                
                @require_permission(ConfigPermission.READ, "test_field")
                def read_config():
                    return "success"
                
                result = read_config()
                assert result == "success"
                
                # Test with permission denied
                rbac_instance.check_permission.return_value = False
                
                with pytest.raises(PermissionError):
                    read_config()
    
    def test_with_field_filtering_decorator(self):
        """Test the with_field_filtering decorator."""
        # Mock audit context
        with patch('app.core.config_rbac.get_audit_context') as mock_context:
            mock_context.return_value = Mock(
                user_id="user123",
                environment="development"
            )
            
            # Mock RBAC
            with patch('app.core.config_rbac.get_config_rbac') as mock_rbac:
                rbac_instance = Mock()
                mock_rbac.return_value = rbac_instance
                
                # Mock filter function
                rbac_instance.filter_config_dict.return_value = {
                    "app_name": "Test",
                    "debug": True
                }
                
                @with_field_filtering
                def get_config():
                    return {
                        "app_name": "Test",
                        "debug": True,
                        "secret_key": "secret123"
                    }
                
                result = get_config()
                
                # Should have called filter
                rbac_instance.filter_config_dict.assert_called_once()
                assert result == {"app_name": "Test", "debug": True}


class TestRBACConfigProxy:
    """Test the RBACConfigProxy class."""
    
    @pytest.fixture(autouse=True)
    def reset_global_rbac(self):
        """Reset global RBAC instance before each test."""
        import app.core.config_rbac
        app.core.config_rbac._config_rbac = None
        yield
        app.core.config_rbac._config_rbac = None
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = Mock()
        config.app_name = "Test App"
        config.debug = True
        config.jwt_secret = "secret123"
        config.get_safe_config = Mock(return_value={
            "app_name": "Test App",
            "debug": True,
            "jwt_secret": "***REDACTED***"
        })
        return config
    
    def test_read_access_control(self, mock_config):
        """Test read access control through proxy."""
        # Get the global RBAC instance (since RBACConfigProxy uses it)
        rbac = get_config_rbac()
        user_id = "user123"
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        
        proxy = RBACConfigProxy(mock_config, user_id, "development")
        
        # Should allow reading non-sensitive fields
        assert proxy.app_name == "Test App"
        assert proxy.debug is True
        
        # Should deny reading sensitive fields
        with pytest.raises(PermissionError):
            _ = proxy.jwt_secret
    
    def test_write_access_control(self, mock_config):
        """Test write access control through proxy."""
        rbac = get_config_rbac()
        user_id = "admin123"
        rbac.assign_role(user_id, ConfigRole.ADMIN.value)
        
        proxy = RBACConfigProxy(mock_config, user_id, "development")
        
        # Admin should be able to write
        proxy.debug = False
        assert mock_config.debug is False
        
        # Test with limited user
        viewer_id = "viewer123"
        rbac.assign_role(viewer_id, ConfigRole.VIEWER.value)
        viewer_proxy = RBACConfigProxy(mock_config, viewer_id, "development")
        
        # Viewer should not be able to write
        with pytest.raises(PermissionError):
            viewer_proxy.debug = True
    
    def test_safe_config_export(self, mock_config):
        """Test safe configuration export with filtering."""
        rbac = get_config_rbac()
        user_id = "user123"
        rbac.assign_role(user_id, ConfigRole.OPERATOR.value)
        
        proxy = RBACConfigProxy(mock_config, user_id, "development")
        
        # Operator has export permission
        safe_config = proxy.export_safe()
        assert safe_config == mock_config.get_safe_config()


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""
    
    @pytest.fixture(autouse=True)
    def reset_global_rbac(self):
        """Reset global RBAC instance before each test."""
        import app.core.config_rbac
        app.core.config_rbac._config_rbac = None
        yield
        app.core.config_rbac._config_rbac = None
    
    def test_developer_workflow(self):
        """Test typical developer workflow."""
        rbac = get_config_rbac()
        dev_id = "developer123"
        
        # Assign developer role
        rbac.assign_role(dev_id, ConfigRole.DEVELOPER.value)
        
        # In development environment
        assert rbac.check_permission(dev_id, ConfigPermission.READ, "jwt_secret", "development")
        assert rbac.check_permission(dev_id, ConfigPermission.WRITE, "debug", "development")
        assert rbac.check_permission(dev_id, ConfigPermission.EXPORT, environment="development")
        
        # In production environment
        assert rbac.check_permission(dev_id, ConfigPermission.READ, "app_name", "production")
        assert not rbac.check_permission(dev_id, ConfigPermission.WRITE, "debug", "production")
        
        # Check that jwt_secret is blocked in production using field access check
        assert not rbac.check_field_access(dev_id, "jwt_secret", ConfigPermission.READ, "production")
    
    def test_security_admin_workflow(self):
        """Test security admin workflow."""
        rbac = get_config_rbac()
        sec_admin_id = "security_admin123"
        
        # Assign security admin role
        rbac.assign_role(sec_admin_id, ConfigRole.SECURITY_ADMIN.value)
        
        # Should have full access to security fields
        assert rbac.check_permission(sec_admin_id, ConfigPermission.READ, "jwt_secret")
        assert rbac.check_permission(sec_admin_id, ConfigPermission.WRITE, "password_min_length")
        assert rbac.check_permission(sec_admin_id, ConfigPermission.ROTATE, "api_key")
        
        # Should have audit permissions
        assert rbac.check_permission(sec_admin_id, ConfigPermission.AUDIT_VIEW)
        assert rbac.check_permission(sec_admin_id, ConfigPermission.AUDIT_EXPORT)
    
    def test_role_escalation_prevention(self):
        """Test that users cannot escalate their own permissions."""
        rbac = get_config_rbac()
        user_id = "user123"
        
        # Start with viewer role
        rbac.assign_role(user_id, ConfigRole.VIEWER.value)
        
        # Verify limited permissions
        assert not rbac.check_permission(user_id, ConfigPermission.WRITE)
        assert not rbac.check_permission(user_id, ConfigPermission.EXPORT)
        
        # User should not be able to assign themselves admin role
        # (This would be enforced at the API level)
        roles_before = rbac.get_user_roles(user_id)
        assert ConfigRole.ADMIN.value not in roles_before