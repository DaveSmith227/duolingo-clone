"""
Email verification endpoints.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import secrets

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.auth import EmailVerificationToken
from app.schemas.auth import EmailVerificationRequest, ResendVerificationRequest
from app.services.rate_limiter import RateLimiter
from app.services.audit_logger import AuditLogger
from app.services.email_service import EmailService
from .auth_utils import get_client_info

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/verify-email")
async def verify_email(
    request: Request,
    data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify user email address with token."""
    # Initialize services
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Find valid verification token
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == data.token,
        EmailVerificationToken.is_used == False,
        EmailVerificationToken.expires_at > datetime.utcnow()
    ).first()
    
    if not verification_token:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="email_verification_invalid_token",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"token": data.token[:8] + "..."}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == verification_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already verified
    if user.is_verified:
        return {
            "message": "Email is already verified",
            "is_verified": True
        }
    
    # Verify user
    user.is_verified = True
    user.verified_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    
    # Mark token as used
    verification_token.is_used = True
    verification_token.used_at = datetime.utcnow()
    verification_token.used_ip = client_info["ip_address"]
    
    db.commit()
    
    # Log successful verification
    await audit_logger.log_event(
        user_id=user.id,
        event_type="email_verification_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True
    )
    
    return {
        "message": "Email verified successfully",
        "is_verified": True
    }


@router.post("/resend-verification")
async def resend_verification_email(
    request: Request,
    data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """Resend email verification link."""
    # Initialize services
    rate_limiter = RateLimiter(settings)
    audit_logger = AuditLogger(db)
    email_service = EmailService(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Check rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        "resend_verification",
        client_info["ip_address"],
        max_requests=3,
        window_minutes=60
    )
    
    if not rate_limit_result["allowed"]:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="resend_verification_rate_limited",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            details={
                "email": data.email,
                "retry_after": rate_limit_result["retry_after"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification requests. Try again in {rate_limit_result['retry_after']} seconds."
        )
    
    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    
    # Always return success to prevent user enumeration
    if user and user.is_active and not user.is_verified:
        # Check for existing valid token
        existing_token = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.is_used == False,
            EmailVerificationToken.expires_at > datetime.utcnow()
        ).first()
        
        if existing_token:
            # Update expiration instead of creating new token
            existing_token.expires_at = datetime.utcnow() + timedelta(hours=24)
            db.commit()
            token = existing_token.token
        else:
            # Generate new verification token
            token = secrets.token_urlsafe(32)
            
            # Create verification token
            verification_token = EmailVerificationToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                created_at=datetime.utcnow()
            )
            
            db.add(verification_token)
            db.commit()
        
        # Send verification email
        await email_service.send_verification_email(
            user.email,
            user.first_name,
            token
        )
        
        # Log resend request
        await audit_logger.log_event(
            user_id=user.id,
            event_type="resend_verification_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
    else:
        # Log attempt for already verified or non-existent user
        await audit_logger.log_event(
            user_id=user.id if user else None,
            event_type="resend_verification_invalid",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={
                "email": data.email,
                "reason": "already_verified" if user and user.is_verified else "user_not_found"
            }
        )
    
    return {
        "message": "If your email is registered and not yet verified, you will receive a verification link."
    }