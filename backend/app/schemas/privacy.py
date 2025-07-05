"""
Privacy & Consent Management Schemas

Pydantic schemas for privacy notices, consent management, and GDPR compliance
request/response models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class PrivacyNoticeResponse(BaseModel):
    """Privacy notice response schema."""
    
    id: str = Field(
        ...,
        description="Privacy notice ID"
    )
    
    notice_type: str = Field(
        ...,
        description="Type of privacy notice"
    )
    
    version: str = Field(
        ...,
        description="Version number"
    )
    
    title: str = Field(
        ...,
        description="Notice title"
    )
    
    content: str = Field(
        ...,
        description="Full notice content"
    )
    
    content_html: Optional[str] = Field(
        None,
        description="HTML formatted content"
    )
    
    summary: Optional[str] = Field(
        None,
        description="Brief summary"
    )
    
    language_code: str = Field(
        ...,
        description="Language code"
    )
    
    effective_date: datetime = Field(
        ...,
        description="Effective date"
    )
    
    requires_consent: bool = Field(
        ...,
        description="Whether consent is required"
    )
    
    is_current: bool = Field(
        ...,
        description="Whether this is the current version"
    )


class ConsentItem(BaseModel):
    """Individual consent item schema."""
    
    consent_type: str = Field(
        ...,
        description="Type of consent",
        example="privacy_policy"
    )
    
    privacy_notice_id: str = Field(
        ...,
        description="Privacy notice ID"
    )
    
    consent_given: bool = Field(
        ...,
        description="Whether consent is given"
    )
    
    purpose_description: Optional[str] = Field(
        None,
        description="Purpose of data processing"
    )
    
    data_categories: Optional[List[str]] = Field(
        None,
        description="Categories of data covered"
    )
    
    processing_activities: Optional[List[str]] = Field(
        None,
        description="Processing activities covered"
    )
    
    withdrawal_reason: Optional[str] = Field(
        None,
        description="Reason for withdrawal (if applicable)"
    )
    
    evidence: Optional[Dict[str, Any]] = Field(
        None,
        description="Evidence of consent"
    )


class ConsentRequest(BaseModel):
    """Consent recording request schema."""
    
    consents: List[ConsentItem] = Field(
        ...,
        description="List of consent items to record",
        min_items=1
    )


class ConsentResponse(BaseModel):
    """Consent recording response schema."""
    
    user_id: str = Field(
        ...,
        description="User ID"
    )
    
    consents_processed: int = Field(
        ...,
        description="Number of consents processed"
    )
    
    results: List[Dict[str, Any]] = Field(
        ...,
        description="Processing results for each consent"
    )
    
    recorded_at: datetime = Field(
        ...,
        description="Recording timestamp"
    )


class UserConsentResponse(BaseModel):
    """User consent status response schema."""
    
    id: str = Field(
        ...,
        description="Consent record ID"
    )
    
    consent_type: str = Field(
        ...,
        description="Type of consent"
    )
    
    privacy_notice_id: str = Field(
        ...,
        description="Privacy notice ID"
    )
    
    status: str = Field(
        ...,
        description="Consent status"
    )
    
    consent_given_at: Optional[datetime] = Field(
        None,
        description="When consent was given"
    )
    
    consent_withdrawn_at: Optional[datetime] = Field(
        None,
        description="When consent was withdrawn"
    )
    
    expires_at: Optional[datetime] = Field(
        None,
        description="Consent expiration"
    )
    
    is_valid: bool = Field(
        ...,
        description="Whether consent is currently valid"
    )
    
    purpose_description: Optional[str] = Field(
        None,
        description="Purpose of data processing"
    )
    
    data_categories: List[str] = Field(
        [],
        description="Categories of data covered"
    )
    
    withdrawal_reason: Optional[str] = Field(
        None,
        description="Reason for withdrawal"
    )
    
    created_at: datetime = Field(
        ...,
        description="Record creation timestamp"
    )


class ConsentWithdrawalRequest(BaseModel):
    """Consent withdrawal request schema."""
    
    reason: Optional[str] = Field(
        None,
        description="Reason for withdrawing consent",
        max_length=500,
        example="No longer wish to receive marketing emails"
    )


class ConsentWithdrawalResponse(BaseModel):
    """Consent withdrawal response schema."""
    
    consent_id: str = Field(
        ...,
        description="Consent record ID"
    )
    
    consent_type: str = Field(
        ...,
        description="Type of consent withdrawn"
    )
    
    status: str = Field(
        ...,
        description="New consent status"
    )
    
    withdrawn_at: datetime = Field(
        ...,
        description="Withdrawal timestamp"
    )
    
    reason: Optional[str] = Field(
        None,
        description="Withdrawal reason"
    )


class ConsentComplianceResponse(BaseModel):
    """Consent compliance status response schema."""
    
    user_id: str = Field(
        ...,
        description="User ID"
    )
    
    overall_compliant: bool = Field(
        ...,
        description="Whether user is overall compliant"
    )
    
    compliance_status: Dict[str, Any] = Field(
        ...,
        description="Detailed compliance status by consent type"
    )
    
    missing_consents: List[Dict[str, Any]] = Field(
        ...,
        description="List of missing required consents"
    )
    
    checked_at: datetime = Field(
        ...,
        description="Compliance check timestamp"
    )


class ConsentAuditEntry(BaseModel):
    """Consent audit trail entry schema."""
    
    id: str = Field(
        ...,
        description="Audit log entry ID"
    )
    
    event_type: str = Field(
        ...,
        description="Type of consent event"
    )
    
    description: str = Field(
        ...,
        description="Event description"
    )
    
    user_id: Optional[str] = Field(
        None,
        description="User ID"
    )
    
    consent_id: Optional[str] = Field(
        None,
        description="Consent record ID"
    )
    
    privacy_notice_id: Optional[str] = Field(
        None,
        description="Privacy notice ID"
    )
    
    performed_by: Optional[str] = Field(
        None,
        description="Who performed the action"
    )
    
    performed_by_type: str = Field(
        ...,
        description="Type of performer"
    )
    
    ip_address: Optional[str] = Field(
        None,
        description="IP address"
    )
    
    old_values: Dict[str, Any] = Field(
        {},
        description="Previous values"
    )
    
    new_values: Dict[str, Any] = Field(
        {},
        description="New values"
    )
    
    created_at: datetime = Field(
        ...,
        description="Event timestamp"
    )


class ConsentAuditResponse(BaseModel):
    """Consent audit trail response schema."""
    
    audit_trail: List[ConsentAuditEntry] = Field(
        ...,
        description="List of audit trail entries"
    )
    
    total_count: Optional[int] = Field(
        None,
        description="Total number of entries available"
    )


class PrivacyNoticesResponse(BaseModel):
    """Privacy notices list response schema."""
    
    notices: List[PrivacyNoticeResponse] = Field(
        ...,
        description="List of privacy notices"
    )
    
    language_code: str = Field(
        ...,
        description="Language code for notices"
    )


class ConsentSummaryResponse(BaseModel):
    """User consent summary response schema."""
    
    user_id: str = Field(
        ...,
        description="User ID"
    )
    
    consents: List[UserConsentResponse] = Field(
        ...,
        description="List of user consents"
    )
    
    total_consents: int = Field(
        ...,
        description="Total number of consents"
    )
    
    active_consents: int = Field(
        ...,
        description="Number of active consents"
    )
    
    withdrawn_consents: int = Field(
        ...,
        description="Number of withdrawn consents"
    )