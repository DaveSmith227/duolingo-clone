"""
Password Reset Service

Service for handling password reset functionality including secure token generation,
validation, and password update operations with comprehensive security measures.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models.auth import PasswordResetToken, SupabaseUser
from app.models.user import User
from app.services.password_security import get_password_security
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity
from app.services.email_service import get_email_service

# Configure logging
logger = logging.getLogger(__name__)


class PasswordResetResult:
    """Result object for password reset operations."""
    
    def __init__(
        self,
        success: bool,
        message: str,
        token: str = None,
        error_code: str = None
    ):
        self.success = success
        self.message = message
        self.token = token
        self.error_code = error_code


class PasswordResetService:
    """
    Password reset service for secure token-based password reset functionality.
    
    Handles token generation, validation, email sending, and password updates
    with comprehensive security measures and audit logging.
    """
    
    def __init__(self, db: Session):
        """Initialize password reset service."""
        self.db = db
        self.settings = get_settings()
        self.password_security = get_password_security()
        self.audit_logger = get_audit_logger(db)
        self.email_service = get_email_service()
    
    async def request_password_reset(
        self,
        email: str,
        ip_address: str,
        user_agent: str
    ) -> PasswordResetResult:
        """
        Request password reset for a user.
        
        Args:
            email: User email address
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            PasswordResetResult with operation status
        """
        try:
            # Find user by email
            user = self.db.query(User).filter(User.email == email).first()
            if not user:
                # Don't reveal whether email exists - generic response
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_REQUEST,
                    success=False,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Email not found"
                )
                
                # Still return success to prevent email enumeration
                return PasswordResetResult(
                    success=True,
                    message="If the email address exists, a password reset link has been sent."
                )
            
            # Find associated Supabase user
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.email == email
            ).first()
            
            if not supabase_user:
                logger.error(f"No Supabase user found for email: {email}")
                return PasswordResetResult(
                    success=True,
                    message="If the email address exists, a password reset link has been sent."
                )
            
            # Check rate limiting - max 3 requests per hour
            recent_tokens = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.supabase_user_id == supabase_user.supabase_id,
                PasswordResetToken.created_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).count()
            
            if recent_tokens >= 3:
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_REQUEST,
                    success=False,
                    user_id=user.id,
                    email=email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Rate limit exceeded"
                )
                
                return PasswordResetResult(
                    success=False,
                    message="Too many password reset requests. Please try again later.",
                    error_code="rate_limit_exceeded"
                )
            
            # Invalidate any existing unused tokens
            existing_tokens = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.supabase_user_id == supabase_user.supabase_id,
                PasswordResetToken.is_used == False
            ).all()
            
            for token in existing_tokens:
                token.is_used = True
                token.used_at = datetime.now(timezone.utc)
            
            # Generate secure token
            raw_token = secrets.token_urlsafe(32)  # 256-bit token
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            
            # Create token expiration (1 hour from now)
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=self.settings.password_reset_expire_hours
            )
            
            # Create password reset token record
            reset_token = PasswordResetToken.create_reset_token(
                supabase_user_id=supabase_user.supabase_id,
                token_hash=token_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(reset_token)
            self.db.commit()
            
            # Send password reset email
            email_sent = await self.email_service.send_password_reset_email(
                email=email,
                reset_token=raw_token,
                user_name=user.display_name or user.first_name,
                ip_address=ip_address
            )
            
            if not email_sent:
                logger.error(f"Failed to send password reset email to {email}")
                # Don't fail the request - token is still valid
            
            # Log successful request
            await self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_RESET_REQUEST,
                success=True,
                user_id=user.id,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"token_id": reset_token.id}
            )
            
            return PasswordResetResult(
                success=True,
                message="If the email address exists, a password reset link has been sent.",
                token=reset_token.id  # Return token ID for tracking
            )
            
        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            self.db.rollback()
            
            return PasswordResetResult(
                success=False,
                message="An error occurred processing your request. Please try again.",
                error_code="internal_error"
            )
    
    async def confirm_password_reset(
        self,
        reset_token: str,
        new_password: str,
        ip_address: str,
        user_agent: str
    ) -> PasswordResetResult:
        """
        Confirm password reset with token and new password.
        
        Args:
            reset_token: Password reset token
            new_password: New password
            ip_address: Request IP address
            user_agent: Request user agent
            
        Returns:
            PasswordResetResult with operation status
        """
        try:
            # Hash the provided token
            token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
            
            # Find valid token
            reset_token_record = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used == False
            ).first()
            
            if not reset_token_record:
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Invalid or expired token"
                )
                
                return PasswordResetResult(
                    success=False,
                    message="Invalid or expired password reset token.",
                    error_code="invalid_token"
                )
            
            # Check if token is expired
            if reset_token_record.is_expired():
                reset_token_record.mark_as_used()
                self.db.commit()
                
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Token expired"
                )
                
                return PasswordResetResult(
                    success=False,
                    message="Password reset token has expired. Please request a new one.",
                    error_code="token_expired"
                )
            
            # Find associated user
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.supabase_id == reset_token_record.supabase_user_id
            ).first()
            
            if not supabase_user:
                logger.error(f"No Supabase user found for token: {reset_token_record.id}")
                return PasswordResetResult(
                    success=False,
                    message="Invalid password reset token.",
                    error_code="invalid_token"
                )
            
            user = self.db.query(User).filter(User.email == supabase_user.email).first()
            if not user:
                logger.error(f"No user found for email: {supabase_user.email}")
                return PasswordResetResult(
                    success=False,
                    message="Invalid password reset token.",
                    error_code="invalid_token"
                )
            
            # Validate new password
            validation_result = self.password_security.validate_password(new_password)
            if not validation_result.is_valid:
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
                    success=False,
                    user_id=user.id,
                    email=user.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Password validation failed"
                )
                
                return PasswordResetResult(
                    success=False,
                    message=f"Password validation failed: {', '.join(validation_result.violations)}",
                    error_code="password_validation_failed"
                )
            
            # Check password history (prevent reuse)
            is_reused = await self.password_security.check_password_history(
                supabase_user.supabase_id,
                new_password
            )
            
            if is_reused:
                await self.audit_logger.log_authentication_event(
                    event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
                    success=False,
                    user_id=user.id,
                    email=user.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message="Password reuse detected"
                )
                
                return PasswordResetResult(
                    success=False,
                    message="You cannot reuse a recent password. Please choose a different password.",
                    error_code="password_reused"
                )
            
            # Hash new password
            hash_result = self.password_security.hash_password(new_password)
            
            # Update password in Supabase and password history
            await self.password_security.update_user_password(
                supabase_user.supabase_id,
                hash_result.hash,
                hash_result.algorithm
            )
            
            # Mark token as used
            reset_token_record.mark_as_used()
            
            # Commit all changes
            self.db.commit()
            
            # Log successful password reset
            await self.audit_logger.log_authentication_event(
                event_type=AuditEventType.PASSWORD_RESET_CONFIRM,
                success=True,
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"token_id": reset_token_record.id}
            )
            
            return PasswordResetResult(
                success=True,
                message="Password has been reset successfully. You can now log in with your new password."
            )
            
        except Exception as e:
            logger.error(f"Password reset confirmation error: {str(e)}")
            self.db.rollback()
            
            return PasswordResetResult(
                success=False,
                message="An error occurred resetting your password. Please try again.",
                error_code="internal_error"
            )
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired password reset tokens.
        
        Returns:
            Number of tokens cleaned up
        """
        try:
            # Find expired tokens
            expired_tokens = self.db.query(PasswordResetToken).filter(
                PasswordResetToken.expires_at <= datetime.now(timezone.utc),
                PasswordResetToken.is_used == False
            ).all()
            
            # Mark as used
            count = 0
            for token in expired_tokens:
                token.mark_as_used()
                count += 1
            
            self.db.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired password reset tokens")
            
            return count
            
        except Exception as e:
            logger.error(f"Token cleanup error: {str(e)}")
            self.db.rollback()
            return 0


def get_password_reset_service(db: Session) -> PasswordResetService:
    """
    Get password reset service instance.
    
    Args:
        db: Database session
        
    Returns:
        PasswordResetService instance
    """
    return PasswordResetService(db)