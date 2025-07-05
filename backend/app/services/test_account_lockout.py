"""
Unit Tests for Account Lockout and Brute Force Protection Service

Tests for account lockout mechanisms, brute force detection, and security features.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from app.services.account_lockout import (
    AccountLockoutService,
    LockoutReason,
    LockoutStatus,
    ThreatLevel,
    LockoutPolicy,
    LockoutInfo,
    BruteForceAttempt,
    ThreatAssessment,
    get_account_lockout_service,
    check_account_lockout,
    record_failed_login,
    record_successful_login
)


class TestLockoutPolicy:
    """Test cases for LockoutPolicy dataclass."""
    
    def test_default_policy(self):
        """Test default lockout policy values."""
        policy = LockoutPolicy()
        
        assert policy.max_failed_attempts == 5
        assert policy.lockout_duration_minutes == 30
        assert policy.progressive_lockout is True
        assert policy.max_lockout_duration_hours == 24
        assert policy.rapid_fire_threshold_seconds == 5
        assert policy.permanent_lockout_threshold == 10
    
    def test_custom_policy(self):
        """Test custom lockout policy configuration."""
        policy = LockoutPolicy(
            max_failed_attempts=3,
            lockout_duration_minutes=60,
            progressive_lockout=False
        )
        
        assert policy.max_failed_attempts == 3
        assert policy.lockout_duration_minutes == 60
        assert policy.progressive_lockout is False


class TestLockoutInfo:
    """Test cases for LockoutInfo dataclass."""
    
    def test_lockout_info_creation(self):
        """Test LockoutInfo creation."""
        info = LockoutInfo(
            is_locked=True,
            lockout_reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
            locked_at=datetime.now(timezone.utc),
            unlock_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            attempt_count=5,
            lockout_count=1,
            threat_level=ThreatLevel.HIGH,
            can_retry_at=None,
            is_permanent=False
        )
        
        assert info.is_locked is True
        assert info.lockout_reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
        assert info.attempt_count == 5
        assert info.lockout_count == 1
        assert info.threat_level == ThreatLevel.HIGH
        assert info.is_permanent is False


class TestBruteForceAttempt:
    """Test cases for BruteForceAttempt dataclass."""
    
    def test_attempt_creation(self):
        """Test BruteForceAttempt creation."""
        attempt = BruteForceAttempt(
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False,
            error_type="invalid_password"
        )
        
        assert attempt.ip_address == "192.168.1.1"
        assert attempt.user_agent == "Mozilla/5.0"
        assert attempt.success is False
        assert attempt.error_type == "invalid_password"


class TestThreatAssessment:
    """Test cases for ThreatAssessment dataclass."""
    
    def test_threat_assessment_creation(self):
        """Test ThreatAssessment creation."""
        assessment = ThreatAssessment(
            threat_level=ThreatLevel.HIGH,
            risk_score=75,
            indicators=["rapid_fire_attempts", "multiple_ip_addresses"],
            recommended_action="progressive_lockout",
            confidence=0.8
        )
        
        assert assessment.threat_level == ThreatLevel.HIGH
        assert assessment.risk_score == 75
        assert len(assessment.indicators) == 2
        assert assessment.confidence == 0.8


class TestAccountLockoutService:
    """Test cases for AccountLockoutService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger."""
        return Mock()
    
    @pytest.fixture
    def lockout_service(self, mock_db):
        """AccountLockoutService instance with mocked dependencies."""
        with patch('app.services.account_lockout.get_audit_logger') as mock_get_logger:
            mock_get_logger.return_value = Mock()
            return AccountLockoutService(mock_db)
    
    def test_init_lockout_service(self, lockout_service, mock_db):
        """Test AccountLockoutService initialization."""
        assert lockout_service.db == mock_db
        assert lockout_service.settings is not None
        assert isinstance(lockout_service.policy, LockoutPolicy)
    
    def test_check_account_lockout_unlocked(self, lockout_service):
        """Test checking unlocked account."""
        with patch.object(lockout_service, '_get_lockout_info') as mock_get_info:
            mock_get_info.return_value = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=2,
                lockout_count=0,
                threat_level=ThreatLevel.LOW,
                can_retry_at=None,
                is_permanent=False
            )
            
            result = lockout_service.check_account_lockout(
                user_id="user-123",
                email="test@example.com"
            )
            
            assert result.is_locked is False
            assert result.attempt_count == 2
            assert result.threat_level == ThreatLevel.LOW
    
    def test_check_account_lockout_expired(self, lockout_service):
        """Test checking account with expired lockout."""
        past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        with patch.object(lockout_service, '_get_lockout_info') as mock_get_info, \
             patch.object(lockout_service, '_unlock_account') as mock_unlock:
            
            mock_get_info.return_value = LockoutInfo(
                is_locked=True,
                lockout_reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                locked_at=past_time - timedelta(minutes=30),
                unlock_at=past_time,
                attempt_count=5,
                lockout_count=1,
                threat_level=ThreatLevel.MEDIUM,
                can_retry_at=None,
                is_permanent=False
            )
            
            mock_unlock.return_value = True
            
            result = lockout_service.check_account_lockout(user_id="user-123")
            
            assert result.is_locked is False
            mock_unlock.assert_called_once()
    
    def test_record_failed_attempt_basic(self, lockout_service):
        """Test recording basic failed attempt."""
        with patch.object(lockout_service, 'check_account_lockout') as mock_check, \
             patch.object(lockout_service, '_assess_threat') as mock_assess, \
             patch.object(lockout_service, '_should_trigger_lockout') as mock_should_lock, \
             patch.object(lockout_service, '_store_attempt') as mock_store, \
             patch.object(lockout_service, '_log_security_event') as mock_log:
            
            mock_check.return_value = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=2,
                lockout_count=0,
                threat_level=ThreatLevel.LOW,
                can_retry_at=None,
                is_permanent=False
            )
            
            mock_assess.return_value = ThreatAssessment(
                threat_level=ThreatLevel.LOW,
                risk_score=20,
                indicators=[],
                recommended_action="continue_monitoring",
                confidence=0.6
            )
            
            mock_should_lock.return_value = (False, None)
            
            result = lockout_service.record_failed_attempt(
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1",
                error_type="invalid_password"
            )
            
            assert result.attempt_count == 3  # Incremented
            assert result.is_locked is False
            mock_store.assert_called_once()
            mock_log.assert_called_once()
    
    def test_record_failed_attempt_triggers_lockout(self, lockout_service):
        """Test recording failed attempt that triggers lockout."""
        with patch.object(lockout_service, 'check_account_lockout') as mock_check, \
             patch.object(lockout_service, '_assess_threat') as mock_assess, \
             patch.object(lockout_service, '_should_trigger_lockout') as mock_should_lock, \
             patch.object(lockout_service, '_apply_lockout') as mock_apply_lock, \
             patch.object(lockout_service, '_store_attempt') as mock_store, \
             patch.object(lockout_service, '_log_security_event') as mock_log:
            
            mock_check.return_value = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=4,
                lockout_count=0,
                threat_level=ThreatLevel.MEDIUM,
                can_retry_at=None,
                is_permanent=False
            )
            
            mock_assess.return_value = ThreatAssessment(
                threat_level=ThreatLevel.HIGH,
                risk_score=80,
                indicators=["rapid_fire_attempts"],
                recommended_action="progressive_lockout",
                confidence=0.9
            )
            
            mock_should_lock.return_value = (True, LockoutReason.FAILED_LOGIN_ATTEMPTS)
            
            locked_info = LockoutInfo(
                is_locked=True,
                lockout_reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                locked_at=datetime.now(timezone.utc),
                unlock_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                attempt_count=5,
                lockout_count=1,
                threat_level=ThreatLevel.HIGH,
                can_retry_at=None,
                is_permanent=False
            )
            
            mock_apply_lock.return_value = locked_info
            
            result = lockout_service.record_failed_attempt(
                user_id="user-123",
                error_type="invalid_password"
            )
            
            assert result.is_locked is True
            assert result.lockout_reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
            mock_apply_lock.assert_called_once()
    
    def test_record_successful_attempt(self, lockout_service):
        """Test recording successful attempt resets counters."""
        with patch.object(lockout_service, '_reset_attempt_counter') as mock_reset, \
             patch.object(lockout_service, '_store_attempt') as mock_store:
            
            lockout_service.record_successful_attempt(
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1"
            )
            
            mock_reset.assert_called_once_with("user-123", "test@example.com")
            mock_store.assert_called_once()
    
    def test_unlock_account_success(self, lockout_service):
        """Test successful account unlock."""
        with patch.object(lockout_service, '_unlock_account') as mock_unlock:
            mock_unlock.return_value = True
            
            result = lockout_service.unlock_account(
                user_id="user-123",
                admin_user_id="admin-456",
                reason="manual_unlock"
            )
            
            assert result is True
            mock_unlock.assert_called_once_with("user-123", None, "manual_unlock")
    
    def test_get_lockout_history(self, lockout_service):
        """Test getting lockout history."""
        mock_events = [
            {
                "id": "log-1",
                "event_type": "account_locked",
                "created_at": "2023-01-01T12:00:00Z",
                "user_id": "user-123"
            },
            {
                "id": "log-2", 
                "event_type": "account_unlocked",
                "created_at": "2023-01-01T12:30:00Z",
                "user_id": "user-123"
            }
        ]
        
        lockout_service.audit_logger.search_audit_logs.return_value = mock_events
        
        result = lockout_service.get_lockout_history(user_id="user-123", days=7)
        
        assert len(result) == 2
        assert result[0]["event_type"] == "account_locked"
        assert result[1]["event_type"] == "account_unlocked"
    
    def test_assess_threat_low_risk(self, lockout_service):
        """Test threat assessment for low risk scenario."""
        with patch.object(lockout_service, '_get_recent_attempts') as mock_get_attempts:
            mock_get_attempts.return_value = [
                BruteForceAttempt(
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
                    ip_address="192.168.1.1",
                    user_agent="Mozilla/5.0",
                    success=False
                )
            ]
            
            assessment = lockout_service._assess_threat(
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1",
                attempt=None
            )
            
            assert assessment.threat_level == ThreatLevel.LOW
            assert assessment.risk_score < 30
            assert "continue_monitoring" in assessment.recommended_action
    
    def test_assess_threat_rapid_fire(self, lockout_service):
        """Test threat assessment for rapid fire attacks."""
        now = datetime.now(timezone.utc)
        rapid_attempts = [
            BruteForceAttempt(
                timestamp=now - timedelta(seconds=i),
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                success=False
            )
            for i in range(5)
        ]
        
        with patch.object(lockout_service, '_get_recent_attempts') as mock_get_attempts:
            mock_get_attempts.return_value = rapid_attempts
            
            assessment = lockout_service._assess_threat(
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1",
                attempt=None
            )
            
            assert "rapid_fire_attempts" in assessment.indicators
            assert assessment.risk_score >= 30
    
    def test_assess_threat_multiple_ips(self, lockout_service):
        """Test threat assessment for multiple IP addresses."""
        now = datetime.now(timezone.utc)
        multi_ip_attempts = [
            BruteForceAttempt(
                timestamp=now - timedelta(minutes=i),
                ip_address=f"192.168.1.{i}",
                user_agent="Mozilla/5.0",
                success=False
            )
            for i in range(5)
        ]
        
        with patch.object(lockout_service, '_get_recent_attempts') as mock_get_attempts:
            mock_get_attempts.return_value = multi_ip_attempts
            
            assessment = lockout_service._assess_threat(
                user_id="user-123",
                email="test@example.com",
                ip_address="192.168.1.1",
                attempt=None
            )
            
            assert "multiple_ip_addresses" in assessment.indicators
            assert assessment.risk_score >= 25
    
    def test_should_trigger_lockout_attempt_threshold(self, lockout_service):
        """Test lockout trigger based on attempt count."""
        lockout_info = LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=5,  # At threshold
            lockout_count=0,
            threat_level=ThreatLevel.MEDIUM,
            can_retry_at=None,
            is_permanent=False
        )
        
        threat_assessment = ThreatAssessment(
            threat_level=ThreatLevel.MEDIUM,
            risk_score=50,
            indicators=[],
            recommended_action="continue_monitoring",
            confidence=0.7
        )
        
        attempt = BruteForceAttempt(
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=False
        )
        
        should_lock, reason = lockout_service._should_trigger_lockout(
            lockout_info, threat_assessment, attempt
        )
        
        assert should_lock is True
        assert reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
    
    def test_should_trigger_lockout_critical_threat(self, lockout_service):
        """Test lockout trigger based on critical threat level."""
        lockout_info = LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=2,  # Below threshold
            lockout_count=0,
            threat_level=ThreatLevel.CRITICAL,
            can_retry_at=None,
            is_permanent=False
        )
        
        threat_assessment = ThreatAssessment(
            threat_level=ThreatLevel.CRITICAL,
            risk_score=90,
            indicators=["potential_credential_stuffing", "bot_like_timing"],
            recommended_action="immediate_lockout",
            confidence=0.95
        )
        
        attempt = BruteForceAttempt(
            timestamp=datetime.now(timezone.utc),
            ip_address="192.168.1.1",
            user_agent="Bot/1.0",
            success=False
        )
        
        should_lock, reason = lockout_service._should_trigger_lockout(
            lockout_info, threat_assessment, attempt
        )
        
        assert should_lock is True
        assert reason == LockoutReason.AUTOMATED_THREAT_DETECTION
    
    def test_apply_lockout_basic(self, lockout_service):
        """Test applying basic lockout."""
        lockout_info = LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=5,
            lockout_count=0,
            threat_level=ThreatLevel.MEDIUM,
            can_retry_at=None,
            is_permanent=False
        )
        
        threat_assessment = ThreatAssessment(
            threat_level=ThreatLevel.MEDIUM,
            risk_score=60,
            indicators=["rapid_fire_attempts"],
            recommended_action="progressive_lockout",
            confidence=0.8
        )
        
        with patch.object(lockout_service, '_store_lockout_info') as mock_store:
            result = lockout_service._apply_lockout(
                user_id="user-123",
                email="test@example.com",
                reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                lockout_info=lockout_info,
                threat_assessment=threat_assessment
            )
            
            assert result.is_locked is True
            assert result.lockout_reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
            assert result.locked_at is not None
            assert result.unlock_at is not None
            assert result.lockout_count == 1
            mock_store.assert_called_once()
    
    def test_apply_lockout_progressive(self, lockout_service):
        """Test progressive lockout with increasing duration."""
        # Set progressive lockout policy
        lockout_service.policy.progressive_lockout = True
        lockout_service.policy.lockout_duration_minutes = 30
        
        lockout_info = LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=5,
            lockout_count=2,  # Third lockout
            threat_level=ThreatLevel.MEDIUM,
            can_retry_at=None,
            is_permanent=False
        )
        
        threat_assessment = ThreatAssessment(
            threat_level=ThreatLevel.MEDIUM,
            risk_score=60,
            indicators=[],
            recommended_action="progressive_lockout",
            confidence=0.8
        )
        
        with patch.object(lockout_service, '_store_lockout_info') as mock_store:
            result = lockout_service._apply_lockout(
                user_id="user-123",
                email="test@example.com",
                reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                lockout_info=lockout_info,
                threat_assessment=threat_assessment
            )
            
            # Duration should be 30 * 3 = 90 minutes for third lockout
            expected_unlock = result.locked_at + timedelta(minutes=90)
            assert abs((result.unlock_at - expected_unlock).total_seconds()) < 60
    
    def test_apply_lockout_permanent(self, lockout_service):
        """Test permanent lockout for excessive attempts."""
        lockout_service.policy.permanent_lockout_threshold = 10
        
        lockout_info = LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=12,  # Exceeds permanent threshold
            lockout_count=5,
            threat_level=ThreatLevel.HIGH,
            can_retry_at=None,
            is_permanent=False
        )
        
        threat_assessment = ThreatAssessment(
            threat_level=ThreatLevel.HIGH,
            risk_score=85,
            indicators=["distributed_attack_pattern"],
            recommended_action="immediate_lockout",
            confidence=0.9
        )
        
        with patch.object(lockout_service, '_store_lockout_info') as mock_store:
            result = lockout_service._apply_lockout(
                user_id="user-123",
                email="test@example.com",
                reason=LockoutReason.SUSPICIOUS_ACTIVITY,
                lockout_info=lockout_info,
                threat_assessment=threat_assessment
            )
            
            assert result.is_permanent is True
            assert result.unlock_at is None


class TestAccountLockoutUtilities:
    """Test cases for account lockout utility functions."""
    
    def test_get_account_lockout_service(self):
        """Test get_account_lockout_service factory function."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_audit_logger'):
            service = get_account_lockout_service(mock_db)
            
            assert isinstance(service, AccountLockoutService)
            assert service.db == mock_db
    
    def test_check_account_lockout_utility(self):
        """Test check_account_lockout utility function."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_account_lockout_service') as mock_get_service:
            mock_service = Mock()
            mock_service.check_account_lockout.return_value = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=1,
                lockout_count=0,
                threat_level=ThreatLevel.LOW,
                can_retry_at=None,
                is_permanent=False
            )
            mock_get_service.return_value = mock_service
            
            result = check_account_lockout(mock_db, user_id="user-123")
            
            assert isinstance(result, LockoutInfo)
            assert result.is_locked is False
            mock_service.check_account_lockout.assert_called_once_with("user-123", None, None)
    
    def test_record_failed_login_utility(self):
        """Test record_failed_login utility function."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_account_lockout_service') as mock_get_service:
            mock_service = Mock()
            mock_service.record_failed_attempt.return_value = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=2,
                lockout_count=0,
                threat_level=ThreatLevel.LOW,
                can_retry_at=None,
                is_permanent=False
            )
            mock_get_service.return_value = mock_service
            
            result = record_failed_login(
                mock_db,
                user_id="user-123",
                ip_address="192.168.1.1",
                error_type="invalid_password"
            )
            
            assert isinstance(result, LockoutInfo)
            assert result.attempt_count == 2
            mock_service.record_failed_attempt.assert_called_once()
    
    def test_record_successful_login_utility(self):
        """Test record_successful_login utility function."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_account_lockout_service') as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            
            record_successful_login(
                mock_db,
                user_id="user-123",
                ip_address="192.168.1.1"
            )
            
            mock_service.record_successful_attempt.assert_called_once_with(
                "user-123", None, "192.168.1.1", None
            )


class TestAccountLockoutIntegration:
    """Integration tests for account lockout service."""
    
    def test_complete_lockout_flow(self):
        """Test complete account lockout and unlock flow."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_audit_logger'):
            service = AccountLockoutService(mock_db)
            
            # Mock storage methods to simulate state persistence
            lockout_state = {}
            
            def mock_get_lockout_info(user_id, email):
                key = user_id or email or "default"
                return lockout_state.get(key, LockoutInfo(
                    is_locked=False,
                    lockout_reason=None,
                    locked_at=None,
                    unlock_at=None,
                    attempt_count=0,
                    lockout_count=0,
                    threat_level=ThreatLevel.LOW,
                    can_retry_at=None,
                    is_permanent=False
                ))
            
            def mock_store_lockout_info(user_id, email, info):
                key = user_id or email or "default"
                lockout_state[key] = info
                return info
            
            service._get_lockout_info = mock_get_lockout_info
            service._store_lockout_info = mock_store_lockout_info
            service._get_recent_attempts = lambda *args: []
            service._store_attempt = lambda *args: None
            service._log_security_event = lambda *args: None
            
            user_id = "user-123"
            
            # Test multiple failed attempts leading to lockout
            for i in range(6):  # One more than threshold
                result = service.record_failed_attempt(
                    user_id=user_id,
                    ip_address="192.168.1.1",
                    error_type="invalid_password"
                )
                
                if i < 4:  # Before threshold
                    assert result.is_locked is False
                    assert result.attempt_count == i + 1
                else:  # At or after threshold
                    assert result.is_locked is True
                    assert result.lockout_reason == LockoutReason.FAILED_LOGIN_ATTEMPTS
            
            # Test that lockout persists
            lockout_check = service.check_account_lockout(user_id=user_id)
            assert lockout_check.is_locked is True
            
            # Test manual unlock
            unlock_success = service.unlock_account(user_id=user_id, reason="admin_unlock")
            assert unlock_success is True
            
            # Test that account is now unlocked
            final_check = service.check_account_lockout(user_id=user_id)
            assert final_check.is_locked is False
    
    def test_progressive_lockout_duration(self):
        """Test that lockout duration increases progressively."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_audit_logger'):
            service = AccountLockoutService(mock_db)
            service.policy.progressive_lockout = True
            service.policy.lockout_duration_minutes = 30
            
            lockout_info = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=5,
                lockout_count=0,
                threat_level=ThreatLevel.MEDIUM,
                can_retry_at=None,
                is_permanent=False
            )
            
            threat_assessment = ThreatAssessment(
                threat_level=ThreatLevel.MEDIUM,
                risk_score=60,
                indicators=[],
                recommended_action="progressive_lockout",
                confidence=0.8
            )
            
            with patch.object(service, '_store_lockout_info'):
                # First lockout
                result1 = service._apply_lockout(
                    user_id="user-123",
                    email=None,
                    reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                    lockout_info=lockout_info,
                    threat_assessment=threat_assessment
                )
                
                duration1 = (result1.unlock_at - result1.locked_at).total_seconds() / 60
                assert duration1 == 30  # Base duration
                
                # Second lockout (simulate repeated offense)
                lockout_info.lockout_count = 1
                result2 = service._apply_lockout(
                    user_id="user-123",
                    email=None,
                    reason=LockoutReason.FAILED_LOGIN_ATTEMPTS,
                    lockout_info=lockout_info,
                    threat_assessment=threat_assessment
                )
                
                duration2 = (result2.unlock_at - result2.locked_at).total_seconds() / 60
                assert duration2 == 60  # 2x base duration
    
    def test_threat_level_escalation(self):
        """Test threat level affects lockout decisions."""
        mock_db = Mock()
        
        with patch('app.services.account_lockout.get_audit_logger'):
            service = AccountLockoutService(mock_db)
            
            # Test that critical threat triggers immediate lockout
            lockout_info = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=2,  # Below normal threshold
                lockout_count=0,
                threat_level=ThreatLevel.CRITICAL,
                can_retry_at=None,
                is_permanent=False
            )
            
            threat_assessment = ThreatAssessment(
                threat_level=ThreatLevel.CRITICAL,
                risk_score=95,
                indicators=["potential_credential_stuffing", "bot_like_timing"],
                recommended_action="immediate_lockout",
                confidence=0.95
            )
            
            attempt = BruteForceAttempt(
                timestamp=datetime.now(timezone.utc),
                ip_address="192.168.1.1",
                user_agent="Bot/1.0",
                success=False
            )
            
            should_lock, reason = service._should_trigger_lockout(
                lockout_info, threat_assessment, attempt
            )
            
            assert should_lock is True
            assert reason == LockoutReason.AUTOMATED_THREAT_DETECTION