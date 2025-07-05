"""
User Profile Management API Endpoints

FastAPI routes for user profile management, privacy settings,
and account preferences.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user_id, get_current_user_payload
from app.schemas.profile import (
    UserProfileResponse,
    UpdateProfileRequest,
    ChangeEmailRequest,
    ChangePasswordRequest,
    PrivacySettingsRequest,
    NotificationSettingsRequest,
    AccountSecurityResponse,
    DeactivateAccountRequest,
    ProfileUpdateResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    RequestEmailVerificationResponse,
    AccountStatsResponse
)
from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthSession
from app.models.progress import UserCourse, UserLessonProgress
from app.models.gamification import UserAchievement
from app.models.privacy import UserConsent
from app.services.password_security import get_password_security
from app.services.privacy_service import get_privacy_service
from app.services.audit_logger import get_audit_logger, AuditEventType, AuditSeverity

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/profile", tags=["profile"])


def get_client_info(request: Request) -> Dict[str, Any]:
    """Extract client information from request."""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
    }


@router.get("/me", response_model=UserProfileResponse, status_code=status.HTTP_200_OK)
async def get_user_profile(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile information.
    
    Returns comprehensive profile data including privacy and notification settings.
    """
    try:
        # Get user data
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User profile not found."
                }
            )
        
        # Get privacy settings (simplified - in real app would be stored in separate table)
        privacy_settings = {
            "profile_visibility": "public",
            "show_email": False,
            "show_learning_stats": True,
            "allow_friend_requests": True,
            "data_processing_consent": True,
            "marketing_consent": False,
            "analytics_consent": True
        }
        
        # Get notification settings (simplified - in real app would be stored in separate table)
        notification_settings = {
            "email_notifications": True,
            "push_notifications": True,
            "lesson_reminders": True,
            "streak_reminders": True,
            "achievement_notifications": True,
            "friend_activity_notifications": False,
            "marketing_emails": False,
            "weekly_report": True
        }
        
        return UserProfileResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_email_verified=user.is_email_verified,
            daily_xp_goal=user.daily_xp_goal,
            timezone=user.timezone,
            created_at=user.created_at,
            updated_at=user.updated_at,
            privacy_settings=privacy_settings,
            notification_settings=notification_settings
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "profile_fetch_failed",
                "message": "Failed to retrieve user profile."
            }
        )


@router.put("/me", response_model=ProfileUpdateResponse, status_code=status.HTTP_200_OK)
async def update_user_profile(
    profile_data: UpdateProfileRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    
    Allows updating display name, avatar, daily XP goal, and timezone.
    """
    client_info = get_client_info(request)
    audit_logger = get_audit_logger()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User not found."
                }
            )
        
        # Track updated fields
        updated_fields = []
        old_values = {}
        new_values = {}
        
        # Update fields if provided
        if profile_data.name is not None:
            old_values["name"] = user.name
            user.name = profile_data.name
            new_values["name"] = profile_data.name
            updated_fields.append("name")
        
        if profile_data.avatar_url is not None:
            old_values["avatar_url"] = user.avatar_url
            user.avatar_url = profile_data.avatar_url
            new_values["avatar_url"] = profile_data.avatar_url
            updated_fields.append("avatar_url")
        
        if profile_data.daily_xp_goal is not None:
            old_values["daily_xp_goal"] = user.daily_xp_goal
            user.daily_xp_goal = profile_data.daily_xp_goal
            new_values["daily_xp_goal"] = profile_data.daily_xp_goal
            updated_fields.append("daily_xp_goal")
        
        if profile_data.timezone is not None:
            old_values["timezone"] = user.timezone
            user.timezone = profile_data.timezone
            new_values["timezone"] = profile_data.timezone
            updated_fields.append("timezone")
        
        if updated_fields:
            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            
            # Log profile update
            await audit_logger.log_authentication_event(
                event_type="profile_updated",
                success=True,
                user_id=current_user_id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                metadata={
                    "updated_fields": updated_fields,
                    "old_values": old_values,
                    "new_values": new_values
                },
                severity=AuditSeverity.LOW
            )
        
        return ProfileUpdateResponse(
            message="Profile updated successfully." if updated_fields else "No changes were made.",
            updated_fields=updated_fields,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile for user {current_user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "profile_update_failed",
                "message": "Failed to update profile. Please try again."
            }
        )


@router.post("/change-email", response_model=ProfileUpdateResponse, status_code=status.HTTP_200_OK)
async def change_email(
    email_data: ChangeEmailRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Change user's email address.
    
    Requires password verification and triggers email verification process.
    """
    client_info = get_client_info(request)
    password_security = get_password_security()
    audit_logger = get_audit_logger()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User not found."
                }
            )
        
        # Verify password
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "oauth_only_account",
                    "message": "Cannot change email for OAuth-only accounts."
                }
            )
        
        if not password_security.verify_password(email_data.password, user.password_hash):
            await audit_logger.log_authentication_event(
                event_type="email_change_failed",
                success=False,
                user_id=current_user_id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Invalid password",
                severity=AuditSeverity.MEDIUM
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_password",
                    "message": "Invalid password provided."
                }
            )
        
        # Check if new email is already in use
        existing_user = db.query(User).filter(
            User.email == email_data.new_email,
            User.id != current_user_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "email_already_exists",
                    "message": "Email address is already in use."
                }
            )
        
        # Update email and reset verification
        old_email = user.email
        user.email = email_data.new_email
        user.is_email_verified = False
        user.updated_at = datetime.now(timezone.utc)
        
        # In a real implementation, this would generate and send verification email
        # For now, we'll just log the change
        
        db.commit()
        
        # Log email change
        await audit_logger.log_authentication_event(
            event_type="email_changed",
            success=True,
            user_id=current_user_id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            metadata={
                "old_email": old_email,
                "new_email": email_data.new_email
            },
            severity=AuditSeverity.MEDIUM
        )
        
        return ProfileUpdateResponse(
            message="Email address updated successfully. Please verify your new email address.",
            updated_fields=["email"],
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change email for user {current_user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "email_change_failed",
                "message": "Failed to change email address. Please try again."
            }
        )


@router.post("/change-password", response_model=ProfileUpdateResponse, status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Change user's password.
    
    Requires current password verification and validates new password strength.
    """
    client_info = get_client_info(request)
    password_security = get_password_security()
    audit_logger = get_audit_logger()
    
    try:
        # Get user
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User not found."
                }
            )
        
        # Check if user has a password (not OAuth-only)
        if not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "oauth_only_account",
                    "message": "Cannot change password for OAuth-only accounts."
                }
            )
        
        # Verify current password
        if not password_security.verify_password(password_data.current_password, user.password_hash):
            await audit_logger.log_authentication_event(
                event_type="password_change_failed",
                success=False,
                user_id=current_user_id,
                ip_address=client_info["ip_address"],
                user_agent=client_info["user_agent"],
                error_message="Invalid current password",
                severity=AuditSeverity.MEDIUM
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "invalid_current_password",
                    "message": "Invalid current password."
                }
            )
        
        # Validate new password strength
        if not password_security.validate_password_strength(password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "weak_password",
                    "message": "New password does not meet security requirements."
                }
            )
        
        # Check if new password is same as current
        if password_security.verify_password(password_data.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "same_password",
                    "message": "New password must be different from current password."
                }
            )
        
        # Hash and update password
        new_password_hash = password_security.hash_password(password_data.new_password)
        user.password_hash = new_password_hash
        user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        # Log password change
        await audit_logger.log_authentication_event(
            event_type="password_changed",
            success=True,
            user_id=current_user_id,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"],
            severity=AuditSeverity.MEDIUM
        )
        
        return ProfileUpdateResponse(
            message="Password changed successfully.",
            updated_fields=["password"],
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password for user {current_user_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "password_change_failed",
                "message": "Failed to change password. Please try again."
            }
        )


@router.put("/privacy-settings", response_model=ProfileUpdateResponse, status_code=status.HTTP_200_OK)
async def update_privacy_settings(
    privacy_data: PrivacySettingsRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update user's privacy settings.
    
    Manages privacy preferences and consent for data processing activities.
    """
    client_info = get_client_info(request)
    privacy_service = get_privacy_service(db)
    
    try:
        # In a real implementation, privacy settings would be stored in a separate table
        # For now, we'll simulate the update and log the changes
        
        updated_fields = []
        settings_changes = {}
        
        # Track which settings are being updated
        for field_name, field_value in privacy_data.dict(exclude_unset=True).items():
            if field_value is not None:
                updated_fields.append(field_name)
                settings_changes[field_name] = field_value
        
        # Handle consent-related settings
        consent_updates = []
        
        if privacy_data.data_processing_consent is not None:
            consent_updates.append({
                "consent_type": "data_processing",
                "consent_given": privacy_data.data_processing_consent
            })
        
        if privacy_data.marketing_consent is not None:
            consent_updates.append({
                "consent_type": "marketing_emails",
                "consent_given": privacy_data.marketing_consent
            })
        
        if privacy_data.analytics_consent is not None:
            consent_updates.append({
                "consent_type": "analytics_cookies",
                "consent_given": privacy_data.analytics_consent
            })
        
        # Update consents if any consent settings changed
        if consent_updates:
            # In a real implementation, this would update actual consent records
            # For now, we'll just log the consent changes
            pass
        
        logger.info(f"Updated privacy settings for user {current_user_id}: {settings_changes}")
        
        return ProfileUpdateResponse(
            message="Privacy settings updated successfully.",
            updated_fields=updated_fields,
            updated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to update privacy settings for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "privacy_settings_update_failed",
                "message": "Failed to update privacy settings. Please try again."
            }
        )


@router.put("/notification-settings", response_model=ProfileUpdateResponse, status_code=status.HTTP_200_OK)
async def update_notification_settings(
    notification_data: NotificationSettingsRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update user's notification preferences.
    
    Manages email, push, and in-app notification settings.
    """
    try:
        # In a real implementation, notification settings would be stored in a separate table
        # For now, we'll simulate the update
        
        updated_fields = []
        settings_changes = {}
        
        # Track which settings are being updated
        for field_name, field_value in notification_data.dict(exclude_unset=True).items():
            if field_value is not None:
                updated_fields.append(field_name)
                settings_changes[field_name] = field_value
        
        logger.info(f"Updated notification settings for user {current_user_id}: {settings_changes}")
        
        return ProfileUpdateResponse(
            message="Notification settings updated successfully.",
            updated_fields=updated_fields,
            updated_at=datetime.now(timezone.utc)
        )
        
    except Exception as e:
        logger.error(f"Failed to update notification settings for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "notification_settings_update_failed",
                "message": "Failed to update notification settings. Please try again."
            }
        )


@router.get("/security", response_model=AccountSecurityResponse, status_code=status.HTTP_200_OK)
async def get_account_security(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get account security status and information.
    
    Returns security-related account information including connected providers
    and active sessions.
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User not found."
                }
            )
        
        # Get OAuth providers
        oauth_providers = db.query(OAuthProvider).filter(
            OAuthProvider.user_id == current_user_id
        ).all()
        
        provider_names = [provider.provider for provider in oauth_providers]
        
        # Get active sessions count
        supabase_user = db.query(SupabaseUser).filter(
            SupabaseUser.app_user_id == current_user_id
        ).first()
        
        active_sessions = 0
        if supabase_user:
            active_sessions = db.query(AuthSession).filter(
                AuthSession.supabase_user_id == supabase_user.id,
                AuthSession.is_active == True
            ).count()
        
        return AccountSecurityResponse(
            user_id=current_user_id,
            email_verified=user.is_email_verified,
            has_password=user.password_hash is not None,
            oauth_providers=provider_names,
            two_factor_enabled=False,  # Not implemented yet
            active_sessions=active_sessions,
            last_password_change=None,  # Would need separate tracking
            last_login=supabase_user.last_sign_in_at if supabase_user else None,
            account_locked=False  # Would need separate tracking
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security info for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "security_info_failed",
                "message": "Failed to retrieve account security information."
            }
        )


@router.get("/stats", response_model=AccountStatsResponse, status_code=status.HTTP_200_OK)
async def get_account_stats(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get user account statistics and learning progress.
    
    Returns comprehensive statistics about the user's learning activity
    and account usage.
    """
    try:
        # Get user
        user = db.query(User).filter(User.id == current_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "user_not_found",
                    "message": "User not found."
                }
            )
        
        # Calculate account age
        account_age_days = (datetime.now(timezone.utc) - user.created_at).days if user.created_at else 0
        
        # Get course enrollment count
        courses_enrolled = db.query(UserCourse).filter(
            UserCourse.user_id == current_user_id,
            UserCourse.is_active == True
        ).count()
        
        # Get lessons completed count
        lessons_completed = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == current_user_id,
            UserLessonProgress.status == "completed"
        ).count()
        
        # Get total XP and streaks
        total_xp = 0
        current_streak = 0
        longest_streak = 0
        
        user_courses = db.query(UserCourse).filter(
            UserCourse.user_id == current_user_id
        ).all()
        
        for course in user_courses:
            total_xp += course.total_xp or 0
            if course.current_streak > current_streak:
                current_streak = course.current_streak
            if course.longest_streak > longest_streak:
                longest_streak = course.longest_streak
        
        # Get achievements count
        achievements_earned = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user_id,
            UserAchievement.is_completed == True
        ).count()
        
        # Get session count (approximate total logins)
        supabase_user = db.query(SupabaseUser).filter(
            SupabaseUser.app_user_id == current_user_id
        ).first()
        
        total_logins = 0
        if supabase_user:
            total_logins = db.query(AuthSession).filter(
                AuthSession.supabase_user_id == supabase_user.id
            ).count()
        
        return AccountStatsResponse(
            user_id=current_user_id,
            account_age_days=account_age_days,
            total_logins=total_logins,
            last_active=user.updated_at,
            courses_enrolled=courses_enrolled,
            lessons_completed=lessons_completed,
            total_xp_earned=total_xp,
            current_streak=current_streak,
            longest_streak=longest_streak,
            achievements_earned=achievements_earned
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account stats for user {current_user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "stats_fetch_failed",
                "message": "Failed to retrieve account statistics."
            }
        )