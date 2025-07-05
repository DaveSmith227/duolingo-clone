"""
Unit Tests for Privacy Service

Tests for privacy and consent management functionality including consent
recording, withdrawal, compliance checking, and audit trail management.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
import json

from app.services.privacy_service import PrivacyService
from app.models.user import User
from app.models.privacy import PrivacyNotice, UserConsent, ConsentAuditLog, ConsentType, ConsentStatus


class TestPrivacyService:
    """Test cases for privacy service functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.mock_audit_logger = AsyncMock()
        
        # Mock the audit logger dependency during initialization
        with patch('app.services.privacy_service.get_audit_logger', return_value=self.mock_audit_logger):
            self.privacy_service = PrivacyService(self.mock_db)
        
        # Test data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        
        self.test_privacy_notice = Mock(spec=PrivacyNotice)
        self.test_privacy_notice.id = "notice-123"
        self.test_privacy_notice.notice_type = "privacy_policy"
        self.test_privacy_notice.version = "1.0"
        self.test_privacy_notice.title = "Privacy Policy"
        self.test_privacy_notice.requires_consent = True
        self.test_privacy_notice.is_active = True
        self.test_privacy_notice.is_current = True
        self.test_privacy_notice.effective_date = datetime.now(timezone.utc)
        self.test_privacy_notice.expiry_date = None
        self.test_privacy_notice.get_content_dict.return_value = {
            "id": "notice-123",
            "notice_type": "privacy_policy",
            "version": "1.0",
            "title": "Privacy Policy",
            "content": "Privacy policy content...",
            "language_code": "en",
            "effective_date": datetime.now(timezone.utc).isoformat(),
            "requires_consent": True,
            "is_current": True
        }
    
    def test_get_current_privacy_notices_success(self):
        """Test successful retrieval of current privacy notices."""
        # Mock query chain properly
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [self.test_privacy_notice]
        self.mock_db.query.return_value = mock_query
        
        # Get privacy notices
        result = self.privacy_service.get_current_privacy_notices(
            language_code="en",
            notice_type="privacy_policy"
        )
        
        # Verify result
        assert len(result) == 1
        assert result[0]["id"] == "notice-123"
        assert result[0]["notice_type"] == "privacy_policy"
        assert result[0]["title"] == "Privacy Policy"
        
        # Verify query was called with correct filters
        self.mock_db.query.assert_called_with(PrivacyNotice)
    
    def test_get_privacy_notice_by_id_success(self):
        """Test successful retrieval of privacy notice by ID."""
        # Mock query result
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_privacy_notice
        
        # Get privacy notice
        result = self.privacy_service.get_privacy_notice_by_id("notice-123")
        
        # Verify result
        assert result is not None
        assert result["id"] == "notice-123"
        assert result["notice_type"] == "privacy_policy"
        
        # Verify query
        self.mock_db.query.assert_called_with(PrivacyNotice)
    
    def test_get_privacy_notice_by_id_not_found(self):
        """Test privacy notice retrieval when notice not found."""
        # Mock query result - not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Get privacy notice
        result = self.privacy_service.get_privacy_notice_by_id("nonexistent")
        
        # Verify result
        assert result is None
    
    @pytest.mark.asyncio
    async def test_record_consent_success(self):
        """Test successful consent recording."""
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_privacy_notice,  # Privacy notice query
            None  # Existing consent query - not found
        ]
        
        # Mock database operations
        self.mock_db.add = Mock()
        self.mock_db.flush = Mock()
        self.mock_db.commit = Mock()
        
        # Test consent data
        consent_data = {
            "consents": [
                {
                    "consent_type": "privacy_policy",
                    "privacy_notice_id": "notice-123",
                    "consent_given": True,
                    "purpose_description": "Data processing for app functionality",
                    "evidence": {"checkbox_checked": True}
                }
            ]
        }
        
        # Record consent
        result = await self.privacy_service.record_consent(
            user_id="user-123",
            consent_data=consent_data,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify result
        assert result["user_id"] == "user-123"
        assert result["consents_processed"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["consent_type"] == "privacy_policy"
        assert result["results"][0]["action"] == "created"
        
        # Verify database operations
        assert self.mock_db.add.call_count >= 2  # Consent + audit log
        self.mock_db.flush.assert_called_once()
        self.mock_db.commit.assert_called_once()
        
        # Verify audit logging
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["event_type"] == "consent_recorded"
        assert call_args[1]["success"] is True
    
    @pytest.mark.asyncio
    async def test_record_consent_user_not_found(self):
        """Test consent recording when user is not found."""
        # Mock user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        consent_data = {
            "consents": [
                {
                    "consent_type": "privacy_policy",
                    "privacy_notice_id": "notice-123",
                    "consent_given": True
                }
            ]
        }
        
        # Test consent recording
        with pytest.raises(ValueError, match="User not found"):
            await self.privacy_service.record_consent(
                user_id="user-123",
                consent_data=consent_data
            )
        
        # Verify rollback and audit logging
        self.mock_db.rollback.assert_called_once()
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is False
    
    @pytest.mark.asyncio
    async def test_record_consent_update_existing(self):
        """Test updating existing consent record."""
        # Mock existing consent
        existing_consent = Mock(spec=UserConsent)
        existing_consent.id = "consent-123"
        existing_consent.consent_status = "given"
        existing_consent.give_consent = Mock()
        existing_consent.withdraw_consent = Mock()
        
        # Mock queries
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_privacy_notice,  # Privacy notice query
            existing_consent  # Existing consent query
        ]
        
        # Mock database operations
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        
        consent_data = {
            "consents": [
                {
                    "consent_type": "privacy_policy",
                    "privacy_notice_id": "notice-123",
                    "consent_given": False,  # Withdrawing consent
                    "withdrawal_reason": "No longer needed"
                }
            ]
        }
        
        # Record consent
        result = await self.privacy_service.record_consent(
            user_id="user-123",
            consent_data=consent_data,
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify result
        assert result["results"][0]["action"] == "updated"
        
        # Verify withdrawal was called
        existing_consent.withdraw_consent.assert_called_once_with("No longer needed")
    
    def test_get_user_consents_success(self):
        """Test successful retrieval of user consents."""
        # Mock consent records
        mock_consent1 = Mock(spec=UserConsent)
        mock_consent1.id = "consent-1"
        mock_consent1.consent_type = "privacy_policy"
        mock_consent1.privacy_notice_id = "notice-123"
        mock_consent1.consent_status = "given"
        mock_consent1.consent_given_at = datetime.now(timezone.utc)
        mock_consent1.consent_withdrawn_at = None
        mock_consent1.expires_at = None
        mock_consent1.purpose_description = "App functionality"
        mock_consent1.withdrawal_reason = None
        mock_consent1.created_at = datetime.now(timezone.utc)
        mock_consent1.is_valid.return_value = True
        mock_consent1.get_data_categories_list.return_value = ["profile", "usage"]
        
        # Mock query
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_consent1
        ]
        
        # Get user consents
        result = self.privacy_service.get_user_consents(
            user_id="user-123",
            consent_type="privacy_policy"
        )
        
        # Verify result
        assert len(result) == 1
        assert result[0]["id"] == "consent-1"
        assert result[0]["consent_type"] == "privacy_policy"
        assert result[0]["status"] == "given"
        assert result[0]["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_withdraw_consent_success(self):
        """Test successful consent withdrawal."""
        # Mock consent record
        mock_consent = Mock(spec=UserConsent)
        mock_consent.id = "consent-123"
        mock_consent.consent_type = "marketing_emails"
        mock_consent.privacy_notice_id = "notice-123"
        mock_consent.consent_status = "given"
        mock_consent.consent_withdrawn_at = datetime.now(timezone.utc)
        mock_consent.withdraw_consent = Mock()
        
        # Mock query
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_consent
        
        # Mock database operations
        self.mock_db.add = Mock()
        self.mock_db.commit = Mock()
        
        # Withdraw consent
        result = await self.privacy_service.withdraw_consent(
            user_id="user-123",
            consent_id="consent-123",
            reason="No longer interested",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify result
        assert result["consent_id"] == "consent-123"
        assert result["consent_type"] == "marketing_emails"
        assert result["reason"] == "No longer interested"
        
        # Verify withdrawal was called
        mock_consent.withdraw_consent.assert_called_once_with("No longer interested")
        
        # Verify database operations
        self.mock_db.add.assert_called_once()  # Audit log
        self.mock_db.commit.assert_called_once()
        
        # Verify audit logging
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["event_type"] == "consent_withdrawn"
        assert call_args[1]["success"] is True
    
    @pytest.mark.asyncio
    async def test_withdraw_consent_not_found(self):
        """Test consent withdrawal when consent not found."""
        # Mock consent not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test withdrawal
        with pytest.raises(ValueError, match="Consent not found or not owned by user"):
            await self.privacy_service.withdraw_consent(
                user_id="user-123",
                consent_id="nonexistent",
                reason="Test"
            )
        
        # Verify rollback and audit logging
        self.mock_db.rollback.assert_called_once()
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is False
    
    @pytest.mark.asyncio
    async def test_withdraw_consent_already_withdrawn(self):
        """Test withdrawing consent that is already withdrawn."""
        # Mock already withdrawn consent
        mock_consent = Mock(spec=UserConsent)
        mock_consent.consent_status = "withdrawn"
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_consent
        
        # Test withdrawal
        with pytest.raises(ValueError, match="Consent is already withdrawn"):
            await self.privacy_service.withdraw_consent(
                user_id="user-123",
                consent_id="consent-123",
                reason="Test"
            )
    
    def test_check_consent_compliance_compliant(self):
        """Test consent compliance check for compliant user."""
        # Mock required privacy notices
        required_notice = Mock(spec=PrivacyNotice)
        required_notice.id = "notice-123"
        required_notice.notice_type = "privacy_policy"
        required_notice.title = "Privacy Policy"
        required_notice.summary = "Our privacy policy"
        
        # Mock user consents
        user_consent = Mock(spec=UserConsent)
        user_consent.privacy_notice_id = "notice-123"
        user_consent.consent_type = "privacy_policy"
        user_consent.is_valid.return_value = True
        
        # Mock queries
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [required_notice],  # Required notices
            [user_consent]  # User consents
        ]
        
        # Check compliance
        result = self.privacy_service.check_consent_compliance("user-123")
        
        # Verify result
        assert result["user_id"] == "user-123"
        assert result["overall_compliant"] is True
        assert len(result["missing_consents"]) == 0
        assert "privacy_policy" in result["compliance_status"]
        assert result["compliance_status"]["privacy_policy"]["consent_given"] is True
        assert result["compliance_status"]["privacy_policy"]["consent_valid"] is True
    
    def test_check_consent_compliance_non_compliant(self):
        """Test consent compliance check for non-compliant user."""
        # Mock required privacy notices
        required_notice = Mock(spec=PrivacyNotice)
        required_notice.id = "notice-123"
        required_notice.notice_type = "privacy_policy"
        required_notice.title = "Privacy Policy"
        required_notice.summary = "Our privacy policy"
        
        # Mock queries - no user consents
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [required_notice],  # Required notices
            []  # No user consents
        ]
        
        # Check compliance
        result = self.privacy_service.check_consent_compliance("user-123")
        
        # Verify result
        assert result["user_id"] == "user-123"
        assert result["overall_compliant"] is False
        assert len(result["missing_consents"]) == 1
        assert result["missing_consents"][0]["notice_type"] == "privacy_policy"
        assert result["compliance_status"]["privacy_policy"]["consent_given"] is False
    
    def test_get_consent_audit_trail_success(self):
        """Test successful retrieval of consent audit trail."""
        # Mock audit log entries
        mock_log1 = Mock(spec=ConsentAuditLog)
        mock_log1.id = "log-1"
        mock_log1.event_type = "consent_given"
        mock_log1.event_description = "Consent given for privacy policy"
        mock_log1.user_id = "user-123"
        mock_log1.consent_id = "consent-123"
        mock_log1.privacy_notice_id = "notice-123"
        mock_log1.performed_by = "user-123"
        mock_log1.performed_by_type = "user"
        mock_log1.ip_address = "192.168.1.1"
        mock_log1.created_at = datetime.now(timezone.utc)
        mock_log1.get_old_values_dict.return_value = {}
        mock_log1.get_new_values_dict.return_value = {"status": "given"}
        
        # Mock query
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            mock_log1
        ]
        
        # Get audit trail
        result = self.privacy_service.get_consent_audit_trail(
            user_id="user-123",
            limit=50,
            offset=0
        )
        
        # Verify result
        assert len(result) == 1
        assert result[0]["id"] == "log-1"
        assert result[0]["event_type"] == "consent_given"
        assert result[0]["user_id"] == "user-123"
        assert result[0]["new_values"]["status"] == "given"
    
    def test_get_consent_audit_trail_with_filters(self):
        """Test audit trail retrieval with filters."""
        # Mock query chain
        mock_query = self.mock_db.query.return_value
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        # Get audit trail with filters
        result = self.privacy_service.get_consent_audit_trail(
            user_id="user-123",
            consent_id="consent-123",
            limit=25,
            offset=10
        )
        
        # Verify query was called with correct parameters
        assert mock_query.offset.call_args[0][0] == 10
        assert mock_query.limit.call_args[0][0] == 25
        assert len(result) == 0