"""
User login and social authentication endpoints.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User, UserProfile
from app.models.auth import AuthSession, SocialLogin
from app.schemas.auth import UserLogin, SocialAuthRequest, AuthTokenResponse
from app.services.rate_limiter import RateLimiter
from app.services.password_security import PasswordSecurity
from app.services.session_manager import SessionManager
from app.services.account_lockout import AccountLockout
from app.services.audit_logger import AuditLogger
from app.services.user_sync_service import UserSyncService
from app.services.cookie_manager import CookieManager
from app.core.supabase import get_supabase_client
from app.middleware.validation import validate_request, Validators
from .auth_utils import (
    get_client_info, 
    create_user_response, 
    verify_oauth_token,
    sanitize_user_input
)

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/login", response_model=AuthTokenResponse)
@validate_request(**Validators.login_validator())
async def login(
    request: Request,
    response: Response,
    data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user with email and password."""
    # Initialize services
    rate_limiter = RateLimiter(settings)
    password_security = PasswordSecurity(db, settings)
    session_manager = SessionManager(db, settings)
    account_lockout = AccountLockout(db, settings)
    audit_logger = AuditLogger(db)
    cookie_manager = CookieManager(settings)
    supabase = get_supabase_client()
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Sanitize input
    sanitized_data = sanitize_user_input(data.dict())
    
    # Check rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        "login",
        client_info["ip_address"],
        max_requests=10,
        window_minutes=15
    )
    
    if not rate_limit_result["allowed"]:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="login_rate_limited",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            details={
                "email": sanitized_data["email"],
                "retry_after": rate_limit_result["retry_after"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {rate_limit_result['retry_after']} seconds."
        )
    
    # Find user
    user = db.query(User).filter(User.email == sanitized_data["email"]).first()
    
    if not user:
        # Log failed attempt for non-existent user
        await audit_logger.log_event(
            user_id=None,
            event_type="login_failed_user_not_found",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"email": sanitized_data["email"]}
        )
        # Generic error to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is locked
    if await account_lockout.is_account_locked(user.id):
        lockout_info = await account_lockout.get_lockout_info(user.id)
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="login_attempt_locked_account",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={
                "lockout_expires": lockout_info.get("expires_at"),
                "failed_attempts": lockout_info.get("failed_attempts")
            }
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is temporarily locked. Try again after {lockout_info.get('expires_at')}"
        )
    
    # Verify password
    if not password_security.verify_password(sanitized_data["password"], user.password_hash):
        # Record failed attempt
        await account_lockout.record_failed_attempt(user.id)
        
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="login_failed_invalid_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={
                "failed_attempts": await account_lockout.get_failed_attempts(user.id)
            }
        )
        
        # Check if account should be locked after this attempt
        if await account_lockout.should_lock_account(user.id):
            await account_lockout.lock_account(user.id)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Too many failed attempts. Account has been temporarily locked."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="login_failed_inactive_account",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )
    
    # Clear failed attempts on successful login
    await account_lockout.clear_failed_attempts(user.id)
    
    # Check if MFA is enabled
    from app.services.mfa_service import MFAService
    mfa_service = MFAService(db, settings)
    
    if await mfa_service.is_mfa_enabled(user.id):
        # Create temporary MFA session
        from app.models.auth import MFAChallenge
        import secrets
        
        challenge_token = secrets.token_urlsafe(32)
        mfa_challenge = MFAChallenge(
            user_id=user.id,
            challenge_token=challenge_token,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            created_at=datetime.utcnow()
        )
        db.add(mfa_challenge)
        db.commit()
        
        # Return MFA required response
        return {
            "mfa_required": True,
            "challenge_token": challenge_token,
            "message": "Please provide your 2FA code to complete login"
        }
    
    # Create session
    session_data = await session_manager.create_session(
        user,
        {
            "ip_address": client_info["ip_address"],
            "user_agent": client_info["user_agent"],
            "device_fingerprint": client_info.get("device_fingerprint", ""),
            "remember_me": sanitized_data.get("remember_me", False)
        }
    )
    
    # Set auth cookies
    cookie_manager.set_auth_cookies(
        response,
        session_data["access_token"],
        session_data["refresh_token"],
        remember_me=sanitized_data.get("remember_me", False)
    )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_info["ip_address"]
    db.commit()
    
    # Log successful login
    await audit_logger.log_event(
        user_id=user.id,
        event_type="login_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True,
        details={
            "login_method": "email",
            "remember_me": sanitized_data.get("remember_me", False)
        }
    )
    
    return {
        "access_token": session_data["access_token"],
        "refresh_token": session_data["refresh_token"],
        "token_type": "bearer",
        "expires_in": session_data["expires_in"],
        "user": create_user_response(user)
    }


@router.post("/social", response_model=AuthTokenResponse)
async def social_auth(
    request: Request,
    response: Response,
    data: SocialAuthRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user via social provider."""
    # Initialize services
    rate_limiter = RateLimiter(settings)
    session_manager = SessionManager(db, settings)
    audit_logger = AuditLogger(db)
    user_sync = UserSyncService(db)
    cookie_manager = CookieManager(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Check rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        "social_auth",
        client_info["ip_address"],
        max_requests=20,
        window_minutes=15
    )
    
    if not rate_limit_result["allowed"]:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="social_auth_rate_limited",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            details={
                "provider": data.provider,
                "retry_after": rate_limit_result["retry_after"]
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many authentication attempts. Try again in {rate_limit_result['retry_after']} seconds."
        )
    
    # Verify OAuth token with provider
    try:
        user_info = await verify_oauth_token(data.provider, data.token)
    except HTTPException as e:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="social_auth_token_verification_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={
                "provider": data.provider,
                "error": e.detail
            }
        )
        raise
    
    # Check if user exists
    user = db.query(User).filter(User.email == user_info["email"]).first()
    
    if not user:
        # Create new user from social login
        user = User(
            email=user_info["email"],
            first_name=user_info.get("first_name", ""),
            last_name=user_info.get("last_name", ""),
            role="user",
            is_active=True,
            is_verified=user_info.get("verified", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        db.flush()
        
        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            display_name=f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0],
            preferred_language="en",
            timezone="UTC",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(profile)
        
        # Sync with external services
        await user_sync.sync_user_creation(user)
    
    # Record social login
    social_login = SocialLogin(
        user_id=user.id,
        provider=data.provider,
        provider_user_id=user_info["provider_id"],
        created_at=datetime.utcnow(),
        last_login_at=datetime.utcnow()
    )
    
    # Check if social login already exists
    existing_social = db.query(SocialLogin).filter(
        SocialLogin.user_id == user.id,
        SocialLogin.provider == data.provider
    ).first()
    
    if existing_social:
        existing_social.last_login_at = datetime.utcnow()
    else:
        db.add(social_login)
    
    # Update user last login
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = client_info["ip_address"]
    
    db.commit()
    db.refresh(user)
    
    # Create session
    session_data = await session_manager.create_session(
        user,
        {
            "ip_address": client_info["ip_address"],
            "user_agent": client_info["user_agent"],
            "device_fingerprint": client_info.get("device_fingerprint", ""),
            "auth_method": f"social_{data.provider}"
        }
    )
    
    # Set auth cookies
    cookie_manager.set_auth_cookies(
        response,
        session_data["access_token"],
        session_data["refresh_token"]
    )
    
    # Log successful social login
    await audit_logger.log_event(
        user_id=user.id,
        event_type="social_login_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True,
        details={
            "provider": data.provider,
            "new_user": existing_social is None
        }
    )
    
    return {
        "access_token": session_data["access_token"],
        "refresh_token": session_data["refresh_token"],
        "token_type": "bearer",
        "expires_in": session_data["expires_in"],
        "user": create_user_response(user)
    }