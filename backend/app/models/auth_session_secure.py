"""
Secure Authentication Session Model

This replaces the JWT-storing AuthSession with a stateless-friendly version.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SecureAuthSession(BaseModel):
    """
    Secure authentication session model for tracking user sessions.
    
    Manages session state WITHOUT storing JWT tokens (stateless design).
    """
    __tablename__ = "secure_auth_sessions"
    
    user_id = Column(
        String(36),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Foreign key to users table"
    )
    
    session_id = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique session identifier (stored in JWT)"
    )
    
    # Device and location tracking
    device_fingerprint = Column(
        String(255),
        nullable=True,
        doc="Device fingerprint for security tracking"
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
    
    # Session metadata
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
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
    
    # Session tracking
    last_activity_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Last activity timestamp"
    )
    
    # MFA status for this session
    mfa_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether MFA was verified for this session"
    )
    
    mfa_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When MFA was verified"
    )
    
    # Session preferences
    remember_me = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a remember-me session"
    )
    
    # Security tracking
    security_flags = Column(
        JSON,
        nullable=True,
        doc="Security flags and warnings for this session"
    )
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def invalidate(self, reason: str = "manual"):
        """Invalidate this session."""
        self.is_active = False
        self.invalidated_at = datetime.now(timezone.utc)
        self.invalidation_reason = reason
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now(timezone.utc)
    
    def verify_mfa(self):
        """Mark MFA as verified for this session."""
        self.mfa_verified = True
        self.mfa_verified_at = datetime.now(timezone.utc)
    
    def is_expired(self, max_idle_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity."""
        if not self.is_active:
            return True
        
        idle_time = datetime.now(timezone.utc) - self.last_activity_at
        return idle_time.total_seconds() > (max_idle_minutes * 60)
    
    def __repr__(self) -> str:
        return f"<SecureAuthSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"