"""
Audit Logging System for Configuration Management

Provides comprehensive audit logging for all configuration access and changes,
tracking who accessed what, when, and what changes were made.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from threading import Lock
import hashlib
import os

from pydantic import BaseModel


class AuditAction(Enum):
    """Types of configuration actions that can be audited."""
    READ = "read"
    WRITE = "write"
    UPDATE = "update"
    DELETE = "delete"
    VALIDATE = "validate"
    RELOAD = "reload"
    EXPORT = "export"
    ROTATE = "rotate"
    ACCESS_DENIED = "access_denied"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    timestamp: str
    action: AuditAction
    user_id: Optional[str]
    user_email: Optional[str]
    field_name: Optional[str]
    old_value: Optional[Any]
    new_value: Optional[Any]
    environment: str
    severity: AuditSeverity
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]
    success: bool
    error_message: Optional[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Convert enums to strings
        result["action"] = self.action.value
        result["severity"] = self.severity.value
        # Mask sensitive values
        if self.old_value and self._is_sensitive_field(self.field_name):
            result["old_value"] = self._mask_value(self.old_value)
        if self.new_value and self._is_sensitive_field(self.field_name):
            result["new_value"] = self._mask_value(self.new_value)
        return result
    
    def _is_sensitive_field(self, field_name: Optional[str]) -> bool:
        """Check if a field contains sensitive data."""
        if not field_name:
            return False
        sensitive_patterns = [
            "password", "secret", "key", "token", "credential",
            "private", "auth", "jwt", "api"
        ]
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in sensitive_patterns)
    
    def _mask_value(self, value: Any) -> str:
        """Mask sensitive values for logging."""
        if value is None:
            return "null"
        str_value = str(value)
        if len(str_value) <= 8:
            return "***"
        # Show first 2 and last 2 characters
        return f"{str_value[:2]}...{str_value[-2:]}"


class AuditContext:
    """Thread-local context for audit information."""
    def __init__(self):
        self.user_id: Optional[str] = None
        self.user_email: Optional[str] = None
        self.ip_address: Optional[str] = None
        self.user_agent: Optional[str] = None
        self.session_id: Optional[str] = None
        self.request_id: Optional[str] = None
        self.environment: str = os.getenv("ENVIRONMENT", "development")
    
    def update(self, **kwargs):
        """Update context values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def clear(self):
        """Clear context values."""
        self.__init__()


# Global audit context (should be thread-local in production)
_audit_context = AuditContext()


def get_audit_context() -> AuditContext:
    """Get the current audit context."""
    return _audit_context


def set_audit_context(**kwargs):
    """Set audit context values."""
    _audit_context.update(**kwargs)


def clear_audit_context():
    """Clear audit context."""
    _audit_context.clear()


class AuditLogger:
    """Main audit logger for configuration operations."""
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 90,
        enable_console: bool = True
    ):
        self.log_dir = log_dir or Path("logs/audit")
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self.enable_console = enable_console
        self._lock = Lock()
        self._current_file_size = 0
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up console logger
        self.logger = logging.getLogger("audit")
        if enable_console and not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _get_current_log_file(self) -> Path:
        """Get the current log file path."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{date_str}.jsonl"
    
    def _rotate_if_needed(self, log_file: Path):
        """Rotate log file if it exceeds max size."""
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            rotated_file = log_file.with_suffix(f".{timestamp}.jsonl")
            log_file.rename(rotated_file)
    
    def _clean_old_logs(self):
        """Remove log files older than retention period."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (self.retention_days * 86400)
        for log_file in self.log_dir.glob("audit-*.jsonl*"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
    
    def log_event(self, event: AuditEvent):
        """Log an audit event."""
        with self._lock:
            try:
                # Get log file and rotate if needed
                log_file = self._get_current_log_file()
                self._rotate_if_needed(log_file)
                
                # Write event to file
                with open(log_file, "a") as f:
                    json.dump(event.to_dict(), f)
                    f.write("\n")
                
                # Log to console if enabled
                if self.enable_console:
                    severity_map = {
                        AuditSeverity.INFO: logging.INFO,
                        AuditSeverity.WARNING: logging.WARNING,
                        AuditSeverity.ERROR: logging.ERROR,
                        AuditSeverity.CRITICAL: logging.CRITICAL
                    }
                    log_level = severity_map.get(event.severity, logging.INFO)
                    
                    message = f"{event.action.value.upper()}: "
                    if event.field_name:
                        message += f"field={event.field_name} "
                    if event.user_email:
                        message += f"user={event.user_email} "
                    if not event.success:
                        message += f"ERROR: {event.error_message}"
                    
                    self.logger.log(log_level, message)
                
                # Clean old logs periodically (every 100 events)
                if hasattr(self, "_event_count"):
                    self._event_count += 1
                    if self._event_count % 100 == 0:
                        self._clean_old_logs()
                else:
                    self._event_count = 1
                    
            except Exception as e:
                # Log error but don't raise - audit logging should not break the app
                if self.enable_console:
                    self.logger.error(f"Failed to write audit log: {e}")
    
    def log_config_read(
        self,
        field_name: Optional[str] = None,
        value: Optional[Any] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a configuration read operation."""
        context = get_audit_context()
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.READ,
            user_id=context.user_id,
            user_email=context.user_email,
            field_name=field_name,
            old_value=None,
            new_value=value,
            environment=context.environment,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            session_id=context.session_id,
            request_id=context.request_id,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        self.log_event(event)
    
    def log_config_write(
        self,
        field_name: str,
        old_value: Optional[Any],
        new_value: Any,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a configuration write operation."""
        context = get_audit_context()
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.WRITE if old_value is None else AuditAction.UPDATE,
            user_id=context.user_id,
            user_email=context.user_email,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            environment=context.environment,
            severity=AuditSeverity.WARNING if success else AuditSeverity.ERROR,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            session_id=context.session_id,
            request_id=context.request_id,
            success=success,
            error_message=error_message,
            metadata=metadata or {}
        )
        self.log_event(event)
    
    def log_config_validation(
        self,
        field_name: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a configuration validation operation."""
        context = get_audit_context()
        
        # Add validation errors to metadata
        if metadata is None:
            metadata = {}
        if validation_errors:
            metadata["validation_errors"] = validation_errors
        
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.VALIDATE,
            user_id=context.user_id,
            user_email=context.user_email,
            field_name=field_name,
            old_value=None,
            new_value=None,
            environment=context.environment,
            severity=AuditSeverity.INFO if success else AuditSeverity.ERROR,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            session_id=context.session_id,
            request_id=context.request_id,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_config_export(
        self,
        export_format: str = "dict",
        include_sensitive: bool = False,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a configuration export operation."""
        context = get_audit_context()
        
        if metadata is None:
            metadata = {}
        metadata["export_format"] = export_format
        metadata["include_sensitive"] = include_sensitive
        
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.EXPORT,
            user_id=context.user_id,
            user_email=context.user_email,
            field_name=None,
            old_value=None,
            new_value=None,
            environment=context.environment,
            severity=AuditSeverity.WARNING if include_sensitive else AuditSeverity.INFO,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            session_id=context.session_id,
            request_id=context.request_id,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_access_denied(
        self,
        action: str,
        resource: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log an access denied event."""
        context = get_audit_context()
        
        if metadata is None:
            metadata = {}
        metadata["attempted_action"] = action
        metadata["resource"] = resource
        metadata["denial_reason"] = reason
        
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=AuditAction.ACCESS_DENIED,
            user_id=context.user_id,
            user_email=context.user_email,
            field_name=None,
            old_value=None,
            new_value=None,
            environment=context.environment,
            severity=AuditSeverity.CRITICAL,
            ip_address=context.ip_address,
            user_agent=context.user_agent,
            session_id=context.session_id,
            request_id=context.request_id,
            success=False,
            error_message=f"Access denied: {reason}",
            metadata=metadata
        )
        self.log_event(event)
    
    def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        field_name: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters."""
        events = []
        
        # Determine date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Iterate through log files in date range
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            log_file = self.log_dir / f"audit-{current_date.strftime('%Y-%m-%d')}.jsonl"
            
            if log_file.exists():
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            
                            # Apply filters
                            if user_id and event.get("user_id") != user_id:
                                continue
                            if action and event.get("action") != action.value:
                                continue
                            if field_name and event.get("field_name") != field_name:
                                continue
                            if severity and event.get("severity") != severity.value:
                                continue
                            
                            # Check timestamp
                            event_time = datetime.fromisoformat(event["timestamp"])
                            if start_date <= event_time <= end_date:
                                events.append(event)
                                
                                if len(events) >= limit:
                                    return events
                                    
                        except json.JSONDecodeError:
                            continue
            
            # Move to next day
            from datetime import timedelta
            current_date = current_date + timedelta(days=1)
        
        return events
    
    def get_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get a summary of audit events."""
        events = self.query_logs(start_date=start_date, end_date=end_date, limit=10000)
        
        summary = {
            "total_events": len(events),
            "by_action": {},
            "by_severity": {},
            "by_user": {},
            "failed_operations": 0,
            "sensitive_field_access": 0,
            "unique_users": set(),
            "time_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
        
        for event in events:
            # Count by action
            action = event.get("action", "unknown")
            summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
            
            # Count by severity
            severity = event.get("severity", "unknown")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # Count by user
            user_email = event.get("user_email", "anonymous")
            summary["by_user"][user_email] = summary["by_user"].get(user_email, 0) + 1
            
            # Count failures
            if not event.get("success", True):
                summary["failed_operations"] += 1
            
            # Count sensitive field access
            field_name = event.get("field_name", "")
            if field_name and any(pattern in field_name.lower() for pattern in 
                                ["password", "secret", "key", "token"]):
                summary["sensitive_field_access"] += 1
            
            # Track unique users
            if event.get("user_id"):
                summary["unique_users"].add(event["user_id"])
        
        summary["unique_users"] = len(summary["unique_users"])
        
        return summary


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(**kwargs):
    """Configure the global audit logger."""
    global _audit_logger
    _audit_logger = AuditLogger(**kwargs)