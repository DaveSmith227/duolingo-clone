"""
Audit Log API Endpoints

Provides endpoints for querying and analyzing audit logs.
Access is restricted to admin users only.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit_logger import get_audit_logger, AuditAction, AuditSeverity
from app.core.config import get_settings
from app.api.auth import get_current_admin_user
from app.models.user import User


router = APIRouter(
    prefix="/api/v1/audit",
    tags=["Audit"],
    dependencies=[Depends(get_current_admin_user)]
)


@router.get("/logs", response_model=Dict[str, Any])
async def get_audit_logs(
    current_user: User = Depends(get_current_admin_user),
    start_date: Optional[datetime] = Query(None, description="Start date for log query"),
    end_date: Optional[datetime] = Query(None, description="End date for log query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    field_name: Optional[str] = Query(None, description="Filter by field name"),
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return")
) -> Dict[str, Any]:
    """
    Query audit logs with filters.
    
    Admin access required.
    """
    settings = get_settings()
    
    # Production restriction
    if settings.is_production and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access audit logs in production"
        )
    
    # Default date range if not provided
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=7)  # Default to last 7 days
    
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    if (end_date - start_date).days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days"
        )
    
    # Convert string parameters to enums if provided
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {action}"
            )
    
    severity_enum = None
    if severity:
        try:
            severity_enum = AuditSeverity(severity.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid severity level: {severity}"
            )
    
    # Query logs
    audit_logger = get_audit_logger()
    logs = audit_logger.query_logs(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        action=action_enum,
        field_name=field_name,
        severity=severity_enum,
        limit=limit
    )
    
    # Log this access
    audit_logger.log_config_read(
        field_name="audit_logs",
        value=f"Queried {len(logs)} logs",
        success=True,
        metadata={
            "admin_user": current_user.email,
            "filters": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "user_id": user_id,
                "action": action,
                "field_name": field_name,
                "severity": severity,
                "limit": limit
            }
        }
    )
    
    return {
        "status": "success",
        "count": len(logs),
        "filters": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "user_id": user_id,
            "action": action,
            "field_name": field_name,
            "severity": severity,
            "limit": limit
        },
        "logs": logs
    }


@router.get("/summary", response_model=Dict[str, Any])
async def get_audit_summary(
    current_user: User = Depends(get_current_admin_user),
    start_date: Optional[datetime] = Query(None, description="Start date for summary"),
    end_date: Optional[datetime] = Query(None, description="End date for summary"),
    period: str = Query("day", description="Summary period: hour, day, week, month")
) -> Dict[str, Any]:
    """
    Get audit log summary and statistics.
    
    Admin access required.
    """
    settings = get_settings()
    
    # Production restriction
    if settings.is_production and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access audit summaries in production"
        )
    
    # Determine date range based on period
    if not end_date:
        end_date = datetime.now(timezone.utc)
    
    if not start_date:
        if period == "hour":
            start_date = end_date - timedelta(hours=24)
        elif period == "day":
            start_date = end_date - timedelta(days=7)
        elif period == "week":
            start_date = end_date - timedelta(weeks=4)
        elif period == "month":
            start_date = end_date - timedelta(days=90)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Use: hour, day, week, or month"
            )
    
    # Get summary
    audit_logger = get_audit_logger()
    summary = audit_logger.get_audit_summary(
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate additional metrics
    if summary["total_events"] > 0:
        summary["failure_rate"] = (summary["failed_operations"] / summary["total_events"]) * 100
        summary["sensitive_access_rate"] = (summary["sensitive_field_access"] / summary["total_events"]) * 100
    else:
        summary["failure_rate"] = 0
        summary["sensitive_access_rate"] = 0
    
    # Log this access
    audit_logger.log_config_read(
        field_name="audit_summary",
        value=f"Generated summary for {summary['total_events']} events",
        success=True,
        metadata={
            "admin_user": current_user.email,
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    )
    
    return {
        "status": "success",
        "period": period,
        "summary": summary
    }


@router.get("/config-access", response_model=Dict[str, Any])
async def get_config_access_report(
    current_user: User = Depends(get_current_admin_user),
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get configuration access report showing most accessed fields.
    
    Admin access required.
    """
    settings = get_settings()
    
    # Query recent configuration access logs
    audit_logger = get_audit_logger()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    logs = audit_logger.query_logs(
        start_date=start_date,
        end_date=end_date,
        action=AuditAction.READ,
        limit=5000
    )
    
    # Analyze configuration field access
    field_access_count = {}
    user_access_count = {}
    sensitive_fields_accessed = []
    
    sensitive_patterns = ["password", "secret", "key", "token", "credential"]
    
    for log in logs:
        field = log.get("field_name")
        user = log.get("user_email", "anonymous")
        
        if field:
            # Count field access
            field_access_count[field] = field_access_count.get(field, 0) + 1
            
            # Check if sensitive
            if any(pattern in field.lower() for pattern in sensitive_patterns):
                sensitive_fields_accessed.append({
                    "field": field,
                    "user": user,
                    "timestamp": log.get("timestamp"),
                    "ip_address": log.get("ip_address")
                })
        
        # Count user access
        user_access_count[user] = user_access_count.get(user, 0) + 1
    
    # Sort by access count
    top_fields = sorted(field_access_count.items(), key=lambda x: x[1], reverse=True)[:20]
    top_users = sorted(user_access_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "status": "success",
        "period_days": days,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "total_accesses": len(logs),
        "unique_fields": len(field_access_count),
        "unique_users": len(user_access_count),
        "top_accessed_fields": [
            {"field": field, "count": count} for field, count in top_fields
        ],
        "top_users": [
            {"user": user, "count": count} for user, count in top_users
        ],
        "sensitive_field_accesses": len(sensitive_fields_accessed),
        "recent_sensitive_accesses": sensitive_fields_accessed[:10]
    }


@router.get("/security-events", response_model=Dict[str, Any])
async def get_security_events(
    current_user: User = Depends(get_current_admin_user),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze")
) -> Dict[str, Any]:
    """
    Get recent security-related audit events.
    
    Admin access required.
    """
    settings = get_settings()
    
    # Production restriction
    if settings.is_production and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can access security events in production"
        )
    
    # Query recent logs
    audit_logger = get_audit_logger()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(hours=hours)
    
    # Get all critical and error severity events
    critical_logs = audit_logger.query_logs(
        start_date=start_date,
        end_date=end_date,
        severity=AuditSeverity.CRITICAL,
        limit=500
    )
    
    error_logs = audit_logger.query_logs(
        start_date=start_date,
        end_date=end_date,
        severity=AuditSeverity.ERROR,
        limit=500
    )
    
    # Get access denied events
    access_denied_logs = audit_logger.query_logs(
        start_date=start_date,
        end_date=end_date,
        action=AuditAction.ACCESS_DENIED,
        limit=500
    )
    
    # Analyze security events
    failed_validations = []
    access_violations = []
    configuration_errors = []
    suspicious_activities = []
    
    for log in error_logs + critical_logs:
        if log.get("action") == "validate":
            failed_validations.append(log)
        elif log.get("action") == "access_denied":
            access_violations.append(log)
        elif log.get("action") in ["write", "update", "delete"] and not log.get("success"):
            configuration_errors.append(log)
        
        # Check for suspicious patterns
        if log.get("user_id") and log.get("ip_address"):
            # Multiple IPs for same user could be suspicious
            suspicious_activities.append({
                "type": "potential_suspicious_activity",
                "log": log
            })
    
    return {
        "status": "success",
        "period_hours": hours,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_security_events": len(critical_logs) + len(error_logs),
            "critical_events": len(critical_logs),
            "error_events": len(error_logs),
            "access_denied": len(access_denied_logs),
            "failed_validations": len(failed_validations),
            "configuration_errors": len(configuration_errors)
        },
        "recent_critical_events": critical_logs[:10],
        "recent_access_violations": access_violations[:10],
        "recent_validation_failures": failed_validations[:10],
        "suspicious_activities": suspicious_activities[:5]
    }