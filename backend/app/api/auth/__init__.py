"""
Authentication module initialization and router aggregation.
"""
from fastapi import APIRouter

from .auth_registration import router as registration_router
from .auth_login import router as login_router
from .auth_session import router as session_router
from .auth_password import router as password_router
from .auth_verification import router as verification_router
from .auth_gdpr import router as gdpr_router
from .auth_mfa import router as mfa_router

# Create main auth router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Include all sub-routers
auth_router.include_router(registration_router)
auth_router.include_router(login_router)
auth_router.include_router(session_router)
auth_router.include_router(password_router)
auth_router.include_router(verification_router)
auth_router.include_router(gdpr_router)
auth_router.include_router(mfa_router)

__all__ = ["auth_router"]