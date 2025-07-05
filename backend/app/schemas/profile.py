"""
User Profile Management Schemas

Pydantic schemas for user profile management, privacy settings,
and account preferences.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator


class UserProfileResponse(BaseModel):
    """User profile response schema."""
    
    id: str = Field(
        ...,
        description="User ID"
    )
    
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    
    name: str = Field(
        ...,
        description="User's display name"
    )
    
    avatar_url: Optional[str] = Field(
        None,
        description="URL to user's avatar image"
    )
    
    is_email_verified: bool = Field(
        ...,
        description="Whether email is verified"
    )
    
    daily_xp_goal: int = Field(
        ...,
        description="Daily XP goal"
    )
    
    timezone: str = Field(
        ...,
        description="User's timezone"
    )
    
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp"
    )
    
    updated_at: Optional[datetime] = Field(
        None,
        description="Last profile update"
    )
    
    privacy_settings: Dict[str, Any] = Field(
        {},
        description="User privacy preferences"
    )
    
    notification_settings: Dict[str, Any] = Field(
        {},
        description="User notification preferences"
    )


class UpdateProfileRequest(BaseModel):
    """Update user profile request schema."""
    
    name: Optional[str] = Field(
        None,
        description="Updated display name",
        min_length=1,
        max_length=255
    )
    
    avatar_url: Optional[str] = Field(
        None,
        description="Updated avatar URL",
        max_length=500
    )
    
    daily_xp_goal: Optional[int] = Field(
        None,
        description="Updated daily XP goal"
    )
    
    timezone: Optional[str] = Field(
        None,
        description="Updated timezone",
        max_length=50
    )
    
    @validator('daily_xp_goal')
    def validate_daily_xp_goal(cls, v):
        if v is not None and v not in [10, 20, 30, 50]:
            raise ValueError('Daily XP goal must be 10, 20, 30, or 50')
        return v
    
    @validator('timezone')
    def validate_timezone(cls, v):
        if v is not None:
            # Basic timezone validation
            import re
            if not re.match(r'^[A-Za-z_/]+$', v):
                raise ValueError('Invalid timezone format')
        return v


class ChangeEmailRequest(BaseModel):
    """Change email request schema."""
    
    new_email: EmailStr = Field(
        ...,
        description="New email address"
    )
    
    password: str = Field(
        ...,
        description="Current password for verification",
        min_length=8,
        max_length=128
    )


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    
    current_password: str = Field(
        ...,
        description="Current password",
        min_length=8,
        max_length=128
    )
    
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )
    
    confirm_password: str = Field(
        ...,
        description="Confirm new password",
        min_length=8,
        max_length=128
    )
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PrivacySettingsRequest(BaseModel):
    """Privacy settings update request schema."""
    
    profile_visibility: Optional[str] = Field(
        None,
        description="Profile visibility setting"
    )
    
    show_email: Optional[bool] = Field(
        None,
        description="Whether to show email in profile"
    )
    
    show_learning_stats: Optional[bool] = Field(
        None,
        description="Whether to show learning statistics"
    )
    
    allow_friend_requests: Optional[bool] = Field(
        None,
        description="Whether to allow friend requests"
    )
    
    data_processing_consent: Optional[bool] = Field(
        None,
        description="Consent for data processing"
    )
    
    marketing_consent: Optional[bool] = Field(
        None,
        description="Consent for marketing communications"
    )
    
    analytics_consent: Optional[bool] = Field(
        None,
        description="Consent for analytics tracking"
    )
    
    @validator('profile_visibility')
    def validate_profile_visibility(cls, v):
        if v is not None and v not in ['public', 'friends', 'private']:
            raise ValueError('Profile visibility must be public, friends, or private')
        return v


class NotificationSettingsRequest(BaseModel):
    """Notification settings update request schema."""
    
    email_notifications: Optional[bool] = Field(
        None,
        description="Enable email notifications"
    )
    
    push_notifications: Optional[bool] = Field(
        None,
        description="Enable push notifications"
    )
    
    lesson_reminders: Optional[bool] = Field(
        None,
        description="Enable lesson reminder notifications"
    )
    
    streak_reminders: Optional[bool] = Field(
        None,
        description="Enable streak reminder notifications"
    )
    
    achievement_notifications: Optional[bool] = Field(
        None,
        description="Enable achievement notifications"
    )
    
    friend_activity_notifications: Optional[bool] = Field(
        None,
        description="Enable friend activity notifications"
    )
    
    marketing_emails: Optional[bool] = Field(
        None,
        description="Enable marketing emails"
    )
    
    weekly_report: Optional[bool] = Field(
        None,
        description="Enable weekly progress reports"
    )


class AccountSecurityResponse(BaseModel):
    """Account security status response schema."""
    
    user_id: str = Field(
        ...,
        description="User ID"
    )
    
    email_verified: bool = Field(
        ...,
        description="Whether email is verified"
    )
    
    has_password: bool = Field(
        ...,
        description="Whether user has a password set"
    )
    
    oauth_providers: List[str] = Field(
        [],
        description="Connected OAuth providers"
    )
    
    two_factor_enabled: bool = Field(
        False,
        description="Whether 2FA is enabled"
    )
    
    active_sessions: int = Field(
        ...,
        description="Number of active sessions"
    )
    
    last_password_change: Optional[datetime] = Field(
        None,
        description="Last password change timestamp"
    )
    
    last_login: Optional[datetime] = Field(
        None,
        description="Last login timestamp"
    )
    
    account_locked: bool = Field(
        False,
        description="Whether account is locked"
    )


class DeactivateAccountRequest(BaseModel):
    """Account deactivation request schema."""
    
    reason: Optional[str] = Field(
        None,
        description="Reason for deactivation",
        max_length=500
    )
    
    password: Optional[str] = Field(
        None,
        description="Password for verification (if user has password)",
        min_length=8,
        max_length=128
    )
    
    confirm_deactivation: bool = Field(
        ...,
        description="Confirmation that user wants to deactivate"
    )
    
    @validator('confirm_deactivation')
    def must_confirm(cls, v):
        if not v:
            raise ValueError('Account deactivation must be confirmed')
        return v


class ProfileUpdateResponse(BaseModel):
    """Profile update response schema."""
    
    message: str = Field(
        ...,
        description="Update confirmation message"
    )
    
    updated_fields: List[str] = Field(
        ...,
        description="List of fields that were updated"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Update timestamp"
    )


class VerifyEmailRequest(BaseModel):
    """Email verification request schema."""
    
    verification_token: str = Field(
        ...,
        description="Email verification token"
    )


class VerifyEmailResponse(BaseModel):
    """Email verification response schema."""
    
    message: str = Field(
        ...,
        description="Verification result message"
    )
    
    email_verified: bool = Field(
        ...,
        description="Whether email is now verified"
    )
    
    verified_at: datetime = Field(
        ...,
        description="Verification timestamp"
    )


class RequestEmailVerificationResponse(BaseModel):
    """Request email verification response schema."""
    
    message: str = Field(
        ...,
        description="Request confirmation message"
    )
    
    email: EmailStr = Field(
        ...,
        description="Email address verification was sent to"
    )
    
    expires_at: datetime = Field(
        ...,
        description="Verification token expiration"
    )


class AccountStatsResponse(BaseModel):
    """Account statistics response schema."""
    
    user_id: str = Field(
        ...,
        description="User ID"
    )
    
    account_age_days: int = Field(
        ...,
        description="Days since account creation"
    )
    
    total_logins: int = Field(
        ...,
        description="Total number of logins"
    )
    
    last_active: Optional[datetime] = Field(
        None,
        description="Last activity timestamp"
    )
    
    courses_enrolled: int = Field(
        ...,
        description="Number of courses enrolled in"
    )
    
    lessons_completed: int = Field(
        ...,
        description="Total lessons completed"
    )
    
    total_xp_earned: int = Field(
        ...,
        description="Total XP earned"
    )
    
    current_streak: int = Field(
        ...,
        description="Current daily streak"
    )
    
    longest_streak: int = Field(
        ...,
        description="Longest streak achieved"
    )
    
    achievements_earned: int = Field(
        ...,
        description="Number of achievements earned"
    )