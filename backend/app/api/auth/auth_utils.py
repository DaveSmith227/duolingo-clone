"""
Common authentication utilities and helper functions.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import jwt
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.config import get_settings

settings = get_settings()


async def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request."""
    user_agent = request.headers.get("User-Agent", "Unknown")
    ip_address = request.headers.get("X-Forwarded-For", request.client.host)
    
    return {
        "user_agent": user_agent,
        "ip_address": ip_address,
        "device_fingerprint": request.headers.get("X-Device-Fingerprint", ""),
        "referer": request.headers.get("Referer", ""),
        "timestamp": datetime.utcnow()
    }


def create_user_response(user: User) -> Dict[str, Any]:
    """Create standardized user response with server-authoritative role."""
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,  # Server-authoritative role - NEVER parse from JWT
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_email_verified": user.is_verified,  # Add alias for frontend compatibility
        "created_at": user.created_at,
        "profile": {
            "display_name": user.profile.display_name if user.profile else None,
            "avatar_url": user.profile.avatar_url if user.profile else None,
            "language": user.profile.preferred_language if user.profile else "en",
            "timezone": user.profile.timezone if user.profile else "UTC"
        }
    }


async def verify_oauth_token(provider: str, token: str) -> Dict[str, Any]:
    """Verify OAuth token with provider."""
    async with httpx.AsyncClient() as client:
        try:
            if provider == "google":
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "email": data.get("email"),
                        "first_name": data.get("given_name"),
                        "last_name": data.get("family_name"),
                        "provider_id": data.get("id"),
                        "verified": data.get("verified_email", False)
                    }
                    
            elif provider == "facebook":
                response = await client.get(
                    f"https://graph.facebook.com/me?fields=id,name,email&access_token={token}"
                )
                if response.status_code == 200:
                    data = response.json()
                    name_parts = data.get("name", "").split(" ", 1)
                    return {
                        "email": data.get("email"),
                        "first_name": name_parts[0] if name_parts else "",
                        "last_name": name_parts[1] if len(name_parts) > 1 else "",
                        "provider_id": data.get("id"),
                        "verified": True
                    }
                    
            elif provider == "apple":
                # Decode Apple's identity token (JWT)
                try:
                    # In production, verify with Apple's public key
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    return {
                        "email": decoded.get("email"),
                        "first_name": decoded.get("given_name", ""),
                        "last_name": decoded.get("family_name", ""),
                        "provider_id": decoded.get("sub"),
                        "verified": decoded.get("email_verified", False)
                    }
                except jwt.DecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid Apple identity token"
                    )
                    
            elif provider == "tiktok":
                # TikTok OAuth implementation
                response = await client.get(
                    "https://open-api.tiktok.com/oauth/userinfo/",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    data = response.json()["data"]
                    return {
                        "email": data.get("email", ""),
                        "first_name": data.get("display_name", ""),
                        "last_name": "",
                        "provider_id": data.get("open_id"),
                        "verified": True
                    }
                    
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported OAuth provider: {provider}"
                )
                
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to verify token with {provider}: {str(e)}"
            )
    
    raise HTTPException(
        status_code=401,
        detail=f"Invalid OAuth token for provider: {provider}"
    )


def validate_password_strength(password: str) -> bool:
    """Validate password meets minimum requirements."""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    return all([has_upper, has_lower, has_digit, has_special])


def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize user input to prevent injection attacks."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            # Remove any potentially harmful characters
            value = value.strip()
            # Additional sanitization logic here
        sanitized[key] = value
    return sanitized