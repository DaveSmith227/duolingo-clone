"""
Session Management Service

Comprehensive session management service for JWT tokens, refresh tokens,
and secure session handling with activity tracking and automatic cleanup.
"""

import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.auth import AuthSession, SupabaseUser, AuthAuditLog
from app.models.user import User
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token, get_token_subject
from app.services.jwt_claims import get_jwt_claims_service

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Comprehensive session management service.
    
    Handles JWT token generation, refresh token rotation, session tracking,
    activity monitoring, and secure session cleanup.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.jwt_service = get_jwt_claims_service(db)
    
    def create_session(
        self,
        user: User,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        remember_me: bool = False,
        single_session: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new authentication session for a user.
        
        Args:
            user: User instance
            user_agent: Client user agent string
            ip_address: Client IP address
            remember_me: Whether to extend session duration
            single_session: Whether to invalidate other sessions
            
        Returns:
            Dictionary containing tokens and session information
        """
        try:
            # Invalidate other sessions if single session mode
            if single_session:
                self._invalidate_user_sessions(user.id, "single_session_login")
            
            # Enforce max active sessions limit
            self._enforce_session_limit(user.id)
            
            # Generate custom claims for the user
            custom_claims = self.jwt_service.generate_custom_claims(user)
            
            # Create token data
            token_data = {
                "sub": user.id,
                "email": user.email,
                **custom_claims
            }
            
            # Generate session ID and tokens
            session_id = self._generate_session_id()
            token_data["session_id"] = session_id
            
            # Set token expiration based on remember_me
            if remember_me:
                access_expires = timedelta(minutes=self.settings.access_token_expire_minutes)
                refresh_expires = timedelta(days=self.settings.remember_me_expire_days)
            else:
                access_expires = timedelta(minutes=self.settings.access_token_expire_minutes)
                refresh_expires = timedelta(days=self.settings.refresh_token_expire_days)
            
            # Generate tokens
            access_token = create_access_token(token_data, access_expires)
            refresh_token = create_refresh_token(token_data, refresh_expires)
            
            # Get Supabase user for session association
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user.id
            ).first()
            
            if not supabase_user:
                raise ValueError(f"No Supabase user found for user {user.id}")
            
            # Create session record
            session = AuthSession(
                supabase_user_id=supabase_user.id,
                session_id=session_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.now(timezone.utc) + access_expires,
                refresh_expires_at=datetime.now(timezone.utc) + refresh_expires,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            self.db.add(session)
            self.db.commit()
            
            # Log session creation
            self._log_auth_event(
                supabase_user_id=supabase_user.id,
                event_type="session_created",
                event_result="success",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "session_id": session_id,
                    "remember_me": remember_me,
                    "single_session": single_session
                }
            )
            
            logger.info(f"Created session for user {user.id} (session: {session_id})")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": int(access_expires.total_seconds()),
                "session_id": session_id,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "roles": custom_claims.get("roles", []),
                    "permissions": custom_claims.get("permissions", [])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create session for user {user.id}: {str(e)}")
            self.db.rollback()
            raise
    
    def refresh_session(self, refresh_token: str, user_agent: Optional[str] = None, 
                       ip_address: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Refresh an authentication session using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            user_agent: Client user agent string
            ip_address: Client IP address
            
        Returns:
            New token pair or None if refresh fails
        """
        try:
            # Verify refresh token
            payload = verify_refresh_token(refresh_token)
            if not payload:
                logger.warning("Invalid refresh token provided")
                return None
            
            user_id = payload.get("sub")
            session_id = payload.get("session_id")
            
            if not user_id or not session_id:
                logger.warning("Missing user_id or session_id in refresh token")
                return None
            
            # Find the session
            session = self.db.query(AuthSession).filter(
                AuthSession.session_id == session_id,
                AuthSession.is_active == True
            ).first()
            
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return None
            
            # Check if session is valid
            if not session.is_valid or session.is_refresh_expired:
                logger.warning(f"Session invalid or refresh token expired: {session_id}")
                session.invalidate("refresh_token_expired")
                self.db.commit()
                return None
            
            # Get user for new token generation
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User not found: {user_id}")
                return None
            
            # Generate new custom claims
            custom_claims = self.jwt_service.generate_custom_claims(user)
            
            # Create new token data
            token_data = {
                "sub": user.id,
                "email": user.email,
                "session_id": session_id,
                **custom_claims
            }
            
            # Generate new tokens (refresh token rotation)
            new_session_id = self._generate_session_id()
            token_data["session_id"] = new_session_id
            
            access_expires = timedelta(minutes=self.settings.access_token_expire_minutes)
            refresh_expires = timedelta(days=self.settings.refresh_token_expire_days)
            
            new_access_token = create_access_token(token_data, access_expires)
            new_refresh_token = create_refresh_token(token_data, refresh_expires)
            
            # Update session with new tokens and ID (refresh token rotation)
            session.session_id = new_session_id
            session.access_token = new_access_token
            session.refresh_token = new_refresh_token
            session.expires_at = datetime.now(timezone.utc) + access_expires
            session.refresh_expires_at = datetime.now(timezone.utc) + refresh_expires
            
            # Update activity tracking
            self._update_session_activity(session, ip_address, user_agent)
            
            self.db.commit()
            
            # Log token refresh
            self._log_auth_event(
                supabase_user_id=session.supabase_user_id,
                event_type="token_refreshed",
                event_result="success",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "old_session_id": session_id,
                    "new_session_id": new_session_id
                }
            )
            
            logger.info(f"Refreshed session for user {user_id} (new session: {new_session_id})")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": int(access_expires.total_seconds()),
                "session_id": new_session_id,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "roles": custom_claims.get("roles", []),
                    "permissions": custom_claims.get("permissions", [])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh session: {str(e)}")
            return None
    
    def invalidate_session(self, session_id: str, reason: str = "logout") -> bool:
        """
        Invalidate a specific session.
        
        Args:
            session_id: Session ID to invalidate
            reason: Reason for invalidation
            
        Returns:
            True if session was invalidated, False if not found
        """
        try:
            session = self.db.query(AuthSession).filter(
                AuthSession.session_id == session_id,
                AuthSession.is_active == True
            ).first()
            
            if not session:
                logger.warning(f"Session not found for invalidation: {session_id}")
                return False
            
            session.invalidate(reason)
            self.db.commit()
            
            # Log session invalidation
            self._log_auth_event(
                supabase_user_id=session.supabase_user_id,
                event_type="session_invalidated",
                event_result="success",
                metadata={
                    "session_id": session_id,
                    "reason": reason
                }
            )
            
            logger.info(f"Invalidated session: {session_id} (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate session {session_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def invalidate_all_user_sessions(self, user_id: str, reason: str = "logout_all") -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            reason: Reason for invalidation
            
        Returns:
            Number of sessions invalidated
        """
        try:
            # Get Supabase user
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            if not supabase_user:
                logger.warning(f"No Supabase user found for user {user_id}")
                return 0
            
            # Get active sessions
            active_sessions = self.db.query(AuthSession).filter(
                AuthSession.supabase_user_id == supabase_user.id,
                AuthSession.is_active == True
            ).all()
            
            count = 0
            for session in active_sessions:
                session.invalidate(reason)
                count += 1
            
            self.db.commit()
            
            # Log bulk invalidation
            self._log_auth_event(
                supabase_user_id=supabase_user.id,
                event_type="all_sessions_invalidated",
                event_result="success",
                metadata={
                    "user_id": user_id,
                    "sessions_invalidated": count,
                    "reason": reason
                }
            )
            
            logger.info(f"Invalidated {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to invalidate all sessions for user {user_id}: {str(e)}")
            self.db.rollback()
            return 0
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active sessions
            
        Returns:
            List of session information dictionaries
        """
        try:
            # Get Supabase user
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            if not supabase_user:
                return []
            
            # Query sessions
            query = self.db.query(AuthSession).filter(
                AuthSession.supabase_user_id == supabase_user.id
            )
            
            if active_only:
                query = query.filter(AuthSession.is_active == True)
            
            sessions = query.order_by(AuthSession.created_at.desc()).all()
            
            return [
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "last_activity": session.updated_at.isoformat(),
                    "user_agent": session.user_agent,
                    "ip_address": session.ip_address,
                    "is_active": session.is_active,
                    "is_expired": session.is_expired,
                    "invalidated_at": session.invalidated_at.isoformat() if session.invalidated_at else None,
                    "invalidation_reason": session.invalidation_reason
                }
                for session in sessions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get sessions for user {user_id}: {str(e)}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired and inactive sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                hours=self.settings.session_activity_timeout_hours
            )
            
            # Find expired sessions
            expired_sessions = self.db.query(AuthSession).filter(
                AuthSession.is_active == True,
                AuthSession.expires_at <= datetime.now(timezone.utc)
            ).all()
            
            # Find inactive sessions
            inactive_sessions = self.db.query(AuthSession).filter(
                AuthSession.is_active == True,
                AuthSession.updated_at <= cutoff_time
            ).all()
            
            count = 0
            
            # Mark expired sessions as invalid
            for session in expired_sessions:
                session.invalidate("token_expired")
                count += 1
            
            # Mark inactive sessions as invalid
            for session in inactive_sessions:
                session.invalidate("inactivity_timeout")
                count += 1
            
            self.db.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired/inactive sessions")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            self.db.rollback()
            return 0
    
    def verify_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session is valid and active.
        
        Args:
            session_id: Session ID to verify
            
        Returns:
            Session information if valid, None otherwise
        """
        try:
            session = self.db.query(AuthSession).filter(
                AuthSession.session_id == session_id,
                AuthSession.is_active == True
            ).first()
            
            if not session or not session.is_valid:
                return None
            
            # Update last activity
            session.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return {
                "session_id": session.session_id,
                "user_id": session.supabase_user.app_user_id,
                "expires_at": session.expires_at.isoformat(),
                "is_valid": session.is_valid
            }
            
        except Exception as e:
            logger.error(f"Failed to verify session {session_id}: {str(e)}")
            return None
    
    def _generate_session_id(self) -> str:
        """Generate a secure session ID."""
        return secrets.token_urlsafe(32)
    
    def _invalidate_user_sessions(self, user_id: str, reason: str):
        """Helper to invalidate all user sessions."""
        self.invalidate_all_user_sessions(user_id, reason)
    
    def _enforce_session_limit(self, user_id: str):
        """Enforce maximum active sessions per user."""
        try:
            # Get Supabase user
            supabase_user = self.db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user_id
            ).first()
            
            if not supabase_user:
                return
            
            # Count active sessions
            active_sessions = self.db.query(AuthSession).filter(
                AuthSession.supabase_user_id == supabase_user.id,
                AuthSession.is_active == True
            ).order_by(AuthSession.created_at.desc()).all()
            
            # If at limit, invalidate oldest sessions
            if len(active_sessions) >= self.settings.max_active_sessions:
                sessions_to_remove = len(active_sessions) - self.settings.max_active_sessions + 1
                for session in active_sessions[-sessions_to_remove:]:
                    session.invalidate("session_limit_exceeded")
                
                self.db.commit()
                logger.info(f"Invalidated {sessions_to_remove} sessions for user {user_id} (limit exceeded)")
                
        except Exception as e:
            logger.error(f"Failed to enforce session limit for user {user_id}: {str(e)}")
    
    def _update_session_activity(self, session: AuthSession, ip_address: Optional[str], 
                                user_agent: Optional[str]):
        """Update session activity information."""
        session.updated_at = datetime.now(timezone.utc)
        if ip_address:
            session.ip_address = ip_address
        if user_agent:
            session.user_agent = user_agent
    
    def _log_auth_event(self, supabase_user_id: str, event_type: str, event_result: str, 
                       **kwargs):
        """Log authentication event for audit purposes."""
        try:
            log_entry = AuthAuditLog.create_log(
                event_type=event_type,
                event_result=event_result,
                supabase_user_id=supabase_user_id,
                **kwargs
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log auth event: {str(e)}")


def get_session_manager(db: Session) -> SessionManager:
    """
    Get SessionManager instance.
    
    Args:
        db: Database session
        
    Returns:
        SessionManager instance
    """
    return SessionManager(db)