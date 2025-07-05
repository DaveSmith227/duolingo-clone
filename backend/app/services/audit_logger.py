"""
Audit Logging Service

Comprehensive audit logging for authentication events and security monitoring.
"""

import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.models.auth import AuthAuditLog
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types for categorization."""
    
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    LOGOUT_ALL = "logout_all"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"
    
    # Registration events
    REGISTRATION_SUCCESS = "registration_success"
    REGISTRATION_FAILURE = "registration_failure"
    EMAIL_VERIFICATION = "email_verification"
    
    # Password events
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    PASSWORD_RESET_FAILURE = "password_reset_failure"
    
    # Session events
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_INVALIDATED = "session_invalidated"
    SESSION_LIMIT_EXCEEDED = "session_limit_exceeded"
    
    # Security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    CSRF_VIOLATION = "csrf_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    
    # OAuth events
    OAUTH_LOGIN_SUCCESS = "oauth_login_success"
    OAUTH_LOGIN_FAILURE = "oauth_login_failure"
    OAUTH_PROVIDER_ERROR = "oauth_provider_error"
    
    # Profile events
    PROFILE_UPDATED = "profile_updated"
    EMAIL_CHANGED = "email_changed"
    ACCOUNT_DELETED = "account_deleted"
    DATA_EXPORTED = "data_exported"
    
    # Admin events
    ADMIN_ACTION = "admin_action"
    USER_SUSPENDED = "user_suspended"
    USER_UNSUSPENDED = "user_unsuspended"
    BULK_OPERATION = "bulk_operation"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure."""
    event_type: AuditEventType
    event_result: str  # success, failure, error
    severity: AuditSeverity = AuditSeverity.MEDIUM
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class AuditLogger:
    """
    Comprehensive audit logging service.
    
    Logs authentication events, security incidents, and user activities
    for compliance, security monitoring, and forensic analysis.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        
        # Configure event severity mapping
        self._severity_mapping = {
            AuditEventType.LOGIN_FAILURE: AuditSeverity.MEDIUM,
            AuditEventType.REGISTRATION_FAILURE: AuditSeverity.LOW,
            AuditEventType.PASSWORD_RESET_FAILURE: AuditSeverity.MEDIUM,
            AuditEventType.RATE_LIMIT_EXCEEDED: AuditSeverity.HIGH,
            AuditEventType.ACCOUNT_LOCKED: AuditSeverity.HIGH,
            AuditEventType.CSRF_VIOLATION: AuditSeverity.HIGH,
            AuditEventType.SUSPICIOUS_ACTIVITY: AuditSeverity.CRITICAL,
            AuditEventType.SESSION_LIMIT_EXCEEDED: AuditSeverity.MEDIUM,
            AuditEventType.OAUTH_PROVIDER_ERROR: AuditSeverity.MEDIUM,
            AuditEventType.ACCOUNT_DELETED: AuditSeverity.HIGH,
            AuditEventType.ADMIN_ACTION: AuditSeverity.HIGH,
        }
    
    def log_event(
        self,
        event_type: Union[AuditEventType, str],
        event_result: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: Optional[AuditSeverity] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (AuditEventType or string)
            event_result: Result of the event (success, failure, error)
            user_id: User ID associated with event
            session_id: Session ID associated with event
            ip_address: Client IP address
            user_agent: Client user agent
            resource: Resource being accessed
            details: Additional event details
            metadata: Additional metadata
            severity: Event severity (auto-detected if not provided)
            correlation_id: Correlation ID for tracking related events
            
        Returns:
            Audit log entry ID
        """
        try:
            # Convert string to enum if needed
            if isinstance(event_type, str):
                try:
                    event_type = AuditEventType(event_type)
                except ValueError:
                    logger.warning(f"Unknown audit event type: {event_type}")
                    event_type = AuditEventType.SUSPICIOUS_ACTIVITY
            
            # Auto-detect severity if not provided
            if severity is None:
                severity = self._severity_mapping.get(event_type, AuditSeverity.MEDIUM)
            
            # Generate correlation ID if not provided
            if correlation_id is None:
                correlation_id = str(uuid.uuid4())
            
            # Create audit event
            audit_event = AuditEvent(
                event_type=event_type,
                event_result=event_result,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource=resource,
                details=details or {},
                metadata=metadata or {},
                correlation_id=correlation_id
            )
            
            # Store in database
            log_entry_id = self._store_audit_log(audit_event)
            
            # Log to application logger based on severity
            self._log_to_application_logger(audit_event, log_entry_id)
            
            # Trigger security alerts for critical events
            if severity == AuditSeverity.CRITICAL:
                self._trigger_security_alert(audit_event, log_entry_id)
            
            return log_entry_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            # Still log to application logger as fallback
            logger.warning(f"Audit event fallback: {event_type.value if isinstance(event_type, AuditEventType) else event_type}")
            raise
    
    def log_authentication_event(
        self,
        event_type: AuditEventType,
        success: bool,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Log authentication-specific events.
        
        Args:
            event_type: Authentication event type
            success: Whether the authentication was successful
            user_id: User ID
            email: User email
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session ID
            provider: OAuth provider (if applicable)
            error_message: Error message for failed attempts
            **kwargs: Additional metadata
            
        Returns:
            Audit log entry ID
        """
        result = "success" if success else "failure"
        
        details = {}
        if email:
            details["email"] = email
        if provider:
            details["provider"] = provider
        if error_message:
            details["error_message"] = error_message
        
        metadata = {
            "event_category": "authentication",
            **kwargs
        }
        
        return self.log_event(
            event_type=event_type,
            event_result=result,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="authentication",
            details=details,
            metadata=metadata
        )
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.HIGH,
        **kwargs
    ) -> str:
        """
        Log security-specific events.
        
        Args:
            event_type: Security event type
            description: Event description
            user_id: User ID (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
            severity: Event severity
            **kwargs: Additional metadata
            
        Returns:
            Audit log entry ID
        """
        details = {
            "description": description,
            **kwargs
        }
        
        metadata = {
            "event_category": "security"
        }
        
        return self.log_event(
            event_type=event_type,
            event_result="detected",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource="security",
            details=details,
            metadata=metadata,
            severity=severity
        )
    
    def log_admin_action(
        self,
        action: str,
        admin_user_id: str,
        target_user_id: Optional[str] = None,
        resource: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Log administrative actions.
        
        Args:
            action: Action performed
            admin_user_id: ID of admin performing action
            target_user_id: ID of user being acted upon
            resource: Resource being modified
            changes: Changes made
            ip_address: Admin IP address
            user_agent: Admin user agent
            **kwargs: Additional metadata
            
        Returns:
            Audit log entry ID
        """
        details = {
            "action": action,
            "admin_user_id": admin_user_id,
        }
        
        if target_user_id:
            details["target_user_id"] = target_user_id
        if changes:
            details["changes"] = changes
        
        metadata = {
            "event_category": "admin",
            **kwargs
        }
        
        return self.log_event(
            event_type=AuditEventType.ADMIN_ACTION,
            event_result="success",
            user_id=admin_user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource or "admin",
            details=details,
            metadata=metadata,
            severity=AuditSeverity.HIGH
        )
    
    def search_audit_logs(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search audit logs with filters.
        
        Args:
            event_types: List of event types to filter by
            user_id: User ID to filter by
            ip_address: IP address to filter by
            start_date: Start date for time range
            end_date: End date for time range
            severity: Severity level to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of audit log entries
        """
        try:
            query = self.db.query(AuthAuditLog)
            
            # Apply filters
            if event_types:
                event_type_values = [et.value for et in event_types]
                query = query.filter(AuthAuditLog.event_type.in_(event_type_values))
            
            if user_id:
                # Search in user_id field
                query = query.filter(AuthAuditLog.supabase_user_id == user_id)
            
            if ip_address:
                query = query.filter(AuthAuditLog.ip_address == ip_address)
            
            if start_date:
                query = query.filter(AuthAuditLog.created_at >= start_date)
            
            if end_date:
                query = query.filter(AuthAuditLog.created_at <= end_date)
            
            if severity:
                # For SQLite compatibility, we'll search in the metadata text
                query = query.filter(AuthAuditLog.metadata.like(f'%"severity": "{severity.value}"%'))
            
            # Apply pagination and ordering
            query = query.order_by(AuthAuditLog.created_at.desc())
            query = query.offset(offset).limit(limit)
            
            # Execute query and format results
            logs = query.all()
            
            return [
                {
                    "id": log.id,
                    "event_type": log.event_type,
                    "event_result": log.event_result,
                    "created_at": log.created_at.isoformat(),
                    "user_id": log.supabase_user_id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "metadata": json.loads(log.metadata) if log.metadata else {}
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to search audit logs: {str(e)}")
            return []
    
    def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Activity summary
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            logs = self.search_audit_logs(
                user_id=user_id,
                start_date=start_date,
                limit=1000
            )
            
            # Analyze activity
            activity_summary = {
                "user_id": user_id,
                "period_days": days,
                "total_events": len(logs),
                "event_types": {},
                "login_attempts": 0,
                "failed_logins": 0,
                "last_activity": None,
                "unique_ips": set(),
                "security_events": 0
            }
            
            for log in logs:
                event_type = log["event_type"]
                activity_summary["event_types"][event_type] = activity_summary["event_types"].get(event_type, 0) + 1
                
                if event_type in ["login_success", "login_failure"]:
                    activity_summary["login_attempts"] += 1
                    if event_type == "login_failure":
                        activity_summary["failed_logins"] += 1
                
                if log["ip_address"]:
                    activity_summary["unique_ips"].add(log["ip_address"])
                
                if event_type in ["rate_limit_exceeded", "csrf_violation", "suspicious_activity"]:
                    activity_summary["security_events"] += 1
                
                if not activity_summary["last_activity"] or log["created_at"] > activity_summary["last_activity"]:
                    activity_summary["last_activity"] = log["created_at"]
            
            activity_summary["unique_ips"] = list(activity_summary["unique_ips"])
            
            return activity_summary
            
        except Exception as e:
            logger.error(f"Failed to get user activity summary: {str(e)}")
            return {"error": str(e)}
    
    def _store_audit_log(self, audit_event: AuditEvent) -> str:
        """Store audit event in database."""
        try:
            # Convert event to AuthAuditLog model
            log_entry = AuthAuditLog.create_log(
                event_type=audit_event.event_type.value,
                event_result=audit_event.event_result,
                supabase_user_id=audit_event.user_id,
                ip_address=audit_event.ip_address,
                user_agent=audit_event.user_agent,
                metadata={
                    "severity": audit_event.severity.value,
                    "session_id": audit_event.session_id,
                    "resource": audit_event.resource,
                    "details": audit_event.details or {},
                    "correlation_id": audit_event.correlation_id,
                    **(audit_event.metadata or {})
                }
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            return log_entry.id
            
        except Exception as e:
            logger.error(f"Failed to store audit log: {str(e)}")
            self.db.rollback()
            raise
    
    def _log_to_application_logger(self, audit_event: AuditEvent, log_id: str):
        """Log event to application logger."""
        try:
            log_data = {
                "audit_id": log_id,
                "event_type": audit_event.event_type.value,
                "severity": audit_event.severity.value,
                "user_id": audit_event.user_id,
                "ip_address": audit_event.ip_address,
                "correlation_id": audit_event.correlation_id
            }
            
            log_message = f"Audit: {audit_event.event_type.value} - {audit_event.event_result}"
            
            if audit_event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                logger.warning(f"{log_message} | {json.dumps(log_data)}")
            else:
                logger.info(f"{log_message} | {json.dumps(log_data)}")
                
        except Exception as e:
            logger.error(f"Failed to log to application logger: {str(e)}")
    
    def _trigger_security_alert(self, audit_event: AuditEvent, log_id: str):
        """Trigger security alert for critical events."""
        try:
            alert_data = {
                "audit_id": log_id,
                "event_type": audit_event.event_type.value,
                "severity": "CRITICAL",
                "user_id": audit_event.user_id,
                "ip_address": audit_event.ip_address,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": audit_event.details
            }
            
            # Log critical alert
            logger.critical(f"SECURITY ALERT: {json.dumps(alert_data)}")
            
            # Here you could integrate with external alerting systems:
            # - Send to SIEM
            # - Trigger webhook
            # - Send email/SMS alerts
            # - Create incident ticket
            
        except Exception as e:
            logger.error(f"Failed to trigger security alert: {str(e)}")


# Global audit logger instance
audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db: Session) -> AuditLogger:
    """
    Get audit logger instance.
    
    Args:
        db: Database session
        
    Returns:
        AuditLogger instance
    """
    return AuditLogger(db)


# Convenience functions for common audit events

def log_login_attempt(
    db: Session,
    success: bool,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_message: Optional[str] = None,
    provider: Optional[str] = None
) -> str:
    """Log login attempt."""
    audit_logger = get_audit_logger(db)
    event_type = AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
    
    return audit_logger.log_authentication_event(
        event_type=event_type,
        success=success,
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        error_message=error_message,
        provider=provider
    )


def log_security_incident(
    db: Session,
    incident_type: str,
    description: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.HIGH,
    **kwargs
) -> str:
    """Log security incident."""
    audit_logger = get_audit_logger(db)
    
    try:
        event_type = AuditEventType(incident_type)
    except ValueError:
        event_type = AuditEventType.SUSPICIOUS_ACTIVITY
    
    return audit_logger.log_security_event(
        event_type=event_type,
        description=description,
        user_id=user_id,
        ip_address=ip_address,
        severity=severity,
        **kwargs
    )