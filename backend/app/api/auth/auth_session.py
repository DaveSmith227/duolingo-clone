"""
Session management endpoints (refresh, logout, current user).
"""
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.models.auth import AuthSession
from app.schemas.auth import AuthTokenResponse, UserResponse
from app.services.session_manager import SessionManager
from app.services.audit_logger import AuditLogger
from app.services.cookie_manager import CookieManager
from .auth_utils import get_client_info, create_user_response

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Check if session exists and is valid
        session = db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.is_active == True,
            AuthSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid"
            )
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Initialize services
    session_manager = SessionManager(db, settings)
    audit_logger = AuditLogger(db)
    cookie_manager = CookieManager(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    try:
        # Refresh the session
        session_data = await session_manager.refresh_session(refresh_token)
        
        # Get user
        user = db.query(User).filter(User.id == session_data["user_id"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Set new auth cookies
        cookie_manager.set_auth_cookies(
            response,
            session_data["access_token"],
            session_data["refresh_token"]
        )
        
        # Log token refresh
        await audit_logger.log_event(
            user_id=user.id,
            event_type="token_refresh",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "expires_in": session_data["expires_in"],
            "user": create_user_response(user)
        }
        
    except ValueError as e:
        await audit_logger.log_security_event(
            user_id=None,
            event_type="token_refresh_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout current user and invalidate session."""
    # Initialize services
    session_manager = SessionManager(db, settings)
    audit_logger = AuditLogger(db)
    cookie_manager = CookieManager(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Get current session from token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            session_id = payload.get("session_id")
            
            if session_id:
                # Invalidate the session
                await session_manager.invalidate_session(session_id)
            
        except jwt.InvalidTokenError:
            pass  # Session already invalid
    
    # Clear auth cookies
    cookie_manager.clear_auth_cookies(response)
    
    # Log logout
    await audit_logger.log_event(
        user_id=user.id,
        event_type="logout",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True
    )
    
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    user: User = Depends(get_current_user)
):
    """Get current authenticated user profile with role information."""
    # Ensure role is included in response (server-authoritative)
    response = create_user_response(user)
    
    # Explicitly include role to ensure it's not parsed from JWT
    response["role"] = user.role
    
    return response