"""
Admin API Schemas

Request/response schemas for admin dashboard functionality including
user management, audit logs, and system analytics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class UserStatusFilter(str, Enum):
    """User status filter options for admin dashboard."""
    ALL = "all"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserSortField(str, Enum):
    """User sort field options."""
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    EMAIL = "email"
    NAME = "name"
    LAST_LOGIN = "last_login"


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class UserSearchRequest(BaseModel):
    """Request schema for user search."""
    
    query: Optional[str] = Field(None, description="Search query for email or name")
    status: UserStatusFilter = Field(UserStatusFilter.ALL, description="Filter by user status")
    created_after: Optional[datetime] = Field(None, description="Filter users created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter users created before this date")
    last_login_after: Optional[datetime] = Field(None, description="Filter users with last login after this date")
    last_login_before: Optional[datetime] = Field(None, description="Filter users with last login before this date")
    sort_by: UserSortField = Field(UserSortField.CREATED_AT, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")


class UserSummary(BaseModel):
    """Summary information for a user in admin dashboard."""
    
    id: str
    email: EmailStr
    name: Optional[str]
    is_active: bool
    is_suspended: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]
    login_count: int
    failed_login_count: int
    roles: List[str]
    supabase_id: Optional[str]
    
    class Config:
        from_attributes = True


class UserSearchResponse(BaseModel):
    """Response schema for user search."""
    
    users: List[UserSummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class UserActionType(str, Enum):
    """User action types for admin operations."""
    SUSPEND = "suspend"
    UNSUSPEND = "unsuspend"
    DELETE = "delete"
    RESET_PASSWORD = "reset_password"
    FORCE_LOGOUT = "force_logout"
    CHANGE_ROLE = "change_role"


class UserActionRequest(BaseModel):
    """Request schema for user actions."""
    
    action: UserActionType
    user_id: str
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for the action")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional action-specific data")
    
    @validator('reason')
    def validate_reason(cls, v):
        if not v.strip():
            raise ValueError('Reason cannot be empty')
        return v.strip()


class UserActionResponse(BaseModel):
    """Response schema for user actions."""
    
    success: bool
    user_id: str
    action: UserActionType
    reason: str
    performed_at: datetime
    performed_by: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BulkUserActionRequest(BaseModel):
    """Request schema for bulk user actions."""
    
    action: UserActionType
    user_ids: List[str] = Field(..., min_items=1, max_items=100, description="List of user IDs")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for the bulk action")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional action-specific data")
    
    @validator('reason')
    def validate_reason(cls, v):
        if not v.strip():
            raise ValueError('Reason cannot be empty')
        return v.strip()


class BulkUserActionResponse(BaseModel):
    """Response schema for bulk user actions."""
    
    total_requested: int
    successful_actions: int
    failed_actions: int
    action: UserActionType
    reason: str
    performed_at: datetime
    performed_by: str
    results: List[UserActionResponse]


class AuditLogFilter(BaseModel):
    """Filter options for audit log search."""
    
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    success: Optional[bool] = Field(None, description="Filter by success status")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    user_agent: Optional[str] = Field(None, description="Filter by user agent")
    created_after: Optional[datetime] = Field(None, description="Filter events after this date")
    created_before: Optional[datetime] = Field(None, description="Filter events before this date")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(50, ge=1, le=200, description="Number of items per page")


class AuditLogEntry(BaseModel):
    """Audit log entry for admin dashboard."""
    
    id: str
    event_type: str
    user_id: Optional[str]
    user_email: Optional[str]
    success: bool
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """Response schema for audit log search."""
    
    logs: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class AuditLogExportRequest(BaseModel):
    """Request schema for audit log export."""
    
    format: str = Field("json", description="Export format (json, csv)")
    filters: Optional[AuditLogFilter] = Field(None, description="Filters to apply")
    include_details: bool = Field(True, description="Whether to include detailed metadata")
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['json', 'csv']:
            raise ValueError('Format must be json or csv')
        return v


class SystemMetrics(BaseModel):
    """System metrics for admin dashboard."""
    
    total_users: int
    active_users: int
    suspended_users: int
    deleted_users: int
    new_users_last_30_days: int
    total_login_attempts_last_24h: int
    successful_logins_last_24h: int
    failed_logins_last_24h: int
    unique_active_users_last_24h: int
    
    class Config:
        from_attributes = True


class SecurityAlert(BaseModel):
    """Security alert for admin dashboard."""
    
    id: str
    alert_type: str
    severity: str
    title: str
    description: str
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AdminAnalyticsResponse(BaseModel):
    """Response schema for admin analytics dashboard."""
    
    metrics: SystemMetrics
    recent_alerts: List[SecurityAlert]
    login_success_rate_last_24h: float
    failed_login_rate_last_24h: float
    generated_at: datetime


class AdminUserDetail(BaseModel):
    """Detailed user information for admin dashboard."""
    
    id: str
    email: EmailStr
    name: Optional[str]
    is_active: bool
    is_suspended: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]
    login_count: int
    failed_login_count: int
    roles: List[str]
    supabase_id: Optional[str]
    profile_data: Optional[Dict[str, Any]]
    consent_status: Optional[Dict[str, Any]]
    recent_sessions: List[Dict[str, Any]]
    recent_audit_events: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    """Response schema for detailed user information."""
    
    user: AdminUserDetail
    permissions: List[str]
    account_statistics: Dict[str, Any]