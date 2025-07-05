"""
Session Manager Interface

Defines the contract for session management services to ensure consistent
session handling across different implementations.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any, List
from datetime import datetime

from app.models.user import User


class ISessionManager(Protocol):
    """
    Protocol for session manager implementations.
    
    This interface defines the core session management operations.
    """
    
    @abstractmethod
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
        ...
    
    @abstractmethod
    def refresh_session(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an authentication session using refresh token.
        
        Args:
            refresh_token: JWT refresh token
            user_agent: Client user agent string
            ip_address: Client IP address
            
        Returns:
            New token pair or None if refresh fails
        """
        ...
    
    @abstractmethod
    def invalidate_session(self, session_id: str, reason: str = "logout") -> bool:
        """
        Invalidate a specific session.
        
        Args:
            session_id: Session ID to invalidate
            reason: Reason for invalidation
            
        Returns:
            True if session was invalidated, False if not found
        """
        ...
    
    @abstractmethod
    def invalidate_all_user_sessions(self, user_id: str, reason: str = "logout_all") -> int:
        """
        Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            reason: Reason for invalidation
            
        Returns:
            Number of sessions invalidated
        """
        ...
    
    @abstractmethod
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active sessions
            
        Returns:
            List of session information dictionaries
        """
        ...
    
    @abstractmethod
    def verify_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Verify a session is valid and active.
        
        Args:
            session_id: Session ID to verify
            
        Returns:
            Session information if valid, None otherwise
        """
        ...
    
    @abstractmethod
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired and inactive sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        ...


class SessionData:
    """Type for session data."""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        refresh_expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        remember_me: bool = False
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at
        self.refresh_expires_at = refresh_expires_at
        self.user_agent = user_agent
        self.ip_address = ip_address
        self.remember_me = remember_me
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "refresh_expires_at": self.refresh_expires_at.isoformat(),
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "remember_me": self.remember_me
        }


class SessionConfig:
    """Configuration type for session management."""
    
    def __init__(
        self,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        remember_me_expire_days: int = 30,
        max_active_sessions: int = 5,
        session_activity_timeout_hours: int = 24
    ):
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.remember_me_expire_days = remember_me_expire_days
        self.max_active_sessions = max_active_sessions
        self.session_activity_timeout_hours = session_activity_timeout_hours