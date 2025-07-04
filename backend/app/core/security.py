"""
Security Utilities

JWT token generation, validation, password hashing, and authentication utilities
for the Duolingo clone backend application.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt

from app.core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT algorithm
ALGORITHM = "HS256"


def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing the payload data
        expires_delta: Optional timedelta for custom expiration
        
    Returns:
        JWT token string
    """
    settings = get_settings()
    
    # Create a copy of the data to avoid modifying the original
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.app_name,
        "type": "access"
    })
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key, 
            algorithm=ALGORITHM
        )
        logger.debug(f"Created access token for subject: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise


def create_refresh_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Dictionary containing the payload data
        expires_delta: Optional timedelta for custom expiration
        
    Returns:
        JWT refresh token string
    """
    settings = get_settings()
    
    # Create a copy of the data to avoid modifying the original
    to_encode = data.copy()
    
    # Set expiration time (longer for refresh tokens)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.app_name,
        "type": "refresh"
    })
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key, 
            algorithm=ALGORITHM
        )
        logger.debug(f"Created refresh token for subject: {data.get('sub', 'unknown')}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[ALGORITHM]
        )
        
        # Validate token type if present
        token_type = payload.get("type")
        if token_type and token_type not in ["access", "refresh", "password_reset"]:
            logger.warning(f"Invalid token type: {token_type}")
            return None
            
        logger.debug(f"Successfully verified {token_type} token for subject: {payload.get('sub', 'unknown')}")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify an access token specifically.
    
    Args:
        token: JWT access token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    payload = verify_token(token)
    
    if payload and payload.get("type") == "access":
        return payload
    
    if payload:
        logger.warning(f"Expected access token but got: {payload.get('type')}")
    
    return None


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a refresh token specifically.
    
    Args:
        token: JWT refresh token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    payload = verify_token(token)
    
    if payload and payload.get("type") == "refresh":
        return payload
    
    if payload:
        logger.warning(f"Expected refresh token but got: {payload.get('type')}")
    
    return None


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Failed to hash password: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"Password verification: {'success' if is_valid else 'failed'}")
        return is_valid
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_data: User data to encode in tokens
        
    Returns:
        Dictionary with access_token and refresh_token
    """
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        JWT token string or None if invalid format
    """
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            logger.debug(f"Invalid authorization scheme: {scheme}")
            return None
        return token
    except ValueError:
        logger.debug("Invalid authorization header format")
        return None


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        Secure random token as hex string
    """
    import secrets
    return secrets.token_hex(length)


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired without full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is expired, False otherwise
    """
    try:
        # Decode without verification to check expiration
        payload = jwt.decode(
            token, 
            options={"verify_signature": False, "verify_exp": False}
        )
        
        exp = payload.get("exp")
        if not exp:
            return True
            
        exp_datetime = datetime.utcfromtimestamp(exp)
        return datetime.utcnow() > exp_datetime
        
    except Exception as e:
        logger.debug(f"Error checking token expiration: {e}")
        return True


def get_token_subject(token: str) -> Optional[str]:
    """
    Extract the subject (user ID) from a token without full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        Token subject or None if not found
    """
    try:
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        return payload.get("sub")
    except Exception as e:
        logger.debug(f"Error extracting token subject: {e}")
        return None


def create_password_reset_token(user_id: str) -> str:
    """
    Create a password reset token.
    
    Args:
        user_id: User ID for the reset token
        
    Returns:
        Password reset token
    """
    data = {
        "sub": user_id,
        "type": "password_reset"
    }
    
    # Password reset tokens expire in 1 hour
    expires_delta = timedelta(hours=1)
    
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.app_name
    })
    
    try:
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.secret_key, 
            algorithm=ALGORITHM
        )
        logger.debug(f"Created password reset token for user: {user_id}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create password reset token: {e}")
        raise


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return user ID.
    
    Args:
        token: Password reset token
        
    Returns:
        User ID if token is valid, None otherwise
    """
    payload = verify_token(token)
    
    if payload and payload.get("type") == "password_reset":
        return payload.get("sub")
    
    return None