"""
Admin API Endpoints

API endpoints for administrative functionality including user management,
audit log viewing, and system analytics.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from math import ceil
import json
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import get_db, get_current_admin_user
from app.models.user import User
from app.models.auth import SupabaseUser, AuthSession, AuthAuditLog
from app.models.rbac import Role, UserRoleAssignment
from app.schemas.admin import (
    UserSearchRequest, UserSearchResponse, UserSummary, UserActionRequest,
    UserActionResponse, BulkUserActionRequest, BulkUserActionResponse,
    AuditLogFilter, AuditLogResponse, AuditLogEntry, AuditLogExportRequest,
    AdminAnalyticsResponse, SystemMetrics, SecurityAlert, AdminUserDetail,
    UserDetailResponse, UserActionType
)
from app.services.audit_logger import get_audit_logger, AuditSeverity
from app.services.gdpr_service import GDPRService
from app.services.session_manager import SessionManager
from app.services.privacy_service import PrivacyService

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/users/search", response_model=UserSearchResponse)
async def search_users(
    request: Request,
    query: Optional[str] = Query(None, description="Search query for email or name"),
    status: str = Query("all", description="Filter by user status"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before this date"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Search and filter users for admin dashboard."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Build base query
        base_query = db.query(User)
        
        # Apply status filter
        if status != "all":
            if status == "active":
                base_query = base_query.filter(User.is_active == True, User.deleted_at.is_(None))
            elif status == "suspended":
                base_query = base_query.filter(User.is_active == False, User.deleted_at.is_(None))
            elif status == "deleted":
                base_query = base_query.filter(User.deleted_at.is_not(None))
        
        # Apply search query
        if query:
            search_filter = or_(
                User.email.ilike(f"%{query}%"),
                User.name.ilike(f"%{query}%")
            )
            base_query = base_query.filter(search_filter)
        
        # Apply date filters
        if created_after:
            base_query = base_query.filter(User.created_at >= created_after)
        if created_before:
            base_query = base_query.filter(User.created_at <= created_before)
        
        # Get total count
        total_count = base_query.count()
        
        # Apply sorting
        if sort_by == "email":
            sort_field = User.email
        elif sort_by == "name":
            sort_field = User.name
        elif sort_by == "updated_at":
            sort_field = User.updated_at
        else:
            sort_field = User.created_at
        
        if sort_order == "desc":
            base_query = base_query.order_by(sort_field.desc())
        else:
            base_query = base_query.order_by(sort_field.asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        users = base_query.offset(offset).limit(page_size).all()
        
        # Build user summaries
        user_summaries = []
        for user in users:
            # Get user roles
            roles = db.query(Role.name).join(UserRoleAssignment).filter(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.is_active == True
            ).all()
            role_names = [role.name for role in roles]
            
            # Get Supabase user
            supabase_user = db.query(SupabaseUser).filter(
                SupabaseUser.app_user_id == user.id
            ).first()
            
            # Get login statistics
            login_count = db.query(AuthAuditLog).filter(
                AuthAuditLog.user_id == user.id,
                AuthAuditLog.event_type == "login",
                AuthAuditLog.success == True
            ).count()
            
            failed_login_count = db.query(AuthAuditLog).filter(
                AuthAuditLog.user_id == user.id,
                AuthAuditLog.event_type == "login",
                AuthAuditLog.success == False
            ).count()
            
            # Get last login
            last_login = db.query(AuthAuditLog.created_at).filter(
                AuthAuditLog.user_id == user.id,
                AuthAuditLog.event_type == "login",
                AuthAuditLog.success == True
            ).order_by(AuthAuditLog.created_at.desc()).first()
            
            user_summaries.append(UserSummary(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                is_suspended=not user.is_active and user.deleted_at is None,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=last_login.created_at if last_login else None,
                login_count=login_count,
                failed_login_count=failed_login_count,
                roles=role_names,
                supabase_id=supabase_user.id if supabase_user else None
            ))
        
        # Calculate pagination info
        total_pages = ceil(total_count / page_size)
        has_next = page < total_pages
        has_previous = page > 1
        
        # Log admin action
        await audit_logger.log_authentication_event(
            event_type="admin_user_search",
            success=True,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "query": query,
                "status_filter": status,
                "results_count": len(user_summaries),
                "total_count": total_count
            },
            severity=AuditSeverity.LOW
        )
        
        return UserSearchResponse(
            users=user_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except Exception as e:
        logger.error(f"Failed to search users: {e}")
        await audit_logger.log_authentication_event(
            event_type="admin_user_search",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"error": str(e)},
            severity=AuditSeverity.HIGH
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    request: Request,
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific user."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user roles
        roles = db.query(Role.name).join(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.is_active == True
        ).all()
        role_names = [role.name for role in roles]
        
        # Get Supabase user
        supabase_user = db.query(SupabaseUser).filter(
            SupabaseUser.app_user_id == user.id
        ).first()
        
        # Get login statistics
        login_count = db.query(AuthAuditLog).filter(
            AuthAuditLog.user_id == user.id,
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == True
        ).count()
        
        failed_login_count = db.query(AuthAuditLog).filter(
            AuthAuditLog.user_id == user.id,
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == False
        ).count()
        
        # Get last login
        last_login = db.query(AuthAuditLog.created_at).filter(
            AuthAuditLog.user_id == user.id,
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == True
        ).order_by(AuthAuditLog.created_at.desc()).first()
        
        # Get recent sessions
        recent_sessions = db.query(AuthSession).filter(
            AuthSession.supabase_user_id == supabase_user.id if supabase_user else None
        ).order_by(AuthSession.created_at.desc()).limit(5).all()
        
        session_data = []
        for session in recent_sessions:
            session_data.append({
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "is_active": session.is_active,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent
            })
        
        # Get recent audit events
        recent_events = db.query(AuthAuditLog).filter(
            AuthAuditLog.user_id == user.id
        ).order_by(AuthAuditLog.created_at.desc()).limit(10).all()
        
        event_data = []
        for event in recent_events:
            event_data.append({
                "id": event.id,
                "event_type": event.event_type,
                "success": event.success,
                "created_at": event.created_at.isoformat(),
                "ip_address": event.ip_address,
                "user_agent": event.user_agent
            })
        
        # Get consent status
        privacy_service = PrivacyService(db)
        consent_status = privacy_service.check_consent_compliance(user.id)
        
        # Build user detail
        user_detail = AdminUserDetail(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_suspended=not user.is_active and user.deleted_at is None,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=last_login.created_at if last_login else None,
            login_count=login_count,
            failed_login_count=failed_login_count,
            roles=role_names,
            supabase_id=supabase_user.id if supabase_user else None,
            profile_data={
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            },
            consent_status=consent_status,
            recent_sessions=session_data,
            recent_audit_events=event_data
        )
        
        # Get permissions (simplified)
        permissions = ["read_profile", "update_profile"] if user.is_active else []
        
        # Calculate account statistics
        account_stats = {
            "total_logins": login_count,
            "failed_logins": failed_login_count,
            "success_rate": login_count / (login_count + failed_login_count) if (login_count + failed_login_count) > 0 else 0,
            "account_age_days": (datetime.now(timezone.utc) - user.created_at).days,
            "last_activity": user.updated_at.isoformat() if user.updated_at else None
        }
        
        # Log admin action
        await audit_logger.log_authentication_event(
            event_type="admin_user_detail_view",
            success=True,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"target_user_id": user_id},
            severity=AuditSeverity.LOW
        )
        
        return UserDetailResponse(
            user=user_detail,
            permissions=permissions,
            account_statistics=account_stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user detail: {e}")
        await audit_logger.log_authentication_event(
            event_type="admin_user_detail_view",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"target_user_id": user_id, "error": str(e)},
            severity=AuditSeverity.HIGH
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user details"
        )


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_admin_analytics(
    request: Request,
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get admin analytics dashboard data."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Calculate system metrics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True, User.deleted_at.is_(None)).count()
        suspended_users = db.query(User).filter(User.is_active == False, User.deleted_at.is_(None)).count()
        deleted_users = db.query(User).filter(User.deleted_at.is_not(None)).count()
        
        # New users last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        new_users_last_30_days = db.query(User).filter(User.created_at >= thirty_days_ago).count()
        
        # Login metrics last 24 hours
        twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
        
        total_login_attempts = db.query(AuthAuditLog).filter(
            AuthAuditLog.event_type == "login",
            AuthAuditLog.created_at >= twenty_four_hours_ago
        ).count()
        
        successful_logins = db.query(AuthAuditLog).filter(
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == True,
            AuthAuditLog.created_at >= twenty_four_hours_ago
        ).count()
        
        failed_logins = db.query(AuthAuditLog).filter(
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == False,
            AuthAuditLog.created_at >= twenty_four_hours_ago
        ).count()
        
        # Unique active users last 24 hours
        unique_active_users = db.query(AuthAuditLog.user_id).filter(
            AuthAuditLog.event_type == "login",
            AuthAuditLog.success == True,
            AuthAuditLog.created_at >= twenty_four_hours_ago
        ).distinct().count()
        
        # Build system metrics
        metrics = SystemMetrics(
            total_users=total_users,
            active_users=active_users,
            suspended_users=suspended_users,
            deleted_users=deleted_users,
            new_users_last_30_days=new_users_last_30_days,
            total_login_attempts_last_24h=total_login_attempts,
            successful_logins_last_24h=successful_logins,
            failed_logins_last_24h=failed_logins,
            unique_active_users_last_24h=unique_active_users
        )
        
        # Get recent security alerts (simplified - would connect to actual alerting system)
        recent_alerts = []
        
        # Check for recent failed login spikes
        if failed_logins > 50:  # Threshold for alert
            recent_alerts.append(SecurityAlert(
                id="failed_login_spike",
                alert_type="authentication",
                severity="medium",
                title="High Failed Login Rate",
                description=f"Detected {failed_logins} failed login attempts in the last 24 hours",
                user_id=None,
                user_email=None,
                ip_address=None,
                created_at=datetime.now(timezone.utc),
                acknowledged=False,
                acknowledged_by=None,
                acknowledged_at=None
            ))
        
        # Calculate success rates
        login_success_rate = (successful_logins / total_login_attempts) if total_login_attempts > 0 else 0
        failed_login_rate = (failed_logins / total_login_attempts) if total_login_attempts > 0 else 0
        
        # Log admin action
        await audit_logger.log_authentication_event(
            event_type="admin_analytics_view",
            success=True,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"metrics_generated": True},
            severity=AuditSeverity.LOW
        )
        
        return AdminAnalyticsResponse(
            metrics=metrics,
            recent_alerts=recent_alerts,
            login_success_rate_last_24h=login_success_rate,
            failed_login_rate_last_24h=failed_login_rate,
            generated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to get admin analytics: {e}")
        await audit_logger.log_authentication_event(
            event_type="admin_analytics_view",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"error": str(e)},
            severity=AuditSeverity.HIGH
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get admin analytics"
        )


@router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    request: Request,
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    created_after: Optional[datetime] = Query(None, description="Filter events after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter events before this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get audit logs for admin dashboard."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Build base query
        base_query = db.query(AuthAuditLog)
        
        # Apply filters
        if user_id:
            base_query = base_query.filter(AuthAuditLog.user_id == user_id)
        if event_type:
            base_query = base_query.filter(AuthAuditLog.event_type == event_type)
        if success is not None:
            base_query = base_query.filter(AuthAuditLog.success == success)
        if ip_address:
            base_query = base_query.filter(AuthAuditLog.ip_address == ip_address)
        if created_after:
            base_query = base_query.filter(AuthAuditLog.created_at >= created_after)
        if created_before:
            base_query = base_query.filter(AuthAuditLog.created_at <= created_before)
        
        # Get total count
        total_count = base_query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        audit_logs = base_query.order_by(AuthAuditLog.created_at.desc()).offset(offset).limit(page_size).all()
        
        # Build audit log entries
        log_entries = []
        for log in audit_logs:
            # Get user email if available
            user_email = None
            if log.user_id:
                user = db.query(User.email).filter(User.id == log.user_id).first()
                if user:
                    user_email = user.email
            
            log_entries.append(AuditLogEntry(
                id=log.id,
                event_type=log.event_type,
                user_id=log.user_id,
                user_email=user_email,
                success=log.success,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                details=log.get_metadata_dict(),
                created_at=log.created_at
            ))
        
        # Calculate pagination info
        total_pages = ceil(total_count / page_size)
        has_next = page < total_pages
        has_previous = page > 1
        
        # Log admin action
        await audit_logger.log_authentication_event(
            event_type="admin_audit_log_view",
            success=True,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "filters": {
                    "user_id": user_id,
                    "event_type": event_type,
                    "success": success,
                    "ip_address": ip_address
                },
                "results_count": len(log_entries)
            },
            severity=AuditSeverity.LOW
        )
        
        return AuditLogResponse(
            logs=log_entries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        await audit_logger.log_authentication_event(
            event_type="admin_audit_log_view",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"error": str(e)},
            severity=AuditSeverity.HIGH
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get audit logs"
        )


@router.post("/audit-logs/export")
async def export_audit_logs(
    export_request: AuditLogExportRequest,
    request: Request,
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Export audit logs in specified format."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Build query with filters
        base_query = db.query(AuthAuditLog)
        
        if export_request.filters:
            filters = export_request.filters
            if filters.user_id:
                base_query = base_query.filter(AuthAuditLog.user_id == filters.user_id)
            if filters.event_type:
                base_query = base_query.filter(AuthAuditLog.event_type == filters.event_type)
            if filters.success is not None:
                base_query = base_query.filter(AuthAuditLog.success == filters.success)
            if filters.ip_address:
                base_query = base_query.filter(AuthAuditLog.ip_address == filters.ip_address)
            if filters.created_after:
                base_query = base_query.filter(AuthAuditLog.created_at >= filters.created_after)
            if filters.created_before:
                base_query = base_query.filter(AuthAuditLog.created_at <= filters.created_before)
        
        # Get logs
        audit_logs = base_query.order_by(AuthAuditLog.created_at.desc()).limit(10000).all()  # Limit for safety
        
        # Log export action
        await audit_logger.log_authentication_event(
            event_type="admin_audit_log_export",
            success=True,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "format": export_request.format,
                "records_exported": len(audit_logs),
                "include_details": export_request.include_details
            },
            severity=AuditSeverity.MEDIUM
        )
        
        if export_request.format == "json":
            # Export as JSON
            export_data = []
            for log in audit_logs:
                log_data = {
                    "id": log.id,
                    "event_type": log.event_type,
                    "user_id": log.user_id,
                    "success": log.success,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "created_at": log.created_at.isoformat()
                }
                if export_request.include_details:
                    log_data["details"] = log.get_metadata_dict()
                export_data.append(log_data)
            
            content = json.dumps(export_data, indent=2)
            media_type = "application/json"
            filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        else:  # CSV format
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            headers = ["id", "event_type", "user_id", "success", "ip_address", "user_agent", "created_at"]
            if export_request.include_details:
                headers.append("details")
            writer.writerow(headers)
            
            # Write data
            for log in audit_logs:
                row = [
                    log.id,
                    log.event_type,
                    log.user_id or "",
                    log.success,
                    log.ip_address or "",
                    log.user_agent or "",
                    log.created_at.isoformat()
                ]
                if export_request.include_details:
                    row.append(json.dumps(log.get_metadata_dict()) if log.get_metadata_dict() else "")
                writer.writerow(row)
            
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        await audit_logger.log_authentication_event(
            event_type="admin_audit_log_export",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={"error": str(e)},
            severity=AuditSeverity.HIGH
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit logs"
        )


@router.post("/users/bulk-actions", response_model=BulkUserActionResponse)
async def perform_bulk_user_actions(
    request: Request,
    bulk_request: BulkUserActionRequest,
    current_admin: str = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Perform bulk actions on multiple users with full audit trail."""
    
    audit_logger = get_audit_logger()
    
    try:
        # Validate action type
        if bulk_request.action not in ['suspend', 'unsuspend']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bulk action '{bulk_request.action}' is not supported"
            )
        
        # Get target users
        users = db.query(User).filter(User.id.in_(bulk_request.user_ids)).all()
        if len(users) != len(bulk_request.user_ids):
            missing_ids = set(bulk_request.user_ids) - set(user.id for user in users)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Users not found: {list(missing_ids)}"
            )
        
        # Prevent admin from including themselves in bulk actions
        if current_admin in bulk_request.user_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot include your own account in bulk actions"
            )
        
        # Perform bulk actions
        results = []
        successful_actions = 0
        failed_actions = 0
        
        for user in users:
            try:
                action_result = UserActionResponse(
                    success=True,
                    user_id=user.id,
                    action=bulk_request.action,
                    reason=bulk_request.reason,
                    performed_at=datetime.now(timezone.utc),
                    performed_by=current_admin
                )
                
                if bulk_request.action == 'suspend':
                    if user.is_active:
                        # Suspend user by deactivating all sessions
                        active_sessions = db.query(AuthSession).filter(
                            and_(
                                AuthSession.supabase_user_id.in_(
                                    db.query(SupabaseUser.id).filter(
                                        SupabaseUser.app_user_id == user.id
                                    )
                                ),
                                AuthSession.expires_at > datetime.now(timezone.utc)
                            )
                        ).all()
                        
                        for session in active_sessions:
                            session.expires_at = datetime.now(timezone.utc)
                        
                        user.is_active = False
                        action_result.details = {
                            "sessions_terminated": len(active_sessions),
                            "previous_status": "active"
                        }
                        successful_actions += 1
                    else:
                        action_result.details = {
                            "message": "User was already inactive",
                            "previous_status": "inactive"
                        }
                        successful_actions += 1
                        
                elif bulk_request.action == 'unsuspend':
                    if not user.is_active:
                        user.is_active = True
                        action_result.details = {
                            "previous_status": "inactive"
                        }
                        successful_actions += 1
                    else:
                        action_result.details = {
                            "message": "User was already active",
                            "previous_status": "active"
                        }
                        successful_actions += 1
                
                results.append(action_result)
                
                # Log individual action
                await audit_logger.log_authentication_event(
                    event_type=f"admin_bulk_{bulk_request.action}",
                    success=True,
                    user_id=current_admin,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("User-Agent"),
                    metadata={
                        "target_user_id": user.id,
                        "target_user_email": user.email,
                        "action": bulk_request.action,
                        "reason": bulk_request.reason,
                        "bulk_operation": True,
                        "total_users_in_batch": len(bulk_request.user_ids)
                    },
                    severity=AuditSeverity.HIGH
                )
                
            except Exception as e:
                failed_actions += 1
                error_result = UserActionResponse(
                    success=False,
                    user_id=user.id,
                    action=bulk_request.action,
                    reason=bulk_request.reason,
                    performed_at=datetime.now(timezone.utc),
                    performed_by=current_admin,
                    error=str(e)
                )
                results.append(error_result)
                
                # Log failed action
                await audit_logger.log_authentication_event(
                    event_type=f"admin_bulk_{bulk_request.action}",
                    success=False,
                    user_id=current_admin,
                    ip_address=request.client.host,
                    user_agent=request.headers.get("User-Agent"),
                    metadata={
                        "target_user_id": user.id,
                        "target_user_email": user.email,
                        "action": bulk_request.action,
                        "reason": bulk_request.reason,
                        "error": str(e),
                        "bulk_operation": True,
                        "total_users_in_batch": len(bulk_request.user_ids)
                    },
                    severity=AuditSeverity.HIGH
                )
        
        # Commit database changes
        db.commit()
        
        # Log bulk operation summary
        await audit_logger.log_authentication_event(
            event_type=f"admin_bulk_{bulk_request.action}_summary",
            success=successful_actions > 0,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "action": bulk_request.action,
                "reason": bulk_request.reason,
                "total_users": len(bulk_request.user_ids),
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "user_ids": bulk_request.user_ids,
                "operation_completed": True
            },
            severity=AuditSeverity.HIGH
        )
        
        return BulkUserActionResponse(
            total_requested=len(bulk_request.user_ids),
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            action=bulk_request.action,
            reason=bulk_request.reason,
            performed_at=datetime.now(timezone.utc),
            performed_by=current_admin,
            results=results
        )
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to perform bulk {bulk_request.action}: {e}")
        
        # Log bulk operation failure
        await audit_logger.log_authentication_event(
            event_type=f"admin_bulk_{bulk_request.action}_error",
            success=False,
            user_id=current_admin,
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
            metadata={
                "action": bulk_request.action,
                "user_ids": bulk_request.user_ids,
                "error": str(e)
            },
            severity=AuditSeverity.HIGH
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform bulk {bulk_request.action}"
        )