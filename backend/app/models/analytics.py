"""
Analytics Models

SQLAlchemy models for analytics event tracking, user progress analytics,
and learning statistics for the Duolingo clone backend application.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint, Float, Index
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class EventType(str, Enum):
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


class AnalyticsEvent(BaseModel):
    """
    Analytics event model for tracking all user learning events.
    
    Stores detailed information about user interactions, learning progress,
    and engagement metrics for analytics and personalization purposes.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user who triggered the event"
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of analytics event"
    )
    
    event_name = Column(
        String(100),
        nullable=False,
        doc="Human-readable name of the event"
    )
    
    event_category = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Category of the event (learning, engagement, progress, etc.)"
    )
    
    # Related entity references
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of related course (if applicable)"
    )
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of related lesson (if applicable)"
    )
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID of related exercise (if applicable)"
    )
    
    # Event metrics
    value = Column(
        Float,
        nullable=True,
        doc="Numeric value associated with the event (XP, score, time, etc.)"
    )
    
    duration = Column(
        Integer,
        nullable=True,
        doc="Duration of the event in seconds (for timed events)"
    )
    
    # Success/failure tracking
    is_success = Column(
        Boolean,
        nullable=True,
        doc="Whether the event represents a successful action"
    )
    
    # User context
    user_level = Column(
        Integer,
        nullable=True,
        doc="User's level at the time of the event"
    )
    
    user_xp = Column(
        Integer,
        nullable=True,
        doc="User's total XP at the time of the event"
    )
    
    user_streak = Column(
        Integer,
        nullable=True,
        doc="User's current streak at the time of the event"
    )
    
    # Device/session context
    session_id = Column(
        String(36),
        nullable=True,
        index=True,
        doc="Session identifier for grouping events"
    )
    
    device_type = Column(
        String(20),
        nullable=True,
        doc="Type of device used (web, mobile, tablet)"
    )
    
    platform = Column(
        String(20),
        nullable=True,
        doc="Platform used (ios, android, web)"
    )
    
    # Additional metadata as JSON-like text for SQLite compatibility
    event_metadata = Column(
        Text,
        nullable=True,
        doc="Additional event metadata (JSON format)"
    )
    
    # Timestamp when the event occurred (may differ from created_at)
    event_timestamp = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="When the event actually occurred"
    )
    
    __table_args__ = (
        CheckConstraint(duration >= 0, name='check_duration_non_negative'),
        CheckConstraint(user_level >= 0, name='check_user_level_non_negative'),
        CheckConstraint(user_xp >= 0, name='check_user_xp_non_negative'),
        CheckConstraint(user_streak >= 0, name='check_user_streak_non_negative'),
        # Composite indexes for common queries
        Index('idx_user_event_type_timestamp', 'user_id', 'event_type', 'event_timestamp'),
        Index('idx_event_category_timestamp', 'event_category', 'event_timestamp'),
        Index('idx_course_event_timestamp', 'course_id', 'event_timestamp'),
        Index('idx_lesson_event_timestamp', 'lesson_id', 'event_timestamp'),
        Index('idx_session_timestamp', 'session_id', 'event_timestamp'),
    )
    
    @validates('event_type')
    def validate_event_type(self, key, value):
        """Validate event type is valid."""
        if value not in [event.value for event in EventType]:
            raise ValueError(f"Invalid event type: {value}")
        return value
    
    @validates('event_category')
    def validate_event_category(self, key, value):
        """Validate event category is valid."""
        valid_categories = [
            'learning', 'engagement', 'progress', 'gamification', 
            'authentication', 'navigation', 'error', 'performance'
        ]
        if value not in valid_categories:
            raise ValueError(f"Invalid event category: {value}")
        return value
    
    @validates('device_type')
    def validate_device_type(self, key, value):
        """Validate device type is valid."""
        if value and value not in ['web', 'mobile', 'tablet']:
            raise ValueError(f"Invalid device type: {value}")
        return value
    
    @validates('platform')
    def validate_platform(self, key, value):
        """Validate platform is valid."""
        if value and value not in ['ios', 'android', 'web']:
            raise ValueError(f"Invalid platform: {value}")
        return value
    
    def get_metadata_dict(self) -> dict:
        """
        Get metadata as dictionary.
        
        Returns:
            Parsed metadata dictionary or empty dict if none
        """
        if not self.event_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.event_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata_dict(self, metadata_dict: dict) -> None:
        """
        Set metadata from dictionary.
        
        Args:
            metadata_dict: Dictionary to store as metadata
        """
        if metadata_dict:
            import json
            self.event_metadata = json.dumps(metadata_dict)
        else:
            self.event_metadata = None
    
    @classmethod
    def create_learning_event(cls, user_id: str, event_type: EventType, 
                            course_id: str = None, lesson_id: str = None,
                            exercise_id: str = None, value: float = None,
                            duration: int = None, is_success: bool = None,
                            user_context: dict = None, session_id: str = None,
                            device_type: str = None, platform: str = None,
                            metadata: dict = None) -> 'AnalyticsEvent':
        """
        Create a learning-related analytics event.
        
        Args:
            user_id: ID of the user
            event_type: Type of event
            course_id: ID of related course
            lesson_id: ID of related lesson
            exercise_id: ID of related exercise
            value: Numeric value (XP, score, etc.)
            duration: Duration in seconds
            is_success: Whether event was successful
            user_context: User context (level, xp, streak)
            session_id: Session identifier
            device_type: Device type
            platform: Platform
            metadata: Additional metadata
            
        Returns:
            New AnalyticsEvent instance
        """
        event = cls(
            user_id=user_id,
            event_type=event_type.value,
            event_name=event_type.value.replace('_', ' ').title(),
            event_category='learning',
            course_id=course_id,
            lesson_id=lesson_id,
            exercise_id=exercise_id,
            value=value,
            duration=duration,
            is_success=is_success,
            session_id=session_id,
            device_type=device_type,
            platform=platform,
            event_timestamp=datetime.utcnow()
        )
        
        # Set user context
        if user_context:
            event.user_level = user_context.get('level')
            event.user_xp = user_context.get('xp')
            event.user_streak = user_context.get('streak')
        
        # Set metadata
        if metadata:
            event.set_metadata_dict(metadata)
        
        return event


class UserProgressSnapshot(BaseModel):
    """
    User progress snapshot model for periodic progress tracking.
    
    Stores periodic snapshots of user progress for trend analysis
    and progress tracking over time.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user"
    )
    
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the course"
    )
    
    # Progress metrics
    total_xp = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total XP at time of snapshot"
    )
    
    current_streak = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current streak at time of snapshot"
    )
    
    lessons_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of lessons completed"
    )
    
    exercises_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of exercises completed"
    )
    
    total_time_spent = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total time spent learning in seconds"
    )
    
    # Accuracy metrics
    correct_answers = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of correct answers"
    )
    
    total_answers = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of answers given"
    )
    
    accuracy_percentage = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Answer accuracy percentage (0.0-100.0)"
    )
    
    # Engagement metrics
    days_active = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of days active in the course"
    )
    
    sessions_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of learning sessions"
    )
    
    avg_session_duration = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average session duration in seconds"
    )
    
    # Difficulty metrics
    hints_used = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total hints used"
    )
    
    exercises_skipped = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of exercises skipped"
    )
    
    # Snapshot metadata
    snapshot_date = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        doc="Date of the snapshot"
    )
    
    snapshot_type = Column(
        String(20),
        default='daily',
        nullable=False,
        doc="Type of snapshot (daily, weekly, monthly)"
    )
    
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', 'snapshot_date', 'snapshot_type', 
                        name='unique_user_course_snapshot'),
        CheckConstraint(total_xp >= 0, name='check_total_xp_non_negative'),
        CheckConstraint(current_streak >= 0, name='check_current_streak_non_negative'),
        CheckConstraint(lessons_completed >= 0, name='check_lessons_completed_non_negative'),
        CheckConstraint(exercises_completed >= 0, name='check_exercises_completed_non_negative'),
        CheckConstraint(total_time_spent >= 0, name='check_total_time_spent_non_negative'),
        CheckConstraint(correct_answers >= 0, name='check_correct_answers_non_negative'),
        CheckConstraint(total_answers >= 0, name='check_total_answers_non_negative'),
        CheckConstraint(accuracy_percentage >= 0.0, name='check_accuracy_percentage_min'),
        CheckConstraint(accuracy_percentage <= 100.0, name='check_accuracy_percentage_max'),
        CheckConstraint(days_active >= 0, name='check_days_active_non_negative'),
        CheckConstraint(sessions_count >= 0, name='check_sessions_count_non_negative'),
        CheckConstraint(avg_session_duration >= 0.0, name='check_avg_session_duration_non_negative'),
        CheckConstraint(hints_used >= 0, name='check_hints_used_non_negative'),
        CheckConstraint(exercises_skipped >= 0, name='check_exercises_skipped_non_negative'),
        # Composite indexes for common queries
        Index('idx_user_snapshot_date', 'user_id', 'snapshot_date'),
        Index('idx_course_snapshot_date', 'course_id', 'snapshot_date'),
        Index('idx_snapshot_type_date', 'snapshot_type', 'snapshot_date'),
    )
    
    @validates('snapshot_type')
    def validate_snapshot_type(self, key, value):
        """Validate snapshot type is valid."""
        valid_types = ['daily', 'weekly', 'monthly']
        if value not in valid_types:
            raise ValueError(f"Invalid snapshot type: {value}")
        return value
    
    @validates('accuracy_percentage')
    def validate_accuracy_percentage(self, key, value):
        """Validate accuracy percentage is between 0 and 100."""
        if not 0.0 <= value <= 100.0:
            raise ValueError("Accuracy percentage must be between 0.0 and 100.0")
        return value
    
    def calculate_accuracy(self) -> float:
        """
        Calculate and update accuracy percentage.
        
        Returns:
            Calculated accuracy percentage
        """
        if self.total_answers == 0:
            self.accuracy_percentage = 0.0
        else:
            self.accuracy_percentage = (self.correct_answers / self.total_answers) * 100.0
        
        return self.accuracy_percentage
    
    def update_metrics(self, user_course_data: dict, exercise_data: dict) -> None:
        """
        Update snapshot metrics from provided data.
        
        Args:
            user_course_data: User course progress data
            exercise_data: Exercise completion data
        """
        # Update basic metrics
        self.total_xp = user_course_data.get('total_xp', 0)
        self.current_streak = user_course_data.get('current_streak', 0)
        self.lessons_completed = user_course_data.get('lessons_completed', 0)
        self.exercises_completed = exercise_data.get('exercises_completed', 0)
        self.total_time_spent = exercise_data.get('total_time_spent', 0)
        
        # Update accuracy metrics
        self.correct_answers = exercise_data.get('correct_answers', 0)
        self.total_answers = exercise_data.get('total_answers', 0)
        self.calculate_accuracy()
        
        # Update engagement metrics
        self.days_active = user_course_data.get('days_active', 0)
        self.sessions_count = exercise_data.get('sessions_count', 0)
        self.avg_session_duration = exercise_data.get('avg_session_duration', 0.0)
        
        # Update difficulty metrics
        self.hints_used = exercise_data.get('hints_used', 0)
        self.exercises_skipped = exercise_data.get('exercises_skipped', 0)


class UserLearningStats(BaseModel):
    """
    User learning statistics model for aggregated analytics.
    
    Stores aggregated learning statistics for quick dashboard access
    and user progress reporting.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user"
    )
    
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="ID of the course (NULL for global stats)"
    )
    
    # Time-based metrics
    total_study_time = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total study time in seconds"
    )
    
    avg_daily_study_time = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average daily study time in seconds"
    )
    
    study_days_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of days with study activity"
    )
    
    # Progress metrics
    total_lessons_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total lessons completed"
    )
    
    total_exercises_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total exercises completed"
    )
    
    total_xp_earned = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total XP earned"
    )
    
    # Performance metrics
    overall_accuracy = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Overall accuracy percentage (0.0-100.0)"
    )
    
    best_streak = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Best streak achieved"
    )
    
    current_streak = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current streak"
    )
    
    # Engagement metrics
    total_sessions = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total learning sessions"
    )
    
    avg_session_duration = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Average session duration in seconds"
    )
    
    # Difficulty metrics
    total_hints_used = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total hints used"
    )
    
    total_exercises_skipped = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total exercises skipped"
    )
    
    # Timestamps
    first_activity_date = Column(
        DateTime,
        nullable=True,
        doc="Date of first activity"
    )
    
    last_activity_date = Column(
        DateTime,
        nullable=True,
        doc="Date of last activity"
    )
    
    last_calculated_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="When these stats were last calculated"
    )
    
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='unique_user_course_stats'),
        CheckConstraint(total_study_time >= 0, name='check_total_study_time_non_negative'),
        CheckConstraint(avg_daily_study_time >= 0.0, name='check_avg_daily_study_time_non_negative'),
        CheckConstraint(study_days_count >= 0, name='check_study_days_count_non_negative'),
        CheckConstraint(total_lessons_completed >= 0, name='check_total_lessons_completed_non_negative'),
        CheckConstraint(total_exercises_completed >= 0, name='check_total_exercises_completed_non_negative'),
        CheckConstraint(total_xp_earned >= 0, name='check_total_xp_earned_non_negative'),
        CheckConstraint(overall_accuracy >= 0.0, name='check_overall_accuracy_min'),
        CheckConstraint(overall_accuracy <= 100.0, name='check_overall_accuracy_max'),
        CheckConstraint(best_streak >= 0, name='check_best_streak_non_negative'),
        CheckConstraint(current_streak >= 0, name='check_current_streak_non_negative'),
        CheckConstraint(total_sessions >= 0, name='check_total_sessions_non_negative'),
        CheckConstraint(avg_session_duration >= 0.0, name='check_avg_session_duration_non_negative'),
        CheckConstraint(total_hints_used >= 0, name='check_total_hints_used_non_negative'),
        CheckConstraint(total_exercises_skipped >= 0, name='check_total_exercises_skipped_non_negative'),
        # Composite indexes for common queries
        Index('idx_user_last_calculated', 'user_id', 'last_calculated_at'),
        Index('idx_course_last_calculated', 'course_id', 'last_calculated_at'),
    )
    
    @validates('overall_accuracy')
    def validate_overall_accuracy(self, key, value):
        """Validate accuracy percentage is between 0 and 100."""
        if not 0.0 <= value <= 100.0:
            raise ValueError("Overall accuracy must be between 0.0 and 100.0")
        return value
    
    def calculate_study_streak(self) -> int:
        """
        Calculate current study streak from activity dates.
        
        Returns:
            Current streak count
        """
        # This would need to be implemented with proper date calculations
        # For now, return the stored value
        return self.current_streak
    
    def update_from_snapshots(self, snapshots: list) -> None:
        """
        Update stats from progress snapshots.
        
        Args:
            snapshots: List of UserProgressSnapshot objects
        """
        if not snapshots:
            return
        
        # Calculate totals from snapshots
        latest_snapshot = max(snapshots, key=lambda s: s.snapshot_date)
        
        self.total_lessons_completed = latest_snapshot.lessons_completed
        self.total_exercises_completed = latest_snapshot.exercises_completed
        self.total_xp_earned = latest_snapshot.total_xp
        self.overall_accuracy = latest_snapshot.accuracy_percentage
        self.current_streak = latest_snapshot.current_streak
        self.total_study_time = latest_snapshot.total_time_spent
        self.total_sessions = latest_snapshot.sessions_count
        self.avg_session_duration = latest_snapshot.avg_session_duration
        self.total_hints_used = latest_snapshot.hints_used
        self.total_exercises_skipped = latest_snapshot.exercises_skipped
        
        # Calculate derived metrics
        self.study_days_count = latest_snapshot.days_active
        if self.study_days_count > 0:
            self.avg_daily_study_time = self.total_study_time / self.study_days_count
        
        # Update timestamps
        self.last_calculated_at = datetime.utcnow()
        
        # Find best streak from all snapshots
        self.best_streak = max(s.current_streak for s in snapshots)