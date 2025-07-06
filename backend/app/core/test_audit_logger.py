"""
Tests for Audit Logger System

Tests the audit logging functionality for configuration management,
including event logging, querying, and integration with settings.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import os

from .audit_logger import (
    AuditLogger, AuditEvent, AuditAction, AuditSeverity,
    AuditContext, get_audit_context, set_audit_context, clear_audit_context,
    get_audit_logger, configure_audit_logger
)
from .audited_config import (
    AuditedSettings, create_audited_settings, audit_config_access,
    AuditedConfigDict
)
from .config import Settings


class TestAuditEvent:
    """Test the AuditEvent dataclass."""
    
    def test_to_dict(self):
        """Test converting audit event to dictionary."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.READ,
            user_id="user123",
            user_email="user@example.com",
            field_name="database_url",
            old_value=None,
            new_value="postgresql://localhost:5432/db",
            environment="development",
            severity=AuditSeverity.INFO,
            ip_address="127.0.0.1",
            user_agent="pytest",
            session_id="session123",
            request_id="req123",
            success=True,
            error_message=None,
            metadata={"test": True}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["action"] == "read"
        assert event_dict["severity"] == "info"
        assert event_dict["user_email"] == "user@example.com"
        assert event_dict["metadata"]["test"] is True
    
    def test_sensitive_field_masking(self):
        """Test that sensitive fields are masked."""
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
        
        event_dict = event.to_dict()
        
        # Sensitive values should be masked
        assert event_dict["old_value"] == "ol...45"
        assert event_dict["new_value"] == "ne...90"
    
    def test_short_sensitive_value_masking(self):
        """Test masking of short sensitive values."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.WRITE,
            user_id="user123",
            user_email="user@example.com",
            field_name="api_key",
            old_value="short",
            new_value=None,
            environment="development",
            severity=AuditSeverity.INFO,
            ip_address=None,
            user_agent=None,
            session_id=None,
            request_id=None,
            success=True,
            error_message=None,
            metadata={}
        )
        
        event_dict = event.to_dict()
        
        # Short sensitive values should be fully masked
        assert event_dict["old_value"] == "***"
        assert event_dict["new_value"] is None


class TestAuditContext:
    """Test the audit context management."""
    
    def test_context_update(self):
        """Test updating audit context."""
        context = AuditContext()
        
        context.update(
            user_id="user123",
            user_email="user@example.com",
            ip_address="192.168.1.1"
        )
        
        assert context.user_id == "user123"
        assert context.user_email == "user@example.com"
        assert context.ip_address == "192.168.1.1"
    
    def test_context_clear(self):
        """Test clearing audit context."""
        context = AuditContext()
        context.user_id = "user123"
        context.user_email = "user@example.com"
        
        context.clear()
        
        assert context.user_id is None
        assert context.user_email is None
    
    def test_global_context_functions(self):
        """Test global context functions."""
        # Set context
        set_audit_context(
            user_id="global123",
            user_email="global@example.com",
            request_id="req999"
        )
        
        context = get_audit_context()
        assert context.user_id == "global123"
        assert context.user_email == "global@example.com"
        assert context.request_id == "req999"
        
        # Clear context
        clear_audit_context()
        context = get_audit_context()
        assert context.user_id is None
        assert context.user_email is None
        assert context.request_id is None


class TestAuditLogger:
    """Test the main AuditLogger class."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """Create an audit logger instance."""
        return AuditLogger(
            log_dir=temp_log_dir,
            max_file_size=1024,  # Small size for testing rotation
            retention_days=1,
            enable_console=False
        )
    
    def test_log_event(self, audit_logger, temp_log_dir):
        """Test logging an event."""
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
            metadata={"test": True}
        )
        
        audit_logger.log_event(event)
        
        # Check that log file was created
        log_files = list(temp_log_dir.glob("audit-*.jsonl"))
        assert len(log_files) == 1
        
        # Check log content
        with open(log_files[0], 'r') as f:
            log_data = json.loads(f.readline())
        
        assert log_data["action"] == "read"
        assert log_data["user_email"] == "user@example.com"
        assert log_data["field_name"] == "debug"
    
    def test_log_rotation(self, audit_logger, temp_log_dir):
        """Test log file rotation when size limit is exceeded."""
        # Create a large event that will exceed the file size limit
        large_metadata = {"data": "x" * 2000}
        
        for i in range(3):
            event = AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=AuditAction.READ,
                user_id=f"user{i}",
                user_email=f"user{i}@example.com",
                field_name="test_field",
                old_value=None,
                new_value="test",
                environment="development",
                severity=AuditSeverity.INFO,
                ip_address="127.0.0.1",
                user_agent="pytest",
                session_id=f"session{i}",
                request_id=f"req{i}",
                success=True,
                error_message=None,
                metadata=large_metadata
            )
            audit_logger.log_event(event)
        
        # Should have rotated files
        log_files = list(temp_log_dir.glob("audit-*.jsonl*"))
        assert len(log_files) > 1
    
    def test_config_operations_logging(self, audit_logger):
        """Test logging configuration operations."""
        set_audit_context(user_id="test_user", user_email="test@example.com")
        
        # Test read operation
        audit_logger.log_config_read(
            field_name="database_url",
            value="postgresql://localhost/db",
            success=True
        )
        
        # Test write operation
        audit_logger.log_config_write(
            field_name="debug",
            old_value=False,
            new_value=True,
            success=True
        )
        
        # Test validation operation
        audit_logger.log_config_validation(
            field_name="jwt_secret",
            success=False,
            error_message="JWT secret too short",
            validation_errors=[{"field": "jwt_secret", "error": "Min length 32"}]
        )
        
        # Test export operation
        audit_logger.log_config_export(
            export_format="json",
            include_sensitive=False,
            success=True
        )
        
        # Test access denied
        audit_logger.log_access_denied(
            action="write",
            resource="production_config",
            reason="Insufficient permissions"
        )
        
        clear_audit_context()
    
    def test_query_logs(self, audit_logger):
        """Test querying audit logs."""
        # Create some test events
        events = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(5):
            event = AuditEvent(
                timestamp=(base_time + timedelta(minutes=i)).isoformat(),
                action=AuditAction.READ if i % 2 == 0 else AuditAction.WRITE,
                user_id=f"user{i % 2}",
                user_email=f"user{i % 2}@example.com",
                field_name=f"field_{i}",
                old_value=None,
                new_value=f"value_{i}",
                environment="development",
                severity=AuditSeverity.INFO,
                ip_address="127.0.0.1",
                user_agent="pytest",
                session_id=f"session{i}",
                request_id=f"req{i}",
                success=True,
                error_message=None,
                metadata={}
            )
            audit_logger.log_event(event)
            events.append(event)
        
        # Query all logs
        all_logs = audit_logger.query_logs(
            start_date=base_time - timedelta(hours=1),
            end_date=base_time + timedelta(hours=1)
        )
        assert len(all_logs) == 5
        
        # Query by user
        user0_logs = audit_logger.query_logs(
            start_date=base_time - timedelta(hours=1),
            user_id="user0"
        )
        assert len(user0_logs) == 3
        
        # Query by action
        read_logs = audit_logger.query_logs(
            start_date=base_time - timedelta(hours=1),
            action=AuditAction.READ
        )
        assert len(read_logs) == 3
        
        # Query with limit
        limited_logs = audit_logger.query_logs(
            start_date=base_time - timedelta(hours=1),
            limit=2
        )
        assert len(limited_logs) == 2
    
    def test_audit_summary(self, audit_logger):
        """Test getting audit summary."""
        # Create various events
        base_time = datetime.now(timezone.utc)
        
        # Successful reads
        for i in range(3):
            audit_logger.log_event(AuditEvent(
                timestamp=base_time.isoformat(),
                action=AuditAction.READ,
                user_id=f"user{i}",
                user_email=f"user{i}@example.com",
                field_name="normal_field",
                old_value=None,
                new_value="value",
                environment="development",
                severity=AuditSeverity.INFO,
                ip_address="127.0.0.1",
                user_agent="pytest",
                session_id="session",
                request_id="req",
                success=True,
                error_message=None,
                metadata={}
            ))
        
        # Failed write
        audit_logger.log_event(AuditEvent(
            timestamp=base_time.isoformat(),
            action=AuditAction.WRITE,
            user_id="user1",
            user_email="user1@example.com",
            field_name="protected_field",
            old_value="old",
            new_value="new",
            environment="development",
            severity=AuditSeverity.ERROR,
            ip_address="127.0.0.1",
            user_agent="pytest",
            session_id="session",
            request_id="req",
            success=False,
            error_message="Permission denied",
            metadata={}
        ))
        
        # Sensitive field access
        audit_logger.log_event(AuditEvent(
            timestamp=base_time.isoformat(),
            action=AuditAction.READ,
            user_id="user2",
            user_email="user2@example.com",
            field_name="jwt_secret",
            old_value=None,
            new_value="***",
            environment="development",
            severity=AuditSeverity.WARNING,
            ip_address="127.0.0.1",
            user_agent="pytest",
            session_id="session",
            request_id="req",
            success=True,
            error_message=None,
            metadata={}
        ))
        
        # Get summary
        summary = audit_logger.get_audit_summary(
            start_date=base_time - timedelta(hours=1),
            end_date=base_time + timedelta(hours=1)
        )
        
        assert summary["total_events"] == 5
        assert summary["by_action"]["read"] == 4
        assert summary["by_action"]["write"] == 1
        assert summary["by_severity"]["info"] == 3
        assert summary["by_severity"]["error"] == 1
        assert summary["by_severity"]["warning"] == 1
        assert summary["failed_operations"] == 1
        assert summary["sensitive_field_access"] == 1
        assert summary["unique_users"] == 3


class TestAuditedSettings:
    """Test the AuditedSettings wrapper."""
    
    @pytest.fixture
    def settings(self):
        """Create a test settings instance."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            "DEBUG": "true"
        }):
            return Settings()
    
    @pytest.fixture
    def audited_settings(self, settings):
        """Create an audited settings wrapper."""
        return create_audited_settings(settings)
    
    def test_attribute_access_logging(self, audited_settings):
        """Test that attribute access is logged."""
        with patch.object(audited_settings._audit_logger, 'log_config_read') as mock_log:
            # Access a field
            value = audited_settings.debug
            
            assert value is True
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'debug'
            assert call_args['value'] is True
            assert call_args['success'] is True
    
    def test_sensitive_field_access(self, audited_settings):
        """Test that sensitive fields are masked in logs."""
        with patch.object(audited_settings._audit_logger, 'log_config_read') as mock_log:
            # Access a sensitive field
            value = audited_settings.secret_key
            
            assert value == "test-secret-key-for-testing-only"
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'secret_key'
            assert call_args['value'] == "***"  # Should be masked
    
    def test_attribute_modification_logging(self, audited_settings):
        """Test that attribute modifications are logged."""
        with patch.object(audited_settings._audit_logger, 'log_config_write') as mock_log:
            # Modify a field
            old_value = audited_settings._settings.debug
            audited_settings.debug = False
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'debug'
            assert call_args['old_value'] is True
            assert call_args['new_value'] is False
            assert call_args['success'] is True
    
    def test_access_stats(self, audited_settings):
        """Test access statistics tracking."""
        # Access fields multiple times
        _ = audited_settings.debug
        _ = audited_settings.debug
        _ = audited_settings.debug
        _ = audited_settings.environment
        _ = audited_settings.app_name
        
        stats = audited_settings.get_access_stats()
        
        assert stats['total_accesses'] == 5
        assert stats['by_field']['debug'] == 3
        assert stats['by_field']['environment'] == 1
        assert stats['by_field']['app_name'] == 1
        assert stats['most_accessed'] == 'debug'
        assert stats['fields_accessed'] == 3
    
    def test_modification_history(self, audited_settings):
        """Test modification history tracking."""
        # Make some modifications
        audited_settings.debug = False
        audited_settings.debug = True
        audited_settings.log_level = "DEBUG"
        
        # Get all history
        all_history = audited_settings.get_modification_history()
        assert 'debug' in all_history
        assert len(all_history['debug']) == 2
        assert 'log_level' in all_history
        assert len(all_history['log_level']) == 1
        
        # Get specific field history
        debug_history = audited_settings.get_modification_history('debug')
        assert len(debug_history['debug']) == 2
        assert debug_history['debug'][0]['old_value'] is True
        assert debug_history['debug'][0]['new_value'] is False
        assert debug_history['debug'][1]['old_value'] is False
        assert debug_history['debug'][1]['new_value'] is True
    
    def test_export_audit_safe(self, audited_settings):
        """Test safe export with audit logging."""
        with patch.object(audited_settings._audit_logger, 'log_config_export') as mock_log:
            config = audited_settings.export_audit_safe()
            
            assert isinstance(config, dict)
            assert 'secret_key' in config
            assert config['secret_key'] == "***REDACTED***"
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['export_format'] == 'dict'
            assert call_args['include_sensitive'] is False
            assert call_args['success'] is True


class TestAuditedConfigDict:
    """Test the AuditedConfigDict class."""
    
    @pytest.fixture
    def audited_dict(self):
        """Create an audited config dictionary."""
        return AuditedConfigDict({
            'debug': True,
            'log_level': 'INFO',
            'api_key': 'test-key-123'
        })
    
    def test_access_logging(self, audited_dict):
        """Test that dictionary access is logged."""
        with patch.object(audited_dict._audit_logger, 'log_config_read') as mock_log:
            value = audited_dict['debug']
            
            assert value is True
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'config_dict.debug'
            assert call_args['value'] is True
    
    def test_modification_logging(self, audited_dict):
        """Test that dictionary modifications are logged."""
        with patch.object(audited_dict._audit_logger, 'log_config_write') as mock_log:
            audited_dict['debug'] = False
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'config_dict.debug'
            assert call_args['old_value'] is True
            assert call_args['new_value'] is False
    
    def test_sensitive_key_masking(self, audited_dict):
        """Test that sensitive keys are masked."""
        with patch.object(audited_dict._audit_logger, 'log_config_read') as mock_log:
            value = audited_dict['api_key']
            
            assert value == 'test-key-123'
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['value'] == '***'  # Should be masked
    
    def test_pop_logging(self, audited_dict):
        """Test that key removal is logged."""
        with patch.object(audited_dict._audit_logger, 'log_config_write') as mock_log:
            value = audited_dict.pop('debug')
            
            assert value is True
            mock_log.assert_called_once()
            call_args = mock_log.call_args[1]
            assert call_args['field_name'] == 'config_dict.debug'
            assert call_args['old_value'] is True
            assert call_args['new_value'] is None
            assert call_args['metadata']['operation'] == 'delete'


class TestAuditConfigDecorator:
    """Test the audit_config_access decorator."""
    
    def test_function_audit_logging(self):
        """Test that decorated functions are logged."""
        @audit_config_access
        def test_function(x, y):
            return x + y
        
        with patch('app.core.audit_logger.get_audit_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            result = test_function(1, 2)
            
            assert result == 3
            mock_logger.log_event.assert_called_once()
            
            # Check the logged event
            logged_event = mock_logger.log_event.call_args[0][0]
            assert logged_event == AuditAction.READ
            assert mock_logger.log_event.call_args[1]['field_name'] == 'function:test_function'
            assert mock_logger.log_event.call_args[1]['success'] is True
    
    def test_function_error_logging(self):
        """Test that function errors are logged."""
        @audit_config_access
        def failing_function():
            raise ValueError("Test error")
        
        with patch('app.core.audit_logger.get_audit_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with pytest.raises(ValueError):
                failing_function()
            
            # Check that error was logged
            mock_logger.log_event.assert_called_once()
            assert mock_logger.log_event.call_args[1]['success'] is False
            assert mock_logger.log_event.call_args[1]['error_message'] == "Test error"


class TestIntegration:
    """Integration tests for audit logging with configuration."""
    
    @pytest.fixture
    def temp_audit_dir(self):
        """Create a temporary directory for audit logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_end_to_end_audit_logging(self, temp_audit_dir):
        """Test complete audit logging workflow."""
        # Configure audit logger
        configure_audit_logger(
            log_dir=temp_audit_dir,
            enable_console=False
        )
        
        # Set audit context
        set_audit_context(
            user_id="test_user",
            user_email="test@example.com",
            ip_address="192.168.1.100",
            request_id="test_request_123"
        )
        
        # Create settings and audited wrapper
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "SECRET_KEY": "test-secret-key",
            "DEBUG": "true"
        }):
            settings = Settings()
            audited = create_audited_settings(settings)
        
        # Perform various operations
        _ = audited.debug  # Read
        _ = audited.secret_key  # Read sensitive
        audited.log_level = "DEBUG"  # Write
        config = audited.export_audit_safe()  # Export
        
        # Clear context
        clear_audit_context()
        
        # Check audit logs were created
        log_files = list(temp_audit_dir.glob("audit-*.jsonl"))
        assert len(log_files) == 1
        
        # Read and verify log content
        events = []
        with open(log_files[0], 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        # Should have multiple events
        assert len(events) >= 4
        
        # Check event types
        actions = [e['action'] for e in events]
        assert 'read' in actions
        assert 'export' in actions
        
        # Check user context was captured
        for event in events:
            if event.get('user_id'):
                assert event['user_id'] == 'test_user'
                assert event['user_email'] == 'test@example.com'
                assert event['ip_address'] == '192.168.1.100'
                assert event['request_id'] == 'test_request_123'