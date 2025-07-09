"""
Multi-Factor Authentication (MFA) endpoints.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import (
    MFAEnableRequest, 
    MFAVerifyRequest, 
    MFADisableRequest,
    MFAStatusResponse,
    MFASetupResponse,
    MFABackupCodesResponse
)
from app.services.mfa_service import MFAService
from app.services.audit_logger import AuditLogger
from app.services.password_security import PasswordSecurity
from .auth_utils import get_client_info
from .auth_session import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.get("/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get MFA status for current user."""
    mfa_service = MFAService(db, settings)
    
    status = await mfa_service.get_mfa_status(user.id)
    
    return {
        "enabled": status["enabled"],
        "method": status["method"],
        "backup_codes_remaining": status["backup_codes_remaining"],
        "last_used_at": status["last_used_at"],
        "enabled_at": status["enabled_at"]
    }


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initialize MFA setup for user."""
    # Initialize services
    mfa_service = MFAService(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Check if MFA is already enabled
    if await mfa_service.is_mfa_enabled(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled for this account"
        )
    
    try:
        # Generate TOTP secret and QR code
        mfa_data = await mfa_service.generate_totp_secret(user.id)
        
        # Log MFA setup initiation
        await audit_logger.log_event(
            user_id=user.id,
            event_type="mfa_setup_initiated",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return {
            "secret": mfa_data["secret"],
            "qr_code": mfa_data["qr_code"],
            "manual_entry_key": mfa_data["secret"],
            "manual_entry_setup": f"Issuer: {mfa_service.issuer_name}, Account: {user.email}"
        }
        
    except Exception as e:
        logger.error(f"MFA setup error for user {user.id}: {str(e)}")
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_setup_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup MFA. Please try again."
        )


@router.post("/mfa/enable", response_model=MFABackupCodesResponse)
async def enable_mfa(
    request: Request,
    data: MFAEnableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable MFA after verifying TOTP code."""
    # Initialize services
    mfa_service = MFAService(db, settings)
    password_security = PasswordSecurity(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Verify password for security
    if not password_security.verify_password(data.password, user.password_hash):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_enable_invalid_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Verify TOTP code and enable MFA
    if await mfa_service.verify_totp_code(user.id, data.totp_code, enable_on_success=True):
        # Generate backup codes
        backup_codes = await mfa_service._generate_backup_codes(user.id)
        
        # Log successful MFA enablement
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_enabled",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True,
            details={"method": "totp"}
        )
        
        return {
            "message": "MFA has been successfully enabled",
            "backup_codes": backup_codes,
            "warning": "Save these backup codes in a secure location. They can be used to access your account if you lose your authenticator device."
        }
    else:
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_enable_invalid_code",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )


@router.post("/mfa/verify")
async def verify_mfa(
    request: Request,
    data: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify MFA code during login."""
    # Initialize services
    mfa_service = MFAService(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # This endpoint would be called during login flow
    # The session_id would be from a temporary MFA challenge session
    # For now, we'll validate the structure
    
    try:
        success = False
        method = data.method
        
        if method == "totp":
            success = await mfa_service.verify_totp_code(data.user_id, data.code)
        elif method == "backup_code":
            success = await mfa_service.verify_backup_code(data.user_id, data.code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA method"
            )
        
        if success:
            await audit_logger.log_event(
                user_id=data.user_id,
                event_type="mfa_verification_success",
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                success=True,
                details={"method": method}
            )
            
            return {"verified": True, "message": "MFA verification successful"}
        else:
            await audit_logger.log_security_event(
                user_id=data.user_id,
                event_type="mfa_verification_failed",
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                success=False,
                details={"method": method}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA verification failed"
        )


@router.post("/mfa/disable")
async def disable_mfa(
    request: Request,
    data: MFADisableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable MFA for user account."""
    # Initialize services
    mfa_service = MFAService(db, settings)
    password_security = PasswordSecurity(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Verify password for security
    if not password_security.verify_password(data.password, user.password_hash):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_disable_invalid_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Verify TOTP code before disabling
    if not await mfa_service.verify_totp_code(user.id, data.totp_code):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_disable_invalid_code",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Disable MFA
    if await mfa_service.disable_mfa(user.id):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_disabled",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return {"message": "MFA has been successfully disabled"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to disable MFA"
        )


@router.post("/mfa/backup-codes/regenerate", response_model=MFABackupCodesResponse)
async def regenerate_backup_codes(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate MFA backup codes."""
    # Initialize services
    mfa_service = MFAService(db, settings)
    audit_logger = AuditLogger(db)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Check if MFA is enabled
    if not await mfa_service.is_mfa_enabled(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled for this account"
        )
    
    # Regenerate backup codes
    backup_codes = await mfa_service.regenerate_backup_codes(user.id)
    
    if backup_codes:
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="mfa_backup_codes_regenerated",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True
        )
        
        return {
            "message": "Backup codes have been regenerated",
            "backup_codes": backup_codes,
            "warning": "Your old backup codes are no longer valid. Save these new codes in a secure location."
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to regenerate backup codes"
        )