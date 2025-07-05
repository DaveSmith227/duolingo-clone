"""
Authentication Models

SQLAlchemy models for Supabase authentication integration,
session management, and audit logging.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import json

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class SupabaseUser(BaseModel):
    """
    Supabase user model for syncing with Supabase Auth.
    
    Stores Supabase user information and maintains sync between
    Supabase Auth and application database.
    """
    
    supabase_id = Column(
        String(36),  # Supabase UUID
        unique=True,
        nullable=False,
        index=True,
        doc="Supabase user ID (UUID)"
    )
    
    app_user_id = Column(
        String(36),  # Application user UUID
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Foreign key to application users table"
    )
    
    email = Column(
        String(255),
        nullable=False,
        index=True,
        doc="User email from Supabase Auth"
    )
    
    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Email verification status from Supabase"
    )
    
    phone = Column(
        String(50),
        nullable=True,
        doc="Phone number from Supabase Auth"
    )
    
    phone_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Phone verification status from Supabase"
    )
    
    provider = Column(
        String(50),
        nullable=False,
        default='email',
        doc="Authentication provider (email, google, facebook, etc.)"
    )
    
    last_sign_in_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last sign-in timestamp from Supabase"
    )
    
    user_metadata = Column(
        JSON,
        nullable=True,
        doc="User metadata from Supabase Auth"
    )
    
    app_metadata = Column(
        JSON,
        nullable=True,
        doc="Application metadata from Supabase Auth"
    )
    
    sync_status = Column(
        String(20),
        default='synced',
        nullable=False,
        doc="Sync status (synced, pending, error)"
    )
    
    last_sync_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Last successful sync timestamp"
    )
    
    sync_error = Column(
        Text,
        nullable=True,
        doc="Last sync error message if any"
    )
    
    # Relationships
    user = relationship(
        "User",
        foreign_keys=[app_user_id],
        doc="Application user associated with this Supabase user"
    )
    
    auth_sessions = relationship(
        "AuthSession",
        back_populates="supabase_user",
        cascade="all, delete-orphan",
        doc="Authentication sessions for this user"
    )
    
    auth_logs = relationship(
        "AuthAuditLog",
        back_populates="supabase_user",
        cascade="all, delete-orphan",
        doc="Authentication audit logs for this user"
    )
    
    @validates('sync_status')
    def validate_sync_status(self, key, status):
        """Validate sync status."""
        valid_statuses = ['synced', 'pending', 'error']
        if status not in valid_statuses:
            raise ValueError(f"Sync status must be one of: {', '.join(valid_statuses)}")
        return status
    
    @validates('provider')
    def validate_provider(self, key, provider):
        """Validate authentication provider."""
        valid_providers = ['email', 'google', 'facebook', 'apple', 'github', 'twitter']
        if provider not in valid_providers:
            raise ValueError(f"Provider must be one of: {', '.join(valid_providers)}")
        return provider
    
    def mark_sync_success(self):
        """Mark successful sync."""
        self.sync_status = 'synced'
        self.last_sync_at = datetime.now(timezone.utc)
        self.sync_error = None
    
    def mark_sync_error(self, error_message: str):
        """Mark sync error."""
        self.sync_status = 'error'
        self.sync_error = error_message
    
    def update_from_supabase(self, supabase_user_data: Dict[str, Any]):
        """
        Update user data from Supabase Auth user object.
        
        Args:
            supabase_user_data: User data from Supabase Auth
        """
        if 'email' in supabase_user_data:
            self.email = supabase_user_data['email']
        
        if 'email_confirmed_at' in supabase_user_data:
            self.email_verified = supabase_user_data['email_confirmed_at'] is not None
        
        if 'phone' in supabase_user_data:
            self.phone = supabase_user_data['phone']
        
        if 'phone_confirmed_at' in supabase_user_data:
            self.phone_verified = supabase_user_data['phone_confirmed_at'] is not None
        
        if 'last_sign_in_at' in supabase_user_data:
            if supabase_user_data['last_sign_in_at']:
                self.last_sign_in_at = datetime.fromisoformat(
                    supabase_user_data['last_sign_in_at'].replace('Z', '+00:00')
                )
        
        if 'user_metadata' in supabase_user_data:
            self.user_metadata = supabase_user_data['user_metadata']
        
        if 'app_metadata' in supabase_user_data:
            self.app_metadata = supabase_user_data['app_metadata']
        
        # Extract primary provider
        if 'identities' in supabase_user_data and supabase_user_data['identities']:
            # Use the first identity as primary provider
            self.provider = supabase_user_data['identities'][0].get('provider', 'email')
    
    def __repr__(self) -> str:
        return f"<SupabaseUser(id={self.id}, supabase_id={self.supabase_id}, email={self.email})>"


class AuthSession(BaseModel):
    """
    Authentication session model for tracking user sessions.
    
    Manages JWT sessions, refresh tokens, and session state
    for authenticated users.
    """
    
    supabase_user_id = Column(
        String(36),
        ForeignKey('supabase_users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Foreign key to supabase_users table"
    )
    
    session_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique session identifier"
    )
    
    access_token = Column(
        Text,
        nullable=False,
        doc="JWT access token"
    )
    
    refresh_token = Column(
        Text,
        nullable=True,
        doc="JWT refresh token"
    )
    
    token_type = Column(
        String(20),
        default='bearer',
        nullable=False,
        doc="Token type (usually 'bearer')"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Access token expiration time"
    )
    
    refresh_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Refresh token expiration time"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string from session creation"
    )
    
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address from session creation"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether session is active"
    )
    
    invalidated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Session invalidation timestamp"
    )
    
    invalidation_reason = Column(
        String(100),
        nullable=True,
        doc="Reason for session invalidation"
    )
    
    # Relationships
    supabase_user = relationship(
        "SupabaseUser",
        back_populates="auth_sessions",
        doc="Supabase user associated with this session"
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return self.expires_at <= datetime.now(timezone.utc)
    
    @property
    def is_refresh_expired(self) -> bool:
        """Check if refresh token is expired."""
        if not self.refresh_expires_at:
            return False
        return self.refresh_expires_at <= datetime.now(timezone.utc)
    
    @property
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return (
            self.is_active and 
            not self.is_expired and 
            self.invalidated_at is None
        )
    
    def invalidate(self, reason: str = 'manual'):
        """
        Invalidate the session.
        
        Args:
            reason: Reason for invalidation
        """
        self.is_active = False
        self.invalidated_at = datetime.now(timezone.utc)
        self.invalidation_reason = reason
    
    def extend_expiration(self, seconds: int):
        """
        Extend session expiration.
        
        Args:
            seconds: Number of seconds to extend
        """
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    
    def __repr__(self) -> str:
        return f"<AuthSession(id={self.id}, session_id={self.session_id}, active={self.is_active})>"


class AuthAuditLog(BaseModel):
    """
    Authentication audit log model for security tracking.
    
    Records all authentication events for security auditing,
    compliance, and troubleshooting purposes.
    """
    
    supabase_user_id = Column(
        String(36),
        ForeignKey('supabase_users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc="Foreign key to supabase_users table (null for anonymous events)"
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Authentication event type"
    )
    
    event_result = Column(
        String(20),
        nullable=False,
        doc="Event result (success, failure, error)"
    )
    
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        index=True,
        doc="IP address of the request"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string"
    )
    
    provider = Column(
        String(50),
        nullable=True,
        doc="Authentication provider used"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        index=True,
        doc="Session ID if applicable"
    )
    
    error_message = Column(
        Text,
        nullable=True,
        doc="Error message if event failed"
    )
    
    event_metadata = Column(
        JSON,
        nullable=True,
        doc="Additional event metadata"
    )
    
    risk_score = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Calculated risk score for the event (0-100)"
    )
    
    # Relationships
    supabase_user = relationship(
        "SupabaseUser",
        back_populates="auth_logs",
        doc="Supabase user associated with this log entry"
    )
    
    @validates('event_type')
    def validate_event_type(self, key, event_type):
        """Validate authentication event type."""
        valid_types = [
            'sign_up', 'sign_in', 'sign_out', 'password_reset', 'password_change',
            'email_verification', 'phone_verification', 'oauth_link', 'oauth_unlink',
            'session_refresh', 'session_invalidate', 'account_delete', 'profile_update'
        ]
        if event_type not in valid_types:
            raise ValueError(f"Event type must be one of: {', '.join(valid_types)}")
        return event_type
    
    @validates('event_result')
    def validate_event_result(self, key, result):
        """Validate event result."""
        valid_results = ['success', 'failure', 'error']
        if result not in valid_results:
            raise ValueError(f"Event result must be one of: {', '.join(valid_results)}")
        return result
    
    @validates('risk_score')
    def validate_risk_score(self, key, score):
        """Validate risk score."""
        if not (0 <= score <= 100):
            raise ValueError("Risk score must be between 0 and 100")
        return score
    
    @classmethod
    def create_log(cls, event_type: str, event_result: str, **kwargs) -> 'AuthAuditLog':
        """
        Create authentication audit log entry.
        
        Args:
            event_type: Type of authentication event
            event_result: Result of the event
            **kwargs: Additional fields
            
        Returns:
            AuthAuditLog instance
        """
        return cls(
            event_type=event_type,
            event_result=event_result,
            **kwargs
        )
    
    def __repr__(self) -> str:
        return f"<AuthAuditLog(id={self.id}, event_type={self.event_type}, result={self.event_result})>"