"""
Audit Logging Models

SQLAlchemy models for audit logging and activity tracking including user actions
and system administrative changes for the Duolingo clone backend application.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import validates

from app.models.base import BaseModel
from app.models.encrypted_fields import HashedString, EncryptedText


class ActionType(str, Enum):
    """Enum for user action types."""
    LOGIN = "login"
    LOGOUT = "logout"
    LESSON_START = "lesson_start"
    LESSON_COMPLETE = "lesson_complete"
    LESSON_FAIL = "lesson_fail"
    EXERCISE_ATTEMPT = "exercise_attempt"
    COURSE_ENROLL = "course_enroll"
    PROFILE_UPDATE = "profile_update"
    ACHIEVEMENT_EARNED = "achievement_earned"
    HEART_LOST = "heart_lost"
    HEART_REFILL = "heart_refill"
    STREAK_UPDATE = "streak_update"
    XP_EARNED = "xp_earned"
    PASSWORD_CHANGE = "password_change"
    EMAIL_CHANGE = "email_change"
    SETTINGS_UPDATE = "settings_update"


class SystemActionType(str, Enum):
    """Enum for system administrative action types."""
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_SUSPEND = "user_suspend"
    USER_REACTIVATE = "user_reactivate"
    COURSE_CREATE = "course_create"
    COURSE_UPDATE = "course_update"
    COURSE_DELETE = "course_delete"
    LESSON_CREATE = "lesson_create"
    LESSON_UPDATE = "lesson_update"
    LESSON_DELETE = "lesson_delete"
    EXERCISE_CREATE = "exercise_create"
    EXERCISE_UPDATE = "exercise_update"
    EXERCISE_DELETE = "exercise_delete"
    ACHIEVEMENT_CREATE = "achievement_create"
    ACHIEVEMENT_UPDATE = "achievement_update"
    ACHIEVEMENT_DELETE = "achievement_delete"
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    DATABASE_MIGRATION = "database_migration"
    BULK_OPERATION = "bulk_operation"


class UserActivityLog(BaseModel):
    """
    User activity log model for tracking user actions.
    
    Captures all user interactions, actions, and activities for analytics,
    security monitoring, and user behavior analysis.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user who performed the action"
    )
    
    action_type = Column(
        String(30),
        nullable=False,
        index=True,
        doc="Type of action performed"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Human-readable description of the action"
    )
    
    ip_address_hash = Column(
        HashedString(64),  # SHA-256 hash length
        nullable=True,
        doc="Hashed IP address for privacy protection"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string from the request"
    )
    
    session_id = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Session identifier for grouping related actions"
    )
    
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Course context for the action (if applicable)"
    )
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Lesson context for the action (if applicable)"
    )
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Exercise context for the action (if applicable)"
    )
    
    success = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the action was successful"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if action failed"
    )
    
    duration_ms = Column(
        Integer,
        nullable=True,
        doc="Duration of the action in milliseconds"
    )
    
    # Additional context data stored as JSON-like text for SQLite compatibility
    action_metadata = Column(
        Text,
        nullable=True,
        doc="Additional action metadata (JSON format)"
    )
    
    # Performance and filtering indexes
    __table_args__ = (
        Index('idx_user_activity_user_time', 'user_id', 'created_at'),
        Index('idx_user_activity_action_time', 'action_type', 'created_at'),
        Index('idx_user_activity_session', 'session_id', 'created_at'),
        Index('idx_user_activity_course_time', 'course_id', 'created_at'),
        CheckConstraint(duration_ms >= 0, name='check_duration_non_negative'),
    )
    
    @validates('action_type')
    def validate_action_type(self, key, value):
        """Validate action type is valid."""
        if value not in [action.value for action in ActionType]:
            raise ValueError(f"Invalid action type: {value}")
        return value
    
    @validates('ip_address_hash')
    def validate_ip_address_hash(self, key, value):
        """Validate IP address hash."""
        # HashedString handles hashing automatically
        # Just return the value
        return value
    
    @validates('duration_ms')
    def validate_duration(self, key, value):
        """Validate duration is reasonable."""
        if value is not None and (value < 0 or value > 3600000):  # Max 1 hour
            raise ValueError("Duration must be between 0 and 3600000 ms")
        return value
    
    def get_metadata_dict(self) -> dict:
        """
        Get metadata as dictionary.
        
        Returns:
            Parsed metadata dictionary or empty dict if none
        """
        if not self.action_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.action_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata_dict(self, metadata_dict: dict) -> None:
        """
        Set metadata from dictionary.
        
        Args:
            metadata_dict: Dictionary to store as metadata
        """
        if metadata_dict:
            import json
            self.action_metadata = json.dumps(metadata_dict)
        else:
            self.action_metadata = None
    
    @classmethod
    def log_action(cls, user_id: str, action_type: str, description: str = None,
                   ip_address: str = None, user_agent: str = None, 
                   session_id: str = None, course_id: str = None,
                   lesson_id: str = None, exercise_id: str = None,
                   success: bool = True, error_message: str = None,
                   duration_ms: int = None, metadata: dict = None) -> 'UserActivityLog':
        """
        Create a new user activity log entry.
        
        Args:
            user_id: ID of the user
            action_type: Type of action performed
            description: Human-readable description
            ip_address: IP address of the user
            user_agent: User agent string
            session_id: Session identifier
            course_id: Course context
            lesson_id: Lesson context
            exercise_id: Exercise context
            success: Whether action was successful
            error_message: Error message if failed
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
            
        Returns:
            New UserActivityLog instance
        """
        log_entry = cls(
            user_id=user_id,
            action_type=action_type,
            description=description,
            ip_address_hash=ip_address,  # HashedString will hash it automatically
            user_agent=user_agent,
            session_id=session_id,
            course_id=course_id,
            lesson_id=lesson_id,
            exercise_id=exercise_id,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        if metadata:
            log_entry.set_metadata_dict(metadata)
        
        return log_entry
    
    def __repr__(self) -> str:
        return f"<UserActivityLog(user_id={self.user_id}, action={self.action_type}, success={self.success})>"


class SystemAuditLog(BaseModel):
    """
    System audit log model for tracking administrative actions.
    
    Records all administrative and system-level changes for compliance,
    security auditing, and change tracking.
    """
    
    admin_user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the admin user who performed the action (NULL for system actions)"
    )
    
    action_type = Column(
        String(30),
        nullable=False,
        index=True,
        doc="Type of administrative action performed"
    )
    
    resource_type = Column(
        String(50),
        nullable=False,
        doc="Type of resource affected (user, course, lesson, etc.)"
    )
    
    resource_id = Column(
        String(36),
        nullable=True,
        index=True,
        doc="ID of the affected resource"
    )
    
    description = Column(
        Text,
        nullable=False,
        doc="Description of the administrative action"
    )
    
    ip_address_hash = Column(
        HashedString(64),
        nullable=True,
        doc="Hashed IP address for privacy protection"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string from the request"
    )
    
    success = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the action was successful"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if action failed"
    )
    
    # Store before/after state for change tracking (encrypted for privacy)
    before_state = Column(
        EncryptedText,
        nullable=True,
        doc="State before the change (JSON format, encrypted)"
    )
    
    after_state = Column(
        EncryptedText,
        nullable=True,
        doc="State after the change (JSON format, encrypted)"
    )
    
    # Additional context data
    audit_metadata = Column(
        Text,
        nullable=True,
        doc="Additional audit metadata (JSON format)"
    )
    
    # Performance and filtering indexes
    __table_args__ = (
        Index('idx_system_audit_admin_time', 'admin_user_id', 'created_at'),
        Index('idx_system_audit_action_time', 'action_type', 'created_at'),
        Index('idx_system_audit_resource', 'resource_type', 'resource_id', 'created_at'),
    )
    
    @validates('action_type')
    def validate_action_type(self, key, value):
        """Validate action type is valid."""
        if value not in [action.value for action in SystemActionType]:
            raise ValueError(f"Invalid system action type: {value}")
        return value
    
    @validates('resource_type')
    def validate_resource_type(self, key, value):
        """Validate resource type."""
        if not value or str(value).strip() == '':
            raise ValueError("Resource type is required")
        
        value = str(value).strip().lower()
        if len(value) > 50:
            raise ValueError("Resource type must be 50 characters or less")
        
        return value
    
    @validates('description')
    def validate_description(self, key, value):
        """Validate description."""
        if not value or str(value).strip() == '':
            raise ValueError("Description is required")
        
        value = str(value).strip()
        if len(value) < 5:
            raise ValueError("Description must be at least 5 characters")
        
        return value
    
    def get_before_state_dict(self) -> dict:
        """Get before state as dictionary."""
        if not self.before_state:
            return {}
        
        try:
            import json
            return json.loads(self.before_state)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_before_state_dict(self, state_dict: dict) -> None:
        """Set before state from dictionary."""
        if state_dict:
            import json
            self.before_state = json.dumps(state_dict)
        else:
            self.before_state = None
    
    def get_after_state_dict(self) -> dict:
        """Get after state as dictionary."""
        if not self.after_state:
            return {}
        
        try:
            import json
            return json.loads(self.after_state)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_after_state_dict(self, state_dict: dict) -> None:
        """Set after state from dictionary."""
        if state_dict:
            import json
            self.after_state = json.dumps(state_dict)
        else:
            self.after_state = None
    
    def get_metadata_dict(self) -> dict:
        """Get metadata as dictionary."""
        if not self.audit_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.audit_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata_dict(self, metadata_dict: dict) -> None:
        """Set metadata from dictionary."""
        if metadata_dict:
            import json
            self.audit_metadata = json.dumps(metadata_dict)
        else:
            self.audit_metadata = None
    
    @classmethod
    def log_admin_action(cls, action_type: str, resource_type: str, description: str,
                        admin_user_id: str = None, resource_id: str = None,
                        ip_address: str = None, user_agent: str = None,
                        success: bool = True, error_message: str = None,
                        before_state: dict = None, after_state: dict = None,
                        metadata: dict = None) -> 'SystemAuditLog':
        """
        Create a new system audit log entry.
        
        Args:
            action_type: Type of administrative action
            resource_type: Type of resource affected
            description: Description of the action
            admin_user_id: ID of admin user (optional for system actions)
            resource_id: ID of affected resource
            ip_address: IP address of admin
            user_agent: User agent string
            success: Whether action was successful
            error_message: Error message if failed
            before_state: State before the change
            after_state: State after the change
            metadata: Additional metadata
            
        Returns:
            New SystemAuditLog instance
        """
        log_entry = cls(
            admin_user_id=admin_user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        if before_state:
            log_entry.set_before_state_dict(before_state)
        
        if after_state:
            log_entry.set_after_state_dict(after_state)
        
        if metadata:
            log_entry.set_metadata_dict(metadata)
        
        return log_entry
    
    def __repr__(self) -> str:
        return f"<SystemAuditLog(admin_id={self.admin_user_id}, action={self.action_type}, resource={self.resource_type})>"