"""
Secure Session Manager Service

Manages authentication sessions with proper JWT handling (stateless).
"""
import jwt
import json
import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.auth_session_secure import SecureAuthSession
from app.core.config import get_settings
from app.core.redis import get_redis_client


class SecureSessionManager:
    """Service for managing authentication sessions securely."""
    
    def __init__(self, db: Session, settings = None):
        self.db = db
        self.settings = settings or get_settings()
        self.redis = get_redis_client()
    
    async def create_session(
        self, 
        user: User, 
        device_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new authentication session."""
        # Generate unique session ID
        session_id = secrets.token_urlsafe(32)
        
        # Create session record (without tokens)
        session = SecureAuthSession(
            user_id=user.id,
            session_id=session_id,
            device_fingerprint=device_info.get("device_fingerprint"),
            user_agent=device_info.get("user_agent"),
            ip_address=device_info.get("ip_address"),
            remember_me=device_info.get("remember_me", False),
            is_active=True,
            last_activity_at=datetime.now(timezone.utc)
        )
        
        self.db.add(session)
        self.db.commit()
        
        # Generate JWT tokens
        access_token = self._generate_access_token(user, session_id)
        refresh_token = self._generate_refresh_token(user, session_id)
        
        # Optional: Store session metadata in Redis for fast lookups
        await self._cache_session_metadata(session_id, user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session_id,
            "expires_in": self.settings.jwt_access_token_expire_minutes * 60
        }
    
    def _generate_access_token(self, user: User, session_id: str) -> str:
        """Generate JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=self.settings.jwt_access_token_expire_minutes
        )
        
        payload = {
            "sub": user.id,  # Subject (user ID)
            "session_id": session_id,
            "email": user.email,
            "role": user.role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(
            payload,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm
        )
    
    def _generate_refresh_token(self, user: User, session_id: str) -> str:
        """Generate JWT refresh token."""
        expire = datetime.utcnow() + timedelta(
            days=self.settings.jwt_refresh_token_expire_days
        )
        
        payload = {
            "sub": user.id,
            "session_id": session_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(
            payload,
            self.settings.secret_key,
            algorithm=self.settings.jwt_algorithm
        )
    
    async def _cache_session_metadata(self, session_id: str, user_id: str):
        """Cache session metadata in Redis for fast validation."""
        if self.redis:
            cache_key = f"session:{session_id}"
            cache_data = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Cache for access token duration
            await self.redis.setex(
                cache_key,
                self.settings.jwt_access_token_expire_minutes * 60,
                json.dumps(cache_data)
            )
    
    async def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and check session status."""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            session_id = payload.get("session_id")
            if not session_id:
                return None
            
            # Check Redis cache first
            if self.redis:
                cache_key = f"session:{session_id}"
                cached = await self.redis.get(cache_key)
                if not cached:
                    # Session not in cache, check database
                    session = self.db.query(SecureAuthSession).filter(
                        SecureAuthSession.session_id == session_id,
                        SecureAuthSession.is_active == True
                    ).first()
                    
                    if not session:
                        return None
                    
                    # Re-cache the session
                    await self._cache_session_metadata(session_id, session.user_id)
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                self.settings.secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")
            
            session_id = payload.get("session_id")
            user_id = payload.get("sub")
            
            # Verify session is still active
            session = self.db.query(SecureAuthSession).filter(
                SecureAuthSession.session_id == session_id,
                SecureAuthSession.is_active == True
            ).first()
            
            if not session:
                raise ValueError("Session not found or inactive")
            
            # Update session activity
            session.update_activity()
            self.db.commit()
            
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Generate new tokens
            new_access_token = self._generate_access_token(user, session_id)
            new_refresh_token = self._generate_refresh_token(user, session_id)
            
            # Update cache
            await self._cache_session_metadata(session_id, user_id)
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "session_id": session_id,
                "user_id": user_id,
                "expires_in": self.settings.jwt_access_token_expire_minutes * 60
            }
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a specific session."""
        session = self.db.query(SecureAuthSession).filter(
            SecureAuthSession.session_id == session_id
        ).first()
        
        if session:
            session.invalidate("logout")
            self.db.commit()
            
            # Remove from cache
            if self.redis:
                cache_key = f"session:{session_id}"
                await self.redis.delete(cache_key)
            
            return True
        
        return False
    
    async def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user."""
        sessions = self.db.query(SecureAuthSession).filter(
            SecureAuthSession.user_id == user_id,
            SecureAuthSession.is_active == True
        ).all()
        
        count = 0
        for session in sessions:
            session.invalidate("bulk_logout")
            count += 1
            
            # Remove from cache
            if self.redis:
                cache_key = f"session:{session.session_id}"
                await self.redis.delete(cache_key)
        
        self.db.commit()
        return count
    
    async def cleanup_expired_sessions(self, max_idle_days: int = 30) -> int:
        """Clean up expired sessions."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_idle_days)
        
        expired_sessions = self.db.query(SecureAuthSession).filter(
            SecureAuthSession.last_activity_at < cutoff_date,
            SecureAuthSession.is_active == True
        ).all()
        
        count = 0
        for session in expired_sessions:
            session.invalidate("expired")
            count += 1
        
        self.db.commit()
        return count