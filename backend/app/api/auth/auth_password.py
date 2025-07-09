"""
Password management endpoints (reset, change).
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import secrets

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.auth import PasswordResetToken, PasswordHistory
from app.schemas.auth import PasswordResetRequest, PasswordResetConfirm
from app.services.rate_limiter import RateLimiter
from app.services.password_security import PasswordSecurity
from app.services.audit_logger import AuditLogger
from app.services.email_service import EmailService
from .auth_utils import get_client_info, sanitize_user_input

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/password-reset")
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset email."""
    # Initialize services
    rate_limiter = RateLimiter(settings)
    audit_logger = AuditLogger(db)
    email_service = EmailService(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Sanitize input
    sanitized_data = sanitize_user_input(data.dict())
    
    # Check rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        "password_reset",
        client_info["ip_address"],
        max_requests=3,
        window_minutes=60
    )
    
    if not rate_limit_result["allowed"]:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="password_reset_rate_limited",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            details={
                "email": sanitized_data["email"],
                "retry_after": rate_limit_result["retry_after"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset requests. Try again in {rate_limit_result['retry_after']} seconds."
        )
    
    # Find user
    user = db.query(User).filter(User.email == sanitized_data["email"]).first()
    
    # Always return success to prevent user enumeration
    if user and user.is_active:
        # Check for existing valid token
        existing_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).first()
        
        if existing_token:
            # Update expiration instead of creating new token
            existing_token.expires_at = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
            token = existing_token.token
        else:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Create reset token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                created_at=datetime.utcnow()
            )
            
            db.add(reset_token)
            db.commit()
        
        # Send reset email
        await email_service.send_password_reset_email(
            user.email,
            user.first_name,
            token
        )
        
        # Log password reset request
        await audit_logger.log_event(
            user_id=user.id,
            event_type="password_reset_requested",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
    else:
        # Log attempt for non-existent user
        await audit_logger.log_event(
            user_id=None,
            event_type="password_reset_requested_invalid_email",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"email": sanitized_data["email"]}
        )
    
    return {
        "message": "If an account exists with this email, you will receive a password reset link."
    }


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token."""
    # Initialize services
    password_security = PasswordSecurity(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Sanitize input
    sanitized_data = sanitize_user_input(data.dict())
    
    # Find valid reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == sanitized_data["token"],
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    
    if not reset_token:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="password_reset_invalid_token",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"token": sanitized_data["token"][:8] + "..."}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate new password
    try:
        password_security.validate_password_strength(sanitized_data["password"])
        
        # Check password history
        password_security.check_password_history(user.id, sanitized_data["password"])
        
    except ValueError as e:
        await audit_logger.log_event(
            user_id=user.id,
            event_type="password_reset_validation_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Update password
    new_password_hash = password_security.hash_password(sanitized_data["password"])
    user.password_hash = new_password_hash
    user.updated_at = datetime.utcnow()
    
    # Mark token as used
    reset_token.is_used = True
    reset_token.used_at = datetime.utcnow()
    reset_token.used_ip = client_info["ip_address"]
    
    # Add to password history
    password_history = PasswordHistory(
        user_id=user.id,
        password_hash=new_password_hash,
        created_at=datetime.utcnow()
    )
    db.add(password_history)
    
    # Invalidate all existing sessions
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        AuthSession.is_active == True
    ).update({"is_active": False})
    
    db.commit()
    
    # Log successful password reset
    await audit_logger.log_security_event(
        user_id=user.id,
        event_type="password_reset_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True
    )
    
    # Send confirmation email
    # await email_service.send_password_changed_email(user.email, user.first_name)
    
    return {
        "message": "Password has been reset successfully. Please login with your new password."
    }