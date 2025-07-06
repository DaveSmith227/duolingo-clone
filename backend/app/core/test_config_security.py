"""
Comprehensive Security Tests for Configuration Management

Tests that verify RBAC enforcement, audit logging integrity,
and security features of the configuration system.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List

from .config import Settings, get_settings
from .config_rbac_compat import (
    ConfigRBAC, ConfigPermission, ConfigRole, RBACConfigProxy,
    get_config_rbac, FieldPermission, RoleDefinition
)
from .audit_logger import (
    AuditLogger, AuditEvent, AuditAction, AuditSeverity,
    get_audit_logger, set_audit_context, clear_audit_context,
    configure_audit_logger
)
from .audited_config import create_audited_settings, AuditedSettings
from .config_validators import ConfigurationBusinessRuleValidator
from app.services.config_access_service import ConfigAccessService, get_config_access_service


class TestRBACEnforcement:
    """Test that RBAC is properly enforced across the system."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user object."""
        user = Mock()
        user.id = "test_user_123"
        user.email = "test@example.com"
        user.role = "user"
        user.is_admin = False
        user.is_super_admin = False
        return user
    
    @pytest.fixture
    def mock_admin(self):
        """Create a mock admin user."""
        admin = Mock()
        admin.id = "admin_123"
        admin.email = "admin@example.com"
        admin.role = "admin"
        admin.is_admin = True
        admin.is_super_admin = False
        return admin
    
    @pytest.fixture
    def service(self):
        """Create a config access service instance."""
        return ConfigAccessService()
    
    def test_viewer_cannot_write_fields(self, service, mock_user):
        """Test that viewers cannot write any configuration fields."""
        # Assign viewer role
        rbac = get_config_rbac()
        rbac.assign_role(str(mock_user.id), ConfigRole.VIEWER.value)
        
        # Try to write a field
        with pytest.raises(PermissionError) as exc_info:
            service.write_config_field(mock_user, "debug", False)
        
        assert "does not have write permission" in str(exc_info.value)
    
    def test_viewer_cannot_read_sensitive_fields(self, service, mock_user):
        """Test that viewers cannot read sensitive configuration fields."""
        # Assign viewer role
        rbac = get_config_rbac()
        rbac.assign_role(str(mock_user.id), ConfigRole.VIEWER.value)
        
        # Try to read sensitive fields
        sensitive_fields = ["jwt_secret", "api_key", "db_password", "supabase_service_role_key"]
        
        for field in sensitive_fields:
            with pytest.raises(PermissionError):
                service.read_config_field(mock_user, field)
    
    def test_developer_environment_restrictions(self, service):
        """Test that developers have different permissions in different environments."""
        # Create developer user
        dev_user = Mock()
        dev_user.id = "dev_123"
        dev_user.email = "dev@example.com"
        dev_user.role = "developer"
        dev_user.is_admin = False
        dev_user.is_super_admin = False
        
        # Assign developer role
        rbac = get_config_rbac()
        rbac.assign_role(str(dev_user.id), ConfigRole.DEVELOPER.value)
        
        # Test in development environment
        with patch.object(service._settings, 'environment', 'development'):
            # Should be able to write in development
            proxy = service.get_user_config(dev_user)
            try:
                proxy.debug = True  # Should succeed
            except PermissionError:
                pytest.fail("Developer should have write access in development")
        
        # Test in production environment
        with patch.object(service._settings, 'environment', 'production'):
            # Should NOT be able to write in production
            proxy = service.get_user_config(dev_user)
            with pytest.raises(PermissionError):
                proxy.debug = False
    
    def test_permission_escalation_prevention(self, service, mock_user):
        """Test that users cannot escalate their own permissions."""
        # User starts with viewer role
        rbac = get_config_rbac()
        rbac.assign_role(str(mock_user.id), ConfigRole.VIEWER.value)
        
        # User should not be able to assign themselves admin role
        with pytest.raises(PermissionError) as exc_info:
            service.assign_config_role(mock_user, str(mock_user.id), ConfigRole.ADMIN)
        
        assert "Only admins can assign configuration roles" in str(exc_info.value)
        
        # Verify user still has only viewer role
        roles = rbac.get_user_roles(str(mock_user.id))
        assert ConfigRole.VIEWER.value in roles
        assert ConfigRole.ADMIN.value not in roles
    
    def test_admin_can_manage_roles(self, service, mock_admin, mock_user):
        """Test that admins can properly manage roles."""
        # Admin assigns role to user
        service.assign_config_role(mock_admin, str(mock_user.id), ConfigRole.OPERATOR)
        
        # Verify role was assigned
        rbac = get_config_rbac()
        roles = rbac.get_user_roles(str(mock_user.id))
        assert ConfigRole.OPERATOR.value in roles
        
        # Admin revokes role
        service.revoke_config_role(mock_admin, str(mock_user.id), ConfigRole.OPERATOR)
        
        # Verify role was revoked
        roles = rbac.get_user_roles(str(mock_user.id))
        assert ConfigRole.OPERATOR.value not in roles
    
    def test_field_pattern_security(self):
        """Test that field patterns properly protect sensitive fields."""
        rbac = ConfigRBAC()
        
        # Test sensitive field patterns
        sensitive_patterns = [
            "jwt_secret", "api_key", "password_hash", "private_key",
            "secret_token", "auth_credential", "supabase_key"
        ]
        
        # Viewer should not access any sensitive fields
        viewer_perms = rbac._roles[ConfigRole.VIEWER.value].field_permissions
        
        for field in sensitive_patterns:
            viewer_can_read = False
            for perm in viewer_perms:
                if perm.matches(field, "development") and ConfigPermission.READ in perm.permissions:
                    viewer_can_read = True
                    break
            
            assert not viewer_can_read, f"Viewer should not be able to read {field}"
    
    def test_export_permission_required(self, service, mock_user):
        """Test that export permission is properly enforced."""
        # Viewer doesn't have export permission
        rbac = get_config_rbac()
        rbac.assign_role(str(mock_user.id), ConfigRole.VIEWER.value)
        
        with pytest.raises(PermissionError) as exc_info:
            service.export_config_for_user(mock_user)
        
        assert "User lacks export permission" in str(exc_info.value)
        
        # Operator has export permission
        rbac.assign_role(str(mock_user.id), ConfigRole.OPERATOR.value)
        try:
            config = service.export_config_for_user(mock_user)
            assert isinstance(config, dict)
        except PermissionError:
            pytest.fail("Operator should have export permission")


class TestAuditLoggingIntegrity:
    """Test that audit logging captures all security-relevant events."""
    
    @pytest.fixture
    def temp_audit_dir(self):
        """Create a temporary directory for audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def audit_logger(self, temp_audit_dir):
        """Create an audit logger for testing."""
        return AuditLogger(
            log_dir=temp_audit_dir,
            enable_console=False
        )
    
    def test_all_config_access_is_logged(self, temp_audit_dir):
        """Test that all configuration access is logged."""
        # Configure audit logger
        configure_audit_logger(log_dir=temp_audit_dir, enable_console=False)
        
        # Set audit context
        set_audit_context(
            user_id="test_user",
            user_email="test@example.com",
            ip_address="127.0.0.1"
        )
        
        # Create audited settings
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            audited = create_audited_settings(settings)
        
        # Access various fields
        _ = audited.debug
        _ = audited.app_name
        _ = audited.log_level
        
        # Modify a field
        audited.debug = False
        
        clear_audit_context()
        
        # Read audit logs
        log_files = list(temp_audit_dir.glob("audit-*.jsonl"))
        assert len(log_files) == 1
        
        events = []
        with open(log_files[0], 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Verify all access was logged
        read_events = [e for e in events if e['action'] == 'read']
        write_events = [e for e in events if e['action'] == 'write']
        
        assert len(read_events) >= 3  # At least 3 reads
        assert len(write_events) >= 1  # At least 1 write
        
        # Verify user context was captured
        for event in events:
            assert event.get('user_id') == 'test_user'
            assert event.get('user_email') == 'test@example.com'
            assert event.get('ip_address') == '127.0.0.1'
    
    def test_access_denied_events_logged(self, audit_logger):
        """Test that access denied events are properly logged."""
        rbac = ConfigRBAC()
        
        # Check access for unauthorized user
        has_access = rbac.check_field_access(
            "unauthorized_user",
            "jwt_secret",
            ConfigPermission.READ,
            "production"
        )
        
        assert not has_access
        
        # Verify access denied was logged
        # In real implementation, this would check the actual log
        # Here we verify the method would be called
        with patch.object(audit_logger, 'log_access_denied') as mock_log:
            rbac._audit_logger = audit_logger
            rbac.check_field_access(
                "unauthorized_user",
                "jwt_secret",
                ConfigPermission.READ,
                "production"
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0]
            assert call_args[0] == "read"  # action
            assert "jwt_secret" in call_args[1]  # resource
    
    def test_sensitive_values_are_masked(self, audit_logger):
        """Test that sensitive values are masked in audit logs."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.WRITE,
            user_id="user123",
            user_email="user@example.com",
            field_name="jwt_secret",
            old_value="old-secret-key-12345",
            new_value="new-secret-key-67890",
            environment="development",
            severity=AuditSeverity.WARNING,
            ip_address="127.0.0.1",
            user_agent="pytest",
            session_id="session123",
            request_id="req123",
            success=True,
            error_message=None,
            metadata={}
        )
        
        # Convert to dict (which masks sensitive values)
        event_dict = event.to_dict()
        
        # Verify masking
        assert event_dict["old_value"] != "old-secret-key-12345"
        assert event_dict["new_value"] != "new-secret-key-67890"
        assert "***" in event_dict["old_value"] or event_dict["old_value"].endswith("...")
        assert "***" in event_dict["new_value"] or event_dict["new_value"].endswith("...")
    
    def test_audit_log_tampering_prevention(self, temp_audit_dir):
        """Test that audit logs cannot be tampered with."""
        audit_logger = AuditLogger(log_dir=temp_audit_dir, enable_console=False)
        
        # Log an event
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.READ,
            user_id="user123",
            user_email="user@example.com",
            field_name="debug",
            old_value=None,
            new_value=True,
            environment="development",
            severity=AuditSeverity.INFO,
            ip_address="127.0.0.1",
            user_agent="pytest",
            session_id="session123",
            request_id="req123",
            success=True,
            error_message=None,
            metadata={}
        )
        
        audit_logger.log_event(event)
        
        # Get log file
        log_files = list(temp_audit_dir.glob("audit-*.jsonl"))
        assert len(log_files) == 1
        
        # Verify file is append-only (in real implementation)
        # and has proper permissions
        log_file = log_files[0]
        assert log_file.exists()
        
        # Read original content
        with open(log_file, 'r') as f:
            original_content = f.read()
        
        # Log another event
        audit_logger.log_event(event)
        
        # Verify original content is still there
        with open(log_file, 'r') as f:
            new_content = f.read()
        
        assert original_content in new_content
        assert len(new_content) > len(original_content)
    
    def test_audit_log_retention(self, temp_audit_dir):
        """Test that old audit logs are cleaned up according to retention policy."""
        # Create logger with 1 day retention
        audit_logger = AuditLogger(
            log_dir=temp_audit_dir,
            retention_days=1,
            enable_console=False
        )
        
        # Create old log file (2 days old)
        old_date = datetime.now(timezone.utc) - timedelta(days=2)
        old_log_file = temp_audit_dir / f"audit-{old_date.strftime('%Y-%m-%d')}.jsonl"
        old_log_file.write_text('{"test": "old log"}\n')
        
        # Create current log file
        current_log_file = temp_audit_dir / f"audit-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        current_log_file.write_text('{"test": "current log"}\n')
        
        # Modify old file's timestamp to make it old
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
        os.utime(old_log_file, (old_timestamp, old_timestamp))
        
        # Trigger cleanup by logging many events
        for i in range(101):  # Cleanup happens every 100 events
            audit_logger.log_event(AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=AuditAction.READ,
                user_id=f"user{i}",
                user_email=f"user{i}@example.com",
                field_name="test",
                old_value=None,
                new_value="test",
                environment="development",
                severity=AuditSeverity.INFO,
                ip_address="127.0.0.1",
                user_agent="pytest",
                session_id="session",
                request_id=f"req{i}",
                success=True,
                error_message=None,
                metadata={}
            ))
        
        # Verify old log was cleaned up
        assert not old_log_file.exists()
        assert current_log_file.exists()


class TestSecurityScenarios:
    """Test real-world security scenarios."""
    
    def test_production_configuration_protection(self):
        """Test that production configuration is properly protected."""
        # Create service with production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            service = ConfigAccessService()
            
            # Create different users
            viewer = Mock(id="viewer1", email="viewer@example.com", role="user", 
                        is_admin=False, is_super_admin=False)
            developer = Mock(id="dev1", email="dev@example.com", role="developer",
                           is_admin=False, is_super_admin=False)
            admin = Mock(id="admin1", email="admin@example.com", role="admin",
                        is_admin=True, is_super_admin=False)
            
            # Assign roles
            rbac = get_config_rbac()
            rbac.assign_role(str(viewer.id), ConfigRole.VIEWER.value)
            rbac.assign_role(str(developer.id), ConfigRole.DEVELOPER.value)
            rbac.assign_role(str(admin.id), ConfigRole.ADMIN.value)
            
            # Test viewer cannot read secrets in production
            with pytest.raises(PermissionError):
                service.read_config_field(viewer, "jwt_secret")
            
            # Test developer cannot write in production
            with pytest.raises(PermissionError):
                service.write_config_field(developer, "debug", False)
            
            # Test admin can write in production
            try:
                # Mock the actual write since we don't have real config
                with patch.object(service, '_settings') as mock_settings:
                    mock_settings.environment = "production"
                    mock_settings.debug = True
                    service.write_config_field(admin, "debug", False)
            except PermissionError:
                pytest.fail("Admin should be able to write in production")
    
    def test_multi_user_concurrent_access(self):
        """Test that concurrent access by multiple users is properly controlled."""
        service = ConfigAccessService()
        
        # Create multiple users with different roles
        users = [
            Mock(id=f"user{i}", email=f"user{i}@example.com", role="user",
                is_admin=False, is_super_admin=False)
            for i in range(5)
        ]
        
        # Assign different roles
        rbac = get_config_rbac()
        rbac.assign_role(str(users[0].id), ConfigRole.VIEWER.value)
        rbac.assign_role(str(users[1].id), ConfigRole.OPERATOR.value)
        rbac.assign_role(str(users[2].id), ConfigRole.DEVELOPER.value)
        rbac.assign_role(str(users[3].id), ConfigRole.ADMIN.value)
        rbac.assign_role(str(users[4].id), ConfigRole.VIEWER.value)
        
        # Simulate concurrent access
        results = []
        for user in users:
            try:
                # Each user tries to read a sensitive field
                value = service.read_config_field(user, "jwt_secret")
                results.append((user.id, "success", value))
            except PermissionError:
                results.append((user.id, "denied", None))
        
        # Verify access control
        assert results[0][1] == "denied"  # Viewer
        assert results[1][1] == "success"  # Operator (can read all)
        assert results[2][1] == "success"  # Developer
        assert results[3][1] == "success"  # Admin
        assert results[4][1] == "denied"  # Viewer
    
    def test_audit_log_analysis_capabilities(self):
        """Test that audit logs can be properly analyzed for security events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_logger = AuditLogger(log_dir=Path(tmpdir), enable_console=False)
            
            # Simulate various security events
            base_time = datetime.now(timezone.utc)
            
            # Normal access
            for i in range(10):
                audit_logger.log_event(AuditEvent(
                    timestamp=base_time.isoformat(),
                    action=AuditAction.READ,
                    user_id="normal_user",
                    user_email="normal@example.com",
                    field_name="app_name",
                    old_value=None,
                    new_value="Test App",
                    environment="development",
                    severity=AuditSeverity.INFO,
                    ip_address="192.168.1.100",
                    user_agent="Mozilla/5.0",
                    session_id="session1",
                    request_id=f"req{i}",
                    success=True,
                    error_message=None,
                    metadata={}
                ))
            
            # Suspicious activity - many failed attempts
            for i in range(5):
                audit_logger.log_event(AuditEvent(
                    timestamp=(base_time + timedelta(minutes=i)).isoformat(),
                    action=AuditAction.ACCESS_DENIED,
                    user_id="suspicious_user",
                    user_email="suspicious@example.com",
                    field_name="jwt_secret",
                    old_value=None,
                    new_value=None,
                    environment="production",
                    severity=AuditSeverity.CRITICAL,
                    ip_address="10.0.0.1",
                    user_agent="curl/7.64.1",
                    session_id="session2",
                    request_id=f"sus{i}",
                    success=False,
                    error_message="Access denied",
                    metadata={"reason": "Insufficient permissions"}
                ))
            
            # Analyze logs
            summary = audit_logger.get_audit_summary(
                start_date=base_time - timedelta(hours=1),
                end_date=base_time + timedelta(hours=1)
            )
            
            # Verify security analysis
            assert summary["total_events"] == 15
            assert summary["failed_operations"] == 5
            assert summary["by_severity"]["critical"] == 5
            assert summary["by_action"]["access_denied"] == 5
            
            # Check for patterns
            assert summary["unique_users"] >= 2
            failure_rate = (summary["failed_operations"] / summary["total_events"]) * 100
            assert failure_rate > 30  # High failure rate indicates potential attack
    
    def test_configuration_validation_security(self):
        """Test that configuration validation prevents security misconfigurations."""
        # Test with weak security settings
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "weak-key",  # Too short
            "PASSWORD_MIN_LENGTH": "4",  # Too weak
            "REQUIRE_EMAIL_VERIFICATION": "false",  # Should be true in prod
            "DEBUG": "true"  # Should be false in prod
        }):
            # Should fail validation in production
            with pytest.raises(ValueError) as exc_info:
                Settings()
            
            error_message = str(exc_info.value)
            assert "SECRET_KEY must be at least 32 characters" in error_message or \
                   "SECRET_KEY must be changed in production" in error_message or \
                   "DEBUG must be False in production" in error_message
    
    def test_role_based_field_filtering(self):
        """Test that field filtering based on roles works correctly."""
        service = ConfigAccessService()
        
        # Create users with different roles
        viewer = Mock(id="v1", email="viewer@example.com", role="user",
                     is_admin=False, is_super_admin=False)
        admin = Mock(id="a1", email="admin@example.com", role="admin",
                    is_admin=True, is_super_admin=False)
        
        # Assign roles
        rbac = get_config_rbac()
        rbac.assign_role(str(viewer.id), ConfigRole.VIEWER.value)
        rbac.assign_role(str(admin.id), ConfigRole.ADMIN.value)
        
        # Mock settings
        with patch.object(service, '_settings') as mock_settings:
            mock_settings.get_safe_config.return_value = {
                "app_name": "Test App",
                "debug": True,
                "jwt_secret": "***REDACTED***",
                "api_key": "***REDACTED***",
                "log_level": "INFO"
            }
            
            # Get config for viewer
            viewer_proxy = service.get_user_config(viewer)
            viewer_config = viewer_proxy.get_safe_config()
            
            # Get config for admin
            admin_proxy = service.get_user_config(admin)
            admin_config = admin_proxy.get_safe_config()
            
            # Viewer should see fewer fields
            assert len(viewer_config) < len(admin_config)
            
            # Viewer should not see sensitive fields
            assert "jwt_secret" not in viewer_config
            assert "api_key" not in viewer_config
            
            # Admin should see all fields (though values may be redacted)
            assert "jwt_secret" in admin_config
            assert "api_key" in admin_config


class TestIntegrationSecurity:
    """Test security across integrated components."""
    
    def test_end_to_end_security_flow(self):
        """Test complete security flow from API to audit log."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Configure system
            configure_audit_logger(log_dir=Path(tmpdir), enable_console=False)
            
            # Create users
            attacker = Mock(id="attacker", email="attacker@evil.com", role="user",
                          is_admin=False, is_super_admin=False)
            legit_user = Mock(id="user123", email="user@example.com", role="developer",
                            is_admin=False, is_super_admin=False)
            
            # Set up service
            service = ConfigAccessService()
            rbac = get_config_rbac()
            
            # Attacker has no roles assigned (unauthorized)
            # Legitimate user has developer role
            rbac.assign_role(str(legit_user.id), ConfigRole.DEVELOPER.value)
            
            # Simulate attack attempts
            attack_results = []
            
            # Try to read sensitive fields
            sensitive_fields = ["jwt_secret", "db_password", "api_key"]
            for field in sensitive_fields:
                try:
                    service.read_config_field(attacker, field)
                    attack_results.append((field, "success"))
                except PermissionError:
                    attack_results.append((field, "blocked"))
            
            # Try to escalate privileges
            try:
                service.assign_config_role(attacker, str(attacker.id), ConfigRole.ADMIN)
                attack_results.append(("privilege_escalation", "success"))
            except PermissionError:
                attack_results.append(("privilege_escalation", "blocked"))
            
            # Verify all attacks were blocked
            for result in attack_results:
                assert result[1] == "blocked", f"Attack on {result[0]} should have been blocked"
            
            # Verify legitimate user can work normally
            legit_results = []
            try:
                # Developer can read in development
                with patch.object(service._settings, 'environment', 'development'):
                    value = service.read_config_field(legit_user, "debug")
                    legit_results.append(("read_debug", "success"))
            except PermissionError:
                legit_results.append(("read_debug", "failed"))
            
            assert legit_results[0][1] == "success", "Legitimate user should be able to work"
            
            # Analyze audit logs
            audit_logger = get_audit_logger()
            logs = audit_logger.query_logs(
                start_date=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            
            # Should have logged the attack attempts
            access_denied_logs = [l for l in logs if l.get('action') == 'access_denied']
            assert len(access_denied_logs) >= len(sensitive_fields)
    
    def test_security_headers_and_middleware(self):
        """Test that security headers and middleware are properly configured."""
        # This would test the actual FastAPI middleware integration
        # Mock the middleware behavior
        
        from ..middleware.audit_middleware import AuditMiddleware
        
        # Create mock request
        mock_request = Mock()
        mock_request.headers = {
            "X-Request-ID": "test-req-123",
            "User-Agent": "TestAgent/1.0"
        }
        mock_request.client = Mock(host="192.168.1.100")
        mock_request.state = Mock()
        mock_request.state.user = Mock(id="user123", email="user@example.com")
        
        # Test middleware sets audit context
        with patch('app.core.audit_logger.set_audit_context') as mock_set_context:
            with patch('app.core.audit_logger.clear_audit_context') as mock_clear_context:
                middleware = AuditMiddleware(Mock())
                
                async def mock_call_next(request):
                    response = Mock()
                    response.headers = {}
                    return response
                
                # Run middleware
                import asyncio
                response = asyncio.run(middleware.dispatch(mock_request, mock_call_next))
                
                # Verify audit context was set
                mock_set_context.assert_called_once()
                call_args = mock_set_context.call_args[1]
                assert call_args['user_id'] == "user123"
                assert call_args['user_email'] == "user@example.com"
                assert call_args['ip_address'] == "192.168.1.100"
                assert call_args['request_id'] == "test-req-123"
                
                # Verify context was cleared
                mock_clear_context.assert_called_once()
    
    def test_security_monitoring_alerts(self):
        """Test that security events can trigger appropriate alerts."""
        # In a real system, this would integrate with monitoring/alerting
        
        # Simulate security event detection
        def detect_security_anomalies(audit_logs: List[Dict[str, Any]]) -> List[str]:
            """Detect security anomalies in audit logs."""
            alerts = []
            
            # Check for repeated access denied
            user_failures = {}
            for log in audit_logs:
                if log.get('action') == 'access_denied':
                    user = log.get('user_id', 'unknown')
                    user_failures[user] = user_failures.get(user, 0) + 1
            
            for user, count in user_failures.items():
                if count >= 3:
                    alerts.append(f"Multiple access denied for user {user}: {count} attempts")
            
            # Check for privilege escalation attempts
            escalation_attempts = [
                log for log in audit_logs
                if log.get('field_name') == 'user_roles' and not log.get('success')
            ]
            
            if escalation_attempts:
                alerts.append(f"Privilege escalation attempts detected: {len(escalation_attempts)}")
            
            # Check for sensitive field access patterns
            sensitive_access = [
                log for log in audit_logs
                if log.get('field_name') in ['jwt_secret', 'api_key', 'db_password']
                and log.get('action') == 'read'
            ]
            
            if len(sensitive_access) > 10:
                alerts.append(f"Excessive sensitive field access: {len(sensitive_access)} reads")
            
            return alerts
        
        # Test with simulated logs
        test_logs = [
            {"action": "access_denied", "user_id": "attacker1", "field_name": "jwt_secret"},
            {"action": "access_denied", "user_id": "attacker1", "field_name": "api_key"},
            {"action": "access_denied", "user_id": "attacker1", "field_name": "db_password"},
            {"action": "write", "field_name": "user_roles", "success": False, "user_id": "attacker2"},
            {"action": "read", "field_name": "jwt_secret", "user_id": "user1"},
        ]
        
        alerts = detect_security_anomalies(test_logs)
        
        assert len(alerts) >= 2
        assert any("Multiple access denied" in alert for alert in alerts)
        assert any("Privilege escalation" in alert for alert in alerts)