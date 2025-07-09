"""
User registration endpoints and functionality.
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.auth import AuthSession, PasswordHistory
from app.schemas.auth import UserRegistrationRequest as UserRegister, UserResponse, AuthenticationResponse
from app.services.auth_service import AuthService
from app.services.cookie_manager import CookieManager
from app.core.exceptions import RateLimitExceededError
from app.middleware.validation import validate_request, Validators
from .auth_utils import get_client_info, create_user_response

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/register", response_model=AuthenticationResponse)
@validate_request(**Validators.registration_validator())
async def register(
    request: Request,
    response: Response,
    data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user with email and password."""
    # Initialize services
    auth_service = AuthService(db)
    cookie_manager = CookieManager(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Check rate limiting
    rate_limit_result = await rate_limiter.check_rate_limit(
        "registration",
        client_info["ip_address"],
        max_requests=5,
        window_minutes=60
    )
    
    if not rate_limit_result["allowed"]:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="registration_rate_limited",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            details={"retry_after": rate_limit_result["retry_after"]}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {rate_limit_result['retry_after']} seconds."
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == sanitized_data["email"]).first()
    if existing_user:
        await audit_logger.log_event(
            user_id=None,
            event_type="registration_duplicate_email",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"email": sanitized_data["email"]}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Please login or reset your password."
        )
    
    # Validate password strength
    try:
        password_security.validate_password_strength(sanitized_data["password"])
    except ValueError as e:
        await audit_logger.log_event(
            user_id=None,
            event_type="registration_weak_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create user in Supabase Auth
    supabase_user = None
    try:
        auth_response = supabase.auth.sign_up({
            "email": sanitized_data["email"],
            "password": sanitized_data["password"],
            "options": {
                "data": {
                    "first_name": sanitized_data.get("first_name", ""),
                    "last_name": sanitized_data.get("last_name", ""),
                    "marketing_consent": sanitized_data.get("marketing_consent", False)
                }
            }
        })
        
        if auth_response.user:
            supabase_user = auth_response.user
        else:
            raise Exception("Failed to create user in Supabase Auth")
            
    except Exception as e:
        logger.error(f"Supabase registration error: {str(e)}")
        await audit_logger.log_security_event(
            user_id=None,
            event_type="registration_supabase_error",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again later."
        )
    
    # Create user in database
    new_user = None
    try:
        # Hash password for local storage
        password_hash = password_security.hash_password(sanitized_data["password"])
        
        # Create user
        new_user = User(
            id=supabase_user.id,
            email=sanitized_data["email"],
            password_hash=password_hash,
            first_name=sanitized_data.get("first_name", ""),
            last_name=sanitized_data.get("last_name", ""),
            role="user",
            is_active=True,
            is_verified=False,
            marketing_consent=sanitized_data.get("marketing_consent", False),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.flush()  # Get the user ID without committing
        
        # Create user profile
        profile = UserProfile(
            user_id=new_user.id,
            display_name=f"{new_user.first_name} {new_user.last_name}".strip() or new_user.email.split("@")[0],
            preferred_language=sanitized_data.get("language", "en"),
            timezone=sanitized_data.get("timezone", "UTC"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(profile)
        
        # Add password to history
        password_history = PasswordHistory(
            user_id=new_user.id,
            password_hash=password_hash,
            created_at=datetime.utcnow()
        )
        db.add(password_history)
        
        # Commit all changes
        db.commit()
        db.refresh(new_user)
        
        # Sync with external services
        await user_sync.sync_user_creation(new_user)
        
    except IntegrityError as e:
        db.rollback()
        # Clean up Supabase user if database creation fails
        if supabase_user:
            try:
                supabase.auth.admin.delete_user(supabase_user.id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup Supabase user: {cleanup_error}")
        
        logger.error(f"Database integrity error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed. Please try again."
        )
    except Exception as e:
        db.rollback()
        # Clean up Supabase user if database creation fails
        if supabase_user:
            try:
                supabase.auth.admin.delete_user(supabase_user.id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup Supabase user: {cleanup_error}")
        
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )
    
    # Create session
    session_data = await session_manager.create_session(
        new_user,
        {
            "ip_address": client_info["ip_address"],
            "user_agent": client_info["user_agent"],
            "device_fingerprint": client_info.get("device_fingerprint", "")
        }
    )
    
    # Set auth cookies
    cookie_manager.set_auth_cookies(
        response,
        session_data["access_token"],
        session_data["refresh_token"]
    )
    
    # Log successful registration
    await audit_logger.log_event(
        user_id=new_user.id,
        event_type="registration_success",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True,
        details={
            "registration_method": "email",
            "marketing_consent": new_user.marketing_consent
        }
    )
    
    # Send verification email (async, don't wait)
    # await email_service.send_verification_email(new_user)
    
    return {
        "access_token": session_data["access_token"],
        "refresh_token": session_data["refresh_token"],
        "token_type": "bearer",
        "expires_in": session_data["expires_in"],
        "user": create_user_response(new_user)
    }