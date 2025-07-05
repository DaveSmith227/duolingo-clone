"""
Cookie Management Service

Secure cookie management for JWT tokens with proper security flags,
httpOnly cookies, and CSRF protection for the authentication system.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CookieManager:
    """
    Secure cookie management service for JWT tokens.
    
    Handles secure storage of access and refresh tokens using httpOnly cookies
    with proper security flags and CSRF protection.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.access_token_name = "access_token"
        self.refresh_token_name = "refresh_token"
        self.csrf_token_name = "csrf_token"
    
    def set_auth_cookies(
        self,
        response: Response,
        access_token: str,
        refresh_token: str,
        csrf_token: Optional[str] = None,
        remember_me: bool = False
    ) -> None:
        """
        Set authentication cookies on response.
        
        Args:
            response: FastAPI Response object
            access_token: JWT access token
            refresh_token: JWT refresh token
            csrf_token: CSRF protection token
            remember_me: Whether to extend cookie expiration
        """
        try:
            # Calculate cookie expiration
            if remember_me:
                access_max_age = self.settings.access_token_expire_minutes * 60
                refresh_max_age = self.settings.remember_me_expire_days * 24 * 60 * 60
            else:
                access_max_age = self.settings.access_token_expire_minutes * 60
                refresh_max_age = self.settings.refresh_token_expire_days * 24 * 60 * 60
            
            # Set access token cookie (httpOnly, secure)
            response.set_cookie(
                key=self.access_token_name,
                value=access_token,
                max_age=access_max_age,
                httponly=True,
                secure=not self.settings.is_development,
                samesite="lax",
                path="/api"
            )
            
            # Set refresh token cookie (httpOnly, secure, longer expiration)
            response.set_cookie(
                key=self.refresh_token_name,
                value=refresh_token,
                max_age=refresh_max_age,
                httponly=True,
                secure=not self.settings.is_development,
                samesite="lax",
                path="/api/auth"  # Restrict to auth endpoints only
            )
            
            # Set CSRF token cookie (accessible to JavaScript for headers)
            if csrf_token:
                response.set_cookie(
                    key=self.csrf_token_name,
                    value=csrf_token,
                    max_age=access_max_age,
                    httponly=False,  # Accessible to JavaScript
                    secure=not self.settings.is_development,
                    samesite="lax",
                    path="/"
                )
            
            logger.debug("Set authentication cookies successfully")
            
        except Exception as e:
            logger.error(f"Failed to set authentication cookies: {str(e)}")
            raise
    
    def clear_auth_cookies(self, response: Response) -> None:
        """
        Clear all authentication cookies.
        
        Args:
            response: FastAPI Response object
        """
        try:
            # Clear access token cookie
            response.delete_cookie(
                key=self.access_token_name,
                path="/api",
                secure=not self.settings.is_development,
                samesite="lax"
            )
            
            # Clear refresh token cookie
            response.delete_cookie(
                key=self.refresh_token_name,
                path="/api/auth",
                secure=not self.settings.is_development,
                samesite="lax"
            )
            
            # Clear CSRF token cookie
            response.delete_cookie(
                key=self.csrf_token_name,
                path="/",
                secure=not self.settings.is_development,
                samesite="lax"
            )
            
            logger.debug("Cleared authentication cookies successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear authentication cookies: {str(e)}")
            raise
    
    def get_access_token_from_cookie(self, request: Request) -> Optional[str]:
        """
        Extract access token from request cookies.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Access token string or None if not found
        """
        try:
            token = request.cookies.get(self.access_token_name)
            if token:
                logger.debug("Access token found in cookies")
                return token
            
            logger.debug("No access token found in cookies")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get access token from cookies: {str(e)}")
            return None
    
    def get_refresh_token_from_cookie(self, request: Request) -> Optional[str]:
        """
        Extract refresh token from request cookies.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Refresh token string or None if not found
        """
        try:
            token = request.cookies.get(self.refresh_token_name)
            if token:
                logger.debug("Refresh token found in cookies")
                return token
            
            logger.debug("No refresh token found in cookies")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get refresh token from cookies: {str(e)}")
            return None
    
    def get_csrf_token_from_cookie(self, request: Request) -> Optional[str]:
        """
        Extract CSRF token from request cookies.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            CSRF token string or None if not found
        """
        try:
            token = request.cookies.get(self.csrf_token_name)
            if token:
                logger.debug("CSRF token found in cookies")
                return token
            
            logger.debug("No CSRF token found in cookies")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get CSRF token from cookies: {str(e)}")
            return None
    
    def get_csrf_token_from_header(self, request: Request) -> Optional[str]:
        """
        Extract CSRF token from request headers.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            CSRF token string or None if not found
        """
        try:
            # Check X-CSRF-Token header
            token = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")
            if token:
                logger.debug("CSRF token found in headers")
                return token
            
            logger.debug("No CSRF token found in headers")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get CSRF token from headers: {str(e)}")
            return None
    
    def validate_csrf_token(self, request: Request) -> bool:
        """
        Validate CSRF token from cookie and header match.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            True if CSRF tokens match, False otherwise
        """
        try:
            # Skip CSRF validation for GET requests (safe methods)
            if request.method.upper() in ["GET", "HEAD", "OPTIONS"]:
                return True
            
            cookie_token = self.get_csrf_token_from_cookie(request)
            header_token = self.get_csrf_token_from_header(request)
            
            if not cookie_token or not header_token:
                logger.warning("Missing CSRF token in cookie or header")
                return False
            
            if cookie_token != header_token:
                logger.warning("CSRF token mismatch between cookie and header")
                return False
            
            logger.debug("CSRF token validation successful")
            return True
            
        except Exception as e:
            logger.error(f"CSRF token validation error: {str(e)}")
            return False
    
    def generate_secure_cookie_data(self, tokens: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate secure cookie data with CSRF token.
        
        Args:
            tokens: Dictionary containing access_token and refresh_token
            
        Returns:
            Dictionary with cookie data and CSRF token
        """
        try:
            import secrets
            
            # Generate CSRF token
            csrf_token = secrets.token_urlsafe(32)
            
            return {
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "csrf_token": csrf_token,
                "token_type": "bearer",
                "expires_in": tokens.get("expires_in")
            }
            
        except Exception as e:
            logger.error(f"Failed to generate secure cookie data: {str(e)}")
            raise
    
    def create_secure_response_with_tokens(
        self,
        response: Response,
        tokens: Dict[str, Any],
        remember_me: bool = False
    ) -> Dict[str, Any]:
        """
        Create secure response with tokens set as cookies.
        
        Args:
            response: FastAPI Response object
            tokens: Token dictionary from session manager
            remember_me: Whether to extend cookie expiration
            
        Returns:
            Response data for client (without sensitive tokens)
        """
        try:
            # Generate secure cookie data
            cookie_data = self.generate_secure_cookie_data(tokens)
            
            # Set secure cookies
            self.set_auth_cookies(
                response=response,
                access_token=cookie_data["access_token"],
                refresh_token=cookie_data["refresh_token"],
                csrf_token=cookie_data["csrf_token"],
                remember_me=remember_me
            )
            
            # Return safe response data (no tokens)
            return {
                "success": True,
                "message": "Authentication successful",
                "csrf_token": cookie_data["csrf_token"],  # Client needs this for requests
                "expires_in": cookie_data["expires_in"],
                "user": tokens.get("user", {}),
                "session_id": tokens.get("session_id")
            }
            
        except Exception as e:
            logger.error(f"Failed to create secure response with tokens: {str(e)}")
            raise


class CookieHTTPBearer(HTTPBearer):
    """
    Custom HTTPBearer that supports cookie-based authentication.
    
    Extends FastAPI's HTTPBearer to check cookies for JWT tokens
    as a fallback when Authorization header is not present.
    """
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.cookie_manager = CookieManager()
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        Extract authorization credentials from header or cookies.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            HTTPAuthorizationCredentials or None
        """
        try:
            # First, try to get token from Authorization header
            try:
                credentials = await super().__call__(request)
                if credentials:
                    return credentials
            except:
                pass  # Fall back to cookies
            
            # Try to get token from cookies
            access_token = self.cookie_manager.get_access_token_from_cookie(request)
            if access_token:
                return HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=access_token
                )
            
            # No token found
            if self.auto_error:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in CookieHTTPBearer: {str(e)}")
            if self.auto_error:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None


# Global instances
cookie_manager = CookieManager()
cookie_bearer = CookieHTTPBearer()


def get_cookie_manager() -> CookieManager:
    """
    Get CookieManager instance.
    
    Returns:
        Global CookieManager instance
    """
    return cookie_manager


def get_cookie_bearer() -> CookieHTTPBearer:
    """
    Get CookieHTTPBearer instance for dependency injection.
    
    Returns:
        Global CookieHTTPBearer instance
    """
    return cookie_bearer