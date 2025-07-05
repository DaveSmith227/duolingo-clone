"""
Account Lockout and Brute Force Protection Service

Comprehensive account security with intelligent lockout mechanisms, brute force detection,
and progressive security measures for authentication protection.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth import AuthAuditLog, SupabaseUser
from app.services.audit_logger import AuditLogger, AuditEventType, AuditSeverity, get_audit_logger

logger = logging.getLogger(__name__)


class LockoutReason(Enum):
    """Account lockout reason types."""
    FAILED_LOGIN_ATTEMPTS = "failed_login_attempts"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MULTIPLE_IP_ATTEMPTS = "multiple_ip_attempts"
    RAPID_FIRE_ATTEMPTS = "rapid_fire_attempts"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SECURITY_VIOLATION = "security_violation"
    MANUAL_LOCKOUT = "manual_lockout"
    AUTOMATED_THREAT_DETECTION = "automated_threat_detection"


class LockoutStatus(Enum):
    """Account lockout status."""
    ACTIVE = "active"
    UNLOCKED = "unlocked"
    EXPIRED = "expired"
    MANUALLY_UNLOCKED = "manually_unlocked"


class ThreatLevel(Enum):
    """Threat assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LockoutPolicy:
    """Account lockout policy configuration."""
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    progressive_lockout: bool = True
    max_lockout_duration_hours: int = 24
    rapid_fire_threshold_seconds: int = 5
    rapid_fire_max_attempts: int = 3
    multiple_ip_threshold: int = 3
    multiple_ip_window_hours: int = 1
    suspicious_pattern_detection: bool = True
    auto_unlock_enabled: bool = True
    notification_enabled: bool = True
    permanent_lockout_threshold: int = 10  # Failed attempts before permanent lockout


@dataclass
class LockoutInfo:
    """Account lockout information."""
    is_locked: bool
    lockout_reason: Optional[LockoutReason]
    locked_at: Optional[datetime]
    unlock_at: Optional[datetime]
    attempt_count: int
    lockout_count: int
    threat_level: ThreatLevel
    can_retry_at: Optional[datetime]
    is_permanent: bool = False
    lockout_id: Optional[str] = None


@dataclass
class BruteForceAttempt:
    """Brute force attempt record."""
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool
    error_type: Optional[str] = None
    geolocation: Optional[Dict[str, Any]] = None


@dataclass
class ThreatAssessment:
    """Security threat assessment."""
    threat_level: ThreatLevel
    risk_score: int  # 0-100
    indicators: List[str]
    recommended_action: str
    confidence: float  # 0.0-1.0


class AccountLockoutService:
    """
    Comprehensive account lockout and brute force protection service.
    
    Provides intelligent account lockout mechanisms with progressive penalties,
    threat detection, and automated security responses.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.audit_logger = get_audit_logger(db)
        
        # Load lockout policy from settings
        self.policy = LockoutPolicy(
            max_failed_attempts=getattr(self.settings, 'lockout_max_failed_attempts', 5),
            lockout_duration_minutes=getattr(self.settings, 'lockout_duration_minutes', 30),
            progressive_lockout=getattr(self.settings, 'lockout_progressive_enabled', True),
            max_lockout_duration_hours=getattr(self.settings, 'lockout_max_duration_hours', 24),
            rapid_fire_threshold_seconds=getattr(self.settings, 'rapid_fire_threshold_seconds', 5),
            rapid_fire_max_attempts=getattr(self.settings, 'rapid_fire_max_attempts', 3),
            multiple_ip_threshold=getattr(self.settings, 'multiple_ip_threshold', 3),
            multiple_ip_window_hours=getattr(self.settings, 'multiple_ip_window_hours', 1),
            permanent_lockout_threshold=getattr(self.settings, 'permanent_lockout_threshold', 10)
        )
        
        # Import here to avoid circular imports
        try:
            from app.services.rate_limiter import get_rate_limiter
            self.rate_limiter = get_rate_limiter()
        except ImportError:
            logger.warning("Rate limiter not available for account lockout service")
            self.rate_limiter = None
    
    def check_account_lockout(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> LockoutInfo:
        """
        Check if account is locked due to security violations.
        
        Args:
            user_id: User ID to check
            email: Email address to check
            ip_address: IP address to check
            
        Returns:
            LockoutInfo with current lockout status
        """
        try:
            # Get current lockout info from cache/database
            lockout_info = self._get_lockout_info(user_id, email)
            
            # Check if lockout has expired
            if lockout_info.is_locked and lockout_info.unlock_at:
                if datetime.now(timezone.utc) >= lockout_info.unlock_at:
                    if not lockout_info.is_permanent:
                        # Auto-unlock expired lockout
                        self._unlock_account(user_id, email, "automatic_expiry")
                        lockout_info.is_locked = False
                        lockout_info.lockout_reason = None
            
            return lockout_info
            
        except Exception as e:
            logger.error(f"Failed to check account lockout: {str(e)}")
            # Fail secure - return locked status on error
            return LockoutInfo(
                is_locked=True,
                lockout_reason=LockoutReason.SECURITY_VIOLATION,
                locked_at=datetime.now(timezone.utc),
                unlock_at=None,
                attempt_count=0,
                lockout_count=0,
                threat_level=ThreatLevel.HIGH,
                can_retry_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                is_permanent=False
            )
    
    def record_failed_attempt(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_type: str = "invalid_credentials",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> LockoutInfo:
        """
        Record failed authentication attempt and apply lockout if necessary.
        
        Args:
            user_id: User ID
            email: Email address
            ip_address: IP address
            user_agent: User agent string
            error_type: Type of authentication error
            additional_context: Additional context for threat assessment
            
        Returns:
            Updated lockout information
        """
        try:
            # Record the attempt
            attempt = BruteForceAttempt(
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address or "unknown",
                user_agent=user_agent or "",
                success=False,
                error_type=error_type
            )
            
            # Get current lockout status
            lockout_info = self.check_account_lockout(user_id, email, ip_address)
            
            # Don't increment attempts if already permanently locked
            if lockout_info.is_permanent:
                return lockout_info
            
            # Perform threat assessment
            threat_assessment = self._assess_threat(
                user_id, email, ip_address, attempt, additional_context
            )
            
            # Increment attempt counter
            lockout_info.attempt_count += 1
            lockout_info.threat_level = threat_assessment.threat_level
            
            # Check if lockout should be triggered
            should_lockout, lockout_reason = self._should_trigger_lockout(
                lockout_info, threat_assessment, attempt
            )
            
            if should_lockout:
                lockout_info = self._apply_lockout(
                    user_id, email, lockout_reason, lockout_info, threat_assessment
                )
            
            # Store attempt and update counters
            self._store_attempt(user_id, email, attempt, lockout_info)
            
            # Update stored lockout info with new attempt count
            if not should_lockout:
                self._store_lockout_info(user_id, email, lockout_info)
            
            # Log security event
            self._log_security_event(
                user_id, email, ip_address, attempt, lockout_info, threat_assessment
            )
            
            return lockout_info
            
        except Exception as e:
            logger.error(f"Failed to record failed attempt: {str(e)}")
            # Return current status on error
            return self.check_account_lockout(user_id, email, ip_address)
    
    def record_successful_attempt(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Record successful authentication attempt and reset counters if appropriate.
        
        Args:
            user_id: User ID
            email: Email address
            ip_address: IP address
            user_agent: User agent string
        """
        try:
            # Reset failed attempt counter on successful login
            self._reset_attempt_counter(user_id, email)
            
            # Record successful attempt
            attempt = BruteForceAttempt(
                timestamp=datetime.now(timezone.utc),
                ip_address=ip_address or "unknown",
                user_agent=user_agent or "",
                success=True
            )
            
            self._store_attempt(user_id, email, attempt, None)
            
            # Log successful authentication
            self.audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_SUCCESS,
                success=True,
                user_id=user_id,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
        except Exception as e:
            logger.error(f"Failed to record successful attempt: {str(e)}")
    
    def unlock_account(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        admin_user_id: Optional[str] = None,
        reason: str = "manual_unlock"
    ) -> bool:
        """
        Manually unlock a locked account.
        
        Args:
            user_id: User ID to unlock
            email: Email address to unlock
            admin_user_id: Admin performing the unlock
            reason: Reason for unlocking
            
        Returns:
            True if successfully unlocked
        """
        try:
            success = self._unlock_account(user_id, email, reason)
            
            if success:
                # Log admin action
                if admin_user_id:
                    self.audit_logger.log_admin_action(
                        action="unlock_account",
                        admin_user_id=admin_user_id,
                        target_user_id=user_id,
                        resource="account_security",
                        changes={"unlocked": True, "reason": reason}
                    )
                
                # Log security event
                self.audit_logger.log_security_event(
                    event_type=AuditEventType.ACCOUNT_UNLOCKED,
                    description=f"Account unlocked: {reason}",
                    user_id=user_id,
                    severity=AuditSeverity.MEDIUM
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to unlock account: {str(e)}")
            return False
    
    def get_lockout_history(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get account lockout history.
        
        Args:
            user_id: User ID
            email: Email address
            days: Number of days to look back
            
        Returns:
            List of lockout events
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Query audit logs for lockout events
            lockout_events = self.audit_logger.search_audit_logs(
                event_types=[
                    AuditEventType.ACCOUNT_LOCKED,
                    AuditEventType.ACCOUNT_UNLOCKED,
                    AuditEventType.LOGIN_FAILURE
                ],
                user_id=user_id,
                start_date=start_date,
                limit=100
            )
            
            return lockout_events
            
        except Exception as e:
            logger.error(f"Failed to get lockout history: {str(e)}")
            return []
    
    def get_threat_assessment(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> ThreatAssessment:
        """
        Get current threat assessment for account/IP.
        
        Args:
            user_id: User ID
            email: Email address
            ip_address: IP address
            
        Returns:
            Current threat assessment
        """
        try:
            # Analyze recent activity patterns
            recent_attempts = self._get_recent_attempts(user_id, email, ip_address)
            
            return self._assess_threat(user_id, email, ip_address, None, {
                "recent_attempts": recent_attempts
            })
            
        except Exception as e:
            logger.error(f"Failed to get threat assessment: {str(e)}")
            return ThreatAssessment(
                threat_level=ThreatLevel.MEDIUM,
                risk_score=50,
                indicators=["assessment_error"],
                recommended_action="manual_review",
                confidence=0.5
            )
    
    def _get_lockout_info(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None
    ) -> LockoutInfo:
        """Get current lockout information from storage."""
        # In a real implementation, this would query Redis or database
        # For now, return default unlocked state
        return LockoutInfo(
            is_locked=False,
            lockout_reason=None,
            locked_at=None,
            unlock_at=None,
            attempt_count=0,
            lockout_count=0,
            threat_level=ThreatLevel.LOW,
            can_retry_at=None,
            is_permanent=False
        )
    
    def _assess_threat(
        self,
        user_id: Optional[str],
        email: Optional[str],
        ip_address: Optional[str],
        attempt: Optional[BruteForceAttempt],
        context: Optional[Dict[str, Any]] = None
    ) -> ThreatAssessment:
        """Assess security threat level based on attempt patterns."""
        indicators = []
        risk_score = 0
        
        # Analyze recent attempts
        recent_attempts = self._get_recent_attempts(user_id, email, ip_address)
        
        # Check for rapid-fire attempts
        if len(recent_attempts) >= self.policy.rapid_fire_max_attempts:
            rapid_attempts = [
                a for a in recent_attempts
                if (datetime.now(timezone.utc) - a.timestamp).total_seconds() 
                <= self.policy.rapid_fire_threshold_seconds
            ]
            if len(rapid_attempts) >= self.policy.rapid_fire_max_attempts:
                indicators.append("rapid_fire_attempts")
                risk_score += 30
        
        # Check for multiple IP addresses
        if user_id or email:
            unique_ips = set(a.ip_address for a in recent_attempts)
            if len(unique_ips) >= self.policy.multiple_ip_threshold:
                indicators.append("multiple_ip_addresses")
                risk_score += 25
        
        # Check for credential stuffing patterns
        if len(recent_attempts) > 10:
            user_agents = set(a.user_agent for a in recent_attempts)
            if len(user_agents) == 1 and len(recent_attempts) > 20:
                indicators.append("potential_credential_stuffing")
                risk_score += 40
        
        # Check for distributed attacks
        if ip_address:
            ip_attempts = [a for a in recent_attempts if a.ip_address == ip_address]
            if len(ip_attempts) > self.policy.max_failed_attempts * 2:
                indicators.append("distributed_attack_pattern")
                risk_score += 35
        
        # Check for suspicious timing patterns
        if len(recent_attempts) >= 5:
            intervals = []
            for i in range(1, len(recent_attempts)):
                interval = (recent_attempts[i].timestamp - recent_attempts[i-1].timestamp).total_seconds()
                intervals.append(interval)
            
            # Check for bot-like regular intervals
            if intervals and max(intervals) - min(intervals) < 2:  # Very regular timing
                indicators.append("bot_like_timing")
                risk_score += 20
        
        # Determine threat level
        if risk_score >= 80:
            threat_level = ThreatLevel.CRITICAL
            recommended_action = "immediate_lockout"
        elif risk_score >= 60:
            threat_level = ThreatLevel.HIGH
            recommended_action = "progressive_lockout"
        elif risk_score >= 30:
            threat_level = ThreatLevel.MEDIUM
            recommended_action = "increased_monitoring"
        else:
            threat_level = ThreatLevel.LOW
            recommended_action = "continue_monitoring"
        
        confidence = min(1.0, len(indicators) * 0.2 + 0.4)
        
        return ThreatAssessment(
            threat_level=threat_level,
            risk_score=risk_score,
            indicators=indicators,
            recommended_action=recommended_action,
            confidence=confidence
        )
    
    def _should_trigger_lockout(
        self,
        lockout_info: LockoutInfo,
        threat_assessment: ThreatAssessment,
        attempt: BruteForceAttempt
    ) -> Tuple[bool, LockoutReason]:
        """Determine if lockout should be triggered."""
        # Check attempt count threshold
        if lockout_info.attempt_count >= self.policy.max_failed_attempts:
            return True, LockoutReason.FAILED_LOGIN_ATTEMPTS
        
        # Check threat level
        if threat_assessment.threat_level == ThreatLevel.CRITICAL:
            return True, LockoutReason.AUTOMATED_THREAT_DETECTION
        
        # Check for rapid fire attempts
        if "rapid_fire_attempts" in threat_assessment.indicators:
            return True, LockoutReason.RAPID_FIRE_ATTEMPTS
        
        # Check for credential stuffing
        if "potential_credential_stuffing" in threat_assessment.indicators:
            return True, LockoutReason.CREDENTIAL_STUFFING
        
        # Check for suspicious patterns
        if threat_assessment.threat_level == ThreatLevel.HIGH and len(threat_assessment.indicators) >= 2:
            return True, LockoutReason.SUSPICIOUS_ACTIVITY
        
        return False, None
    
    def _apply_lockout(
        self,
        user_id: Optional[str],
        email: Optional[str],
        reason: LockoutReason,
        lockout_info: LockoutInfo,
        threat_assessment: ThreatAssessment
    ) -> LockoutInfo:
        """Apply account lockout with progressive penalties."""
        lockout_info.is_locked = True
        lockout_info.lockout_reason = reason
        lockout_info.locked_at = datetime.now(timezone.utc)
        lockout_info.lockout_count += 1
        
        # Calculate lockout duration based on policy and threat level
        base_duration = self.policy.lockout_duration_minutes
        
        if self.policy.progressive_lockout:
            # Progressive penalty: each lockout increases duration
            multiplier = min(lockout_info.lockout_count, 5)  # Cap at 5x
            duration_minutes = base_duration * multiplier
        else:
            duration_minutes = base_duration
        
        # Adjust based on threat level
        if threat_assessment.threat_level == ThreatLevel.CRITICAL:
            duration_minutes *= 3
        elif threat_assessment.threat_level == ThreatLevel.HIGH:
            duration_minutes *= 2
        
        # Cap at maximum duration
        max_duration_minutes = self.policy.max_lockout_duration_hours * 60
        duration_minutes = min(duration_minutes, max_duration_minutes)
        
        # Check for permanent lockout
        if lockout_info.attempt_count >= self.policy.permanent_lockout_threshold:
            lockout_info.is_permanent = True
            lockout_info.unlock_at = None
        else:
            lockout_info.unlock_at = lockout_info.locked_at + timedelta(minutes=duration_minutes)
        
        # Store lockout info
        self._store_lockout_info(user_id, email, lockout_info)
        
        # Log lockout event
        self.audit_logger.log_security_event(
            event_type=AuditEventType.ACCOUNT_LOCKED,
            description=f"Account locked: {reason.value}",
            user_id=user_id,
            severity=AuditSeverity.HIGH,
            threat_level=threat_assessment.threat_level.value,
            lockout_duration_minutes=duration_minutes,
            is_permanent=lockout_info.is_permanent
        )
        
        return lockout_info
    
    def _unlock_account(
        self,
        user_id: Optional[str],
        email: Optional[str],
        reason: str
    ) -> bool:
        """Unlock account and reset counters."""
        try:
            # Reset lockout info
            lockout_info = LockoutInfo(
                is_locked=False,
                lockout_reason=None,
                locked_at=None,
                unlock_at=None,
                attempt_count=0,
                lockout_count=0,
                threat_level=ThreatLevel.LOW,
                can_retry_at=None,
                is_permanent=False
            )
            
            self._store_lockout_info(user_id, email, lockout_info)
            return True
            
        except Exception as e:
            logger.error(f"Failed to unlock account: {str(e)}")
            return False
    
    def _reset_attempt_counter(self, user_id: Optional[str], email: Optional[str]) -> None:
        """Reset failed attempt counter on successful login."""
        try:
            lockout_info = self._get_lockout_info(user_id, email)
            lockout_info.attempt_count = 0
            lockout_info.threat_level = ThreatLevel.LOW
            self._store_lockout_info(user_id, email, lockout_info)
            
        except Exception as e:
            logger.error(f"Failed to reset attempt counter: {str(e)}")
    
    def _get_recent_attempts(
        self,
        user_id: Optional[str],
        email: Optional[str],
        ip_address: Optional[str],
        hours: int = 24
    ) -> List[BruteForceAttempt]:
        """Get recent authentication attempts for analysis."""
        # In a real implementation, this would query stored attempts
        # For now, return empty list
        return []
    
    def _store_attempt(
        self,
        user_id: Optional[str],
        email: Optional[str],
        attempt: BruteForceAttempt,
        lockout_info: Optional[LockoutInfo]
    ) -> None:
        """Store authentication attempt for analysis."""
        # In a real implementation, this would store in Redis or database
        pass
    
    def _store_lockout_info(
        self,
        user_id: Optional[str],
        email: Optional[str],
        lockout_info: LockoutInfo
    ) -> None:
        """Store lockout information."""
        # In a real implementation, this would store in Redis or database
        pass
    
    def _log_security_event(
        self,
        user_id: Optional[str],
        email: Optional[str],
        ip_address: Optional[str],
        attempt: BruteForceAttempt,
        lockout_info: LockoutInfo,
        threat_assessment: ThreatAssessment
    ) -> None:
        """Log security event for monitoring."""
        event_type = AuditEventType.LOGIN_FAILURE
        
        if lockout_info.is_locked:
            if lockout_info.lockout_reason == LockoutReason.FAILED_LOGIN_ATTEMPTS:
                event_type = AuditEventType.ACCOUNT_LOCKED
            else:
                event_type = AuditEventType.SUSPICIOUS_ACTIVITY
        
        self.audit_logger.log_security_event(
            event_type=event_type,
            description=f"Failed login attempt - {attempt.error_type}",
            user_id=user_id,
            ip_address=ip_address,
            severity=AuditSeverity.MEDIUM if not lockout_info.is_locked else AuditSeverity.HIGH,
            attempt_count=lockout_info.attempt_count,
            threat_level=threat_assessment.threat_level.value,
            risk_score=threat_assessment.risk_score,
            threat_indicators=threat_assessment.indicators
        )


# Global account lockout service instance
account_lockout_service: Optional[AccountLockoutService] = None


def get_account_lockout_service(db: Session) -> AccountLockoutService:
    """
    Get account lockout service instance.
    
    Args:
        db: Database session
        
    Returns:
        AccountLockoutService instance
    """
    return AccountLockoutService(db)


# Convenience functions

def check_account_lockout(
    db: Session,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None
) -> LockoutInfo:
    """Check if account is locked."""
    service = get_account_lockout_service(db)
    return service.check_account_lockout(user_id, email, ip_address)


def record_failed_login(
    db: Session,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_type: str = "invalid_credentials"
) -> LockoutInfo:
    """Record failed login attempt."""
    service = get_account_lockout_service(db)
    return service.record_failed_attempt(user_id, email, ip_address, user_agent, error_type)


def record_successful_login(
    db: Session,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Record successful login attempt."""
    service = get_account_lockout_service(db)
    service.record_successful_attempt(user_id, email, ip_address, user_agent)