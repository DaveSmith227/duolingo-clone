"""
User Progress & Gamification Models

SQLAlchemy models for tracking user progress, course enrollment, lesson completion,
exercise interactions, and gamification features for the Duolingo clone backend application.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class ProgressStatus(str, Enum):
    """Enum for progress status values."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    LOCKED = "locked"


class InteractionType(str, Enum):
    """Enum for exercise interaction types."""
    ATTEMPT = "attempt"
    HINT_USED = "hint_used"
    SKIP = "skip"
    COMPLETE = "complete"
    INCORRECT = "incorrect"
    TIMEOUT = "timeout"


class UserCourse(BaseModel):
    """
    User course enrollment model for tracking XP, streaks, and hearts.
    
    Tracks user progress through courses including experience points,
    streak maintenance, hearts system, and enrollment metadata.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the enrolled user"
    )
    
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the enrolled course"
    )
    
    total_xp = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total experience points earned in this course"
    )
    
    current_streak = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current consecutive days streak"
    )
    
    longest_streak = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Longest consecutive days streak achieved"
    )
    
    current_hearts = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Current number of hearts available"
    )
    
    max_hearts = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Maximum number of hearts allowed"
    )
    
    last_heart_refill = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Last time hearts were refilled"
    )
    
    last_activity_date = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Last date user was active in this course"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the enrollment is currently active"
    )
    
    completion_percentage = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Overall course completion percentage (0.0-100.0)"
    )
    
    enrolled_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when user enrolled in the course"
    )
    
    # Ensure unique enrollment per user-course pair
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='unique_user_course_enrollment'),
        CheckConstraint(total_xp >= 0, name='check_total_xp_non_negative'),
        CheckConstraint(current_streak >= 0, name='check_current_streak_non_negative'),
        CheckConstraint(longest_streak >= 0, name='check_longest_streak_non_negative'),
        CheckConstraint(current_hearts >= 0, name='check_current_hearts_non_negative'),
        CheckConstraint(current_hearts <= max_hearts, name='check_current_hearts_not_exceed_max'),
        CheckConstraint(max_hearts > 0, name='check_max_hearts_positive'),
        CheckConstraint(completion_percentage >= 0.0, name='check_completion_percentage_min'),
        CheckConstraint(completion_percentage <= 100.0, name='check_completion_percentage_max'),
    )
    
    @validates('current_hearts')
    def validate_current_hearts(self, key, value):
        """Validate current hearts doesn't exceed max hearts."""
        if value < 0:
            raise ValueError("Current hearts cannot be negative")
        if hasattr(self, 'max_hearts') and self.max_hearts and value > self.max_hearts:
            raise ValueError("Current hearts cannot exceed max hearts")
        return value
    
    @validates('max_hearts')
    def validate_max_hearts(self, key, value):
        """Validate max hearts is positive."""
        if value <= 0:
            raise ValueError("Max hearts must be positive")
        return value
    
    @validates('completion_percentage')
    def validate_completion_percentage(self, key, value):
        """Validate completion percentage is between 0 and 100."""
        if not 0.0 <= value <= 100.0:
            raise ValueError("Completion percentage must be between 0.0 and 100.0")
        return value
    
    def add_xp(self, xp_amount: int) -> int:
        """
        Add experience points to the user's total.
        
        Args:
            xp_amount: Amount of XP to add
            
        Returns:
            New total XP amount
        """
        if xp_amount < 0:
            raise ValueError("XP amount must be non-negative")
        
        self.total_xp += xp_amount
        return self.total_xp
    
    def lose_heart(self) -> int:
        """
        Remove one heart from the user's current hearts.
        
        Returns:
            Remaining hearts count
            
        Raises:
            ValueError: If user has no hearts to lose
        """
        if self.current_hearts <= 0:
            raise ValueError("No hearts available to lose")
        
        self.current_hearts -= 1
        return self.current_hearts
    
    def can_refill_hearts(self) -> bool:
        """
        Check if hearts can be refilled (4 hours since last refill).
        
        Returns:
            True if hearts can be refilled
        """
        if self.current_hearts >= self.max_hearts:
            return False
        
        time_since_refill = datetime.utcnow() - self.last_heart_refill
        return time_since_refill >= timedelta(hours=4)
    
    def refill_hearts(self) -> int:
        """
        Refill hearts to maximum if enough time has passed.
        
        Returns:
            New hearts count
            
        Raises:
            ValueError: If hearts cannot be refilled yet
        """
        if not self.can_refill_hearts():
            raise ValueError("Hearts cannot be refilled yet")
        
        self.current_hearts = self.max_hearts
        self.last_heart_refill = datetime.utcnow()
        return self.current_hearts
    
    def update_streak(self, activity_date: Optional[datetime] = None) -> int:
        """
        Update streak based on activity date.
        
        Args:
            activity_date: Date of activity (defaults to now)
            
        Returns:
            New current streak value
        """
        if activity_date is None:
            activity_date = datetime.utcnow()
        
        # Check if this is consecutive day activity
        days_since_last = (activity_date.date() - self.last_activity_date.date()).days
        
        if days_since_last == 1:
            # Consecutive day - increment streak
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
        elif days_since_last == 0:
            # Same day - no streak change
            pass
        else:
            # Streak broken - reset to 1
            self.current_streak = 1
        
        self.last_activity_date = activity_date
        return self.current_streak


class UserLessonProgress(BaseModel):
    """
    User lesson progress model for tracking lesson completion.
    
    Tracks user progress through individual lessons including completion status,
    attempts, scores, and timing information.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user"
    )
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the lesson"
    )
    
    status = Column(
        String(20),
        default=ProgressStatus.NOT_STARTED.value,
        nullable=False,
        doc="Current progress status of the lesson"
    )
    
    attempts = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of attempts made on this lesson"
    )
    
    best_score = Column(
        Float,
        nullable=True,
        doc="Best score achieved (0.0-100.0)"
    )
    
    last_score = Column(
        Float,
        nullable=True,
        doc="Most recent score achieved (0.0-100.0)"
    )
    
    xp_earned = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total XP earned from this lesson"
    )
    
    time_spent = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total time spent on lesson in seconds"
    )
    
    first_completed_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp when lesson was first completed"
    )
    
    last_attempted_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp of last attempt"
    )
    
    is_locked = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the lesson is locked (prerequisites not met)"
    )
    
    # Ensure unique progress per user-lesson pair
    __table_args__ = (
        UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson_progress'),
        CheckConstraint(attempts >= 0, name='check_attempts_non_negative'),
        CheckConstraint(best_score >= 0.0, name='check_best_score_min'),
        CheckConstraint(best_score <= 100.0, name='check_best_score_max'),
        CheckConstraint(last_score >= 0.0, name='check_last_score_min'),
        CheckConstraint(last_score <= 100.0, name='check_last_score_max'),
        CheckConstraint(xp_earned >= 0, name='check_xp_earned_non_negative'),
        CheckConstraint(time_spent >= 0, name='check_time_spent_non_negative'),
    )
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate status is a valid ProgressStatus."""
        if value not in [status.value for status in ProgressStatus]:
            raise ValueError(f"Invalid status: {value}")
        return value
    
    @validates('best_score', 'last_score')
    def validate_score(self, key, value):
        """Validate score is between 0 and 100."""
        if value is not None and not 0.0 <= value <= 100.0:
            raise ValueError(f"{key} must be between 0.0 and 100.0")
        return value
    
    def start_attempt(self) -> int:
        """
        Mark lesson as started and increment attempt counter.
        
        Returns:
            New attempt count
        """
        if self.status == ProgressStatus.NOT_STARTED.value:
            self.status = ProgressStatus.IN_PROGRESS.value
        
        self.attempts += 1
        self.last_attempted_at = datetime.utcnow()
        return self.attempts
    
    def complete_lesson(self, score: float, xp_gained: int, time_spent: int) -> None:
        """
        Mark lesson as completed with score and rewards.
        
        Args:
            score: Score achieved (0.0-100.0)
            xp_gained: XP gained from completion
            time_spent: Time spent on this attempt in seconds
        """
        if not 0.0 <= score <= 100.0:
            raise ValueError("Score must be between 0.0 and 100.0")
        if xp_gained < 0:
            raise ValueError("XP gained must be non-negative")
        if time_spent < 0:
            raise ValueError("Time spent must be non-negative")
        
        self.status = ProgressStatus.COMPLETED.value
        self.last_score = score
        self.time_spent = (self.time_spent or 0) + time_spent
        self.xp_earned = (self.xp_earned or 0) + xp_gained
        
        # Update best score if this is better
        if self.best_score is None or score > self.best_score:
            self.best_score = score
        
        # Set first completion timestamp if this is the first time
        if self.first_completed_at is None:
            self.first_completed_at = datetime.utcnow()
    
    def fail_lesson(self, score: float, time_spent: int) -> None:
        """
        Mark lesson as failed.
        
        Args:
            score: Score achieved (0.0-100.0)
            time_spent: Time spent on this attempt in seconds
        """
        if not 0.0 <= score <= 100.0:
            raise ValueError("Score must be between 0.0 and 100.0")
        if time_spent < 0:
            raise ValueError("Time spent must be non-negative")
        
        self.status = ProgressStatus.FAILED.value
        self.last_score = score
        self.time_spent = (self.time_spent or 0) + time_spent
    
    def unlock_lesson(self) -> None:
        """Unlock the lesson (prerequisites met)."""
        self.is_locked = False
        if self.status == ProgressStatus.LOCKED.value:
            self.status = ProgressStatus.NOT_STARTED.value


class UserExerciseInteraction(BaseModel):
    """
    User exercise interaction model for detailed tracking.
    
    Logs all user interactions with exercises including attempts, timing,
    answers, and performance metrics for analytics and personalization.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user"
    )
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the exercise"
    )
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="ID of the lesson (if part of lesson)"
    )
    
    interaction_type = Column(
        String(20),
        nullable=False,
        doc="Type of interaction (attempt, hint_used, skip, complete, etc.)"
    )
    
    user_answer = Column(
        Text,
        nullable=True,
        doc="User's answer or response"
    )
    
    is_correct = Column(
        Boolean,
        nullable=True,
        doc="Whether the answer was correct (NULL for non-answer interactions)"
    )
    
    time_taken = Column(
        Integer,
        nullable=True,
        doc="Time taken for this interaction in seconds"
    )
    
    xp_earned = Column(
        Integer,
        default=0,
        nullable=False,
        doc="XP earned from this interaction"
    )
    
    hints_used = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of hints used during this interaction"
    )
    
    attempt_number = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Attempt number for this exercise (1-based)"
    )
    
    session_id = Column(
        String(36),
        nullable=True,
        doc="Session identifier for grouping interactions"
    )
    
    # Additional metadata stored as JSON-like text for SQLite compatibility
    interaction_metadata = Column(
        Text,
        nullable=True,
        doc="Additional interaction metadata (JSON format)"
    )
    
    __table_args__ = (
        CheckConstraint(time_taken >= 0, name='check_time_taken_non_negative'),
        CheckConstraint(xp_earned >= 0, name='check_xp_earned_non_negative'),
        CheckConstraint(hints_used >= 0, name='check_hints_used_non_negative'),
        CheckConstraint(attempt_number >= 1, name='check_attempt_number_positive'),
    )
    
    @validates('interaction_type')
    def validate_interaction_type(self, key, value):
        """Validate interaction type is valid."""
        if value not in [itype.value for itype in InteractionType]:
            raise ValueError(f"Invalid interaction type: {value}")
        return value
    
    @validates('time_taken')
    def validate_time_taken(self, key, value):
        """Validate time taken is reasonable (max 1 hour per interaction)."""
        if value is not None and (value < 0 or value > 3600):
            raise ValueError("Time taken must be between 0 and 3600 seconds")
        return value
    
    def get_metadata_dict(self) -> dict:
        """
        Get metadata as dictionary.
        
        Returns:
            Parsed metadata dictionary or empty dict if none
        """
        if not self.interaction_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.interaction_metadata)
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
            self.interaction_metadata = json.dumps(metadata_dict)
        else:
            self.interaction_metadata = None
    
    @classmethod
    def log_attempt(cls, user_id: str, exercise_id: str, user_answer: str, 
                   is_correct: bool, time_taken: int, lesson_id: str = None,
                   xp_earned: int = 0, hints_used: int = 0, 
                   attempt_number: int = 1, session_id: str = None,
                   metadata: dict = None) -> 'UserExerciseInteraction':
        """
        Create a new exercise attempt interaction.
        
        Args:
            user_id: ID of the user
            exercise_id: ID of the exercise
            user_answer: User's answer
            is_correct: Whether answer was correct
            time_taken: Time taken in seconds
            lesson_id: ID of lesson (optional)
            xp_earned: XP earned from attempt
            hints_used: Number of hints used
            attempt_number: Attempt number
            session_id: Session identifier
            metadata: Additional metadata
            
        Returns:
            New UserExerciseInteraction instance
        """
        interaction = cls(
            user_id=user_id,
            exercise_id=exercise_id,
            lesson_id=lesson_id,
            interaction_type=InteractionType.ATTEMPT.value,
            user_answer=user_answer,
            is_correct=is_correct,
            time_taken=time_taken,
            xp_earned=xp_earned,
            hints_used=hints_used,
            attempt_number=attempt_number,
            session_id=session_id
        )
        
        if metadata:
            interaction.set_metadata_dict(metadata)
        
        return interaction
    
    @classmethod
    def log_hint_used(cls, user_id: str, exercise_id: str, lesson_id: str = None,
                     session_id: str = None, metadata: dict = None) -> 'UserExerciseInteraction':
        """
        Create a hint usage interaction.
        
        Args:
            user_id: ID of the user
            exercise_id: ID of the exercise
            lesson_id: ID of lesson (optional)
            session_id: Session identifier
            metadata: Additional metadata
            
        Returns:
            New UserExerciseInteraction instance
        """
        interaction = cls(
            user_id=user_id,
            exercise_id=exercise_id,
            lesson_id=lesson_id,
            interaction_type=InteractionType.HINT_USED.value,
            hints_used=1,
            session_id=session_id
        )
        
        if metadata:
            interaction.set_metadata_dict(metadata)
        
        return interaction
    
    @classmethod
    def log_skip(cls, user_id: str, exercise_id: str, lesson_id: str = None,
                session_id: str = None, metadata: dict = None) -> 'UserExerciseInteraction':
        """
        Create a skip interaction.
        
        Args:
            user_id: ID of the user
            exercise_id: ID of the exercise
            lesson_id: ID of lesson (optional)
            session_id: Session identifier
            metadata: Additional metadata
            
        Returns:
            New UserExerciseInteraction instance
        """
        interaction = cls(
            user_id=user_id,
            exercise_id=exercise_id,
            lesson_id=lesson_id,
            interaction_type=InteractionType.SKIP.value,
            session_id=session_id
        )
        
        if metadata:
            interaction.set_metadata_dict(metadata)
        
        return interaction