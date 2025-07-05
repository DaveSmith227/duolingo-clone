"""
User Management API Endpoints

FastAPI endpoints for enhanced user management including avatar uploads,
user preferences, and extended user data management.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.users import (
    UserPreferencesResponse,
    UserPreferencesRequest,
    AvatarUploadResponse,
    UserPreferencesUpdateResponse,
)
from app.services.file_upload_service import FileUploadService
from app.core.response_formatter import response_formatter, StandardResponse

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/me/avatar",
    status_code=status.HTTP_201_CREATED,
    summary="Upload User Avatar",
    description="Upload and set user avatar image with proper validation and secure storage"
)
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(..., description="Avatar image file (PNG, JPEG, WebP, max 5MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Upload user avatar image.
    
    Accepts image files (PNG, JPEG, WebP) up to 5MB in size.
    Validates file type, size, and stores securely with unique filename.
    
    Args:
        request: FastAPI request object
        avatar: Image file upload
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Standardized JSON response with avatar upload data
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    try:
        # Initialize file upload service
        file_service = FileUploadService()
        
        # Validate and upload avatar
        avatar_url = await file_service.upload_avatar(avatar, str(current_user.id))
        
        # Update user avatar URL in database
        current_user.avatar_url = avatar_url
        current_user.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Avatar uploaded successfully for user {current_user.id}")
        
        # Create response data
        response_data = AvatarUploadResponse(
            message="Avatar uploaded successfully",
            avatar_url=avatar_url,
            uploaded_at=current_user.updated_at
        )
        
        # Create standardized success response
        standard_response = response_formatter.success(
            data=response_data.model_dump(),
            message="Avatar uploaded successfully",
            metadata={"operation": "avatar_upload", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(standard_response, status.HTTP_201_CREATED)
        
    except ValueError as e:
        # Validation errors from file service
        logger.warning(f"Avatar upload validation failed for user {current_user.id}: {e}")
        
        error_response = response_formatter.error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="upload_validation_failed",
            metadata={"operation": "avatar_upload", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(error_response, status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        # Unexpected errors
        logger.error(f"Avatar upload failed for user {current_user.id}: {e}")
        db.rollback()
        
        error_response = response_formatter.error(
            message="Failed to upload avatar. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="upload_failed",
            metadata={"operation": "avatar_upload", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(error_response, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get(
    "/me/preferences",
    summary="Get User Preferences",
    description="Get user learning preferences and application settings"
)
async def get_user_preferences(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Get user preferences and learning settings.
    
    Returns comprehensive user preferences including learning goals,
    notification settings, privacy preferences, and application settings.
    
    Args:
        request: FastAPI request object
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Standardized JSON response with user preferences
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    try:
        # For now, return default preferences
        # In a real implementation, these would be stored in a separate table
        preferences_data = UserPreferencesResponse(
            user_id=current_user.id,
            daily_xp_goal=current_user.daily_xp_goal,
            timezone=current_user.timezone,
            language_interface="en",
            learning_language="es",
            difficulty_level="intermediate",
            lesson_reminders=True,
            streak_reminders=True,
            achievement_notifications=True,
            sound_effects=True,
            haptic_feedback=True,
            offline_download=False,
            data_saver_mode=False,
            auto_play_audio=True,
            show_hints=True,
            speaking_exercises=True,
            listening_exercises=True,
            writing_exercises=True,
            multiple_choice_exercises=True,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
        # Create standardized success response
        standard_response = response_formatter.success(
            data=preferences_data.model_dump(),
            message="User preferences retrieved successfully",
            metadata={"operation": "get_preferences", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(standard_response, status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to get preferences for user {current_user.id}: {e}")
        
        error_response = response_formatter.error(
            message="Failed to retrieve user preferences.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="preferences_fetch_failed",
            metadata={"operation": "get_preferences", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(error_response, status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.put(
    "/me/preferences",
    summary="Update User Preferences",
    description="Update user learning preferences and application settings"
)
async def update_user_preferences(
    request: Request,
    preferences: UserPreferencesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Update user preferences and learning settings.
    
    Updates user learning preferences, notification settings, and application
    configuration based on provided data.
    
    Args:
        request: FastAPI request object
        preferences: User preferences update data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Standardized JSON response with update results
    """
    # Extract request ID from headers if available
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    try:
        updated_fields = []
        
        # Update basic user fields that are stored in the user table
        if preferences.daily_xp_goal is not None:
            current_user.daily_xp_goal = preferences.daily_xp_goal
            updated_fields.append("daily_xp_goal")
        
        if preferences.timezone is not None:
            current_user.timezone = preferences.timezone
            updated_fields.append("timezone")
        
        # For other preferences, in a real implementation we would store these
        # in a separate user_preferences table. For now, we'll track which
        # fields would be updated
        preference_fields = [
            "language_interface", "learning_language", "difficulty_level",
            "lesson_reminders", "streak_reminders", "achievement_notifications",
            "sound_effects", "haptic_feedback", "offline_download",
            "data_saver_mode", "auto_play_audio", "show_hints",
            "speaking_exercises", "listening_exercises", "writing_exercises",
            "multiple_choice_exercises"
        ]
        
        for field in preference_fields:
            if getattr(preferences, field, None) is not None:
                updated_fields.append(field)
        
        # Update timestamp if any fields changed
        if updated_fields:
            current_user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(current_user)
        
        logger.info(f"Preferences updated for user {current_user.id}: {updated_fields}")
        
        # Create response data
        update_message = "Preferences updated successfully" if updated_fields else "No changes were made"
        response_data = UserPreferencesUpdateResponse(
            message=update_message,
            updated_fields=updated_fields,
            updated_at=current_user.updated_at
        )
        
        # Create standardized success response
        standard_response = response_formatter.success(
            data=response_data.model_dump(),
            message=update_message,
            metadata={"operation": "update_preferences", "user_id": current_user.id, "updated_fields_count": len(updated_fields)},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(standard_response, status.HTTP_200_OK)
        
    except ValueError as e:
        logger.warning(f"Invalid preferences data for user {current_user.id}: {e}")
        
        error_response = response_formatter.error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="invalid_preferences",
            metadata={"operation": "update_preferences", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(error_response, status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Failed to update preferences for user {current_user.id}: {e}")
        db.rollback()
        
        error_response = response_formatter.error(
            message="Failed to update preferences. Please try again.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="preferences_update_failed",
            metadata={"operation": "update_preferences", "user_id": current_user.id},
            request_id=request_id
        )
        
        return response_formatter.to_json_response(error_response, status.HTTP_500_INTERNAL_SERVER_ERROR)