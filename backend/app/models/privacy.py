"""
Privacy & Consent Management Models

SQLAlchemy models for privacy notices, user consent tracking, and GDPR compliance
for the Duolingo clone backend application.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
import json

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class ConsentType(str, Enum):
    """Enum for consent types."""
    PRIVACY_POLICY = "privacy_policy"
    TERMS_OF_SERVICE = "terms_of_service" 
    DATA_PROCESSING = "data_processing"
    MARKETING_EMAILS = "marketing_emails"
    ANALYTICS_COOKIES = "analytics_cookies"
    FUNCTIONAL_COOKIES = "functional_cookies"
    ADVERTISING_COOKIES = "advertising_cookies"
    THIRD_PARTY_SHARING = "third_party_sharing"
    LOCATION_DATA = "location_data"
    PROFILE_VISIBILITY = "profile_visibility"


class ConsentStatus(str, Enum):
    """Enum for consent status values."""
    PENDING = "pending"
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class PrivacyNotice(BaseModel):
    """
    Privacy notice model for tracking privacy policy versions.
    
    Stores privacy notices and terms of service with version control
    for GDPR compliance and consent management.
    """
    
    notice_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of privacy notice (privacy_policy, terms_of_service, etc.)"
    )
    
    version = Column(
        String(20),
        nullable=False,
        doc="Version number of the notice (e.g., '1.0', '2.1')"
    )
    
    title = Column(
        String(200),
        nullable=False,
        doc="Human-readable title of the notice"
    )
    
    content = Column(
        Text,
        nullable=False,
        doc="Full text content of the privacy notice"
    )
    
    content_html = Column(
        Text,
        nullable=True,
        doc="HTML formatted version of the content"
    )
    
    summary = Column(
        Text,
        nullable=True,
        doc="Brief summary of key points"
    )
    
    language_code = Column(
        String(10),
        default='en',
        nullable=False,
        doc="Language code for the notice (e.g., 'en', 'es', 'fr')"
    )
    
    effective_date = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Date when this notice becomes effective"
    )
    
    expiry_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date when this notice expires (optional)"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this notice is currently active"
    )
    
    is_current = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the current version for this notice type"
    )
    
    requires_consent = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether explicit user consent is required for this notice"
    )
    
    # Metadata for change tracking
    change_summary = Column(
        Text,
        nullable=True,
        doc="Summary of changes from previous version"
    )
    
    created_by = Column(
        String(36),
        nullable=True,
        doc="ID of user who created this notice"
    )
    
    approved_by = Column(
        String(36),
        nullable=True,
        doc="ID of user who approved this notice"
    )
    
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when notice was approved"
    )
    
    # Relationships
    consent_records = relationship(
        "UserConsent",
        back_populates="privacy_notice",
        cascade="all, delete-orphan",
        doc="User consent records for this notice"
    )
    
    @validates('notice_type')
    def validate_notice_type(self, key, notice_type):
        """Validate notice type."""
        valid_types = [consent.value for consent in ConsentType]
        if notice_type not in valid_types:
            raise ValueError(f"Notice type must be one of: {', '.join(valid_types)}")
        return notice_type
    
    @validates('version')
    def validate_version(self, key, version):
        """Validate version format."""
        if not version or not version.strip():
            raise ValueError("Version is required")
        
        # Basic version format validation (e.g., "1.0", "2.1.3")
        import re
        if not re.match(r'^\d+(\.\d+)*$', version.strip()):
            raise ValueError("Version must be in format like '1.0' or '2.1.3'")
        
        return version.strip()
    
    @validates('language_code')
    def validate_language_code(self, key, language_code):
        """Validate language code format."""
        if not language_code:
            return 'en'
        
        # Basic language code validation (ISO 639-1 or locale format)
        import re
        if not re.match(r'^[a-z]{2}(-[A-Z]{2})?$', language_code):
            raise ValueError("Language code must be in format 'en' or 'en-US'")
        
        return language_code
    
    def is_effective(self) -> bool:
        """Check if notice is currently effective."""
        now = datetime.now(timezone.utc)
        
        if not self.is_active:
            return False
        
        if self.effective_date > now:
            return False
        
        if self.expiry_date and self.expiry_date <= now:
            return False
        
        return True
    
    def get_content_dict(self) -> Dict[str, Any]:
        """Get structured content information."""
        return {
            "notice_type": self.notice_type,
            "version": self.version,
            "title": self.title,
            "content": self.content,
            "content_html": self.content_html,
            "summary": self.summary,
            "language_code": self.language_code,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "requires_consent": self.requires_consent,
            "is_current": self.is_current
        }
    
    def __repr__(self) -> str:
        return f"<PrivacyNotice(type={self.notice_type}, version={self.version}, current={self.is_current})>"


class UserConsent(BaseModel):
    """
    User consent model for tracking privacy and data processing consent.
    
    Records user consent for privacy notices, data processing activities,
    and other consent-requiring features with full audit trail.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user giving consent"
    )
    
    privacy_notice_id = Column(
        String(36),
        ForeignKey("privacy_notices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the privacy notice being consented to"
    )
    
    consent_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of consent being given"
    )
    
    consent_status = Column(
        String(20),
        default=ConsentStatus.PENDING.value,
        nullable=False,
        doc="Current status of the consent"
    )
    
    consent_given_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when consent was given"
    )
    
    consent_withdrawn_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when consent was withdrawn"
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Consent expiration timestamp (if applicable)"
    )
    
    # Consent context
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address when consent was given"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string when consent was given"
    )
    
    consent_method = Column(
        String(50),
        nullable=True,
        doc="Method of consent (web_form, api, email_confirmation, etc.)"
    )
    
    consent_evidence = Column(
        Text,
        nullable=True,
        doc="Evidence of consent (form data, checkbox states, etc.) as JSON"
    )
    
    # Additional metadata
    purpose_description = Column(
        Text,
        nullable=True,
        doc="Description of the purpose for which consent was requested"
    )
    
    data_categories = Column(
        Text,
        nullable=True,
        doc="Categories of data covered by this consent (JSON array)"
    )
    
    processing_activities = Column(
        Text,
        nullable=True,
        doc="Processing activities covered by this consent (JSON array)"
    )
    
    third_parties = Column(
        Text,
        nullable=True,
        doc="Third parties that may process data under this consent (JSON array)"
    )
    
    withdrawal_reason = Column(
        Text,
        nullable=True,
        doc="Reason for consent withdrawal (if applicable)"
    )
    
    # Relationships
    privacy_notice = relationship(
        "PrivacyNotice",
        back_populates="consent_records",
        doc="Privacy notice associated with this consent"
    )
    
    @validates('consent_type')
    def validate_consent_type(self, key, consent_type):
        """Validate consent type."""
        valid_types = [consent.value for consent in ConsentType]
        if consent_type not in valid_types:
            raise ValueError(f"Consent type must be one of: {', '.join(valid_types)}")
        return consent_type
    
    @validates('consent_status')
    def validate_consent_status(self, key, status):
        """Validate consent status."""
        valid_statuses = [status.value for status in ConsentStatus]
        if status not in valid_statuses:
            raise ValueError(f"Consent status must be one of: {', '.join(valid_statuses)}")
        return status
    
    @validates('consent_method')
    def validate_consent_method(self, key, method):
        """Validate consent method."""
        if method is None:
            return method
        
        valid_methods = [
            'web_form', 'api', 'email_confirmation', 'phone_verification',
            'in_person', 'written_form', 'opt_in', 'opt_out'
        ]
        
        if method not in valid_methods:
            raise ValueError(f"Consent method must be one of: {', '.join(valid_methods)}")
        
        return method
    
    def give_consent(
        self,
        ip_address: str = None,
        user_agent: str = None,
        method: str = 'web_form',
        evidence: Dict[str, Any] = None
    ) -> None:
        """
        Record consent being given.
        
        Args:
            ip_address: IP address of the user
            user_agent: User agent string
            method: Method of consent collection
            evidence: Additional evidence of consent
        """
        self.consent_status = ConsentStatus.GIVEN.value
        self.consent_given_at = datetime.now(timezone.utc)
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.consent_method = method
        
        if evidence:
            self.consent_evidence = json.dumps(evidence)
    
    def withdraw_consent(self, reason: str = None) -> None:
        """
        Record consent withdrawal.
        
        Args:
            reason: Reason for withdrawal
        """
        self.consent_status = ConsentStatus.WITHDRAWN.value
        self.consent_withdrawn_at = datetime.now(timezone.utc)
        self.withdrawal_reason = reason
    
    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.consent_status != ConsentStatus.GIVEN.value:
            return False
        
        if self.expires_at and self.expires_at <= datetime.now(timezone.utc):
            return False
        
        return True
    
    def get_evidence_dict(self) -> Dict[str, Any]:
        """Get consent evidence as dictionary."""
        if not self.consent_evidence:
            return {}
        
        try:
            return json.loads(self.consent_evidence)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_evidence_dict(self, evidence: Dict[str, Any]) -> None:
        """Set consent evidence from dictionary."""
        if evidence:
            self.consent_evidence = json.dumps(evidence)
        else:
            self.consent_evidence = None
    
    def get_data_categories_list(self) -> list:
        """Get data categories as list."""
        if not self.data_categories:
            return []
        
        try:
            return json.loads(self.data_categories)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_data_categories_list(self, categories: list) -> None:
        """Set data categories from list."""
        if categories:
            self.data_categories = json.dumps(categories)
        else:
            self.data_categories = None
    
    def __repr__(self) -> str:
        return f"<UserConsent(user_id={self.user_id}, type={self.consent_type}, status={self.consent_status})>"


class ConsentAuditLog(BaseModel):
    """
    Consent audit log model for tracking all consent-related activities.
    
    Provides comprehensive audit trail for consent management including
    consent grants, withdrawals, updates, and policy changes.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the user (null for system events)"
    )
    
    consent_id = Column(
        String(36),
        ForeignKey("user_consents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the consent record (if applicable)"
    )
    
    privacy_notice_id = Column(
        String(36),
        ForeignKey("privacy_notices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of the privacy notice (if applicable)"
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of consent event"
    )
    
    event_description = Column(
        Text,
        nullable=False,
        doc="Human-readable description of the event"
    )
    
    old_values = Column(
        Text,
        nullable=True,
        doc="Previous values before change (JSON format)"
    )
    
    new_values = Column(
        Text,
        nullable=True,
        doc="New values after change (JSON format)"
    )
    
    ip_address = Column(
        String(45),  # IPv6 max length
        nullable=True,
        doc="IP address where event occurred"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        doc="User agent string"
    )
    
    session_id = Column(
        String(255),
        nullable=True,
        doc="Session identifier"
    )
    
    # Administrative fields
    performed_by = Column(
        String(36),
        nullable=True,
        doc="ID of user/admin who performed the action"
    )
    
    performed_by_type = Column(
        String(20),
        default='user',
        nullable=False,
        doc="Type of actor (user, admin, system)"
    )
    
    legal_basis = Column(
        String(100),
        nullable=True,
        doc="Legal basis for processing under GDPR"
    )
    
    event_metadata = Column(
        Text,
        nullable=True,
        doc="Additional event metadata (JSON format)"
    )
    
    @validates('event_type')
    def validate_event_type(self, key, event_type):
        """Validate event type."""
        valid_types = [
            'consent_given', 'consent_withdrawn', 'consent_updated', 'consent_expired',
            'notice_published', 'notice_updated', 'notice_expired',
            'policy_accepted', 'policy_rejected', 'bulk_consent_update',
            'data_export_requested', 'data_deletion_requested'
        ]
        
        if event_type not in valid_types:
            raise ValueError(f"Event type must be one of: {', '.join(valid_types)}")
        
        return event_type
    
    @validates('performed_by_type')
    def validate_performed_by_type(self, key, actor_type):
        """Validate performer type."""
        valid_types = ['user', 'admin', 'system', 'api']
        if actor_type not in valid_types:
            raise ValueError(f"Performed by type must be one of: {', '.join(valid_types)}")
        return actor_type
    
    def get_old_values_dict(self) -> Dict[str, Any]:
        """Get old values as dictionary."""
        if not self.old_values:
            return {}
        
        try:
            return json.loads(self.old_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_old_values_dict(self, values: Dict[str, Any]) -> None:
        """Set old values from dictionary."""
        if values:
            self.old_values = json.dumps(values)
        else:
            self.old_values = None
    
    def get_new_values_dict(self) -> Dict[str, Any]:
        """Get new values as dictionary."""
        if not self.new_values:
            return {}
        
        try:
            return json.loads(self.new_values)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_new_values_dict(self, values: Dict[str, Any]) -> None:
        """Set new values from dictionary."""
        if values:
            self.new_values = json.dumps(values)
        else:
            self.new_values = None
    
    @classmethod
    def log_consent_event(
        cls,
        event_type: str,
        description: str,
        user_id: str = None,
        consent_id: str = None,
        privacy_notice_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        performed_by: str = None,
        performed_by_type: str = 'user',
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> 'ConsentAuditLog':
        """
        Create consent audit log entry.
        
        Args:
            event_type: Type of consent event
            description: Human-readable description
            user_id: ID of affected user
            consent_id: ID of consent record
            privacy_notice_id: ID of privacy notice
            ip_address: IP address
            user_agent: User agent string
            performed_by: ID of user performing action
            performed_by_type: Type of performer
            old_values: Previous values
            new_values: New values
            metadata: Additional metadata
            
        Returns:
            ConsentAuditLog instance
        """
        log_entry = cls(
            event_type=event_type,
            event_description=description,
            user_id=user_id,
            consent_id=consent_id,
            privacy_notice_id=privacy_notice_id,
            ip_address=ip_address,
            user_agent=user_agent,
            performed_by=performed_by,
            performed_by_type=performed_by_type
        )
        
        if old_values:
            log_entry.set_old_values_dict(old_values)
        
        if new_values:
            log_entry.set_new_values_dict(new_values)
        
        if metadata:
            log_entry.event_metadata = json.dumps(metadata)
        
        return log_entry
    
    def __repr__(self) -> str:
        return f"<ConsentAuditLog(event_type={self.event_type}, user_id={self.user_id})>"