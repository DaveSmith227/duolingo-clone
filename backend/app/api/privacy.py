"""
Privacy & Consent Management API Endpoints

FastAPI routes for privacy notices, consent management, and GDPR compliance
including consent collection, withdrawal, and audit trail access.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_id, get_current_user_payload
from app.schemas.privacy import (
    PrivacyNoticesResponse,
    PrivacyNoticeResponse,
    ConsentRequest,
    ConsentResponse,
    ConsentSummaryResponse,
    UserConsentResponse,
    ConsentWithdrawalRequest,
    ConsentWithdrawalResponse,
    ConsentComplianceResponse,
    ConsentAuditResponse,
    ConsentAuditEntry
)
from app.services.privacy_service import get_privacy_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/privacy", tags=["privacy"])


def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
    }


@router.get("/notices", response_model=PrivacyNoticesResponse, status_code=status.HTTP_200_OK)
async def get_privacy_notices(
    language_code: str = Query("en", description="Language code for notices"),
    notice_type: Optional[str] = Query(None, description="Filter by specific notice type"),
    db: Session = Depends(get_db)
):
    """
    Get current active privacy notices.
    
    Returns all active privacy notices for the specified language.
    Optionally filter by specific notice type.
    """
    try:
        privacy_service = get_privacy_service(db)
        
        notices = privacy_service.get_current_privacy_notices(
            language_code=language_code,
            notice_type=notice_type
        )
        
        # Convert to response format
        notice_responses = []
        for notice in notices:
            notice_response = PrivacyNoticeResponse(
                id=notice.get("id", ""),
                notice_type=notice["notice_type"],
                version=notice["version"],
                title=notice["title"],
                content=notice["content"],
                content_html=notice.get("content_html"),
                summary=notice.get("summary"),
                language_code=notice["language_code"],
                effective_date=datetime.fromisoformat(notice["effective_date"]) if notice.get("effective_date") else datetime.now(timezone.utc),
                requires_consent=notice["requires_consent"],
                is_current=notice["is_current"]
            )
            notice_responses.append(notice_response)
        
        return PrivacyNoticesResponse(
            notices=notice_responses,
            language_code=language_code
        )
        
    except Exception as e:
        logger.error(f"Failed to get privacy notices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "notices_fetch_failed",
                "message": "Failed to retrieve privacy notices."
            }
        )


@router.get("/notices/{notice_id}", response_model=PrivacyNoticeResponse, status_code=status.HTTP_200_OK)
async def get_privacy_notice(
    notice_id: str,
    db: Session = Depends(get_db)
):
    """
    Get specific privacy notice by ID.
    
    Returns detailed information about a specific privacy notice.
    """
    try:
        privacy_service = get_privacy_service(db)
        
        notice = privacy_service.get_privacy_notice_by_id(notice_id)
        
        if not notice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "notice_not_found",
                    "message": "Privacy notice not found."
                }
            )
        
        return PrivacyNoticeResponse(
            id=notice.get("id", notice_id),
            notice_type=notice["notice_type"],
            version=notice["version"],
            title=notice["title"],
            content=notice["content"],
            content_html=notice.get("content_html"),
            summary=notice.get("summary"),
            language_code=notice["language_code"],
            effective_date=datetime.fromisoformat(notice["effective_date"]) if notice.get("effective_date") else datetime.now(timezone.utc),
            requires_consent=notice["requires_consent"],
            is_current=notice["is_current"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get privacy notice {notice_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "notice_fetch_failed",
                "message": "Failed to retrieve privacy notice."
            }
        )


@router.post("/consent", response_model=ConsentResponse, status_code=status.HTTP_200_OK)
async def record_consent(
    consent_data: ConsentRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Record user consent for privacy notices.
    
    Allows users to give or withdraw consent for various data processing
    activities and privacy notices.
    """
    client_info = get_client_info(request)
    
    try:
        privacy_service = get_privacy_service(db)
        
        # Convert consent data to service format
        consent_dict = {
            "consents": []
        }
        
        for consent_item in consent_data.consents:
            consent_dict["consents"].append({
                "consent_type": consent_item.consent_type,
                "privacy_notice_id": consent_item.privacy_notice_id,
                "consent_given": consent_item.consent_given,
                "purpose_description": consent_item.purpose_description,
                "data_categories": consent_item.data_categories,
                "processing_activities": consent_item.processing_activities,
                "withdrawal_reason": consent_item.withdrawal_reason,
                "evidence": consent_item.evidence or {}
            })
        
        # Record consent
        result = await privacy_service.record_consent(
            user_id=current_user_id,
            consent_data=consent_dict,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        return ConsentResponse(
            user_id=result["user_id"],
            consents_processed=result["consents_processed"],
            results=result["results"],
            recorded_at=datetime.fromisoformat(result["recorded_at"])
        )
        
    except ValueError as e:
        logger.warning(f"Invalid consent data for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_consent_data",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to record consent for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "consent_recording_failed",
                "message": "Failed to record consent. Please try again."
            }
        )


@router.get("/consent", response_model=ConsentSummaryResponse, status_code=status.HTTP_200_OK)
async def get_user_consents(
    consent_type: Optional[str] = Query(None, description="Filter by consent type"),
    include_withdrawn: bool = Query(False, description="Include withdrawn consents"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get user's consent records.
    
    Returns all consent records for the authenticated user,
    optionally filtered by consent type.
    """
    try:
        privacy_service = get_privacy_service(db)
        
        consents = privacy_service.get_user_consents(
            user_id=current_user_id,
            consent_type=consent_type,
            include_withdrawn=include_withdrawn
        )
        
        # Convert to response format
        consent_responses = []
        active_count = 0
        withdrawn_count = 0
        
        for consent in consents:
            consent_response = UserConsentResponse(
                id=consent["id"],
                consent_type=consent["consent_type"],
                privacy_notice_id=consent["privacy_notice_id"],
                status=consent["status"],
                consent_given_at=datetime.fromisoformat(consent["consent_given_at"]) if consent["consent_given_at"] else None,
                consent_withdrawn_at=datetime.fromisoformat(consent["consent_withdrawn_at"]) if consent["consent_withdrawn_at"] else None,
                expires_at=datetime.fromisoformat(consent["expires_at"]) if consent["expires_at"] else None,
                is_valid=consent["is_valid"],
                purpose_description=consent["purpose_description"],
                data_categories=consent["data_categories"],
                withdrawal_reason=consent["withdrawal_reason"],
                created_at=datetime.fromisoformat(consent["created_at"])
            )
            consent_responses.append(consent_response)
            
            if consent["status"] == "given":
                active_count += 1
            elif consent["status"] == "withdrawn":
                withdrawn_count += 1
        
        return ConsentSummaryResponse(
            user_id=current_user_id,
            consents=consent_responses,
            total_consents=len(consent_responses),
            active_consents=active_count,
            withdrawn_consents=withdrawn_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get consents for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "consents_fetch_failed",
                "message": "Failed to retrieve consent records."
            }
        )


@router.post("/consent/{consent_id}/withdraw", response_model=ConsentWithdrawalResponse, status_code=status.HTTP_200_OK)
async def withdraw_consent(
    consent_id: str,
    withdrawal_data: ConsentWithdrawalRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Withdraw user consent.
    
    Allows users to withdraw previously given consent for data processing
    activities with proper audit trail.
    """
    client_info = get_client_info(request)
    
    try:
        privacy_service = get_privacy_service(db)
        
        result = await privacy_service.withdraw_consent(
            user_id=current_user_id,
            consent_id=consent_id,
            reason=withdrawal_data.reason,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )
        
        return ConsentWithdrawalResponse(
            consent_id=result["consent_id"],
            consent_type=result["consent_type"],
            status=result["status"],
            withdrawn_at=datetime.fromisoformat(result["withdrawn_at"]),
            reason=result["reason"]
        )
        
    except ValueError as e:
        logger.warning(f"Invalid consent withdrawal for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_withdrawal",
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Failed to withdraw consent {consent_id} for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "withdrawal_failed",
                "message": "Failed to withdraw consent. Please try again."
            }
        )


@router.get("/compliance", response_model=ConsentComplianceResponse, status_code=status.HTTP_200_OK)
async def check_consent_compliance(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Check user's consent compliance status.
    
    Returns the user's compliance status with required privacy notices
    and identifies any missing consents.
    """
    try:
        privacy_service = get_privacy_service(db)
        
        compliance = privacy_service.check_consent_compliance(current_user_id)
        
        return ConsentComplianceResponse(
            user_id=compliance["user_id"],
            overall_compliant=compliance["overall_compliant"],
            compliance_status=compliance["compliance_status"],
            missing_consents=compliance["missing_consents"],
            checked_at=datetime.fromisoformat(compliance["checked_at"])
        )
        
    except Exception as e:
        logger.error(f"Failed to check compliance for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "compliance_check_failed",
                "message": "Failed to check consent compliance."
            }
        )


@router.get("/audit", response_model=ConsentAuditResponse, status_code=status.HTTP_200_OK)
async def get_consent_audit_trail(
    consent_id: Optional[str] = Query(None, description="Filter by consent ID"),
    limit: int = Query(50, description="Maximum records to return", ge=1, le=100),
    offset: int = Query(0, description="Number of records to skip", ge=0),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get consent audit trail for the authenticated user.
    
    Returns audit trail of all consent-related activities for the user
    with optional filtering by consent ID.
    """
    try:
        privacy_service = get_privacy_service(db)
        
        audit_trail = privacy_service.get_consent_audit_trail(
            user_id=current_user_id,
            consent_id=consent_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        audit_entries = []
        for entry in audit_trail:
            audit_entry = ConsentAuditEntry(
                id=entry["id"],
                event_type=entry["event_type"],
                description=entry["description"],
                user_id=entry["user_id"],
                consent_id=entry["consent_id"],
                privacy_notice_id=entry["privacy_notice_id"],
                performed_by=entry["performed_by"],
                performed_by_type=entry["performed_by_type"],
                ip_address=entry["ip_address"],
                old_values=entry["old_values"],
                new_values=entry["new_values"],
                created_at=datetime.fromisoformat(entry["created_at"])
            )
            audit_entries.append(audit_entry)
        
        return ConsentAuditResponse(
            audit_trail=audit_entries,
            total_count=len(audit_entries)
        )
        
    except Exception as e:
        logger.error(f"Failed to get audit trail for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "audit_fetch_failed",
                "message": "Failed to retrieve audit trail."
            }
        )