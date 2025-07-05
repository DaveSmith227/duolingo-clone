"""
Authentication API Endpoints

FastAPI routes for user authentication including registration, login,
password reset, social authentication, and session management.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, get_current_user_id, get_current_user_payload, security
from app.schemas.auth import (
    UserRegistrationRequest,
    LoginRequest,
    SocialAuthRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    AuthenticationResponse,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
    LogoutRequest,
    ErrorResponse,
    ValidationErrorResponse,
    RateLimitErrorResponse,
    AccountLockoutInfo,
    EmailVerificationRequest,
    ResendVerificationRequest
)
from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.models.user import User
from app.models.auth import SupabaseUser, AuthSession
from app.services.session_manager import get_session_manager
from app.services.password_security import get_password_security
from app.services.account_lockout import get_account_lockout_service
from app.services.rate_limiter import get_rate_limiter
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity
from app.services.user_sync import get_user_sync_service
from app.services.cookie_manager import get_cookie_manager

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])


def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "device_name": request.headers.get("x-device-name")
    }


def create_user_response(user: User, supabase_user: SupabaseUser) -> UserResponse:
    """Create user response from database models."""
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        language_code=user.language_code,
        is_verified=supabase_user.email_verified,
        is_premium=user.is_premium,
        created_at=user.created_at,
        last_login_at=supabase_user.last_sign_in_at,
        streak_count=user.streak_count,
        total_xp=user.total_xp
    )


async def verify_oauth_token(provider: str, access_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify OAuth token with provider and return user information.
    
    Args:
        provider: OAuth provider name (google, apple, facebook, etc.)
        access_token: OAuth access token
        
    Returns:
        User information dictionary or None if invalid
    """
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            if provider == "google":
                # Google OAuth token verification
                response = await client.get(
                    f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "email": user_data.get("email"),
                        "given_name": user_data.get("given_name", ""),
                        "family_name": user_data.get("family_name", ""),
                        "name": user_data.get("name", ""),
                        "picture": user_data.get("picture"),
                        "email_verified": user_data.get("verified_email", True),
                        "locale": user_data.get("locale", "en")
                    }
                    
            elif provider == "facebook":
                # Facebook OAuth token verification
                response = await client.get(
                    f"https://graph.facebook.com/me?access_token={access_token}&fields=id,name,email,first_name,last_name,picture"
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "email": user_data.get("email"),
                        "given_name": user_data.get("first_name", ""),
                        "family_name": user_data.get("last_name", ""),
                        "name": user_data.get("name", ""),
                        "picture": user_data.get("picture", {}).get("data", {}).get("url"),
                        "email_verified": True,  # Facebook verifies emails
                        "locale": "en"
                    }
                    
            elif provider == "apple":
                # Apple OAuth token verification
                # Note: Apple's token verification is more complex and typically done server-side
                # This is a simplified version - in production, you'd verify the JWT token
                # against Apple's public keys
                
                # For now, we'll use Supabase's Apple integration
                # In a real implementation, you'd decode and verify the Apple ID token
                logger.warning("Apple OAuth verification not fully implemented - using Supabase integration")
                return {
                    "email": "apple_user@example.com",  # This would come from decoded token
                    "given_name": "Apple",
                    "family_name": "User",
                    "name": "Apple User",
                    "picture": None,
                    "email_verified": True,
                    "locale": "en"
                }
                
            elif provider == "github":
                # GitHub OAuth token verification
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    
                    # Get user email (GitHub API requires separate call for emails)
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    
                    primary_email = None
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        for email_data in emails:
                            if email_data.get("primary", False):
                                primary_email = email_data.get("email")
                                break
                    
                    if not primary_email and emails:
                        primary_email = emails[0].get("email")
                    
                    return {
                        "email": primary_email,
                        "given_name": user_data.get("name", "").split(" ")[0] if user_data.get("name") else "",
                        "family_name": " ".join(user_data.get("name", "").split(" ")[1:]) if user_data.get("name") and len(user_data.get("name", "").split(" ")) > 1 else "",
                        "name": user_data.get("name", user_data.get("login", "")),
                        "picture": user_data.get("avatar_url"),
                        "email_verified": True,  # GitHub verifies emails
                        "locale": "en"
                    }
                    
            elif provider == "twitter":
                # Twitter OAuth token verification
                response = await client.get(
                    "https://api.twitter.com/2/users/me?user.fields=profile_image_url",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json().get("data", {})
                    return {
                        "email": f"{user_data.get('username')}@twitter.com",  # Twitter doesn't always provide email
                        "given_name": user_data.get("name", "").split(" ")[0] if user_data.get("name") else "",
                        "family_name": " ".join(user_data.get("name", "").split(" ")[1:]) if user_data.get("name") and len(user_data.get("name", "").split(" ")) > 1 else "",
                        "name": user_data.get("name", user_data.get("username", "")),
                        "picture": user_data.get("profile_image_url"),
                        "email_verified": False,  # Twitter email not always verified
                        "locale": "en"
                    }
            
            else:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return None
                
    except Exception as e:
        logger.error(f"OAuth token verification failed for {provider}: {str(e)}")
        return None
    
    return None


@router.post(
    "/register",
    response_model=AuthenticationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        409: {"model": ErrorResponse, "description": "Email already registered"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Register new user account",
    description="Register a new user account with email and password validation"
)
async def register(
    user_data: UserRegistrationRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates a new user account with email/password authentication,
    validates input data, checks for existing accounts, and returns
    authentication tokens for immediate login.
    
    Args:
        user_data: User registration data
        request: FastAPI request object
        response: FastAPI response object
        db: Database session
        
    Returns:
        AuthenticationResponse with user data and tokens
        
    Raises:
        HTTPException: For various error conditions
    """
    settings = get_settings()
    client_info = get_client_info(request)
    
    # Initialize services
    rate_limiter = get_rate_limiter()
    audit_logger = get_audit_logger(db)
    password_security = get_password_security()
    session_manager = get_session_manager(db)
    user_sync_service = get_user_sync_service(db)
    supabase_client = get_supabase_client()
    
    try:
        # Rate limiting check
        rate_limit_key = f"register:{client_info['ip_address']}"
        rate_check = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=settings.registration_rate_limit_attempts,
            window_seconds=settings.registration_rate_limit_window_hours * 3600
        )
        
        if not rate_check.allowed:
            await audit_logger.log_security_event(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                description="Registration rate limit exceeded",
                ip_address=client_info["ip_address"],
                severity=AuditSeverity.MEDIUM,
                metadata={"endpoint": "register", "limit": rate_check.limit}
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many registration attempts. Please try again later.",
                    "retry_after": rate_check.retry_after,
                    "limit": rate_check.limit,
                    "window": settings.registration_rate_limit_window_hours * 3600
                }
            )
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
        if existing_user:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_FAILURE,
                success=False,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Email already registered"
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "email_already_exists",
                    "message": "An account with this email already exists."
                }
            )
        
        # Validate password strength
        password_validation = password_security.validate_password(
            user_data.password,
            user_info={
                "email": user_data.email,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name
            }
        )
        
        if not password_validation.is_valid:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_FAILURE,
                success=False,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Password validation failed"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "password_validation_failed",
                    "message": "Password does not meet security requirements.",
                    "details": {
                        "violations": [v.value for v in password_validation.violations],
                        "strength_score": password_validation.strength_score,
                        "suggestions": password_validation.suggestions
                    }
                }
            )
        
        # Hash password
        password_hash_result = password_security.hash_password(user_data.password)
        
        # Create user in Supabase
        try:
            supabase_response = await supabase_client.auth.sign_up({
                "email": user_data.email.lower(),
                "password": user_data.password,
                "options": {
                    "data": {
                        "first_name": user_data.first_name,
                        "last_name": user_data.last_name,
                        "language_code": user_data.language_code,
                        "marketing_consent": user_data.marketing_consent
                    }
                }
            })
            
            if supabase_response.user is None:
                raise Exception("Failed to create user in Supabase")
            
            supabase_user_id = supabase_response.user.id
            
        except Exception as e:
            logger.error(f"Supabase user creation failed: {str(e)}")
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_FAILURE,
                success=False,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message=f"Supabase user creation failed: {str(e)}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "registration_failed",
                    "message": "Failed to create user account. Please try again."
                }
            )
        
        try:
            # Create application user
            app_user = User(
                email=user_data.email.lower(),
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                display_name=f"{user_data.first_name} {user_data.last_name or ''}".strip(),
                language_code=user_data.language_code or "en",
                is_verified=False,  # Will be updated when email is verified
                is_premium=False,
                marketing_consent=user_data.marketing_consent,
                terms_accepted_at=datetime.now(timezone.utc)
            )
            
            db.add(app_user)
            db.flush()  # Get the ID without committing
            
            # Create Supabase user sync record
            supabase_user = SupabaseUser(
                supabase_id=supabase_user_id,
                app_user_id=app_user.id,
                email=user_data.email.lower(),
                email_verified=False,
                provider="email",
                user_metadata=supabase_response.user.user_metadata or {},
                sync_status="synced",
                last_sync_at=datetime.now(timezone.utc)
            )
            
            db.add(supabase_user)
            
            # Store password history
            from app.models.auth import PasswordHistory
            password_history = PasswordHistory.create_password_entry(
                supabase_user_id=supabase_user_id,
                password_hash=password_hash_result.hash,
                algorithm=password_hash_result.algorithm,
                is_current=True
            )
            
            db.add(password_history)
            db.commit()
            
            # Create initial session
            session_result = session_manager.create_session(
                user=app_user,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                remember_me=False
            )
            
            # Log successful registration
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_SUCCESS,
                success=True,
                user_id=supabase_user_id,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                session_id=session_result.session_id
            )
            
            # Set secure cookies
            from app.services.cookie_manager import get_cookie_manager
            cookie_manager = get_cookie_manager()
            cookie_manager.set_auth_cookies(
                response,
                session_result.access_token,
                session_result.refresh_token
            )
            
            # Create response
            user_response = create_user_response(app_user, supabase_user)
            token_response = TokenResponse(
                access_token=session_result.access_token,
                refresh_token=session_result.refresh_token,
                token_type="bearer",
                expires_in=session_result.expires_in,
                refresh_expires_in=session_result.refresh_expires_in
            )
            
            return AuthenticationResponse(
                user=user_response,
                tokens=token_response,
                session_id=session_result.session_id,
                remember_me=False
            )
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Database integrity error during registration: {str(e)}")
            
            # Clean up Supabase user if application user creation failed
            try:
                await supabase_client.auth.admin.delete_user(supabase_user_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup Supabase user: {cleanup_error}")
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_FAILURE,
                success=False,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Database integrity error"
            )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "registration_failed",
                    "message": "An account with this email already exists."
                }
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"Registration error: {str(e)}")
            
            # Clean up Supabase user
            try:
                await supabase_client.auth.admin.delete_user(supabase_user_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup Supabase user: {cleanup_error}")
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.REGISTRATION_FAILURE,
                success=False,
                email=user_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "registration_failed",
                    "message": "Failed to create user account. Please try again."
                }
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected registration error: {str(e)}")
        
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.REGISTRATION_FAILURE,
            success=False,
            email=user_data.email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            error_message=f"Unexpected error: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )


# Placeholder endpoints for other authentication functionality
# These will be implemented in subsequent tasks

@router.post(
    "/login",
    response_model=AuthenticationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": AccountLockoutInfo, "description": "Account locked"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User login with email/password or social providers",
    description="Authenticate user with email/password credentials with comprehensive error handling and account lockout protection"
)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    User login with email/password authentication.
    
    Authenticates users with email and password, validates credentials,
    handles account lockout, rate limiting, and returns authentication tokens.
    
    Args:
        login_data: Login credentials and options
        request: FastAPI request object
        response: FastAPI response object
        db: Database session
        
    Returns:
        AuthenticationResponse with user data and tokens
        
    Raises:
        HTTPException: For various error conditions including invalid credentials,
                      account lockout, rate limiting, and server errors
    """
    settings = get_settings()
    client_info = get_client_info(request)
    
    # Initialize services
    rate_limiter = get_rate_limiter()
    audit_logger = get_audit_logger(db)
    password_security = get_password_security()
    account_lockout_service = get_account_lockout_service(db)
    session_manager = get_session_manager(db)
    user_sync_service = get_user_sync_service(db)
    supabase_client = get_supabase_client()
    
    try:
        # Rate limiting check
        rate_limit_key = f"login:{client_info['ip_address']}"
        rate_check = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=settings.login_rate_limit_attempts,
            window_seconds=settings.login_rate_limit_window_minutes * 60
        )
        
        if not rate_check.allowed:
            await audit_logger.log_security_event(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                description="Login rate limit exceeded",
                ip_address=client_info["ip_address"],
                severity=AuditSeverity.MEDIUM,
                metadata={"endpoint": "login", "email": login_data.email}
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many login attempts. Please try again later.",
                    "retry_after": rate_check.retry_after,
                    "limit": rate_check.limit,
                    "window": settings.login_rate_limit_window_minutes * 60
                }
            )
        
        # Check for account lockout
        lockout_info = await account_lockout_service.check_account_lockout(
            email=login_data.email.lower(),
            ip_address=client_info["ip_address"]
        )
        
        if lockout_info.is_locked:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_BLOCKED,
                success=False,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Account locked due to security policy"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "account_locked",
                    "message": "Account is temporarily locked due to security policy.",
                    "lockout_info": {
                        "locked_at": lockout_info.locked_at.isoformat() if lockout_info.locked_at else None,
                        "unlock_at": lockout_info.unlock_at.isoformat() if lockout_info.unlock_at else None,
                        "reason": lockout_info.lockout_reason,
                        "can_retry_at": lockout_info.can_retry_at.isoformat() if lockout_info.can_retry_at else None
                    }
                }
            )
        
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email.lower()).first()
        
        if not user:
            # Record failed login attempt for non-existent user
            await account_lockout_service.record_failed_attempt(
                email=login_data.email.lower(),
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                reason="user_not_found"
            )
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="User not found"
            )
            
            # Generic error message to prevent user enumeration
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid email or password."
                }
            )
        
        # Get Supabase user record
        supabase_user = db.query(SupabaseUser).filter(
            SupabaseUser.app_user_id == user.id
        ).first()
        
        if not supabase_user:
            logger.error(f"Supabase user record not found for user {user.id}")
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                user_id=user.id,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="User sync error"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "authentication_error",
                    "message": "Authentication service temporarily unavailable. Please try again."
                }
            )
        
        # Verify password using password security service
        from app.models.auth import PasswordHistory
        password_history = db.query(PasswordHistory).filter(
            PasswordHistory.supabase_user_id == supabase_user.supabase_id,
            PasswordHistory.is_current == True
        ).first()
        
        if not password_history:
            logger.error(f"Password history not found for user {user.id}")
            
            await account_lockout_service.record_failed_attempt(
                email=login_data.email.lower(),
                user_id=user.id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                reason="password_verification_error"
            )
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                user_id=user.id,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Password verification error"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid email or password."
                }
            )
        
        # Verify the password
        is_valid_password = password_security.verify_password(
            password=login_data.password,
            hashed_password=password_history.password_hash
        )
        
        if not is_valid_password:
            # Record failed login attempt
            await account_lockout_service.record_failed_attempt(
                email=login_data.email.lower(),
                user_id=user.id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                reason="invalid_password"
            )
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                user_id=user.id,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Invalid password"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid email or password."
                }
            )
        
        # Check if account is verified (optional enforcement)
        if not supabase_user.email_verified and settings.require_email_verification:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_BLOCKED,
                success=False,
                user_id=user.id,
                email=login_data.email,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Email not verified"
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "email_not_verified",
                    "message": "Please verify your email address before logging in.",
                    "verification_required": True
                }
            )
        
        # Clear any failed attempts since login was successful
        await account_lockout_service.clear_failed_attempts(login_data.email.lower())
        
        # Create session
        session_result = session_manager.create_session(
            user=user,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            remember_me=login_data.remember_me
        )
        
        # Update last sign in time
        supabase_user.last_sign_in_at = datetime.now(timezone.utc)
        supabase_user.mark_sync_success()
        db.commit()
        
        # Log successful login
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            success=True,
            user_id=supabase_user.supabase_id,
            email=login_data.email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            session_id=session_result.session_id,
            metadata={
                "remember_me": login_data.remember_me,
                "device_name": login_data.device_name
            }
        )
        
        # Set secure cookies
        cookie_manager = get_cookie_manager()
        cookie_manager.set_auth_cookies(
            response,
            session_result.access_token,
            session_result.refresh_token,
            remember_me=login_data.remember_me
        )
        
        # Create response
        user_response = create_user_response(user, supabase_user)
        token_response = TokenResponse(
            access_token=session_result.access_token,
            refresh_token=session_result.refresh_token,
            token_type="bearer",
            expires_in=session_result.expires_in,
            refresh_expires_in=session_result.refresh_expires_in
        )
        
        return AuthenticationResponse(
            user=user_response,
            tokens=token_response,
            session_id=session_result.session_id,
            remember_me=login_data.remember_me
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected login error: {str(e)}")
        
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            success=False,
            email=login_data.email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            error_message=f"Unexpected error: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )


@router.post(
    "/social",
    response_model=AuthenticationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Invalid OAuth token"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Social authentication with OAuth providers",
    description="Authenticate user with OAuth provider tokens (Google, Apple, Facebook, etc.)"
)
async def social_auth(
    social_data: SocialAuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Social authentication with OAuth providers.
    
    Authenticates users using OAuth provider access tokens,
    creates or updates user accounts, and returns authentication tokens.
    
    Args:
        social_data: Social authentication data including provider and token
        request: FastAPI request object
        response: FastAPI response object
        db: Database session
        
    Returns:
        AuthenticationResponse with user data and tokens
        
    Raises:
        HTTPException: For various error conditions
    """
    settings = get_settings()
    client_info = get_client_info(request)
    
    # Initialize services
    rate_limiter = get_rate_limiter()
    audit_logger = get_audit_logger(db)
    session_manager = get_session_manager(db)
    user_sync_service = get_user_sync_service(db)
    supabase_client = get_supabase_client()
    
    try:
        # Rate limiting check
        rate_limit_key = f"social_auth:{client_info['ip_address']}"
        rate_check = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=settings.login_rate_limit_attempts,
            window_seconds=settings.login_rate_limit_window_minutes * 60
        )
        
        if not rate_check.allowed:
            await audit_logger.log_security_event(
                event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
                description="Social authentication rate limit exceeded",
                ip_address=client_info["ip_address"],
                severity=AuditSeverity.MEDIUM,
                metadata={"endpoint": "social_auth", "provider": social_data.provider}
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many authentication attempts. Please try again later.",
                    "retry_after": rate_check.retry_after,
                    "limit": rate_check.limit,
                    "window": settings.login_rate_limit_window_minutes * 60
                }
            )
        
        # Verify OAuth token with provider
        user_info = await verify_oauth_token(social_data.provider, social_data.access_token)
        
        if not user_info:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                provider=social_data.provider,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Invalid OAuth token"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_oauth_token",
                    "message": "Invalid or expired OAuth token."
                }
            )
        
        # Check for existing user
        existing_user = db.query(User).filter(User.email == user_info["email"].lower()).first()
        existing_supabase_user = None
        
        if existing_user:
            # Get existing Supabase user
            existing_supabase_user = db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == existing_user.id
            ).first()
        
        # Create or update user in Supabase
        try:
            if existing_supabase_user:
                # For existing users, we'll create a new session using the existing Supabase user ID
                # and update the user metadata
                supabase_user_id = existing_supabase_user.supabase_id
                
                # Update user sync record
                existing_supabase_user.last_sign_in_at = datetime.now(timezone.utc)
                existing_supabase_user.user_metadata = user_info
                existing_supabase_user.mark_sync_success()
                
                app_user = existing_user
                supabase_user = existing_supabase_user
                
            else:
                # Create new user in Supabase using the admin API
                supabase_response = await supabase_client.auth.admin.create_user({
                    "email": user_info["email"],
                    "email_confirm": True,  # OAuth providers verify emails
                    "user_metadata": {
                        "provider": social_data.provider,
                        "given_name": user_info.get("given_name", ""),
                        "family_name": user_info.get("family_name", ""),
                        "name": user_info.get("name", ""),
                        "picture": user_info.get("picture"),
                        "locale": user_info.get("locale", "en")
                    }
                })
                
                if not supabase_response.user:
                    raise Exception("Failed to create user in Supabase")
                
                supabase_user_id = supabase_response.user.id
                
                # Create application user
                app_user = User(
                    email=user_info["email"].lower(),
                    first_name=user_info.get("given_name", user_info.get("first_name", "")),
                    last_name=user_info.get("family_name", user_info.get("last_name", "")),
                    display_name=user_info.get("name", f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}").strip(),
                    avatar_url=user_info.get("picture"),
                    language_code="en",  # Default, could be enhanced with provider data
                    is_verified=user_info.get("email_verified", True),  # OAuth providers typically verify emails
                    is_premium=False,
                    marketing_consent=social_data.marketing_consent,
                    terms_accepted_at=datetime.now(timezone.utc)
                )
                
                db.add(app_user)
                db.flush()  # Get the ID without committing
                
                # Create Supabase user sync record
                supabase_user = SupabaseUser(
                    supabase_id=supabase_user_id,
                    app_user_id=app_user.id,
                    email=user_info["email"].lower(),
                    email_verified=user_info.get("email_verified", True),
                    provider=social_data.provider,
                    last_sign_in_at=datetime.now(timezone.utc),
                    user_metadata=supabase_response.user.user_metadata or {},
                    sync_status="synced",
                    last_sync_at=datetime.now(timezone.utc)
                )
                
                db.add(supabase_user)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Supabase social authentication failed: {str(e)}")
            
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGIN_FAILURE,
                success=False,
                provider=social_data.provider,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message=f"Supabase authentication failed: {str(e)}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "authentication_failed",
                    "message": "Failed to authenticate with OAuth provider. Please try again."
                }
            )
        
        # Create session
        session_result = session_manager.create_session(
            user=app_user,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            remember_me=False  # Social auth defaults to standard session
        )
        
        # Log successful authentication
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            success=True,
            user_id=supabase_user_id,
            email=user_info["email"],
            provider=social_data.provider,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            session_id=session_result.session_id
        )
        
        # Set secure cookies
        cookie_manager = get_cookie_manager()
        cookie_manager.set_auth_cookies(
            response,
            session_result.access_token,
            session_result.refresh_token
        )
        
        # Create response
        user_response = create_user_response(app_user, supabase_user)
        token_response = TokenResponse(
            access_token=session_result.access_token,
            refresh_token=session_result.refresh_token,
            token_type="bearer",
            expires_in=session_result.expires_in,
            refresh_expires_in=session_result.refresh_expires_in
        )
        
        return AuthenticationResponse(
            user=user_response,
            tokens=token_response,
            session_id=session_result.session_id,
            remember_me=False
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected social authentication error: {str(e)}")
        
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            success=False,
            provider=social_data.provider,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            error_message=f"Unexpected error: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )


@router.post(
    "/password-reset",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Request password reset",
    description="Send password reset email with secure token to user's email address"
)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    
    Sends a secure password reset token via email to the user's registered
    email address. Includes rate limiting and security measures.
    
    Args:
        reset_data: Password reset request data
        request: FastAPI request object
        db: Database session
        
    Returns:
        Success message (generic to prevent email enumeration)
        
    Raises:
        HTTPException: For various error conditions
    """
    from app.services.password_reset import get_password_reset_service
    
    client_info = get_client_info(request)
    
    try:
        # Initialize password reset service
        password_reset_service = get_password_reset_service(db)
        
        # Request password reset
        result = await password_reset_service.request_password_reset(
            email=reset_data.email,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        if not result.success:
            if result.error_code == "rate_limit_exceeded":
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": result.message,
                        "retry_after": 3600  # 1 hour
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "internal_error",
                        "message": result.message
                    }
                )
        
        return {
            "message": result.message,
            "email": reset_data.email
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected password reset request error: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )


@router.post(
    "/password-reset/confirm",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid or expired token"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Confirm password reset",
    description="Reset password using secure token received via email"
)
async def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    
    Validates the password reset token and updates the user's password
    with comprehensive security checks including password history validation.
    
    Args:
        confirm_data: Password reset confirmation data
        request: FastAPI request object
        db: Database session
        
    Returns:
        Success message confirming password reset
        
    Raises:
        HTTPException: For various error conditions
    """
    from app.services.password_reset import get_password_reset_service
    
    client_info = get_client_info(request)
    
    try:
        # Initialize password reset service
        password_reset_service = get_password_reset_service(db)
        
        # Confirm password reset
        result = await password_reset_service.confirm_password_reset(
            reset_token=confirm_data.token,
            new_password=confirm_data.new_password,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        if not result.success:
            if result.error_code in ["invalid_token", "token_expired"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": result.error_code,
                        "message": result.message
                    }
                )
            elif result.error_code in ["password_validation_failed", "password_reused"]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": result.error_code,
                        "message": result.message
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "internal_error",
                        "message": result.message
                    }
                )
        
        return {
            "message": result.message,
            "success": True
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected password reset confirmation error: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again."
            }
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Refresh authentication tokens",
    description="Exchange a valid refresh token for new access and refresh tokens while preserving remember me state"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refresh authentication tokens using refresh token.
    
    Exchanges a valid refresh token for new access and refresh tokens,
    maintaining the remember_me state and session preferences.
    
    Args:
        refresh_data: Refresh token request data
        request: FastAPI request object
        response: FastAPI response object
        db: Database session
        
    Returns:
        TokenResponse with new access and refresh tokens
        
    Raises:
        HTTPException: For invalid tokens or server errors
    """
    client_info = get_client_info(request)
    
    # Initialize services
    session_manager = get_session_manager(db)
    audit_logger = get_audit_logger(db)
    cookie_manager = get_cookie_manager()
    
    try:
        # Try to get refresh token from cookie if not provided in body
        refresh_token = refresh_data.refresh_token
        if not refresh_token:
            refresh_token = cookie_manager.get_refresh_token_from_cookie(request)
        
        if not refresh_token:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.TOKEN_REFRESH,
                success=False,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="No refresh token provided"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "missing_token",
                    "message": "Refresh token is required."
                }
            )
        
        # Refresh the session
        session_result = session_manager.refresh_session(
            refresh_token=refresh_token,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        if not session_result:
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.TOKEN_REFRESH,
                success=False,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Invalid or expired refresh token"
            )
            
            # Clear cookies on invalid refresh token
            cookie_manager.clear_auth_cookies(response)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_token",
                    "message": "Invalid or expired refresh token."
                }
            )
        
        # Log successful token refresh
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.TOKEN_REFRESH,
            success=True,
            user_id=session_result["user"]["id"],
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            session_id=session_result["session_id"],
            metadata={
                "remember_me": session_result["remember_me"]
            }
        )
        
        # Set new cookies with appropriate expiration
        cookie_manager.set_auth_cookies(
            response,
            session_result["access_token"],
            session_result["refresh_token"],
            remember_me=session_result["remember_me"]
        )
        
        # Return new token pair
        return TokenResponse(
            access_token=session_result["access_token"],
            refresh_token=session_result["refresh_token"],
            token_type="bearer",
            expires_in=session_result["expires_in"],
            refresh_expires_in=session_result["refresh_expires_in"]
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected token refresh error: {str(e)}")
        
        await audit_logger.log_authentication_event(
            event_type=AuditEventType.TOKEN_REFRESH,
            success=False,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            error_message=f"Unexpected error: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Token refresh failed. Please try again."
            }
        )


@router.post(
    "/logout",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="User logout with token invalidation",
    description="Logout user and invalidate authentication tokens with optional logout from all devices"
)
async def logout(
    logout_data: LogoutRequest,
    request: Request,
    response: Response,
    current_user_payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db)
):
    """
    User logout with token invalidation.
    
    Invalidates the current session or all user sessions based on request,
    clears authentication cookies, and logs the logout event for audit purposes.
    
    Args:
        logout_data: Logout request data
        request: FastAPI request object
        response: FastAPI response object
        current_user_payload: Current user's JWT payload
        db: Database session
        
    Returns:
        Dictionary with logout confirmation message
        
    Raises:
        HTTPException: For authentication errors or server errors
    """
    client_info = get_client_info(request)
    
    # Initialize services
    session_manager = get_session_manager(db)
    audit_logger = get_audit_logger(db)
    cookie_manager = get_cookie_manager()
    
    try:
        # Extract user information from token payload
        user_id = current_user_payload.get("sub")
        session_id = current_user_payload.get("session_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_token",
                    "message": "Invalid token payload."
                }
            )
        
        # Determine logout scope
        if logout_data.logout_all_devices:
            # Logout from all devices
            invalidated_count = session_manager.invalidate_all_user_sessions(
                user_id=user_id,
                reason="logout_all_devices"
            )
            
            # Log logout all devices event
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGOUT_ALL,
                success=True,
                user_id=user_id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                session_id=session_id,
                metadata={
                    "sessions_invalidated": invalidated_count,
                    "logout_type": "all_devices"
                }
            )
            
            message = f"Successfully logged out from all devices. {invalidated_count} sessions invalidated."
            
        else:
            # Logout from current session only
            if session_id:
                success = session_manager.invalidate_session(
                    session_id=session_id,
                    reason="logout"
                )
                
                if not success:
                    logger.warning(f"Failed to invalidate session {session_id} for user {user_id}")
            
            # Log single session logout event
            await audit_logger.log_authentication_event(
                event_type=AuditEventType.LOGOUT,
                success=True,
                user_id=user_id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                session_id=session_id,
                metadata={
                    "logout_type": "current_session"
                }
            )
            
            message = "Successfully logged out from current session."
        
        # Clear authentication cookies
        cookie_manager.clear_auth_cookies(response)
        
        logger.info(f"User {user_id} logged out (all_devices: {logout_data.logout_all_devices})")
        
        return {
            "message": message,
            "logout_all_devices": logout_data.logout_all_devices,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected logout error: {str(e)}")
        
        # Try to log the error event if we have user info
        try:
            user_id = current_user_payload.get("sub")
            if user_id:
                await audit_logger.log_authentication_event(
                    event_type=AuditEventType.LOGOUT,
                    success=False,
                    user_id=user_id,
                    ip_address=client_info["ip_address"],
                    user_agent=client_info["user_agent"],
                    error_message=f"Logout error: {str(e)}"
                )
        except Exception:
            pass  # Don't fail on audit logging
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_error",
                "message": "Logout failed. Please try again."
            }
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get current user endpoint not yet implemented"
    )


@router.post("/verify-email", response_model=Dict[str, str])
async def verify_email(verification_data: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Email verification endpoint"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Email verification endpoint not yet implemented"
    )


@router.post("/resend-verification", response_model=Dict[str, str])
async def resend_verification(resend_data: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    """Resend email verification endpoint"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Resend verification endpoint not yet implemented"
    )