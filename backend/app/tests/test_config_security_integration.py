"""
Integration Tests for Configuration Security System

Tests the complete integration of RBAC, audit logging, validation,
and security features across the configuration management system.
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings, Settings
from app.core.config_rbac import ConfigRole, get_config_rbac
from app.core.audit_logger import configure_audit_logger, get_audit_logger
from app.api.config import router as config_router
from app.api.audit import router as audit_router
from app.models.user import User
from app.middleware.audit_middleware import setup_audit_middleware


class TestConfigurationAPISecurityIntegration:
    """Test security features through the API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with config routes."""
        app = FastAPI()
        setup_audit_middleware(app)
        app.include_router(config_router)
        app.include_router(audit_router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_users(self):
        """Create mock users with different roles."""
        users = {
            "viewer": Mock(
                id="viewer123",
                email="viewer@example.com",
                role="user",
                is_admin=False,
                is_super_admin=False
            ),
            "developer": Mock(
                id="dev123",
                email="dev@example.com",
                role="developer",
                is_admin=False,
                is_super_admin=False
            ),
            "admin": Mock(
                id="admin123",
                email="admin@example.com",
                role="admin",
                is_admin=True,
                is_super_admin=False
            ),
            "super_admin": Mock(
                id="super123",
                email="super@example.com",
                role="admin",
                is_admin=True,
                is_super_admin=True
            )
        }
        
        # Assign configuration roles
        rbac = get_config_rbac()
        rbac.assign_role(users["viewer"].id, ConfigRole.VIEWER.value)
        rbac.assign_role(users["developer"].id, ConfigRole.DEVELOPER.value)
        rbac.assign_role(users["admin"].id, ConfigRole.ADMIN.value)
        rbac.assign_role(users["super_admin"].id, ConfigRole.SUPER_ADMIN.value)
        
        return users
    
    def test_api_field_access_control(self, client, mock_users):
        """Test that API enforces field-level access control."""
        # Mock authentication dependencies
        from app.api.auth import get_current_user
        
        # Test viewer access
        with patch('app.api.config.get_current_user', return_value=mock_users["viewer"]):
            # Can read non-sensitive fields
            response = client.get("/api/v1/config/field/app_name")
            assert response.status_code == 200
            
            # Cannot read sensitive fields
            response = client.get("/api/v1/config/field/jwt_secret")
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
            
            # Cannot write any fields
            response = client.put(
                "/api/v1/config/field",
                json={"field_name": "debug", "value": False}
            )
            assert response.status_code == 403
    
    def test_api_environment_based_permissions(self, client, mock_users):
        """Test that API respects environment-based permissions."""
        # Test developer in different environments
        with patch('app.api.config.get_current_user', return_value=mock_users["developer"]):
            # In development environment
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.environment = "development"
                mock_settings.return_value.is_production = False
                
                response = client.put(
                    "/api/v1/config/field",
                    json={"field_name": "debug", "value": True}
                )
                # Should succeed in development
                assert response.status_code in [200, 400]  # 400 if actual write fails
            
            # In production environment
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.environment = "production"
                mock_settings.return_value.is_production = True
                
                response = client.put(
                    "/api/v1/config/field",
                    json={"field_name": "debug", "value": True}
                )
                # Should fail in production (non-admin)
                assert response.status_code == 403
    
    def test_api_role_management_security(self, client, mock_users):
        """Test that role management APIs are properly secured."""
        # Non-admin cannot assign roles
        with patch('app.api.config.get_current_user', return_value=mock_users["viewer"]):
            with patch('app.api.config.get_current_admin_user', side_effect=Exception("Not admin")):
                response = client.post(
                    "/api/v1/config/roles/assign",
                    json={"user_id": "target123", "role": "admin"}
                )
                assert response.status_code in [403, 422, 500]
        
        # Admin can assign roles
        with patch('app.api.config.get_current_admin_user', return_value=mock_users["admin"]):
            response = client.post(
                "/api/v1/config/roles/assign",
                json={"user_id": "target123", "role": "operator"}
            )
            assert response.status_code == 200
            assert response.json()["status"] == "success"
    
    def test_api_export_security(self, client, mock_users):
        """Test that configuration export respects permissions."""
        # Viewer cannot export
        with patch('app.api.config.get_current_user', return_value=mock_users["viewer"]):
            response = client.get("/api/v1/config/export")
            assert response.status_code == 403
            assert "export permission" in response.json()["detail"]
        
        # Developer can export but no sensitive values
        with patch('app.api.config.get_current_user', return_value=mock_users["developer"]):
            response = client.get("/api/v1/config/export")
            assert response.status_code == 200
            config = response.json()["configuration"]
            # Should not include actual sensitive values
            for key in config:
                if any(sensitive in key.lower() for sensitive in ["secret", "password", "key"]):
                    assert config[key] in [None, "***REDACTED***", "***"]
        
        # Admin can request sensitive export
        with patch('app.api.config.get_current_user', return_value=mock_users["admin"]):
            response = client.get("/api/v1/config/export?include_sensitive=true")
            assert response.status_code == 200
    
    def test_api_audit_log_access(self, client, mock_users):
        """Test that audit log APIs are properly secured."""
        # Regular user cannot access audit logs
        with patch('app.api.audit.get_current_admin_user', side_effect=Exception("Not admin")):
            response = client.get("/api/v1/audit/logs")
            assert response.status_code in [403, 422, 500]
        
        # Admin can access audit logs
        with patch('app.api.audit.get_current_admin_user', return_value=mock_users["admin"]):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.is_production = False
                
                response = client.get("/api/v1/audit/logs")
                assert response.status_code == 200
        
        # In production, only super admin can access
        with patch('app.api.audit.get_current_admin_user', return_value=mock_users["admin"]):
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value.is_production = True
                
                response = client.get("/api/v1/audit/logs")
                assert response.status_code == 403
                assert "super admin" in response.json()["detail"].lower()


class TestSecurityValidationIntegration:
    """Test integration of security validation features."""
    
    def test_secret_detection_prevents_commits(self, tmp_path):
        """Test that secret detection prevents committing secrets."""
        # Create a test file with secrets
        test_file = tmp_path / "config.py"
        test_file.write_text("""
# Configuration file
API_KEY = "sk-1234567890abcdef1234567890abcdef"
PASSWORD = "mysecretpassword123"
DB_URL = "postgresql://user:realPassword123@localhost/db"
""")
        
        # Run secret detection
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from detect_secrets import SecretDetector
        
        detector = SecretDetector()
        results = detector.scan_file(test_file)
        
        # Should detect secrets
        assert len(results) >= 3
        secret_types = [r.secret_type.value for r in results]
        assert "api_key" in secret_types
        assert "password" in secret_types
        assert "connection_string" in secret_types
    
    def test_configuration_validation_security_rules(self):
        """Test that configuration validation enforces security rules."""
        # Test production configuration requirements
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "production-secret-key-that-is-long-enough-123456",
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "test-key",
            "DEBUG": "false",
            "REQUIRE_EMAIL_VERIFICATION": "true",
            "CSRF_PROTECTION_ENABLED": "true",
            "PASSWORD_MIN_LENGTH": "12"
        }):
            try:
                settings = Settings()
                # Should pass validation
                assert settings.environment == "production"
                assert settings.debug is False
                assert settings.require_email_verification is True
                assert settings.password_min_length >= 10
            except ValueError as e:
                pytest.fail(f"Valid production config should not fail: {e}")
        
        # Test invalid production configuration
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "too-short",
            "DEBUG": "true"
        }):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            
            error = str(exc_info.value)
            assert "SECRET_KEY" in error or "DEBUG" in error
    
    def test_audit_validation_integration(self):
        """Test that validation attempts are properly audited."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_audit_logger(log_dir=Path(tmpdir), enable_console=False)
            
            from app.services.config_access_service import ConfigAccessService
            service = ConfigAccessService()
            
            # Create test user
            user = Mock(
                id="test123",
                email="test@example.com",
                role="developer",
                is_admin=False,
                is_super_admin=False
            )
            
            # Assign developer role
            rbac = get_config_rbac()
            rbac.assign_role(str(user.id), ConfigRole.DEVELOPER.value)
            
            # Validate configuration updates
            validation_result = service.validate_config_for_user(
                user,
                {
                    "debug": False,
                    "log_level": "WARNING",
                    "jwt_secret": "new-secret"  # Should be denied
                }
            )
            
            # Check validation result
            assert not validation_result["valid"]
            assert "jwt_secret" in validation_result["denied_fields"]
            
            # Check audit logs
            audit_logger = get_audit_logger()
            logs = audit_logger.query_logs(
                start_date=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            
            # Should have logged validation attempt
            validation_logs = [l for l in logs if l.get("action") == "validate"]
            assert len(validation_logs) > 0
            
            # Should include denied fields in metadata
            for log in validation_logs:
                if log.get("metadata", {}).get("denied_fields"):
                    assert "jwt_secret" in log["metadata"]["denied_fields"]


class TestSecurityMonitoringIntegration:
    """Test security monitoring and alerting integration."""
    
    def test_attack_pattern_detection(self):
        """Test that attack patterns can be detected from audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_audit_logger(log_dir=Path(tmpdir), enable_console=False)
            audit_logger = get_audit_logger()
            
            # Simulate attack pattern
            attacker_id = "attacker123"
            base_time = datetime.now(timezone.utc)
            
            # Pattern 1: Rapid access attempts to sensitive fields
            for i in range(10):
                audit_logger.log_config_read(
                    field_name="jwt_secret",
                    value=None,
                    success=False,
                    error_message="Access denied",
                    metadata={
                        "user_id": attacker_id,
                        "timestamp": (base_time + timedelta(seconds=i)).isoformat()
                    }
                )
            
            # Pattern 2: Privilege escalation attempts
            for i in range(3):
                audit_logger.log_access_denied(
                    action="assign_role",
                    resource="config_roles",
                    reason="Insufficient permissions",
                    metadata={
                        "user_id": attacker_id,
                        "attempted_role": "admin"
                    }
                )
            
            # Analyze patterns
            logs = audit_logger.query_logs(
                start_date=base_time - timedelta(minutes=1),
                user_id=attacker_id
            )
            
            # Detect rapid access pattern
            access_times = []
            for log in logs:
                if log.get("field_name") == "jwt_secret":
                    access_times.append(log["timestamp"])
            
            # Check for rapid succession (more than 5 attempts in 10 seconds)
            if len(access_times) >= 5:
                first_time = datetime.fromisoformat(access_times[0].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(access_times[4].replace('Z', '+00:00'))
                time_diff = (last_time - first_time).total_seconds()
                
                assert time_diff < 10, "Should detect rapid access pattern"
            
            # Detect privilege escalation attempts
            escalation_attempts = [
                l for l in logs 
                if l.get("action") == "access_denied" 
                and l.get("metadata", {}).get("attempted_role") == "admin"
            ]
            
            assert len(escalation_attempts) >= 3, "Should detect privilege escalation attempts"
    
    def test_anomaly_detection_across_users(self):
        """Test detection of anomalous behavior across multiple users."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_audit_logger(log_dir=Path(tmpdir), enable_console=False)
            audit_logger = get_audit_logger()
            
            # Normal user behavior
            normal_users = ["user1", "user2", "user3"]
            for user in normal_users:
                audit_logger.log_config_read(
                    field_name="app_name",
                    value="Test App",
                    success=True,
                    metadata={"user_id": user}
                )
                audit_logger.log_config_read(
                    field_name="debug",
                    value=True,
                    success=True,
                    metadata={"user_id": user}
                )
            
            # Anomalous behavior
            anomalous_user = "anomaly123"
            sensitive_fields = [
                "jwt_secret", "api_key", "db_password", 
                "supabase_service_role_key", "openai_api_key"
            ]
            
            for field in sensitive_fields:
                audit_logger.log_config_read(
                    field_name=field,
                    value="***",
                    success=True,
                    metadata={"user_id": anomalous_user}
                )
            
            # Analyze behavior
            summary = audit_logger.get_audit_summary(
                start_date=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            
            # Anomalous user should stand out
            assert summary["sensitive_field_access"] >= len(sensitive_fields)
            
            # Check user-specific behavior
            all_logs = audit_logger.query_logs(
                start_date=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            
            user_sensitive_access = {}
            for log in all_logs:
                user = log.get("metadata", {}).get("user_id")
                field = log.get("field_name", "")
                
                if user and any(s in field for s in ["secret", "key", "password"]):
                    user_sensitive_access[user] = user_sensitive_access.get(user, 0) + 1
            
            # Anomalous user should have significantly more sensitive access
            if anomalous_user in user_sensitive_access:
                anomaly_count = user_sensitive_access[anomalous_user]
                normal_max = max(
                    [user_sensitive_access.get(u, 0) for u in normal_users],
                    default=0
                )
                
                assert anomaly_count > normal_max * 3, "Should detect anomalous access pattern"
    
    def test_security_metrics_dashboard(self):
        """Test that security metrics can be generated for monitoring."""
        with tempfile.TemporaryDirectory() as tmpdir:
            configure_audit_logger(log_dir=Path(tmpdir), enable_console=False)
            
            # Simulate various security events over time
            service = ConfigAccessService()
            rbac = get_config_rbac()
            
            # Create test users
            users = []
            for i in range(5):
                user = Mock(
                    id=f"user{i}",
                    email=f"user{i}@example.com",
                    role="user" if i < 3 else "developer",
                    is_admin=False,
                    is_super_admin=False
                )
                users.append(user)
                
                # Assign appropriate role
                if i < 3:
                    rbac.assign_role(str(user.id), ConfigRole.VIEWER.value)
                else:
                    rbac.assign_role(str(user.id), ConfigRole.DEVELOPER.value)
            
            # Generate various events
            for user in users:
                try:
                    # Normal operations
                    service.read_config_field(user, "app_name")
                    service.read_config_field(user, "debug")
                    
                    # Some users try sensitive fields
                    if user.role == "user":
                        try:
                            service.read_config_field(user, "jwt_secret")
                        except PermissionError:
                            pass
                    
                except Exception:
                    pass
            
            # Generate security metrics
            audit_logger = get_audit_logger()
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            summary = audit_logger.get_audit_summary(start_time, end_time)
            
            # Calculate security metrics
            metrics = {
                "total_events": summary["total_events"],
                "failure_rate": summary.get("failure_rate", 0),
                "sensitive_access_rate": summary.get("sensitive_access_rate", 0),
                "unique_users": summary["unique_users"],
                "access_denied_events": summary["by_action"].get("access_denied", 0),
                "critical_events": summary["by_severity"].get("critical", 0),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }
            
            # Verify metrics are reasonable
            assert metrics["total_events"] > 0
            assert metrics["unique_users"] == len(users)
            assert "failure_rate" in metrics
            assert "sensitive_access_rate" in metrics