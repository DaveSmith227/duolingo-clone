"""
Analytics Schemas

Pydantic schemas for analytics endpoints including request/response validation
for the Duolingo clone backend application.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, validator
from pydantic.types import UUID4


class EventTypeEnum(str, Enum):
    """Enum for analytics event types."""
    LESSON_START = "lesson_start"
    LESSON_COMPLETE = "lesson_complete"
    LESSON_FAIL = "lesson_fail"
    EXERCISE_ATTEMPT = "exercise_attempt"
    EXERCISE_COMPLETE = "exercise_complete"
    EXERCISE_SKIP = "exercise_skip"
    HINT_USED = "hint_used"
    HEART_LOST = "heart_lost"
    HEART_REFILL = "heart_refill"
    STREAK_EXTENDED = "streak_extended"
    STREAK_BROKEN = "streak_broken"
    XP_EARNED = "xp_earned"
    COURSE_STARTED = "course_started"
    COURSE_COMPLETED = "course_completed"
    LOGIN = "login"
    LOGOUT = "logout"
    PROFILE_UPDATE = "profile_update"


class EventCategoryEnum(str, Enum):
    """Enum for analytics event categories."""
    LEARNING = "learning"
    ENGAGEMENT = "engagement"
    PROGRESS = "progress"
    GAMIFICATION = "gamification"
    AUTHENTICATION = "authentication"
    NAVIGATION = "navigation"
    ERROR = "error"
    PERFORMANCE = "performance"


class DeviceTypeEnum(str, Enum):
    """Enum for device types."""
    WEB = "web"
    MOBILE = "mobile"
    TABLET = "tablet"


class PlatformEnum(str, Enum):
    """Enum for platforms."""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


class SnapshotTypeEnum(str, Enum):
    """Enum for snapshot types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Base schemas
class AnalyticsEventBase(BaseModel):
    """Base schema for analytics events."""
    event_type: EventTypeEnum
    event_category: EventCategoryEnum
    course_id: Optional[UUID4] = None
    lesson_id: Optional[UUID4] = None
    exercise_id: Optional[UUID4] = None
    value: Optional[float] = Field(None, description="Numeric value associated with the event")
    duration: Optional[int] = Field(None, ge=0, description="Duration in seconds")
    is_success: Optional[bool] = None
    session_id: Optional[str] = None
    device_type: Optional[DeviceTypeEnum] = None
    platform: Optional[PlatformEnum] = None
    event_metadata: Optional[Dict[str, Any]] = None
    event_timestamp: Optional[datetime] = None

    @validator('duration')
    def validate_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError('Duration must be non-negative')
        return v


class AnalyticsEventCreate(AnalyticsEventBase):
    """Schema for creating analytics events."""
    pass


class AnalyticsEventInDB(AnalyticsEventBase):
    """Schema for analytics events in database."""
    id: UUID4
    user_id: UUID4
    event_name: str
    user_level: Optional[int] = None
    user_xp: Optional[int] = None
    user_streak: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    event_timestamp: datetime

    class Config:
        orm_mode = True


class AnalyticsEventResponse(AnalyticsEventInDB):
    """Schema for analytics event responses."""
    pass


# Batch event creation
class AnalyticsEventBatch(BaseModel):
    """Schema for batch analytics event creation."""
    events: List[AnalyticsEventCreate] = Field(..., min_items=1, max_items=100)

    @validator('events')
    def validate_events(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 events per batch')
        return v


# Progress snapshot schemas
class UserProgressSnapshotBase(BaseModel):
    """Base schema for user progress snapshots."""
    course_id: UUID4
    total_xp: int = Field(0, ge=0)
    current_streak: int = Field(0, ge=0)
    lessons_completed: int = Field(0, ge=0)
    exercises_completed: int = Field(0, ge=0)
    total_time_spent: int = Field(0, ge=0)
    correct_answers: int = Field(0, ge=0)
    total_answers: int = Field(0, ge=0)
    accuracy_percentage: float = Field(0.0, ge=0.0, le=100.0)
    days_active: int = Field(0, ge=0)
    sessions_count: int = Field(0, ge=0)
    avg_session_duration: float = Field(0.0, ge=0.0)
    hints_used: int = Field(0, ge=0)
    exercises_skipped: int = Field(0, ge=0)
    snapshot_type: SnapshotTypeEnum = SnapshotTypeEnum.DAILY


class UserProgressSnapshotCreate(UserProgressSnapshotBase):
    """Schema for creating user progress snapshots."""
    pass


class UserProgressSnapshotInDB(UserProgressSnapshotBase):
    """Schema for user progress snapshots in database."""
    id: UUID4
    user_id: UUID4
    snapshot_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserProgressSnapshotResponse(UserProgressSnapshotInDB):
    """Schema for user progress snapshot responses."""
    pass


# Learning stats schemas
class UserLearningStatsBase(BaseModel):
    """Base schema for user learning statistics."""
    course_id: Optional[UUID4] = None
    total_study_time: int = Field(0, ge=0)
    avg_daily_study_time: float = Field(0.0, ge=0.0)
    study_days_count: int = Field(0, ge=0)
    total_lessons_completed: int = Field(0, ge=0)
    total_exercises_completed: int = Field(0, ge=0)
    total_xp_earned: int = Field(0, ge=0)
    overall_accuracy: float = Field(0.0, ge=0.0, le=100.0)
    best_streak: int = Field(0, ge=0)
    current_streak: int = Field(0, ge=0)
    total_sessions: int = Field(0, ge=0)
    avg_session_duration: float = Field(0.0, ge=0.0)
    total_hints_used: int = Field(0, ge=0)
    total_exercises_skipped: int = Field(0, ge=0)
    first_activity_date: Optional[datetime] = None
    last_activity_date: Optional[datetime] = None


class UserLearningStatsInDB(UserLearningStatsBase):
    """Schema for user learning statistics in database."""
    id: UUID4
    user_id: UUID4
    last_calculated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserLearningStatsResponse(UserLearningStatsInDB):
    """Schema for user learning statistics responses."""
    pass


# API request/response schemas
class AnalyticsEventRequest(BaseModel):
    """Request schema for analytics event tracking."""
    event_type: EventTypeEnum
    event_category: EventCategoryEnum
    course_id: Optional[UUID4] = None
    lesson_id: Optional[UUID4] = None
    exercise_id: Optional[UUID4] = None
    value: Optional[float] = None
    duration: Optional[int] = Field(None, ge=0)
    is_success: Optional[bool] = None
    session_id: Optional[str] = None
    device_type: Optional[DeviceTypeEnum] = None
    platform: Optional[PlatformEnum] = None
    event_metadata: Optional[Dict[str, Any]] = None

    @validator('duration')
    def validate_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError('Duration must be non-negative')
        return v


class AnalyticsEventBatchRequest(BaseModel):
    """Request schema for batch analytics event tracking."""
    events: List[AnalyticsEventRequest] = Field(..., min_items=1, max_items=100)

    @validator('events')
    def validate_events(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 events per batch')
        return v


class UserProgressRequest(BaseModel):
    """Request schema for user progress tracking."""
    course_id: Optional[UUID4] = None
    include_global_stats: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class UserProgressResponse(BaseModel):
    """Response schema for user progress."""
    user_id: UUID4
    course_id: Optional[UUID4] = None
    total_xp: int
    current_streak: int
    longest_streak: int
    lessons_completed: int
    exercises_completed: int
    total_study_time: int
    accuracy_percentage: float
    days_active: int
    hearts_remaining: int
    level: int
    xp_to_next_level: int
    completion_percentage: float
    last_activity_date: datetime
    created_at: datetime


class CourseCompletionRequest(BaseModel):
    """Request schema for course completion tracking."""
    course_id: UUID4
    completion_date: Optional[datetime] = None
    final_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    total_time_spent: Optional[int] = Field(None, ge=0)
    lessons_completed: Optional[int] = Field(None, ge=0)
    exercises_completed: Optional[int] = Field(None, ge=0)
    total_xp_earned: Optional[int] = Field(None, ge=0)
    metadata: Optional[Dict[str, Any]] = None


class CourseCompletionResponse(BaseModel):
    """Response schema for course completion."""
    user_id: UUID4
    course_id: UUID4
    completion_date: datetime
    final_score: Optional[float] = None
    total_time_spent: int
    lessons_completed: int
    exercises_completed: int
    total_xp_earned: int
    achievements_unlocked: List[str] = []
    created_at: datetime


class LessonCompletionRequest(BaseModel):
    """Request schema for lesson completion tracking."""
    lesson_id: UUID4
    completion_date: Optional[datetime] = None
    score: float = Field(..., ge=0.0, le=100.0)
    time_spent: int = Field(..., ge=0)
    xp_earned: int = Field(0, ge=0)
    exercises_completed: int = Field(0, ge=0)
    exercises_correct: int = Field(0, ge=0)
    hints_used: int = Field(0, ge=0)
    hearts_lost: int = Field(0, ge=0)
    metadata: Optional[Dict[str, Any]] = None

    @validator('exercises_correct')
    def validate_exercises_correct(cls, v, values):
        if 'exercises_completed' in values and v > values['exercises_completed']:
            raise ValueError('Exercises correct cannot exceed exercises completed')
        return v


class LessonCompletionResponse(BaseModel):
    """Response schema for lesson completion."""
    user_id: UUID4
    lesson_id: UUID4
    completion_date: datetime
    score: float
    time_spent: int
    xp_earned: int
    exercises_completed: int
    exercises_correct: int
    accuracy_percentage: float
    hints_used: int
    hearts_lost: int
    achievements_unlocked: List[str] = []
    created_at: datetime


class UserStatsRequest(BaseModel):
    """Request schema for user statistics."""
    course_id: Optional[UUID4] = None
    include_global_stats: bool = True
    include_historical: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class UserStatsResponse(BaseModel):
    """Response schema for user statistics."""
    user_id: UUID4
    course_id: Optional[UUID4] = None
    
    # Basic stats
    total_xp: int
    current_streak: int
    longest_streak: int
    level: int
    xp_to_next_level: int
    
    # Progress stats
    lessons_completed: int
    exercises_completed: int
    courses_completed: int
    completion_percentage: float
    
    # Time stats
    total_study_time: int
    avg_daily_study_time: float
    study_days_count: int
    total_sessions: int
    avg_session_duration: float
    
    # Performance stats
    overall_accuracy: float
    total_hints_used: int
    total_exercises_skipped: int
    
    # Engagement stats
    last_activity_date: Optional[datetime] = None
    first_activity_date: Optional[datetime] = None
    
    # Achievement stats
    achievements_earned: int
    badges_earned: int
    
    # Gamification
    hearts_remaining: int
    
    # Historical data (if requested)
    historical_snapshots: Optional[List[UserProgressSnapshotResponse]] = None
    
    # Timestamps
    last_calculated_at: datetime
    created_at: datetime


class AnalyticsMetricsResponse(BaseModel):
    """Response schema for analytics metrics."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_category: Dict[str, int]
    active_users: int
    engagement_rate: float
    avg_session_duration: float
    completion_rates: Dict[str, float]
    top_courses: List[Dict[str, Any]]
    date_range: Dict[str, datetime]
    last_updated: datetime


# Error response schemas
class AnalyticsErrorResponse(BaseModel):
    """Error response schema for analytics endpoints."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Query parameter schemas
class AnalyticsQueryParams(BaseModel):
    """Query parameters for analytics endpoints."""
    course_id: Optional[UUID4] = None
    lesson_id: Optional[UUID4] = None
    exercise_id: Optional[UUID4] = None
    event_type: Optional[EventTypeEnum] = None
    event_category: Optional[EventCategoryEnum] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    limit: Optional[int] = Field(100, ge=1, le=1000)
    offset: Optional[int] = Field(0, ge=0)
    session_id: Optional[str] = None
    device_type: Optional[DeviceTypeEnum] = None
    platform: Optional[PlatformEnum] = None