"""
Secure User Model with Field-Level Encryption

Example implementation showing how to protect sensitive user data.
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.models.encrypted_fields import EncryptedString, EncryptedText, HashedString


class SecureUser(BaseModel):
    """
    User model with encrypted sensitive fields.
    
    This demonstrates best practices for storing sensitive user data.
    """
    __tablename__ = "secure_users"
    
    # Basic fields (not encrypted)
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)
    
    # Password (hashed, not encrypted)
    password_hash = Column(String(255), nullable=False)
    
    # Name fields (encrypted for privacy)
    first_name = Column(EncryptedString(100), nullable=True)
    last_name = Column(EncryptedString(100), nullable=True)
    
    # Sensitive personal data (encrypted)
    phone_number = Column(EncryptedString(50), nullable=True)
    date_of_birth = Column(EncryptedString(20), nullable=True)  # Store as encrypted string
    
    # Government IDs (encrypted with searchable hash)
    ssn_encrypted = Column(EncryptedString(20), nullable=True, doc="Encrypted SSN")
    ssn_hash = Column(HashedString(64), nullable=True, index=True, doc="Hashed SSN for searching")
    
    passport_number_encrypted = Column(EncryptedString(50), nullable=True)
    passport_number_hash = Column(HashedString(64), nullable=True, index=True)
    
    # Address information (encrypted)
    street_address = Column(EncryptedText, nullable=True)
    city = Column(EncryptedString(100), nullable=True)
    state_province = Column(EncryptedString(100), nullable=True)
    postal_code = Column(EncryptedString(20), nullable=True)
    country = Column(String(2), nullable=True)  # ISO country code, not encrypted
    
    # Financial information (highly sensitive - encrypted)
    credit_card_last_four = Column(String(4), nullable=True)  # Only store last 4 digits
    bank_account_encrypted = Column(EncryptedString(255), nullable=True)
    
    # Account status (not encrypted)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="user", nullable=False)
    
    # Timestamps (not encrypted)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # IP tracking (hashed for privacy)
    last_login_ip_hash = Column(HashedString(64), nullable=True)
    registration_ip_hash = Column(HashedString(64), nullable=True)
    
    # Preferences (encrypted JSON)
    # sensitive_preferences = Column(EncryptedJSON, nullable=True)
    
    # Relationships
    sessions = relationship("SecureAuthSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def set_ssn(self, ssn: str):
        """Set SSN with both encrypted and hashed versions."""
        if ssn:
            self.ssn_encrypted = ssn  # Automatically encrypted by EncryptedString
            from app.models.encrypted_fields import create_searchable_hash
            self.ssn_hash = create_searchable_hash(ssn)
    
    def set_passport_number(self, passport_number: str):
        """Set passport number with both encrypted and hashed versions."""
        if passport_number:
            self.passport_number_encrypted = passport_number
            from app.models.encrypted_fields import create_searchable_hash
            self.passport_number_hash = create_searchable_hash(passport_number)
    
    def get_full_name(self) -> str:
        """Get decrypted full name."""
        # EncryptedString fields automatically decrypt when accessed
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.email.split("@")[0]
    
    def mask_sensitive_data(self) -> dict:
        """Return user data with sensitive fields masked."""
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name[:1] + "***" if self.first_name else None,
            "last_name": self.last_name[:1] + "***" if self.last_name else None,
            "phone_number": "***-***-" + self.phone_number[-4:] if self.phone_number else None,
            "has_ssn": bool(self.ssn_encrypted),
            "has_passport": bool(self.passport_number_encrypted),
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at
        }
    
    def __repr__(self):
        # Don't include sensitive data in repr
        return f"<SecureUser(id={self.id}, email={self.email}, role={self.role})>"


class SecureAuditLog(BaseModel):
    """
    Audit log with privacy protection.
    """
    __tablename__ = "secure_audit_logs"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    
    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    event_details = Column(EncryptedText, nullable=True)  # Encrypted details
    
    # Privacy-preserving IP tracking
    ip_address_hash = Column(HashedString(64), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)  # Not encrypted (less sensitive)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SecureAuditLog(id={self.id}, event={self.event_type}, user={self.user_id})>"