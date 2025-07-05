"""
User Management Schemas

Pydantic schemas for user management endpoints including avatar uploads,
preferences, and extended user data validation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class LanguageEnum(str, Enum):
    """Supported languages for interface and learning."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"
    DUTCH = "nl"
    RUSSIAN = "ru"


class DifficultyLevelEnum(str, Enum):
    """Learning difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class AvatarUploadResponse(BaseModel):
    """Response schema for avatar upload."""
    message: str = Field(..., description="Success message")
    avatar_url: str = Field(..., description="URL of the uploaded avatar")
    uploaded_at: datetime = Field(..., description="Timestamp of upload")
    
    class Config:
        from_attributes = True


class UserPreferencesRequest(BaseModel):
    """Request schema for updating user preferences."""
    
    # Basic settings
    daily_xp_goal: Optional[int] = Field(None, ge=10, le=100, description="Daily XP goal (10-100)")
    timezone: Optional[str] = Field(None, max_length=50, description="User timezone")
    language_interface: Optional[LanguageEnum] = Field(None, description="Interface language")
    learning_language: Optional[LanguageEnum] = Field(None, description="Target learning language")
    difficulty_level: Optional[DifficultyLevelEnum] = Field(None, description="Learning difficulty level")
    
    # Notification preferences
    lesson_reminders: Optional[bool] = Field(None, description="Enable lesson reminders")
    streak_reminders: Optional[bool] = Field(None, description="Enable streak reminders")
    achievement_notifications: Optional[bool] = Field(None, description="Enable achievement notifications")
    
    # Audio and interaction preferences
    sound_effects: Optional[bool] = Field(None, description="Enable sound effects")
    haptic_feedback: Optional[bool] = Field(None, description="Enable haptic feedback")
    auto_play_audio: Optional[bool] = Field(None, description="Auto-play audio in exercises")
    
    # Learning preferences
    show_hints: Optional[bool] = Field(None, description="Show hints during exercises")
    speaking_exercises: Optional[bool] = Field(None, description="Include speaking exercises")
    listening_exercises: Optional[bool] = Field(None, description="Include listening exercises")
    writing_exercises: Optional[bool] = Field(None, description="Include writing exercises")
    multiple_choice_exercises: Optional[bool] = Field(None, description="Include multiple choice exercises")
    
    # Performance and data preferences
    offline_download: Optional[bool] = Field(None, description="Enable offline content download")
    data_saver_mode: Optional[bool] = Field(None, description="Enable data saver mode")
    
    @validator('daily_xp_goal')
    def validate_daily_xp_goal(cls, v):
        """Validate daily XP goal is a valid option."""
        if v is not None and v not in [10, 20, 30, 50, 100]:
            raise ValueError("Daily XP goal must be 10, 20, 30, 50, or 100")
        return v
    
    @validator('timezone')
    def validate_timezone(cls, v):
        """Validate timezone format."""
        if v is not None:
            # Basic timezone validation (simplified)
            if not v or len(v) > 50:
                raise ValueError("Invalid timezone format")
        return v
    
    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    """Response schema for user preferences."""
    
    user_id: str = Field(..., description="User ID")
    
    # Basic settings
    daily_xp_goal: int = Field(..., description="Daily XP goal")
    timezone: str = Field(..., description="User timezone")
    language_interface: str = Field(..., description="Interface language")
    learning_language: str = Field(..., description="Target learning language")
    difficulty_level: str = Field(..., description="Learning difficulty level")
    
    # Notification preferences
    lesson_reminders: bool = Field(..., description="Lesson reminders enabled")
    streak_reminders: bool = Field(..., description="Streak reminders enabled")
    achievement_notifications: bool = Field(..., description="Achievement notifications enabled")
    
    # Audio and interaction preferences
    sound_effects: bool = Field(..., description="Sound effects enabled")
    haptic_feedback: bool = Field(..., description="Haptic feedback enabled")
    auto_play_audio: bool = Field(..., description="Auto-play audio enabled")
    
    # Learning preferences
    show_hints: bool = Field(..., description="Show hints enabled")
    speaking_exercises: bool = Field(..., description="Speaking exercises enabled")
    listening_exercises: bool = Field(..., description="Listening exercises enabled")
    writing_exercises: bool = Field(..., description="Writing exercises enabled")
    multiple_choice_exercises: bool = Field(..., description="Multiple choice exercises enabled")
    
    # Performance and data preferences
    offline_download: bool = Field(..., description="Offline download enabled")
    data_saver_mode: bool = Field(..., description="Data saver mode enabled")
    
    # Metadata
    created_at: datetime = Field(..., description="Preferences created timestamp")
    updated_at: datetime = Field(..., description="Preferences last updated timestamp")
    
    class Config:
        from_attributes = True


class UserPreferencesUpdateResponse(BaseModel):
    """Response schema for user preferences update."""
    message: str = Field(..., description="Success message")
    updated_fields: List[str] = Field(..., description="List of fields that were updated")
    updated_at: datetime = Field(..., description="Timestamp of update")
    
    class Config:
        from_attributes = True


class UserManagementErrorResponse(BaseModel):
    """Error response schema for user management operations."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    
    class Config:
        from_attributes = True