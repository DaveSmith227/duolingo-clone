"""
Gamification Models

SQLAlchemy models for gamification features including daily XP tracking,
hearts system, achievements, and rewards for the Duolingo clone backend application.
"""

from datetime import datetime, timezone, timedelta, date
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint, Float, Date
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class AchievementType(str, Enum):
    """Enum for achievement types."""
    STREAK = "streak"
    XP_MILESTONE = "xp_milestone"
    LESSON_COMPLETION = "lesson_completion"
    COURSE_COMPLETION = "course_completion"
    PERFECT_LESSON = "perfect_lesson"
    SPEED_CHALLENGE = "speed_challenge"
    CONSISTENCY = "consistency"
    SOCIAL = "social"
    SPECIAL_EVENT = "special_event"


class HeartActionType(str, Enum):
    """Enum for heart action types."""
    LOST = "lost"
    GAINED = "gained"
    REFILLED = "refilled"
    PURCHASED = "purchased"
    BONUS = "bonus"


class UserDailyXP(BaseModel):
    """
    User daily XP model for streak calculation and goal tracking.
    
    Tracks daily experience points for streak calculation, goal achievement,
    and consistency metrics. Supports flexible daily goals and streak logic.
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
        doc="ID of the course (NULL for overall daily XP)"
    )
    
    date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date for this XP record"
    )
    
    xp_earned = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total XP earned on this date"
    )
    
    daily_goal = Column(
        Integer,
        default=50,
        nullable=False,
        doc="Daily XP goal for this date"
    )
    
    goal_met = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether daily goal was met"
    )
    
    lessons_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of lessons completed on this date"
    )
    
    exercises_completed = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of exercises completed on this date"
    )
    
    time_spent = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Total time spent learning in seconds"
    )
    
    streak_count = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Streak count at the end of this day"
    )
    
    # Ensure unique record per user-course-date combination
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', 'date', name='unique_user_course_daily_xp'),
        CheckConstraint(xp_earned >= 0, name='check_xp_earned_non_negative'),
        CheckConstraint(daily_goal > 0, name='check_daily_goal_positive'),
        CheckConstraint(lessons_completed >= 0, name='check_lessons_completed_non_negative'),
        CheckConstraint(exercises_completed >= 0, name='check_exercises_completed_non_negative'),
        CheckConstraint(time_spent >= 0, name='check_time_spent_non_negative'),
        CheckConstraint(streak_count >= 0, name='check_streak_count_non_negative'),
    )
    
    @validates('daily_goal')
    def validate_daily_goal(self, key, value):
        """Validate daily goal is reasonable (between 1 and 1000)."""
        if not 1 <= value <= 1000:
            raise ValueError("Daily goal must be between 1 and 1000 XP")
        return value
    
    def add_xp(self, xp_amount: int) -> int:
        """
        Add XP to daily total and check goal completion.
        
        Args:
            xp_amount: Amount of XP to add
            
        Returns:
            New total XP for the day
        """
        if xp_amount < 0:
            raise ValueError("XP amount must be non-negative")
        
        self.xp_earned += xp_amount
        self.goal_met = self.xp_earned >= self.daily_goal
        return self.xp_earned
    
    def increment_lessons(self) -> int:
        """
        Increment lessons completed count.
        
        Returns:
            New lessons completed count
        """
        self.lessons_completed = (self.lessons_completed or 0) + 1
        return self.lessons_completed
    
    def increment_exercises(self) -> int:
        """
        Increment exercises completed count.
        
        Returns:
            New exercises completed count
        """
        self.exercises_completed = (self.exercises_completed or 0) + 1
        return self.exercises_completed
    
    def add_time(self, seconds: int) -> int:
        """
        Add time spent learning.
        
        Args:
            seconds: Time to add in seconds
            
        Returns:
            New total time spent
        """
        if seconds < 0:
            raise ValueError("Time must be non-negative")
        
        self.time_spent = (self.time_spent or 0) + seconds
        return self.time_spent
    
    @classmethod
    def get_or_create_for_date(cls, session, user_id: str, date_obj: date, 
                              course_id: str = None, daily_goal: int = 50) -> 'UserDailyXP':
        """
        Get existing or create new UserDailyXP for date.
        
        Args:
            session: SQLAlchemy session
            user_id: ID of the user
            date_obj: Date for the record
            course_id: ID of the course (optional)
            daily_goal: Daily XP goal
            
        Returns:
            UserDailyXP instance for the date
        """
        existing = session.query(cls).filter(
            cls.user_id == user_id,
            cls.course_id == course_id,
            cls.date == date_obj
        ).first()
        
        if existing:
            return existing
        
        new_record = cls(
            user_id=user_id,
            course_id=course_id,
            date=date_obj,
            daily_goal=daily_goal
        )
        session.add(new_record)
        return new_record
    
    @classmethod
    def calculate_streak(cls, session, user_id: str, course_id: str = None) -> int:
        """
        Calculate current streak for user.
        
        Args:
            session: SQLAlchemy session
            user_id: ID of the user
            course_id: ID of the course (optional)
            
        Returns:
            Current streak count
        """
        today = date.today()
        current_streak = 0
        
        # Check each day backwards from today
        for days_back in range(365):  # Check up to 1 year back
            check_date = today - timedelta(days=days_back)
            
            daily_xp = session.query(cls).filter(
                cls.user_id == user_id,
                cls.course_id == course_id,
                cls.date == check_date
            ).first()
            
            if daily_xp and daily_xp.goal_met:
                current_streak += 1
            else:
                break
        
        return current_streak


class UserHeartsLog(BaseModel):
    """
    User hearts log model for tracking heart loss/regeneration.
    
    Logs all heart-related activities including loss from wrong answers,
    automatic regeneration, purchases, and bonus hearts from achievements.
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
        doc="ID of the course (if course-specific)"
    )
    
    action_type = Column(
        String(20),
        nullable=False,
        doc="Type of heart action (lost, gained, refilled, purchased, bonus)"
    )
    
    hearts_before = Column(
        Integer,
        nullable=False,
        doc="Number of hearts before the action"
    )
    
    hearts_after = Column(
        Integer,
        nullable=False,
        doc="Number of hearts after the action"
    )
    
    hearts_changed = Column(
        Integer,
        nullable=False,
        doc="Number of hearts gained or lost (positive for gain, negative for loss)"
    )
    
    reason = Column(
        Text,
        nullable=True,
        doc="Reason for the heart change (e.g., 'incorrect answer', 'auto refill')"
    )
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of exercise that caused heart loss (if applicable)"
    )
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of lesson where heart change occurred (if applicable)"
    )
    
    # Additional metadata
    action_metadata = Column(
        Text,
        nullable=True,
        doc="Additional metadata about the heart action (JSON format)"
    )
    
    __table_args__ = (
        CheckConstraint(hearts_before >= 0, name='check_hearts_before_non_negative'),
        CheckConstraint(hearts_after >= 0, name='check_hearts_after_non_negative'),
    )
    
    @validates('action_type')
    def validate_action_type(self, key, value):
        """Validate action type is valid."""
        if value not in [action.value for action in HeartActionType]:
            raise ValueError(f"Invalid action type: {value}")
        return value
    
    @validates('hearts_changed')
    def validate_hearts_changed(self, key, value):
        """Validate hearts changed matches before/after values."""
        if hasattr(self, 'hearts_before') and hasattr(self, 'hearts_after'):
            expected_change = self.hearts_after - self.hearts_before
            if value != expected_change:
                raise ValueError("Hearts changed must match difference between before and after")
        return value
    
    def get_metadata_dict(self) -> dict:
        """
        Get metadata as dictionary.
        
        Returns:
            Parsed metadata dictionary or empty dict if none
        """
        if not self.action_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.action_metadata)
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
            self.action_metadata = json.dumps(metadata_dict)
        else:
            self.action_metadata = None
    
    @classmethod
    def log_heart_loss(cls, user_id: str, course_id: str, hearts_before: int,
                      reason: str = None, exercise_id: str = None, 
                      lesson_id: str = None, metadata: dict = None) -> 'UserHeartsLog':
        """
        Log a heart loss event.
        
        Args:
            user_id: ID of the user
            course_id: ID of the course
            hearts_before: Hearts before loss
            reason: Reason for heart loss
            exercise_id: ID of exercise that caused loss
            lesson_id: ID of lesson where loss occurred
            metadata: Additional metadata
            
        Returns:
            New UserHeartsLog instance
        """
        hearts_after = max(0, hearts_before - 1)
        
        log_entry = cls(
            user_id=user_id,
            course_id=course_id,
            action_type=HeartActionType.LOST.value,
            hearts_before=hearts_before,
            hearts_after=hearts_after,
            hearts_changed=-1,
            reason=reason or "Heart lost",
            exercise_id=exercise_id,
            lesson_id=lesson_id
        )
        
        if metadata:
            log_entry.set_metadata_dict(metadata)
        
        return log_entry
    
    @classmethod
    def log_heart_refill(cls, user_id: str, course_id: str, hearts_before: int,
                        max_hearts: int, reason: str = None, 
                        metadata: dict = None) -> 'UserHeartsLog':
        """
        Log a heart refill event.
        
        Args:
            user_id: ID of the user
            course_id: ID of the course
            hearts_before: Hearts before refill
            max_hearts: Maximum hearts to refill to
            reason: Reason for refill
            metadata: Additional metadata
            
        Returns:
            New UserHeartsLog instance
        """
        hearts_gained = max_hearts - hearts_before
        
        log_entry = cls(
            user_id=user_id,
            course_id=course_id,
            action_type=HeartActionType.REFILLED.value,
            hearts_before=hearts_before,
            hearts_after=max_hearts,
            hearts_changed=hearts_gained,
            reason=reason or "Automatic refill"
        )
        
        if metadata:
            log_entry.set_metadata_dict(metadata)
        
        return log_entry


class Achievement(BaseModel):
    """
    Achievement model for defining available achievements.
    
    Defines achievement types, requirements, rewards, and metadata
    for the gamification system. Achievements can be earned by users
    for various milestones and activities.
    """
    
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        doc="Unique name of the achievement"
    )
    
    display_name = Column(
        String(200),
        nullable=False,
        doc="Human-readable display name"
    )
    
    description = Column(
        Text,
        nullable=False,
        doc="Description of how to earn the achievement"
    )
    
    achievement_type = Column(
        String(20),
        nullable=False,
        doc="Category/type of achievement"
    )
    
    icon_url = Column(
        String(500),
        nullable=True,
        doc="URL to achievement icon image"
    )
    
    badge_color = Column(
        String(20),
        nullable=True,
        doc="Color theme for the achievement badge"
    )
    
    xp_reward = Column(
        Integer,
        default=0,
        nullable=False,
        doc="XP reward for earning this achievement"
    )
    
    hearts_reward = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Heart reward for earning this achievement"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this achievement is currently active"
    )
    
    is_hidden = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this achievement is hidden until earned"
    )
    
    sort_order = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Display order for achievement lists"
    )
    
    # Requirements stored as JSON-like text for SQLite compatibility
    requirements = Column(
        Text,
        nullable=True,
        doc="Achievement requirements (JSON format)"
    )
    
    # Additional metadata
    achievement_metadata = Column(
        Text,
        nullable=True,
        doc="Additional achievement metadata (JSON format)"
    )
    
    __table_args__ = (
        CheckConstraint(xp_reward >= 0, name='check_xp_reward_non_negative'),
        CheckConstraint(hearts_reward >= 0, name='check_hearts_reward_non_negative'),
    )
    
    @validates('achievement_type')
    def validate_achievement_type(self, key, value):
        """Validate achievement type is valid."""
        if value not in [atype.value for atype in AchievementType]:
            raise ValueError(f"Invalid achievement type: {value}")
        return value
    
    def get_requirements_dict(self) -> dict:
        """
        Get requirements as dictionary.
        
        Returns:
            Parsed requirements dictionary or empty dict if none
        """
        if not self.requirements:
            return {}
        
        try:
            import json
            return json.loads(self.requirements)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_requirements_dict(self, requirements_dict: dict) -> None:
        """
        Set requirements from dictionary.
        
        Args:
            requirements_dict: Dictionary to store as requirements
        """
        if requirements_dict:
            import json
            self.requirements = json.dumps(requirements_dict)
        else:
            self.requirements = None
    
    def get_metadata_dict(self) -> dict:
        """
        Get metadata as dictionary.
        
        Returns:
            Parsed metadata dictionary or empty dict if none
        """
        if not self.achievement_metadata:
            return {}
        
        try:
            import json
            return json.loads(self.achievement_metadata)
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
            self.achievement_metadata = json.dumps(metadata_dict)
        else:
            self.achievement_metadata = None


class UserAchievement(BaseModel):
    """
    User achievement model for tracking earned achievements.
    
    Records when users earn achievements, tracks progress toward
    multi-step achievements, and manages achievement rewards.
    """
    
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the user"
    )
    
    achievement_id = Column(
        String(36),
        ForeignKey("achievements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the achievement"
    )
    
    earned_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="Timestamp when achievement was earned"
    )
    
    progress = Column(
        Float,
        default=0.0,
        nullable=False,
        doc="Progress toward earning achievement (0.0-100.0)"
    )
    
    is_completed = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the achievement has been fully earned"
    )
    
    current_value = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Current value for progress tracking (e.g., current streak)"
    )
    
    target_value = Column(
        Integer,
        nullable=True,
        doc="Target value needed to complete achievement"
    )
    
    xp_awarded = Column(
        Integer,
        default=0,
        nullable=False,
        doc="XP actually awarded for this achievement"
    )
    
    hearts_awarded = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Hearts actually awarded for this achievement"
    )
    
    # Additional context
    course_id = Column(
        String(36),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        doc="Course context where achievement was earned (if applicable)"
    )
    
    # Ensure unique achievement per user
    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),
        CheckConstraint(progress >= 0.0, name='check_progress_min'),
        CheckConstraint(progress <= 100.0, name='check_progress_max'),
        CheckConstraint(current_value >= 0, name='check_current_value_non_negative'),
        CheckConstraint(target_value >= 0, name='check_target_value_non_negative'),
        CheckConstraint(xp_awarded >= 0, name='check_xp_awarded_non_negative'),
        CheckConstraint(hearts_awarded >= 0, name='check_hearts_awarded_non_negative'),
    )
    
    @validates('progress')
    def validate_progress(self, key, value):
        """Validate progress is between 0 and 100."""
        if not 0.0 <= value <= 100.0:
            raise ValueError("Progress must be between 0.0 and 100.0")
        return value
    
    def update_progress(self, current_value: int, target_value: int = None) -> float:
        """
        Update achievement progress.
        
        Args:
            current_value: Current progress value
            target_value: Target value (optional, uses existing if not provided)
            
        Returns:
            New progress percentage
        """
        if current_value < 0:
            raise ValueError("Current value must be non-negative")
        
        self.current_value = current_value
        
        if target_value is not None:
            if target_value <= 0:
                raise ValueError("Target value must be positive")
            self.target_value = target_value
        
        if self.target_value and self.target_value > 0:
            self.progress = min(100.0, (self.current_value / self.target_value) * 100.0)
        else:
            self.progress = 0.0
        
        # Check if achievement is completed
        if self.progress >= 100.0 and not self.is_completed:
            self.complete_achievement()
        
        return self.progress
    
    def complete_achievement(self) -> None:
        """Mark achievement as completed and set earned timestamp."""
        self.is_completed = True
        self.progress = 100.0
        self.earned_at = datetime.utcnow()
    
    def award_rewards(self, xp_amount: int, hearts_amount: int) -> None:
        """
        Award XP and hearts for this achievement.
        
        Args:
            xp_amount: XP to award
            hearts_amount: Hearts to award
        """
        if xp_amount < 0:
            raise ValueError("XP amount must be non-negative")
        if hearts_amount < 0:
            raise ValueError("Hearts amount must be non-negative")
        
        self.xp_awarded = xp_amount
        self.hearts_awarded = hearts_amount
    
    @classmethod
    def get_or_create_progress(cls, session, user_id: str, achievement_id: str,
                              course_id: str = None) -> 'UserAchievement':
        """
        Get existing or create new achievement progress.
        
        Args:
            session: SQLAlchemy session
            user_id: ID of the user
            achievement_id: ID of the achievement
            course_id: ID of the course (optional)
            
        Returns:
            UserAchievement instance
        """
        existing = session.query(cls).filter(
            cls.user_id == user_id,
            cls.achievement_id == achievement_id
        ).first()
        
        if existing:
            return existing
        
        new_progress = cls(
            user_id=user_id,
            achievement_id=achievement_id,
            course_id=course_id
        )
        session.add(new_progress)
        return new_progress