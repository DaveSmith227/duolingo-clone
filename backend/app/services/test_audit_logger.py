"""
Unit Tests for Audit Logger Service

Tests for comprehensive audit logging, security monitoring, and compliance.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.audit_logger import (
    AuditLogger,
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    get_audit_logger,
    log_login_attempt,
    log_security_incident
)
from app.models.auth import AuthAuditLog


class TestAuditEventType:
    """Test cases for AuditEventType enum."""
    
    def test_authentication_events(self):
        """Test authentication event types."""
        assert AuditEventType.LOGIN_SUCCESS.value == "login_success"
        assert AuditEventType.LOGIN_FAILURE.value == "login_failure"
        assert AuditEventType.LOGOUT.value == "logout"
        assert AuditEventType.TOKEN_REFRESH.value == "token_refresh"
    
    def test_security_events(self):
        """Test security event types."""
        assert AuditEventType.RATE_LIMIT_EXCEEDED.value == "rate_limit_exceeded"
        assert AuditEventType.ACCOUNT_LOCKED.value == "account_locked"
        assert AuditEventType.CSRF_VIOLATION.value == "csrf_violation"
        assert AuditEventType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"
    
    def test_admin_events(self):
        """Test admin event types."""
        assert AuditEventType.ADMIN_ACTION.value == "admin_action"
        assert AuditEventType.USER_SUSPENDED.value == "user_suspended"
        assert AuditEventType.BULK_OPERATION.value == "bulk_operation"


class TestAuditSeverity:
    """Test cases for AuditSeverity enum."""
    
    def test_severity_levels(self):
        """Test severity level values."""
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditEvent:
    """Test cases for AuditEvent dataclass."""
    
    def test_audit_event_creation(self):
        """Test AuditEvent creation with required fields."""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            event_result="success"
        )
        
        assert event.event_type == AuditEventType.LOGIN_SUCCESS
        assert event.event_result == "success"
        assert event.severity == AuditSeverity.MEDIUM  # Default
        assert event.user_id is None
        assert event.details is None
    
    def test_audit_event_with_all_fields(self):
        """Test AuditEvent creation with all fields."""
        details = {"email": "test@example.com"}
        metadata = {"source": "web"}
        
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_FAILURE,
            event_result="failure",
            severity=AuditSeverity.HIGH,
            user_id="user-123",
            session_id="session-456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            resource="authentication",
            details=details,
            metadata=metadata,
            correlation_id="corr-789"
        )
        
        assert event.severity == AuditSeverity.HIGH
        assert event.user_id == "user-123"
        assert event.details == details
        assert event.metadata == metadata


class TestAuditLogger:
    """Test cases for AuditLogger class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_audit_log(self):
        """Mock AuthAuditLog model."""
        mock_log = Mock(spec=AuthAuditLog)
        mock_log.id = "log-123"
        mock_log.event_type = "login_success"
        mock_log.event_result = "success"
        mock_log.created_at = datetime.now(timezone.utc)
        mock_log.supabase_user_id = "user-123"
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Mozilla/5.0"
        mock_log.metadata = '{"severity": "medium"}'
        return mock_log
    
    @pytest.fixture
    def audit_logger(self, mock_db):
        """AuditLogger instance with mocked database."""
        return AuditLogger(mock_db)
    
    def test_init_audit_logger(self, audit_logger, mock_db):
        """Test AuditLogger initialization."""
        assert audit_logger.db == mock_db
        assert audit_logger.settings is not None
        assert AuditEventType.LOGIN_FAILURE in audit_logger._severity_mapping
    
    def test_severity_mapping(self, audit_logger):
        """Test automatic severity mapping for event types."""
        mapping = audit_logger._severity_mapping
        
        assert mapping[AuditEventType.LOGIN_FAILURE] == AuditSeverity.MEDIUM
        assert mapping[AuditEventType.RATE_LIMIT_EXCEEDED] == AuditSeverity.HIGH
        assert mapping[AuditEventType.SUSPICIOUS_ACTIVITY] == AuditSeverity.CRITICAL
        assert mapping[AuditEventType.ACCOUNT_LOCKED] == AuditSeverity.HIGH
    
    def test_log_event_success(self, audit_logger, mock_db):
        """Test successful event logging."""
        with patch.object(audit_logger, '_store_audit_log') as mock_store, \
             patch.object(audit_logger, '_log_to_application_logger') as mock_app_log:
            
            mock_store.return_value = "log-123"
            
            log_id = audit_logger.log_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                event_result="success",
                user_id="user-123",
                ip_address="192.168.1.1"
            )
            
            assert log_id == "log-123"
            mock_store.assert_called_once()
            mock_app_log.assert_called_once()
    
    def test_log_event_with_string_type(self, audit_logger):
        """Test logging event with string event type."""
        with patch.object(audit_logger, '_store_audit_log') as mock_store, \
             patch.object(audit_logger, '_log_to_application_logger'):
            
            mock_store.return_value = "log-123"
            
            log_id = audit_logger.log_event(
                event_type="login_success",
                event_result="success"
            )
            
            assert log_id == "log-123"
            # Verify the call was made with converted enum
            call_args = mock_store.call_args[0][0]
            assert call_args.event_type == AuditEventType.LOGIN_SUCCESS
    
    def test_log_event_unknown_string_type(self, audit_logger):
        """Test logging event with unknown string event type."""
        with patch.object(audit_logger, '_store_audit_log') as mock_store, \
             patch.object(audit_logger, '_log_to_application_logger'):
            
            mock_store.return_value = "log-123"
            
            log_id = audit_logger.log_event(
                event_type="unknown_event",
                event_result="success"
            )
            
            assert log_id == "log-123"
            # Should default to suspicious activity
            call_args = mock_store.call_args[0][0]
            assert call_args.event_type == AuditEventType.SUSPICIOUS_ACTIVITY
    
    def test_log_event_auto_severity(self, audit_logger):
        """Test automatic severity detection."""
        with patch.object(audit_logger, '_store_audit_log') as mock_store, \
             patch.object(audit_logger, '_log_to_application_logger'):
            
            mock_store.return_value = "log-123"
            
            # Test high severity event
            audit_logger.log_event(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                event_result="detected"
            )
            
            call_args = mock_store.call_args[0][0]
            assert call_args.severity == AuditSeverity.HIGH
    
    def test_log_event_critical_triggers_alert(self, audit_logger):
        """Test that critical events trigger security alerts."""
        with patch.object(audit_logger, '_store_audit_log') as mock_store, \
             patch.object(audit_logger, '_log_to_application_logger'), \
             patch.object(audit_logger, '_trigger_security_alert') as mock_alert:
            
            mock_store.return_value = "log-123"
            
            audit_logger.log_event(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                event_result="detected"
            )
            
            mock_alert.assert_called_once()
    
    def test_log_authentication_event(self, audit_logger):
        """Test authentication event logging."""
        with patch.object(audit_logger, 'log_event') as mock_log:
            mock_log.return_value = "log-123"
            
            log_id = audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                success=True,
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1",
                provider="google"
            )
            
            assert log_id == "log-123"
            mock_log.assert_called_once()
            
            # Verify call arguments
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["event_result"] == "success"
            assert call_kwargs["details"]["email"] == "test@example.com"
            assert call_kwargs["details"]["provider"] == "google"
            assert call_kwargs["metadata"]["event_category"] == "authentication"
    
    def test_log_authentication_event_failure(self, audit_logger):
        """Test failed authentication event logging."""
        with patch.object(audit_logger, 'log_event') as mock_log:
            mock_log.return_value = "log-123"
            
            audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                email="test@example.com",
                error_message="Invalid password"
            )
            
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["event_result"] == "failure"
            assert call_kwargs["details"]["error_message"] == "Invalid password"
    
    def test_log_security_event(self, audit_logger):
        """Test security event logging."""
        with patch.object(audit_logger, 'log_event') as mock_log:
            mock_log.return_value = "log-123"
            
            log_id = audit_logger.log_security_event(
                event_type=AuditEventType.CSRF_VIOLATION,
                description="CSRF token mismatch",
                user_id="user-123",
                ip_address="192.168.1.1",
                severity=AuditSeverity.HIGH
            )
            
            assert log_id == "log-123"
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["event_result"] == "detected"
            assert call_kwargs["details"]["description"] == "CSRF token mismatch"
            assert call_kwargs["metadata"]["event_category"] == "security"
            assert call_kwargs["severity"] == AuditSeverity.HIGH
    
    def test_log_admin_action(self, audit_logger):
        """Test admin action logging."""
        with patch.object(audit_logger, 'log_event') as mock_log:
            mock_log.return_value = "log-123"
            
            changes = {"status": "suspended"}
            
            log_id = audit_logger.log_admin_action(
                action="suspend_user",
                admin_user_id="admin-123",
                target_user_id="user-456",
                resource="user_management",
                changes=changes,
                ip_address="10.0.0.1"
            )
            
            assert log_id == "log-123"
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["event_type"] == AuditEventType.ADMIN_ACTION
            assert call_kwargs["details"]["action"] == "suspend_user"
            assert call_kwargs["details"]["admin_user_id"] == "admin-123"
            assert call_kwargs["details"]["target_user_id"] == "user-456"
            assert call_kwargs["details"]["changes"] == changes
            assert call_kwargs["severity"] == AuditSeverity.HIGH
    
    def test_search_audit_logs(self, audit_logger, mock_db, mock_audit_log):
        """Test audit log searching."""
        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_audit_log]
        mock_db.query.return_value = mock_query
        
        results = audit_logger.search_audit_logs(
            event_types=[AuditEventType.LOGIN_SUCCESS],
            user_id="user-123",
            limit=50
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "log-123"
        assert results[0]["event_type"] == "login_success"
        assert results[0]["user_id"] == "user-123"
    
    def test_search_audit_logs_with_date_range(self, audit_logger, mock_db, mock_audit_log):
        """Test audit log searching with date range."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_audit_log]
        mock_db.query.return_value = mock_query
        
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)
        
        results = audit_logger.search_audit_logs(
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(results) == 1
        # Verify date filters were applied
        assert mock_query.filter.call_count >= 2
    
    def test_get_user_activity_summary(self, audit_logger):
        """Test user activity summary generation."""
        mock_logs = [
            {
                "event_type": "login_success",
                "created_at": "2023-01-01T12:00:00Z",
                "ip_address": "192.168.1.1"
            },
            {
                "event_type": "login_failure", 
                "created_at": "2023-01-01T11:30:00Z",
                "ip_address": "192.168.1.2"
            },
            {
                "event_type": "rate_limit_exceeded",
                "created_at": "2023-01-01T11:00:00Z",
                "ip_address": "192.168.1.1"
            }
        ]
        
        with patch.object(audit_logger, 'search_audit_logs') as mock_search:
            mock_search.return_value = mock_logs
            
            summary = audit_logger.get_user_activity_summary("user-123", days=30)
            
            assert summary["user_id"] == "user-123"
            assert summary["total_events"] == 3
            assert summary["login_attempts"] == 2
            assert summary["failed_logins"] == 1
            assert summary["security_events"] == 1
            assert len(summary["unique_ips"]) == 2
            assert "192.168.1.1" in summary["unique_ips"]
            assert "192.168.1.2" in summary["unique_ips"]
    
    def test_store_audit_log(self, audit_logger, mock_db):
        """Test storing audit log in database."""
        mock_log_entry = Mock()
        mock_log_entry.id = "log-123"
        
        with patch('app.services.audit_logger.AuthAuditLog.create_log') as mock_create:
            mock_create.return_value = mock_log_entry
            
            audit_event = AuditEvent(
                event_type=AuditEventType.LOGIN_SUCCESS,
                event_result="success",
                severity=AuditSeverity.MEDIUM,
                user_id="user-123",
                correlation_id="corr-456"
            )
            
            log_id = audit_logger._store_audit_log(audit_event)
            
            assert log_id == "log-123"
            mock_create.assert_called_once()
            mock_db.add.assert_called_once_with(mock_log_entry)
            mock_db.commit.assert_called_once()
    
    def test_store_audit_log_error_handling(self, audit_logger, mock_db):
        """Test audit log storage error handling."""
        mock_db.add.side_effect = Exception("Database error")
        
        audit_event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            event_result="success"
        )
        
        with pytest.raises(Exception):
            audit_logger._store_audit_log(audit_event)
        
        mock_db.rollback.assert_called_once()
    
    def test_log_to_application_logger(self, audit_logger):
        """Test application logger integration."""
        audit_event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            event_result="success",
            severity=AuditSeverity.MEDIUM,
            user_id="user-123"
        )
        
        with patch('app.services.audit_logger.logger') as mock_logger:
            audit_logger._log_to_application_logger(audit_event, "log-123")
            
            mock_logger.info.assert_called_once()
    
    def test_log_to_application_logger_high_severity(self, audit_logger):
        """Test application logger with high severity events."""
        audit_event = AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            event_result="detected",
            severity=AuditSeverity.CRITICAL
        )
        
        with patch('app.services.audit_logger.logger') as mock_logger:
            audit_logger._log_to_application_logger(audit_event, "log-123")
            
            mock_logger.warning.assert_called_once()
    
    def test_trigger_security_alert(self, audit_logger):
        """Test security alert triggering."""
        audit_event = AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            event_result="detected",
            severity=AuditSeverity.CRITICAL,
            user_id="user-123",
            details={"threat_level": "high"}
        )
        
        with patch('app.services.audit_logger.logger') as mock_logger:
            audit_logger._trigger_security_alert(audit_event, "log-123")
            
            mock_logger.critical.assert_called_once()


class TestAuditLoggerUtilities:
    """Test cases for audit logger utility functions."""
    
    def test_get_audit_logger(self):
        """Test get_audit_logger factory function."""
        mock_db = Mock(spec=Session)
        
        logger = get_audit_logger(mock_db)
        
        assert isinstance(logger, AuditLogger)
        assert logger.db == mock_db
    
    def test_log_login_attempt_success(self):
        """Test login attempt logging utility."""
        mock_db = Mock(spec=Session)
        
        with patch('app.services.audit_logger.get_audit_logger') as mock_get_logger:
            mock_audit_logger = Mock()
            mock_audit_logger.log_authentication_event.return_value = "log-123"
            mock_get_logger.return_value = mock_audit_logger
            
            log_id = log_login_attempt(
                db=mock_db,
                success=True,
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1"
            )
            
            assert log_id == "log-123"
            mock_audit_logger.log_authentication_event.assert_called_once()
            call_kwargs = mock_audit_logger.log_authentication_event.call_args[1]
            assert call_kwargs["event_type"] == AuditEventType.LOGIN_SUCCESS
            assert call_kwargs["success"] is True
    
    def test_log_login_attempt_failure(self):
        """Test failed login attempt logging utility."""
        mock_db = Mock(spec=Session)
        
        with patch('app.services.audit_logger.get_audit_logger') as mock_get_logger:
            mock_audit_logger = Mock()
            mock_audit_logger.log_authentication_event.return_value = "log-123"
            mock_get_logger.return_value = mock_audit_logger
            
            log_id = log_login_attempt(
                db=mock_db,
                success=False,
                email="test@example.com",
                error_message="Invalid credentials"
            )
            
            assert log_id == "log-123"
            call_kwargs = mock_audit_logger.log_authentication_event.call_args[1]
            assert call_kwargs["event_type"] == AuditEventType.LOGIN_FAILURE
            assert call_kwargs["success"] is False
            assert call_kwargs["error_message"] == "Invalid credentials"
    
    def test_log_security_incident(self):
        """Test security incident logging utility."""
        mock_db = Mock(spec=Session)
        
        with patch('app.services.audit_logger.get_audit_logger') as mock_get_logger:
            mock_audit_logger = Mock()
            mock_audit_logger.log_security_event.return_value = "log-123"
            mock_get_logger.return_value = mock_audit_logger
            
            log_id = log_security_incident(
                db=mock_db,
                incident_type="rate_limit_exceeded",
                description="Too many failed login attempts",
                user_id="user-123",
                ip_address="192.168.1.1"
            )
            
            assert log_id == "log-123"
            mock_audit_logger.log_security_event.assert_called_once()
            call_kwargs = mock_audit_logger.log_security_event.call_args[1]
            assert call_kwargs["event_type"] == AuditEventType.RATE_LIMIT_EXCEEDED
            assert call_kwargs["description"] == "Too many failed login attempts"
    
    def test_log_security_incident_unknown_type(self):
        """Test security incident logging with unknown type."""
        mock_db = Mock(spec=Session)
        
        with patch('app.services.audit_logger.get_audit_logger') as mock_get_logger:
            mock_audit_logger = Mock()
            mock_audit_logger.log_security_event.return_value = "log-123"
            mock_get_logger.return_value = mock_audit_logger
            
            log_id = log_security_incident(
                db=mock_db,
                incident_type="unknown_incident",
                description="Unknown security event"
            )
            
            assert log_id == "log-123"
            call_kwargs = mock_audit_logger.log_security_event.call_args[1]
            assert call_kwargs["event_type"] == AuditEventType.SUSPICIOUS_ACTIVITY


class TestAuditLoggerIntegration:
    """Integration tests for audit logger with real database operations."""
    
    def test_complete_audit_flow(self):
        """Test complete audit logging flow."""
        # This would require actual database setup
        # Implementation depends on test database configuration
        pass
    
    def test_audit_log_search_performance(self):
        """Test audit log search performance with large datasets."""
        # This would test search performance with many records
        pass
    
    def test_audit_log_retention(self):
        """Test audit log retention and cleanup."""
        # This would test log retention policies
        pass