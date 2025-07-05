"""
Multi-Factor Authentication (MFA) database models.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index, Integer
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class MFASettings(Base):
    """User MFA settings and configuration."""
    __tablename__ = "mfa_settings"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    
    # TOTP settings
    totp_secret = Column(String, nullable=True, doc="Encrypted TOTP secret key")
    
    # MFA status
    is_enabled = Column(Boolean, default=False, nullable=False)
    enabled_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="mfa_settings")
    
    def __repr__(self):
        return f"<MFASettings(user_id={self.user_id}, enabled={self.is_enabled})>"


class MFABackupCodes(Base):
    """Backup codes for MFA recovery."""
    __tablename__ = "mfa_backup_codes"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Code information
    code_hash = Column(String, nullable=False, doc="SHA256 hash of the backup code")
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    used_ip = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, doc="Optional expiration for backup codes")
    
    # Relationships
    user = relationship("User", back_populates="mfa_backup_codes")
    
    def __repr__(self):
        return f"<MFABackupCode(user_id={self.user_id}, used={self.is_used})>"


class MFALog(Base):
    """Audit log for MFA events."""
    __tablename__ = "mfa_logs"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Event details
    event_type = Column(String, nullable=False, doc="Type of MFA event (enable, disable, verify, etc.)")
    success = Column(Boolean, nullable=False)
    method = Column(String, nullable=True, doc="MFA method used (totp, backup_code)")
    
    # Request information
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    
    # Additional details
    details = Column(Text, nullable=True, doc="JSON string of additional event details")
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<MFALog(user_id={self.user_id}, event={self.event_type}, success={self.success})>"


class MFAChallenge(Base):
    """Temporary MFA challenge tokens for login flow."""
    __tablename__ = "mfa_challenges"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    challenge_token = Column(String, unique=True, nullable=False, index=True)
    
    # Challenge status
    is_verified = Column(Boolean, default=False, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    
    # Request information
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_mfa_challenge_token', 'challenge_token'),
        Index('idx_mfa_challenge_expiry', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<MFAChallenge(user_id={self.user_id}, verified={self.is_verified})>"