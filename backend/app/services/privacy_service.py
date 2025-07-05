"""
Privacy & Consent Management Service

Service for handling privacy notices, user consent tracking, and GDPR compliance
including consent collection, withdrawal, and audit trail management.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.models.privacy import PrivacyNotice, UserConsent, ConsentAuditLog, ConsentType, ConsentStatus
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)


class PrivacyService:
    """Service for privacy and consent management."""
    
    def __init__(self, db: Session):
        self.db = db
        self.audit_logger = get_audit_logger()
    
    def get_current_privacy_notices(
        self,
        language_code: str = 'en',
        notice_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get current active privacy notices.
        
        Args:
            language_code: Language code for notices
            notice_type: Specific notice type to filter by
            
        Returns:
            List of current privacy notices
        """
        try:
            query = self.db.query(PrivacyNotice).filter(
                PrivacyNotice.is_active == True,
                PrivacyNotice.is_current == True,
                PrivacyNotice.language_code == language_code,
                PrivacyNotice.effective_date <= datetime.now(timezone.utc)
            )
            
            if notice_type:
                query = query.filter(PrivacyNotice.notice_type == notice_type)
            
            # Filter out expired notices
            now = datetime.now(timezone.utc)
            query = query.filter(
                (PrivacyNotice.expiry_date.is_(None)) |
                (PrivacyNotice.expiry_date > now)
            )
            
            notices = query.order_by(PrivacyNotice.notice_type).all()
            
            return [notice.get_content_dict() for notice in notices]
            
        except Exception as e:
            logger.error(f"Failed to get privacy notices: {e}")
            raise
    
    def get_privacy_notice_by_id(self, notice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific privacy notice by ID.
        
        Args:
            notice_id: ID of the privacy notice
            
        Returns:
            Privacy notice data or None if not found
        """
        try:
            notice = self.db.query(PrivacyNotice).filter(
                PrivacyNotice.id == notice_id
            ).first()
            
            if not notice:
                return None
            
            return notice.get_content_dict()
            
        except Exception as e:
            logger.error(f"Failed to get privacy notice {notice_id}: {e}")
            raise
    
    async def record_consent(
        self,
        user_id: str,
        consent_data: Dict[str, Any],
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Record user consent for privacy notices.
        
        Args:
            user_id: ID of user giving consent
            consent_data: Consent information
            ip_address: IP address of user
            user_agent: User agent string
            
        Returns:
            Consent recording results
            
        Raises:
            ValueError: If required data is missing
            Exception: If consent recording fails
        """
        try:
            # Validate user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User not found: {user_id}")
            
            consent_results = []
            
            # Process each consent item
            for consent_item in consent_data.get('consents', []):
                consent_type = consent_item.get('consent_type')
                privacy_notice_id = consent_item.get('privacy_notice_id')
                consent_given = consent_item.get('consent_given', False)
                
                if not consent_type or not privacy_notice_id:
                    raise ValueError("consent_type and privacy_notice_id are required")
                
                # Validate privacy notice exists
                privacy_notice = self.db.query(PrivacyNotice).filter(
                    PrivacyNotice.id == privacy_notice_id
                ).first()
                
                if not privacy_notice:
                    raise ValueError(f"Privacy notice not found: {privacy_notice_id}")
                
                # Check for existing consent record
                existing_consent = self.db.query(UserConsent).filter(
                    UserConsent.user_id == user_id,
                    UserConsent.privacy_notice_id == privacy_notice_id,
                    UserConsent.consent_type == consent_type
                ).first()
                
                if existing_consent:
                    # Update existing consent
                    old_status = existing_consent.consent_status
                    
                    if consent_given:
                        existing_consent.give_consent(
                            ip_address=ip_address,
                            user_agent=user_agent,
                            method='web_form',
                            evidence=consent_item.get('evidence', {})
                        )
                    else:
                        existing_consent.withdraw_consent(
                            reason=consent_item.get('withdrawal_reason', 'User choice')
                        )
                    
                    # Log consent change
                    audit_log = ConsentAuditLog.log_consent_event(
                        event_type='consent_updated',
                        description=f"Consent {consent_type} updated from {old_status} to {existing_consent.consent_status}",
                        user_id=user_id,
                        consent_id=existing_consent.id,
                        privacy_notice_id=privacy_notice_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        old_values={'status': old_status},
                        new_values={'status': existing_consent.consent_status}
                    )
                    self.db.add(audit_log)
                    
                    consent_results.append({
                        'consent_type': consent_type,
                        'privacy_notice_id': privacy_notice_id,
                        'status': existing_consent.consent_status,
                        'action': 'updated'
                    })
                
                else:
                    # Create new consent record
                    new_consent = UserConsent(
                        user_id=user_id,
                        privacy_notice_id=privacy_notice_id,
                        consent_type=consent_type,
                        purpose_description=consent_item.get('purpose_description'),
                        data_categories=consent_item.get('data_categories'),
                        processing_activities=consent_item.get('processing_activities')
                    )
                    
                    if consent_given:
                        new_consent.give_consent(
                            ip_address=ip_address,
                            user_agent=user_agent,
                            method='web_form',
                            evidence=consent_item.get('evidence', {})
                        )
                    
                    self.db.add(new_consent)
                    self.db.flush()  # Get the ID
                    
                    # Log consent creation
                    audit_log = ConsentAuditLog.log_consent_event(
                        event_type='consent_given' if consent_given else 'consent_withdrawn',
                        description=f"New consent {consent_type} recorded with status {new_consent.consent_status}",
                        user_id=user_id,
                        consent_id=new_consent.id,
                        privacy_notice_id=privacy_notice_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        new_values={'status': new_consent.consent_status}
                    )
                    self.db.add(audit_log)
                    
                    consent_results.append({
                        'consent_type': consent_type,
                        'privacy_notice_id': privacy_notice_id,
                        'status': new_consent.consent_status,
                        'action': 'created'
                    })
            
            # Commit all changes
            self.db.commit()
            
            # Log overall consent event
            await self.audit_logger.log_authentication_event(
                event_type="consent_recorded",
                success=True,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "consent_count": len(consent_results),
                    "consent_types": [r['consent_type'] for r in consent_results]
                },
                severity=AuditSeverity.MEDIUM
            )
            
            logger.info(f"Recorded {len(consent_results)} consent items for user {user_id}")
            
            return {
                "user_id": user_id,
                "consents_processed": len(consent_results),
                "results": consent_results,
                "recorded_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            
            # Log consent failure
            await self.audit_logger.log_authentication_event(
                event_type="consent_recorded",
                success=False,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(e),
                severity=AuditSeverity.MEDIUM
            )
            
            logger.error(f"Failed to record consent for user {user_id}: {e}")
            raise
    
    def get_user_consents(
        self,
        user_id: str,
        consent_type: str = None,
        include_withdrawn: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get user's consent records.
        
        Args:
            user_id: ID of user
            consent_type: Specific consent type to filter by
            include_withdrawn: Whether to include withdrawn consents
            
        Returns:
            List of user consent records
        """
        try:
            query = self.db.query(UserConsent).filter(
                UserConsent.user_id == user_id
            )
            
            if consent_type:
                query = query.filter(UserConsent.consent_type == consent_type)
            
            if not include_withdrawn:
                query = query.filter(
                    UserConsent.consent_status != ConsentStatus.WITHDRAWN.value
                )
            
            consents = query.order_by(UserConsent.created_at.desc()).all()
            
            consent_list = []
            for consent in consents:
                consent_data = {
                    "id": consent.id,
                    "consent_type": consent.consent_type,
                    "privacy_notice_id": consent.privacy_notice_id,
                    "status": consent.consent_status,
                    "consent_given_at": consent.consent_given_at.isoformat() if consent.consent_given_at else None,
                    "consent_withdrawn_at": consent.consent_withdrawn_at.isoformat() if consent.consent_withdrawn_at else None,
                    "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                    "is_valid": consent.is_valid(),
                    "purpose_description": consent.purpose_description,
                    "data_categories": consent.get_data_categories_list(),
                    "withdrawal_reason": consent.withdrawal_reason,
                    "created_at": consent.created_at.isoformat() if consent.created_at else None
                }
                consent_list.append(consent_data)
            
            return consent_list
            
        except Exception as e:
            logger.error(f"Failed to get user consents for {user_id}: {e}")
            raise
    
    async def withdraw_consent(
        self,
        user_id: str,
        consent_id: str,
        reason: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Withdraw user consent.
        
        Args:
            user_id: ID of user withdrawing consent
            consent_id: ID of consent to withdraw
            reason: Reason for withdrawal
            ip_address: IP address of user
            user_agent: User agent string
            
        Returns:
            Withdrawal confirmation
            
        Raises:
            ValueError: If consent not found or not owned by user
            Exception: If withdrawal fails
        """
        try:
            # Find consent record
            consent = self.db.query(UserConsent).filter(
                UserConsent.id == consent_id,
                UserConsent.user_id == user_id
            ).first()
            
            if not consent:
                raise ValueError(f"Consent not found or not owned by user: {consent_id}")
            
            if consent.consent_status == ConsentStatus.WITHDRAWN.value:
                raise ValueError("Consent is already withdrawn")
            
            # Record withdrawal
            old_status = consent.consent_status
            consent.withdraw_consent(reason)
            
            # Log withdrawal
            audit_log = ConsentAuditLog.log_consent_event(
                event_type='consent_withdrawn',
                description=f"Consent {consent.consent_type} withdrawn by user",
                user_id=user_id,
                consent_id=consent_id,
                privacy_notice_id=consent.privacy_notice_id,
                ip_address=ip_address,
                user_agent=user_agent,
                old_values={'status': old_status},
                new_values={'status': consent.consent_status, 'reason': reason}
            )
            self.db.add(audit_log)
            
            self.db.commit()
            
            # Log withdrawal event
            await self.audit_logger.log_authentication_event(
                event_type="consent_withdrawn",
                success=True,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "consent_id": consent_id,
                    "consent_type": consent.consent_type,
                    "reason": reason
                },
                severity=AuditSeverity.MEDIUM
            )
            
            logger.info(f"Consent {consent_id} withdrawn for user {user_id}")
            
            return {
                "consent_id": consent_id,
                "consent_type": consent.consent_type,
                "status": consent.consent_status,
                "withdrawn_at": consent.consent_withdrawn_at.isoformat(),
                "reason": reason
            }
            
        except Exception as e:
            self.db.rollback()
            
            # Log withdrawal failure
            await self.audit_logger.log_authentication_event(
                event_type="consent_withdrawn",
                success=False,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                error_message=str(e),
                metadata={"consent_id": consent_id},
                severity=AuditSeverity.MEDIUM
            )
            
            logger.error(f"Failed to withdraw consent {consent_id} for user {user_id}: {e}")
            raise
    
    def check_consent_compliance(self, user_id: str) -> Dict[str, Any]:
        """
        Check user's consent compliance status.
        
        Args:
            user_id: ID of user to check
            
        Returns:
            Compliance status and required consents
        """
        try:
            # Get current required privacy notices
            required_notices = self.db.query(PrivacyNotice).filter(
                PrivacyNotice.is_active == True,
                PrivacyNotice.is_current == True,
                PrivacyNotice.requires_consent == True,
                PrivacyNotice.effective_date <= datetime.now(timezone.utc)
            ).all()
            
            # Get user's consents
            user_consents = self.db.query(UserConsent).filter(
                UserConsent.user_id == user_id,
                UserConsent.consent_status == ConsentStatus.GIVEN.value
            ).all()
            
            # Check compliance for each required notice
            compliance_status = {}
            missing_consents = []
            
            for notice in required_notices:
                consent_given = False
                consent_valid = False
                
                for consent in user_consents:
                    if (consent.privacy_notice_id == notice.id and 
                        consent.consent_type == notice.notice_type):
                        consent_given = True
                        consent_valid = consent.is_valid()
                        break
                
                compliance_status[notice.notice_type] = {
                    "notice_id": notice.id,
                    "notice_title": notice.title,
                    "consent_given": consent_given,
                    "consent_valid": consent_valid,
                    "required": True
                }
                
                if not consent_given or not consent_valid:
                    missing_consents.append({
                        "notice_id": notice.id,
                        "notice_type": notice.notice_type,
                        "title": notice.title,
                        "summary": notice.summary
                    })
            
            overall_compliant = len(missing_consents) == 0
            
            return {
                "user_id": user_id,
                "overall_compliant": overall_compliant,
                "compliance_status": compliance_status,
                "missing_consents": missing_consents,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check consent compliance for user {user_id}: {e}")
            raise
    
    def get_consent_audit_trail(
        self,
        user_id: str = None,
        consent_id: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get consent audit trail.
        
        Args:
            user_id: Filter by user ID
            consent_id: Filter by specific consent ID
            limit: Maximum records to return
            offset: Number of records to skip
            
        Returns:
            List of audit trail entries
        """
        try:
            query = self.db.query(ConsentAuditLog)
            
            if user_id:
                query = query.filter(ConsentAuditLog.user_id == user_id)
            
            if consent_id:
                query = query.filter(ConsentAuditLog.consent_id == consent_id)
            
            audit_logs = query.order_by(
                ConsentAuditLog.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            audit_trail = []
            for log in audit_logs:
                audit_data = {
                    "id": log.id,
                    "event_type": log.event_type,
                    "description": log.event_description,
                    "user_id": log.user_id,
                    "consent_id": log.consent_id,
                    "privacy_notice_id": log.privacy_notice_id,
                    "performed_by": log.performed_by,
                    "performed_by_type": log.performed_by_type,
                    "ip_address": log.ip_address,
                    "old_values": log.get_old_values_dict(),
                    "new_values": log.get_new_values_dict(),
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                audit_trail.append(audit_data)
            
            return audit_trail
            
        except Exception as e:
            logger.error(f"Failed to get consent audit trail: {e}")
            raise


def get_privacy_service(db: Session) -> PrivacyService:
    """Get privacy service instance."""
    return PrivacyService(db)