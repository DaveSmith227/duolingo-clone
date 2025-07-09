"""
Authentication Service Layer

Provides a clean interface for authentication operations, coordinating
between repositories, utilities, and other services.
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.auth import AuthSession, PasswordResetToken, EmailVerificationToken
from app.repositories.user_repository import UserRepository
from app.repositories.auth_repository import AuthRepository
from app.services.password_security import PasswordSecurity
from app.services.session_manager_secure import SecureSessionManager
from app.services.mfa_service import MFAService
from app.services.email_service import EmailService
from app.services.rate_limiter import RateLimiter
from app.services.audit_logger import AuditLogger
from app.services.account_lockout import AccountLockoutService
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    UserNotFoundError,
    AccountLockedError,
    InvalidTokenError,
    RateLimitExceededError
)


class AuthService:
    """
    Authentication service that coordinates all auth-related operations.
    
    This service follows the single responsibility principle by delegating
    specific tasks to specialized services and repositories.
    """
    
    def __init__(
        self,
        db: Session,
        user_repo: Optional[UserRepository] = None,
        auth_repo: Optional[AuthRepository] = None,
        password_security: Optional[PasswordSecurity] = None,
        session_manager: Optional[SecureSessionManager] = None,
        mfa_service: Optional[MFAService] = None,
        email_service: Optional[EmailService] = None,
        rate_limiter: Optional[RateLimiter] = None,
        audit_logger: Optional[AuditLogger] = None,
        account_lockout: Optional[AccountLockoutService] = None
    ):
        """Initialize authentication service with dependencies."""
        self.db = db
        self.settings = get_settings()
        
        # Initialize repositories
        self.user_repo = user_repo or UserRepository(db)
        self.auth_repo = auth_repo or AuthRepository(db)
        
        # Initialize services
        self.password_security = password_security or PasswordSecurity(db, self.settings)
        self.session_manager = session_manager or SecureSessionManager(db, self.settings)
        self.mfa_service = mfa_service or MFAService(db, self.settings)
        self.email_service = email_service or EmailService(self.settings)
        self.rate_limiter = rate_limiter or RateLimiter(self.settings)
        self.audit_logger = audit_logger or AuditLogger(db)
        self.account_lockout = account_lockout or AccountLockoutService(db, self.settings)
    
    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        client_info: Dict[str, Any]
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Register a new user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            first_name: User's first name
            last_name: User's last name
            client_info: Client information (IP, user agent, etc.)
            
        Returns:
            Tuple of (User, session_data)
            
        Raises:
            RateLimitExceededError: If rate limit exceeded
            ValueError: If validation fails
        """
        # Check rate limiting
        await self._check_rate_limit("registration", client_info["ip_address"])
        
        # Validate inputs
        self._validate_registration_data(email, password, first_name, last_name)
        
        # Check if user exists
        if await self.user_repo.get_by_email(email):
            await self.audit_logger.log_event(
                user_id=None,
                event_type="registration_duplicate_email",
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                success=False,
                details={"email": email}
            )
            raise ValueError("Email already registered")
        
        # Create user
        user = await self.user_repo.create_user(
            email=email,
            password_hash=self.password_security.hash_password(password),
            first_name=first_name,
            last_name=last_name
        )
        
        # Create session
        session_data = await self.session_manager.create_session(user, client_info)
        
        # Send verification email
        await self._send_verification_email(user)
        
        # Log successful registration
        await self.audit_logger.log_event(
            user_id=user.id,
            event_type="registration_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return user, session_data
    
    async def login_user(
        self,
        email: str,
        password: str,
        client_info: Dict[str, Any],
        remember_me: bool = False
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email
            password: User's password
            client_info: Client information
            remember_me: Whether to create long-lived session
            
        Returns:
            Tuple of (User, session_data or mfa_challenge)
            
        Raises:
            AuthenticationError: If authentication fails
            AccountLockedError: If account is locked
            RateLimitExceededError: If rate limit exceeded
        """
        # Check rate limiting
        await self._check_rate_limit("login", client_info["ip_address"])
        
        # Get user
        user = await self.user_repo.get_by_email(email)
        if not user:
            await self._log_failed_login(email, client_info, "user_not_found")
            raise AuthenticationError("Invalid email or password")
        
        # Check account lock
        if await self.account_lockout.is_account_locked(user.id):
            await self._log_failed_login(email, client_info, "account_locked")
            raise AccountLockedError("Account is temporarily locked")
        
        # Verify password
        if not self.password_security.verify_password(password, user.password_hash):
            await self.account_lockout.record_failed_attempt(user.id)
            await self._log_failed_login(email, client_info, "invalid_password")
            
            # Check if should lock account
            if await self.account_lockout.should_lock_account(user.id):
                await self.account_lockout.lock_account(user.id)
                raise AccountLockedError("Too many failed attempts")
            
            raise AuthenticationError("Invalid email or password")
        
        # Clear failed attempts
        await self.account_lockout.clear_failed_attempts(user.id)
        
        # Check MFA requirement
        if await self.mfa_service.is_mfa_enabled(user.id):
            return user, await self._create_mfa_challenge(user, client_info)
        
        # Create session
        session_data = await self.session_manager.create_session(
            user,
            {**client_info, "remember_me": remember_me}
        )
        
        # Update last login
        await self.user_repo.update_last_login(user.id, client_info["ip_address"])
        
        # Log successful login
        await self.audit_logger.log_event(
            user_id=user.id,
            event_type="login_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return user, session_data
    
    async def verify_mfa(
        self,
        challenge_token: str,
        mfa_code: str,
        method: str,
        client_info: Dict[str, Any]
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Verify MFA code and complete login.
        
        Args:
            challenge_token: MFA challenge token
            mfa_code: User-provided MFA code
            method: MFA method (totp or backup_code)
            client_info: Client information
            
        Returns:
            Tuple of (User, session_data)
            
        Raises:
            InvalidTokenError: If challenge token invalid
            AuthenticationError: If MFA code invalid
        """
        # Get challenge
        challenge = await self.auth_repo.get_mfa_challenge(challenge_token)
        if not challenge or challenge.is_expired():
            raise InvalidTokenError("Invalid or expired challenge")
        
        # Verify MFA code
        if method == "totp":
            valid = await self.mfa_service.verify_totp_code(challenge.user_id, mfa_code)
        elif method == "backup_code":
            valid = await self.mfa_service.verify_backup_code(challenge.user_id, mfa_code)
        else:
            raise ValueError("Invalid MFA method")
        
        if not valid:
            await self._log_mfa_failure(challenge.user_id, client_info)
            raise AuthenticationError("Invalid MFA code")
        
        # Mark challenge as verified
        await self.auth_repo.mark_challenge_verified(challenge_token)
        
        # Get user and create session
        user = await self.user_repo.get_by_id(challenge.user_id)
        session_data = await self.session_manager.create_session(user, client_info)
        
        # Log successful MFA
        await self.audit_logger.log_event(
            user_id=user.id,
            event_type="mfa_verification_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True,
            details={"method": method}
        )
        
        return user, session_data
    
    async def logout_user(
        self,
        session_id: str,
        user_id: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Logout user and invalidate session.
        
        Args:
            session_id: Session to invalidate
            user_id: User ID for logging
            client_info: Client information
        """
        # Invalidate session
        await self.session_manager.invalidate_session(session_id)
        
        # Log logout
        await self.audit_logger.log_event(
            user_id=user_id,
            event_type="logout",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
    
    async def request_password_reset(
        self,
        email: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Request password reset for user.
        
        Args:
            email: User's email
            client_info: Client information
        """
        # Check rate limiting
        await self._check_rate_limit("password_reset", client_info["ip_address"])
        
        # Get user (but don't reveal if exists)
        user = await self.user_repo.get_by_email(email)
        
        if user and user.is_active:
            # Create reset token
            token = await self.auth_repo.create_password_reset_token(user.id)
            
            # Send reset email
            await self.email_service.send_password_reset_email(
                user.email,
                user.first_name,
                token
            )
            
            # Log request
            await self.audit_logger.log_event(
                user_id=user.id,
                event_type="password_reset_requested",
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                success=True
            )
    
    async def reset_password(
        self,
        token: str,
        new_password: str,
        client_info: Dict[str, Any]
    ) -> None:
        """
        Reset user password with token.
        
        Args:
            token: Password reset token
            new_password: New password
            client_info: Client information
            
        Raises:
            InvalidTokenError: If token invalid
            ValueError: If password invalid
        """
        # Get and validate token
        reset_token = await self.auth_repo.get_password_reset_token(token)
        if not reset_token or reset_token.is_expired() or reset_token.is_used:
            raise InvalidTokenError("Invalid or expired reset token")
        
        # Validate new password
        self.password_security.validate_password_strength(new_password)
        
        # Check password history
        self.password_security.check_password_history(reset_token.user_id, new_password)
        
        # Update password
        new_hash = self.password_security.hash_password(new_password)
        await self.user_repo.update_password(reset_token.user_id, new_hash)
        
        # Mark token as used
        await self.auth_repo.mark_reset_token_used(token, client_info["ip_address"])
        
        # Invalidate all sessions
        await self.session_manager.invalidate_all_user_sessions(reset_token.user_id)
        
        # Log password reset
        await self.audit_logger.log_security_event(
            user_id=reset_token.user_id,
            event_type="password_reset_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
    
    # Private helper methods
    
    async def _check_rate_limit(self, action: str, ip_address: str) -> None:
        """Check rate limiting for action."""
        result = await self.rate_limiter.check_rate_limit(
            action,
            ip_address,
            max_requests=self._get_rate_limit(action),
            window_minutes=self._get_rate_window(action)
        )
        
        if not result["allowed"]:
            raise RateLimitExceededError(
                f"Too many {action} attempts. Try again in {result['retry_after']} seconds."
            )
    
    def _validate_registration_data(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> None:
        """Validate registration input data."""
        # Email validation
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        
        # Password validation
        self.password_security.validate_password_strength(password)
        
        # Name validation
        if not first_name or not first_name.strip():
            raise ValueError("First name is required")
        
        if not last_name or not last_name.strip():
            raise ValueError("Last name is required")
    
    async def _create_mfa_challenge(
        self,
        user: User,
        client_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create MFA challenge for user."""
        challenge_token = await self.auth_repo.create_mfa_challenge(
            user.id,
            client_info["ip_address"],
            client_info["user_agent"]
        )
        
        return {
            "mfa_required": True,
            "challenge_token": challenge_token,
            "message": "Please provide your 2FA code"
        }
    
    async def _send_verification_email(self, user: User) -> None:
        """Send email verification to user."""
        token = await self.auth_repo.create_email_verification_token(user.id)
        await self.email_service.send_verification_email(
            user.email,
            user.first_name,
            token
        )
    
    async def _log_failed_login(
        self,
        email: str,
        client_info: Dict[str, Any],
        reason: str
    ) -> None:
        """Log failed login attempt."""
        await self.audit_logger.log_security_event(
            user_id=None,
            event_type=f"login_failed_{reason}",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"email": email}
        )
    
    async def _log_mfa_failure(
        self,
        user_id: str,
        client_info: Dict[str, Any]
    ) -> None:
        """Log failed MFA attempt."""
        await self.audit_logger.log_security_event(
            user_id=user_id,
            event_type="mfa_verification_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
    
    def _get_rate_limit(self, action: str) -> int:
        """Get rate limit for action."""
        limits = {
            "registration": 5,
            "login": 10,
            "password_reset": 3,
            "mfa_verify": 5
        }
        return limits.get(action, 10)
    
    def _get_rate_window(self, action: str) -> int:
        """Get rate limit window in minutes."""
        windows = {
            "registration": 60,
            "login": 15,
            "password_reset": 60,
            "mfa_verify": 5
        }
        return windows.get(action, 15)