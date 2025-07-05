"""
Authentication Repository

Handles all authentication-related database operations.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import secrets

from app.models.auth import (
    AuthSession,
    PasswordResetToken,
    EmailVerificationToken,
    AuthEvent
)
from app.models.mfa import MFAChallenge
from app.repositories.base_repository import BaseRepository


class AuthRepository:
    """Repository for authentication-related database operations."""
    
    def __init__(self, db: Session):
        """Initialize auth repository with database session."""
        self.db = db
        
        # Initialize base repositories for each model
        self.session_repo = BaseRepository(AuthSession, db)
        self.reset_token_repo = BaseRepository(PasswordResetToken, db)
        self.verify_token_repo = BaseRepository(EmailVerificationToken, db)
        self.auth_event_repo = BaseRepository(AuthEvent, db)
        self.mfa_challenge_repo = BaseRepository(MFAChallenge, db)
    
    # Session Management
    
    async def get_active_session(self, session_id: str) -> Optional[AuthSession]:
        """
        Get active session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Active session or None
        """
        session = await self.session_repo.find_one(
            session_id=session_id,
            is_active=True
        )
        
        # Check if session is expired
        if session and session.expires_at < datetime.utcnow():
            return None
        
        return session
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[AuthSession]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            
        Returns:
            List of user sessions
        """
        filters = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True
        
        return await self.session_repo.find_many(**filters)
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions invalidated
        """
        sessions = await self.get_user_sessions(user_id, active_only=True)
        count = 0
        
        for session in sessions:
            session.is_active = False
            session.invalidated_at = datetime.utcnow()
            session.invalidation_reason = "bulk_invalidation"
            count += 1
        
        self.db.commit()
        return count
    
    # Password Reset
    
    async def create_password_reset_token(
        self,
        user_id: str,
        expires_minutes: int = 15
    ) -> str:
        """
        Create password reset token for user.
        
        Args:
            user_id: User ID
            expires_minutes: Token expiration in minutes
            
        Returns:
            Reset token string
        """
        # Check for existing valid token
        existing = self.db.query(PasswordResetToken).filter(
            and_(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.is_used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        ).first()
        
        if existing:
            # Update expiration
            existing.expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
            self.db.commit()
            return existing.token
        
        # Create new token
        token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
            created_at=datetime.utcnow()
        )
        
        self.db.add(reset_token)
        self.db.commit()
        
        return token
    
    async def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Get password reset token.
        
        Args:
            token: Reset token string
            
        Returns:
            Reset token or None
        """
        return await self.reset_token_repo.find_one(token=token)
    
    async def mark_reset_token_used(self, token: str, ip_address: str) -> bool:
        """
        Mark reset token as used.
        
        Args:
            token: Reset token string
            ip_address: IP address that used the token
            
        Returns:
            True if marked, False if not found
        """
        reset_token = await self.get_password_reset_token(token)
        if not reset_token:
            return False
        
        reset_token.is_used = True
        reset_token.used_at = datetime.utcnow()
        reset_token.used_ip = ip_address
        
        self.db.commit()
        return True
    
    # Email Verification
    
    async def create_email_verification_token(
        self,
        user_id: str,
        expires_hours: int = 24
    ) -> str:
        """
        Create email verification token.
        
        Args:
            user_id: User ID
            expires_hours: Token expiration in hours
            
        Returns:
            Verification token string
        """
        # Check for existing valid token
        existing = self.db.query(EmailVerificationToken).filter(
            and_(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.is_used == False,
                EmailVerificationToken.expires_at > datetime.utcnow()
            )
        ).first()
        
        if existing:
            # Update expiration
            existing.expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            self.db.commit()
            return existing.token
        
        # Create new token
        token = secrets.token_urlsafe(32)
        verify_token = EmailVerificationToken(
            user_id=user_id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
            created_at=datetime.utcnow()
        )
        
        self.db.add(verify_token)
        self.db.commit()
        
        return token
    
    async def get_email_verification_token(
        self,
        token: str
    ) -> Optional[EmailVerificationToken]:
        """
        Get email verification token.
        
        Args:
            token: Verification token string
            
        Returns:
            Verification token or None
        """
        return await self.verify_token_repo.find_one(token=token)
    
    async def mark_email_verified(self, token: str, ip_address: str) -> bool:
        """
        Mark email verification token as used.
        
        Args:
            token: Verification token string
            ip_address: IP address that verified
            
        Returns:
            True if marked, False if not found
        """
        verify_token = await self.get_email_verification_token(token)
        if not verify_token:
            return False
        
        verify_token.is_used = True
        verify_token.used_at = datetime.utcnow()
        verify_token.used_ip = ip_address
        
        self.db.commit()
        return True
    
    # MFA Challenges
    
    async def create_mfa_challenge(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        expires_minutes: int = 5
    ) -> str:
        """
        Create MFA challenge token.
        
        Args:
            user_id: User ID
            ip_address: Request IP address
            user_agent: Request user agent
            expires_minutes: Challenge expiration in minutes
            
        Returns:
            Challenge token string
        """
        token = secrets.token_urlsafe(32)
        
        challenge = MFAChallenge(
            user_id=user_id,
            challenge_token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
            created_at=datetime.utcnow()
        )
        
        self.db.add(challenge)
        self.db.commit()
        
        return token
    
    async def get_mfa_challenge(self, token: str) -> Optional[MFAChallenge]:
        """
        Get MFA challenge by token.
        
        Args:
            token: Challenge token
            
        Returns:
            MFA challenge or None
        """
        return await self.mfa_challenge_repo.find_one(challenge_token=token)
    
    async def mark_challenge_verified(self, token: str) -> bool:
        """
        Mark MFA challenge as verified.
        
        Args:
            token: Challenge token
            
        Returns:
            True if marked, False if not found
        """
        challenge = await self.get_mfa_challenge(token)
        if not challenge:
            return False
        
        challenge.is_verified = True
        challenge.verified_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    # Auth Events
    
    async def log_auth_event(
        self,
        user_id: Optional[str],
        event_type: str,
        event_result: str,
        ip_address: str,
        user_agent: str,
        provider: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuthEvent:
        """
        Log authentication event.
        
        Args:
            user_id: User ID (optional)
            event_type: Type of event
            event_result: Result (success, failure, error)
            ip_address: Request IP
            user_agent: Request user agent
            provider: Auth provider
            error_code: Error code if failed
            details: Additional details
            
        Returns:
            Created auth event
        """
        import json
        
        event = AuthEvent(
            user_id=user_id,
            event_type=event_type,
            event_result=event_result,
            ip_address_hash=ip_address,  # Will be hashed by HashedString
            user_agent=user_agent,
            provider=provider,
            error_code=error_code,
            event_details=json.dumps(details) if details else None,
            created_at=datetime.utcnow()
        )
        
        self.db.add(event)
        self.db.commit()
        
        return event
    
    async def get_user_auth_events(
        self,
        user_id: str,
        event_type: Optional[str] = None,
        limit: int = 50
    ) -> List[AuthEvent]:
        """
        Get authentication events for user.
        
        Args:
            user_id: User ID
            event_type: Filter by event type
            limit: Maximum events to return
            
        Returns:
            List of auth events
        """
        query = self.db.query(AuthEvent).filter(
            AuthEvent.user_id == user_id
        )
        
        if event_type:
            query = query.filter(AuthEvent.event_type == event_type)
        
        return query.order_by(
            AuthEvent.created_at.desc()
        ).limit(limit).all()
    
    # Cleanup Operations
    
    async def cleanup_expired_tokens(self) -> Dict[str, int]:
        """
        Clean up expired tokens from all tables.
        
        Returns:
            Dictionary with counts of cleaned records
        """
        now = datetime.utcnow()
        counts = {}
        
        # Clean expired password reset tokens
        counts["password_reset"] = self.db.query(PasswordResetToken).filter(
            and_(
                PasswordResetToken.expires_at < now,
                PasswordResetToken.is_used == False
            )
        ).delete()
        
        # Clean expired email verification tokens
        counts["email_verification"] = self.db.query(EmailVerificationToken).filter(
            and_(
                EmailVerificationToken.expires_at < now,
                EmailVerificationToken.is_used == False
            )
        ).delete()
        
        # Clean expired MFA challenges
        counts["mfa_challenges"] = self.db.query(MFAChallenge).filter(
            and_(
                MFAChallenge.expires_at < now,
                MFAChallenge.is_verified == False
            )
        ).delete()
        
        self.db.commit()
        return counts