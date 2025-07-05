"""
GDPR compliance endpoints (data export, account deletion).
"""
import logging
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import tempfile
import os

from app.core.database import get_db
from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import AccountDeletionRequest, DataExportRequest
from app.services.audit_logger import AuditLogger
from app.services.gdpr_service import GDPRService
from app.services.password_security import PasswordSecurity
from .auth_utils import get_client_info
from .auth_session import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/delete-account")
async def delete_account(
    request: Request,
    data: AccountDeletionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account (GDPR compliance)."""
    # Initialize services
    password_security = PasswordSecurity(db, settings)
    audit_logger = AuditLogger(db)
    gdpr_service = GDPRService(db, settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Verify password for security
    if not password_security.verify_password(data.password, user.password_hash):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="account_deletion_invalid_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Log deletion request
    await audit_logger.log_security_event(
        user_id=user.id,
        event_type="account_deletion_requested",
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        success=True,
        details={
            "reason": data.reason,
            "feedback": data.feedback
        }
    )
    
    try:
        # Perform account deletion
        deletion_result = await gdpr_service.delete_user_account(
            user.id,
            reason=data.reason,
            feedback=data.feedback
        )
        
        if deletion_result["success"]:
            # Log successful deletion
            await audit_logger.log_security_event(
                user_id=user.id,
                event_type="account_deletion_success",
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                success=True,
                details={
                    "data_removed": deletion_result.get("data_removed", {}),
                    "anonymized": deletion_result.get("anonymized", False)
                }
            )
            
            return {
                "message": "Your account has been successfully deleted.",
                "deletion_id": deletion_result.get("deletion_id")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account deletion failed. Please contact support."
            )
            
    except Exception as e:
        logger.error(f"Account deletion error for user {user.id}: {str(e)}")
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="account_deletion_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed. Please contact support."
        )


@router.post("/export-data")
async def export_user_data(
    request: Request,
    data: DataExportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all user data (GDPR compliance)."""
    # Initialize services
    password_security = PasswordSecurity(db, settings)
    audit_logger = AuditLogger(db)
    gdpr_service = GDPRService(db, settings)
    
    # Get client info
    client_info = await get_client_info(request)
    
    # Verify password for security
    if not password_security.verify_password(data.password, user.password_hash):
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="data_export_invalid_password",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Check rate limiting for data exports
    last_export = await gdpr_service.get_last_export_time(user.id)
    if last_export and (datetime.utcnow() - last_export).days < 7:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Data export can only be requested once every 7 days"
        )
    
    try:
        # Collect all user data
        user_data = await gdpr_service.collect_user_data(user.id)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as tmp_file:
            json.dump(user_data, tmp_file, indent=2, default=str)
            tmp_file_path = tmp_file.name
        
        # Log data export
        await audit_logger.log_event(
            user_id=user.id,
            event_type="data_export_success",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=True,
            details={
                "format": data.format,
                "data_size": os.path.getsize(tmp_file_path)
            }
        )
        
        # Return file
        return FileResponse(
            path=tmp_file_path,
            filename=f"user_data_{user.id}_{datetime.utcnow().strftime('%Y%m%d')}.json",
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=user_data_{user.id}.json"
            }
        )
        
    except Exception as e:
        logger.error(f"Data export error for user {user.id}: {str(e)}")
        await audit_logger.log_security_event(
            user_id=user.id,
            event_type="data_export_failed",
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data export failed. Please try again later."
        )