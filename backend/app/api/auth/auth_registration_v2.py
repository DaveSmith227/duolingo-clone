"""
User registration endpoint using service layer pattern.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.schemas.auth import UserRegister, AuthTokenResponse
from app.services.auth_service import AuthService
from app.services.cookie_manager import CookieManager
from app.core.exceptions import (
    RateLimitExceededError,
    ValidationError,
    DuplicateError
)
from .auth_utils import get_client_info, create_user_response

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/register", response_model=AuthTokenResponse)
async def register(
    request: Request,
    response: Response,
    data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.
    
    This endpoint uses the AuthService to handle all registration logic,
    demonstrating clean separation of concerns.
    """
    # Initialize services
    auth_service = AuthService(db)
    cookie_manager = CookieManager(settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    try:
        # Register user through service layer
        user, session_data = await auth_service.register_user(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            client_info=client_info
        )
        
        # Set auth cookies
        cookie_manager.set_auth_cookies(
            response,
            session_data["access_token"],
            session_data["refresh_token"]
        )
        
        # Return response
        return {
            "access_token": session_data["access_token"],
            "refresh_token": session_data["refresh_token"],
            "token_type": "bearer",
            "expires_in": session_data["expires_in"],
            "user": create_user_response(user)
        }
        
    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except (ValidationError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DuplicateError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )