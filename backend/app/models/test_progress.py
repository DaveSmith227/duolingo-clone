"""
Unit tests for progress and gamification models.

Comprehensive test coverage for UserCourse, UserLessonProgress, UserExerciseInteraction,
UserDailyXP, UserHeartsLog, Achievement, and UserAchievement models with validation
and business logic testing.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta, date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models.progress import (
    UserCourse, UserLessonProgress, UserExerciseInteraction,
    ProgressStatus, InteractionType
)
from app.models.gamification import (
    UserDailyXP, UserHeartsLog, Achievement, UserAchievement,
    AchievementType, HeartActionType
)
# Import all models so foreign keys can be resolved
from app.models.user import User, OAuthProvider
from app.models.course import Language, Course, Section, Unit, Lesson, LessonPrerequisite
from app.models.exercise import ExerciseType, Exercise, ExerciseOption, LessonExercise, AudioFile


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


# Test UserCourse Model
class TestUserCourse:
    """Test cases for UserCourse model."""
    
    def test_create_user_course(self, db_session):
        """Test creating a user course enrollment."""
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            total_xp=100,
            current_streak=5,
            longest_streak=10,
            current_hearts=3,
            max_hearts=5
        )
        
        db_session.add(user_course)
        db_session.commit()
        db_session.refresh(user_course)
        
        assert user_course.id is not None
        assert user_course.total_xp == 100
        assert user_course.current_streak == 5
        assert user_course.longest_streak == 10
        assert user_course.current_hearts == 3
        assert user_course.max_hearts == 5
        assert user_course.completion_percentage == 0.0
    
    def test_user_course_validation(self, db_session):
        """Test UserCourse validation constraints."""
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4())
        )
        
        # Test negative XP validation
        with pytest.raises(ValueError, match="Current hearts cannot be negative"):
            user_course.current_hearts = -1
        
        # Test hearts exceeding max validation
        user_course.max_hearts = 5
        with pytest.raises(ValueError, match="Current hearts cannot exceed max hearts"):
            user_course.current_hearts = 6
        
        # Test invalid completion percentage
        with pytest.raises(ValueError, match="Completion percentage must be between 0.0 and 100.0"):
            user_course.completion_percentage = 150.0
    
    def test_add_xp(self, db_session):
        """Test adding XP to user course."""
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            total_xp=50
        )
        
        # Add XP
        new_total = user_course.add_xp(25)
        assert new_total == 75
        assert user_course.total_xp == 75
        
        # Test negative XP validation
        with pytest.raises(ValueError, match="XP amount must be non-negative"):
            user_course.add_xp(-10)
    
    def test_lose_heart(self, db_session):
        """Test losing hearts."""
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            current_hearts=3,
            max_hearts=5
        )
        
        # Lose a heart
        remaining = user_course.lose_heart()
        assert remaining == 2
        assert user_course.current_hearts == 2
        
        # Lose all hearts
        user_course.lose_heart()
        user_course.lose_heart()
        
        # Try to lose when no hearts left
        with pytest.raises(ValueError, match="No hearts available to lose"):
            user_course.lose_heart()
    
    def test_heart_refill_logic(self, db_session):
        """Test heart refill mechanics."""
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            current_hearts=2,
            max_hearts=5,
            last_heart_refill=datetime.utcnow() - timedelta(hours=5)
        )
        
        # Should be able to refill after 4+ hours
        assert user_course.can_refill_hearts() is True
        
        hearts = user_course.refill_hearts()
        assert hearts == 5
        assert user_course.current_hearts == 5
        
        # Should not be able to refill immediately after
        assert user_course.can_refill_hearts() is False
        
        with pytest.raises(ValueError, match="Hearts cannot be refilled yet"):
            user_course.refill_hearts()
    
    def test_streak_update(self, db_session):
        """Test streak calculation logic."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        user_course = UserCourse(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            current_streak=5,
            longest_streak=8,
            last_activity_date=yesterday
        )
        
        # Consecutive day should increment streak
        today = datetime.utcnow()
        new_streak = user_course.update_streak(today)
        assert new_streak == 6
        assert user_course.current_streak == 6
        
        # Same day should not change streak
        same_day_streak = user_course.update_streak(today)
        assert same_day_streak == 6
        
        # Update longest streak if needed
        user_course.current_streak = 9  # Set to one less than target
        user_course.longest_streak = 8  # Reset to previous value
        tomorrow = datetime.utcnow() + timedelta(days=1)
        user_course.update_streak(tomorrow)  # This should increment to 10
        assert user_course.longest_streak == 10
        
        # Broken streak should reset
        future_date = datetime.utcnow() + timedelta(days=3)
        broken_streak = user_course.update_streak(future_date)
        assert broken_streak == 1
        assert user_course.current_streak == 1
    
    def test_unique_enrollment_constraint(self, db_session):
        """Test unique user-course enrollment constraint."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        
        # Create first enrollment
        user_course1 = UserCourse(user_id=user_id, course_id=course_id)
        db_session.add(user_course1)
        db_session.commit()
        
        # Try to create duplicate enrollment
        user_course2 = UserCourse(user_id=user_id, course_id=course_id)
        db_session.add(user_course2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


# Test UserLessonProgress Model
class TestUserLessonProgress:
    """Test cases for UserLessonProgress model."""
    
    def test_create_lesson_progress(self, db_session):
        """Test creating lesson progress."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            status=ProgressStatus.IN_PROGRESS.value,
            attempts=2,
            best_score=85.5,
            last_score=75.0
        )
        
        db_session.add(progress)
        db_session.commit()
        db_session.refresh(progress)
        
        assert progress.id is not None
        assert progress.status == ProgressStatus.IN_PROGRESS.value
        assert progress.attempts == 2
        assert progress.best_score == 85.5
        assert progress.last_score == 75.0
    
    def test_lesson_progress_validation(self, db_session):
        """Test lesson progress validation."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4())
        )
        
        # Test invalid status
        with pytest.raises(ValueError, match="Invalid status"):
            progress.status = "invalid_status"
        
        # Test invalid score range
        with pytest.raises(ValueError, match="best_score must be between 0.0 and 100.0"):
            progress.best_score = 150.0
        
        with pytest.raises(ValueError, match="last_score must be between 0.0 and 100.0"):
            progress.last_score = -10.0
    
    def test_start_attempt(self, db_session):
        """Test starting a lesson attempt."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            status=ProgressStatus.NOT_STARTED.value,
            attempts=0
        )
        
        attempt_count = progress.start_attempt()
        assert attempt_count == 1
        assert progress.attempts == 1
        assert progress.status == ProgressStatus.IN_PROGRESS.value
        assert progress.last_attempted_at is not None
    
    def test_complete_lesson(self, db_session):
        """Test completing a lesson."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            status=ProgressStatus.IN_PROGRESS.value,
            best_score=80.0
        )
        
        # Complete with higher score
        progress.complete_lesson(score=90.0, xp_gained=50, time_spent=300)
        
        assert progress.status == ProgressStatus.COMPLETED.value
        assert progress.last_score == 90.0
        assert progress.best_score == 90.0  # Updated to higher score
        assert progress.xp_earned == 50
        assert progress.time_spent == 300
        assert progress.first_completed_at is not None
        
        # Complete again with lower score
        progress.complete_lesson(score=75.0, xp_gained=25, time_spent=200)
        
        assert progress.last_score == 75.0
        assert progress.best_score == 90.0  # Should remain the best
        assert progress.xp_earned == 75  # Cumulative
        assert progress.time_spent == 500  # Cumulative
    
    def test_fail_lesson(self, db_session):
        """Test failing a lesson."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            status=ProgressStatus.IN_PROGRESS.value
        )
        
        progress.fail_lesson(score=45.0, time_spent=180)
        
        assert progress.status == ProgressStatus.FAILED.value
        assert progress.last_score == 45.0
        assert progress.time_spent == 180
    
    def test_unlock_lesson(self, db_session):
        """Test unlocking a lesson."""
        progress = UserLessonProgress(
            user_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            status=ProgressStatus.LOCKED.value,
            is_locked=True
        )
        
        progress.unlock_lesson()
        
        assert progress.is_locked is False
        assert progress.status == ProgressStatus.NOT_STARTED.value


# Test UserExerciseInteraction Model
class TestUserExerciseInteraction:
    """Test cases for UserExerciseInteraction model."""
    
    def test_create_exercise_interaction(self, db_session):
        """Test creating exercise interaction."""
        interaction = UserExerciseInteraction(
            user_id=str(uuid.uuid4()),
            exercise_id=str(uuid.uuid4()),
            lesson_id=str(uuid.uuid4()),
            interaction_type=InteractionType.ATTEMPT.value,
            user_answer="Hello",
            is_correct=True,
            time_taken=45,
            xp_earned=10
        )
        
        db_session.add(interaction)
        db_session.commit()
        db_session.refresh(interaction)
        
        assert interaction.id is not None
        assert interaction.interaction_type == InteractionType.ATTEMPT.value
        assert interaction.user_answer == "Hello"
        assert interaction.is_correct is True
        assert interaction.time_taken == 45
        assert interaction.xp_earned == 10
    
    def test_exercise_interaction_validation(self, db_session):
        """Test exercise interaction validation."""
        interaction = UserExerciseInteraction(
            user_id=str(uuid.uuid4()),
            exercise_id=str(uuid.uuid4())
        )
        
        # Test invalid interaction type
        with pytest.raises(ValueError, match="Invalid interaction type"):
            interaction.interaction_type = "invalid_type"
        
        # Test invalid time taken
        with pytest.raises(ValueError, match="Time taken must be between 0 and 3600 seconds"):
            interaction.time_taken = -10
        
        with pytest.raises(ValueError, match="Time taken must be between 0 and 3600 seconds"):
            interaction.time_taken = 4000
    
    def test_metadata_handling(self, db_session):
        """Test metadata handling for exercise interactions."""
        interaction = UserExerciseInteraction(
            user_id=str(uuid.uuid4()),
            exercise_id=str(uuid.uuid4()),
            interaction_type=InteractionType.ATTEMPT.value
        )
        
        # Set metadata
        metadata = {"difficulty": "beginner", "hints_available": 3}
        interaction.set_metadata_dict(metadata)
        
        # Get metadata
        retrieved_metadata = interaction.get_metadata_dict()
        assert retrieved_metadata == metadata
    
    def test_log_attempt_factory(self, db_session):
        """Test log_attempt factory method."""
        user_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        lesson_id = str(uuid.uuid4())
        
        interaction = UserExerciseInteraction.log_attempt(
            user_id=user_id,
            exercise_id=exercise_id,
            user_answer="Hola",
            is_correct=True,
            time_taken=30,
            lesson_id=lesson_id,
            xp_earned=15,
            hints_used=1,
            attempt_number=2,
            metadata={"confidence": 0.8}
        )
        
        assert interaction.user_id == user_id
        assert interaction.exercise_id == exercise_id
        assert interaction.lesson_id == lesson_id
        assert interaction.interaction_type == InteractionType.ATTEMPT.value
        assert interaction.user_answer == "Hola"
        assert interaction.is_correct is True
        assert interaction.time_taken == 30
        assert interaction.xp_earned == 15
        assert interaction.hints_used == 1
        assert interaction.attempt_number == 2
        assert interaction.get_metadata_dict() == {"confidence": 0.8}
    
    def test_log_hint_used_factory(self, db_session):
        """Test log_hint_used factory method."""
        user_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        interaction = UserExerciseInteraction.log_hint_used(
            user_id=user_id,
            exercise_id=exercise_id
        )
        
        assert interaction.interaction_type == InteractionType.HINT_USED.value
        assert interaction.hints_used == 1
    
    def test_log_skip_factory(self, db_session):
        """Test log_skip factory method."""
        user_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        interaction = UserExerciseInteraction.log_skip(
            user_id=user_id,
            exercise_id=exercise_id
        )
        
        assert interaction.interaction_type == InteractionType.SKIP.value


# Test UserDailyXP Model
class TestUserDailyXP:
    """Test cases for UserDailyXP model."""
    
    def test_create_daily_xp(self, db_session):
        """Test creating daily XP record."""
        today = date.today()
        daily_xp = UserDailyXP(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            date=today,
            xp_earned=75,
            daily_goal=50,
            goal_met=True
        )
        
        db_session.add(daily_xp)
        db_session.commit()
        db_session.refresh(daily_xp)
        
        assert daily_xp.id is not None
        assert daily_xp.date == today
        assert daily_xp.xp_earned == 75
        assert daily_xp.daily_goal == 50
        assert daily_xp.goal_met is True
    
    def test_daily_xp_validation(self, db_session):
        """Test daily XP validation."""
        daily_xp = UserDailyXP(
            user_id=str(uuid.uuid4()),
            date=date.today()
        )
        
        # Test invalid daily goal
        with pytest.raises(ValueError, match="Daily goal must be between 1 and 1000 XP"):
            daily_xp.daily_goal = 0
        
        with pytest.raises(ValueError, match="Daily goal must be between 1 and 1000 XP"):
            daily_xp.daily_goal = 1500
    
    def test_add_xp_and_goal_check(self, db_session):
        """Test adding XP and goal completion check."""
        daily_xp = UserDailyXP(
            user_id=str(uuid.uuid4()),
            date=date.today(),
            xp_earned=30,
            daily_goal=50
        )
        
        # Add XP but don't meet goal
        new_total = daily_xp.add_xp(15)
        assert new_total == 45
        assert daily_xp.goal_met is False
        
        # Add more XP to meet goal
        daily_xp.add_xp(10)
        assert daily_xp.xp_earned == 55
        assert daily_xp.goal_met is True
    
    def test_increment_counters(self, db_session):
        """Test incrementing lesson and exercise counters."""
        daily_xp = UserDailyXP(
            user_id=str(uuid.uuid4()),
            date=date.today()
        )
        
        # Increment lessons
        lessons = daily_xp.increment_lessons()
        assert lessons == 1
        assert daily_xp.lessons_completed == 1
        
        # Increment exercises
        exercises = daily_xp.increment_exercises()
        assert exercises == 1
        assert daily_xp.exercises_completed == 1
    
    def test_add_time(self, db_session):
        """Test adding time spent."""
        daily_xp = UserDailyXP(
            user_id=str(uuid.uuid4()),
            date=date.today(),
            time_spent=300
        )
        
        new_total = daily_xp.add_time(180)
        assert new_total == 480
        assert daily_xp.time_spent == 480
        
        # Test negative time validation
        with pytest.raises(ValueError, match="Time must be non-negative"):
            daily_xp.add_time(-50)
    
    def test_get_or_create_for_date(self, db_session):
        """Test get_or_create_for_date class method."""
        user_id = str(uuid.uuid4())
        today = date.today()
        
        # Create new record
        daily_xp1 = UserDailyXP.get_or_create_for_date(
            db_session, user_id, today, daily_goal=75
        )
        db_session.commit()
        
        assert daily_xp1.user_id == user_id
        assert daily_xp1.date == today
        assert daily_xp1.daily_goal == 75
        
        # Get existing record
        daily_xp2 = UserDailyXP.get_or_create_for_date(
            db_session, user_id, today
        )
        
        assert daily_xp1.id == daily_xp2.id  # Same record
    
    def test_calculate_streak(self, db_session):
        """Test streak calculation."""
        user_id = str(uuid.uuid4())
        
        # Create daily XP records for streak
        today = date.today()
        for days_back in range(5):
            record_date = today - timedelta(days=days_back)
            daily_xp = UserDailyXP(
                user_id=user_id,
                date=record_date,
                xp_earned=50,
                daily_goal=30,
                goal_met=True
            )
            db_session.add(daily_xp)
        
        db_session.commit()
        
        # Calculate streak
        streak = UserDailyXP.calculate_streak(db_session, user_id)
        assert streak == 5
        
        # Break streak with missing day
        broken_day = today - timedelta(days=2)
        broken_record = db_session.query(UserDailyXP).filter(
            UserDailyXP.user_id == user_id,
            UserDailyXP.date == broken_day
        ).first()
        broken_record.goal_met = False
        db_session.commit()
        
        # Recalculate streak
        new_streak = UserDailyXP.calculate_streak(db_session, user_id)
        assert new_streak == 2  # Only today and yesterday
    
    def test_unique_user_course_date_constraint(self, db_session):
        """Test unique user-course-date constraint."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        today = date.today()
        
        # Create first record
        daily_xp1 = UserDailyXP(
            user_id=user_id,
            course_id=course_id,
            date=today
        )
        db_session.add(daily_xp1)
        db_session.commit()
        
        # Try to create duplicate
        daily_xp2 = UserDailyXP(
            user_id=user_id,
            course_id=course_id,
            date=today
        )
        db_session.add(daily_xp2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


# Test UserHeartsLog Model
class TestUserHeartsLog:
    """Test cases for UserHeartsLog model."""
    
    def test_create_hearts_log(self, db_session):
        """Test creating hearts log entry."""
        hearts_log = UserHeartsLog(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            action_type=HeartActionType.LOST.value,
            hearts_before=5,
            hearts_after=4,
            hearts_changed=-1,
            reason="Incorrect answer"
        )
        
        db_session.add(hearts_log)
        db_session.commit()
        db_session.refresh(hearts_log)
        
        assert hearts_log.id is not None
        assert hearts_log.action_type == HeartActionType.LOST.value
        assert hearts_log.hearts_before == 5
        assert hearts_log.hearts_after == 4
        assert hearts_log.hearts_changed == -1
        assert hearts_log.reason == "Incorrect answer"
    
    def test_hearts_log_validation(self, db_session):
        """Test hearts log validation."""
        hearts_log = UserHeartsLog(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            hearts_before=5,
            hearts_after=4
        )
        
        # Test invalid action type
        with pytest.raises(ValueError, match="Invalid action type"):
            hearts_log.action_type = "invalid_action"
    
    def test_log_heart_loss_factory(self, db_session):
        """Test log_heart_loss factory method."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        hearts_log = UserHeartsLog.log_heart_loss(
            user_id=user_id,
            course_id=course_id,
            hearts_before=3,
            reason="Wrong answer",
            exercise_id=exercise_id
        )
        
        assert hearts_log.user_id == user_id
        assert hearts_log.course_id == course_id
        assert hearts_log.action_type == HeartActionType.LOST.value
        assert hearts_log.hearts_before == 3
        assert hearts_log.hearts_after == 2
        assert hearts_log.hearts_changed == -1
        assert hearts_log.reason == "Wrong answer"
        assert hearts_log.exercise_id == exercise_id
    
    def test_log_heart_refill_factory(self, db_session):
        """Test log_heart_refill factory method."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        
        hearts_log = UserHeartsLog.log_heart_refill(
            user_id=user_id,
            course_id=course_id,
            hearts_before=2,
            max_hearts=5,
            reason="4-hour refill"
        )
        
        assert hearts_log.action_type == HeartActionType.REFILLED.value
        assert hearts_log.hearts_before == 2
        assert hearts_log.hearts_after == 5
        assert hearts_log.hearts_changed == 3
        assert hearts_log.reason == "4-hour refill"
    
    def test_hearts_log_metadata(self, db_session):
        """Test hearts log metadata handling."""
        hearts_log = UserHeartsLog(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            action_type=HeartActionType.LOST.value,
            hearts_before=5,
            hearts_after=4,
            hearts_changed=-1
        )
        
        # Set metadata
        metadata = {"exercise_type": "translation", "difficulty": "hard"}
        hearts_log.set_metadata_dict(metadata)
        
        # Get metadata
        retrieved_metadata = hearts_log.get_metadata_dict()
        assert retrieved_metadata == metadata


# Test Achievement Model
class TestAchievement:
    """Test cases for Achievement model."""
    
    def test_create_achievement(self, db_session):
        """Test creating an achievement."""
        achievement = Achievement(
            name="first_lesson",
            display_name="First Lesson",
            description="Complete your first lesson",
            achievement_type=AchievementType.LESSON_COMPLETION.value,
            xp_reward=25,
            hearts_reward=1,
            is_active=True
        )
        
        db_session.add(achievement)
        db_session.commit()
        db_session.refresh(achievement)
        
        assert achievement.id is not None
        assert achievement.name == "first_lesson"
        assert achievement.display_name == "First Lesson"
        assert achievement.achievement_type == AchievementType.LESSON_COMPLETION.value
        assert achievement.xp_reward == 25
        assert achievement.hearts_reward == 1
    
    def test_achievement_validation(self, db_session):
        """Test achievement validation."""
        achievement = Achievement(
            name="test_achievement",
            display_name="Test Achievement",
            description="Test description"
        )
        
        # Test invalid achievement type
        with pytest.raises(ValueError, match="Invalid achievement type"):
            achievement.achievement_type = "invalid_type"
    
    def test_achievement_requirements_handling(self, db_session):
        """Test achievement requirements handling."""
        achievement = Achievement(
            name="streak_master",
            display_name="Streak Master",
            description="Maintain a 30-day streak",
            achievement_type=AchievementType.STREAK.value
        )
        
        # Set requirements
        requirements = {"streak_days": 30, "course_specific": False}
        achievement.set_requirements_dict(requirements)
        
        # Get requirements
        retrieved_requirements = achievement.get_requirements_dict()
        assert retrieved_requirements == requirements
    
    def test_achievement_metadata_handling(self, db_session):
        """Test achievement metadata handling."""
        achievement = Achievement(
            name="speed_demon",
            display_name="Speed Demon",
            description="Complete lesson in under 2 minutes",
            achievement_type=AchievementType.SPEED_CHALLENGE.value
        )
        
        # Set metadata
        metadata = {"time_limit": 120, "minimum_score": 90}
        achievement.set_metadata_dict(metadata)
        
        # Get metadata
        retrieved_metadata = achievement.get_metadata_dict()
        assert retrieved_metadata == metadata
    
    def test_unique_achievement_name(self, db_session):
        """Test unique achievement name constraint."""
        # Create first achievement
        achievement1 = Achievement(
            name="unique_name",
            display_name="First Achievement",
            description="First description",
            achievement_type=AchievementType.XP_MILESTONE.value
        )
        db_session.add(achievement1)
        db_session.commit()
        
        # Try to create duplicate name
        achievement2 = Achievement(
            name="unique_name",
            display_name="Second Achievement",
            description="Second description",
            achievement_type=AchievementType.STREAK.value
        )
        db_session.add(achievement2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


# Test UserAchievement Model
class TestUserAchievement:
    """Test cases for UserAchievement model."""
    
    def test_create_user_achievement(self, db_session):
        """Test creating user achievement progress."""
        user_achievement = UserAchievement(
            user_id=str(uuid.uuid4()),
            achievement_id=str(uuid.uuid4()),
            progress=50.0,
            current_value=5,
            target_value=10,
            is_completed=False
        )
        
        db_session.add(user_achievement)
        db_session.commit()
        db_session.refresh(user_achievement)
        
        assert user_achievement.id is not None
        assert user_achievement.progress == 50.0
        assert user_achievement.current_value == 5
        assert user_achievement.target_value == 10
        assert user_achievement.is_completed is False
    
    def test_user_achievement_validation(self, db_session):
        """Test user achievement validation."""
        user_achievement = UserAchievement(
            user_id=str(uuid.uuid4()),
            achievement_id=str(uuid.uuid4())
        )
        
        # Test invalid progress range
        with pytest.raises(ValueError, match="Progress must be between 0.0 and 100.0"):
            user_achievement.progress = 150.0
        
        with pytest.raises(ValueError, match="Progress must be between 0.0 and 100.0"):
            user_achievement.progress = -10.0
    
    def test_update_progress(self, db_session):
        """Test updating achievement progress."""
        user_achievement = UserAchievement(
            user_id=str(uuid.uuid4()),
            achievement_id=str(uuid.uuid4()),
            current_value=0,
            target_value=10,
            is_completed=False  # Explicitly set default
        )
        
        # Update progress
        new_progress = user_achievement.update_progress(5)
        assert new_progress == 50.0
        assert user_achievement.current_value == 5
        assert user_achievement.progress == 50.0
        assert user_achievement.is_completed is False
        
        # Complete achievement
        user_achievement.update_progress(10)
        assert user_achievement.progress == 100.0
        assert user_achievement.is_completed is True
        assert user_achievement.earned_at is not None
    
    def test_complete_achievement(self, db_session):
        """Test manually completing achievement."""
        user_achievement = UserAchievement(
            user_id=str(uuid.uuid4()),
            achievement_id=str(uuid.uuid4()),
            progress=90.0
        )
        
        user_achievement.complete_achievement()
        
        assert user_achievement.is_completed is True
        assert user_achievement.progress == 100.0
        assert user_achievement.earned_at is not None
    
    def test_award_rewards(self, db_session):
        """Test awarding achievement rewards."""
        user_achievement = UserAchievement(
            user_id=str(uuid.uuid4()),
            achievement_id=str(uuid.uuid4())
        )
        
        user_achievement.award_rewards(50, 2)
        
        assert user_achievement.xp_awarded == 50
        assert user_achievement.hearts_awarded == 2
        
        # Test negative rewards validation
        with pytest.raises(ValueError, match="XP amount must be non-negative"):
            user_achievement.award_rewards(-10, 1)
        
        with pytest.raises(ValueError, match="Hearts amount must be non-negative"):
            user_achievement.award_rewards(10, -1)
    
    def test_get_or_create_progress(self, db_session):
        """Test get_or_create_progress class method."""
        user_id = str(uuid.uuid4())
        achievement_id = str(uuid.uuid4())
        
        # Create new progress
        progress1 = UserAchievement.get_or_create_progress(
            db_session, user_id, achievement_id
        )
        db_session.commit()
        
        assert progress1.user_id == user_id
        assert progress1.achievement_id == achievement_id
        
        # Get existing progress
        progress2 = UserAchievement.get_or_create_progress(
            db_session, user_id, achievement_id
        )
        
        assert progress1.id == progress2.id  # Same record
    
    def test_unique_user_achievement_constraint(self, db_session):
        """Test unique user-achievement constraint."""
        user_id = str(uuid.uuid4())
        achievement_id = str(uuid.uuid4())
        
        # Create first user achievement
        user_achievement1 = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id
        )
        db_session.add(user_achievement1)
        db_session.commit()
        
        # Try to create duplicate
        user_achievement2 = UserAchievement(
            user_id=user_id,
            achievement_id=achievement_id
        )
        db_session.add(user_achievement2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


# Integration Tests
class TestProgressGamificationIntegration:
    """Integration tests for progress and gamification models."""
    
    def test_complete_lesson_flow(self, db_session):
        """Test complete lesson completion flow with gamification."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        lesson_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        # Create user course enrollment
        user_course = UserCourse(
            user_id=user_id,
            course_id=course_id,
            current_hearts=5,
            max_hearts=5
        )
        db_session.add(user_course)
        
        # Create lesson progress
        lesson_progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id
        )
        db_session.add(lesson_progress)
        
        # Create daily XP record
        today = date.today()
        daily_xp = UserDailyXP.get_or_create_for_date(
            db_session, user_id, today, course_id=course_id
        )
        
        db_session.commit()
        
        # Start lesson
        lesson_progress.start_attempt()
        
        # Log exercise interactions
        interaction1 = UserExerciseInteraction.log_attempt(
            user_id=user_id,
            exercise_id=exercise_id,
            lesson_id=lesson_id,
            user_answer="Correct answer",
            is_correct=True,
            time_taken=30,
            xp_earned=10
        )
        db_session.add(interaction1)
        
        # Complete lesson
        lesson_progress.complete_lesson(score=85.0, xp_gained=50, time_spent=300)
        
        # Update course progress
        user_course.add_xp(50)
        user_course.update_streak()
        
        # Update daily XP
        daily_xp.add_xp(50)
        daily_xp.increment_lessons()
        daily_xp.increment_exercises()
        daily_xp.add_time(300)
        
        db_session.commit()
        
        # Verify final state
        assert lesson_progress.status == ProgressStatus.COMPLETED.value
        assert lesson_progress.best_score == 85.0
        assert user_course.total_xp == 50
        assert daily_xp.xp_earned == 50
        assert daily_xp.lessons_completed == 1
        assert daily_xp.exercises_completed == 1
    
    def test_heart_loss_and_refill_flow(self, db_session):
        """Test heart loss and refill mechanics."""
        user_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        # Create user course with hearts
        user_course = UserCourse(
            user_id=user_id,
            course_id=course_id,
            current_hearts=3,
            max_hearts=5,
            last_heart_refill=datetime.utcnow() - timedelta(hours=5)
        )
        db_session.add(user_course)
        db_session.commit()
        
        # Log incorrect answer causing heart loss
        hearts_before = user_course.current_hearts
        user_course.lose_heart()
        
        # Log the heart loss
        heart_log = UserHeartsLog.log_heart_loss(
            user_id=user_id,
            course_id=course_id,
            hearts_before=hearts_before,
            reason="Incorrect answer",
            exercise_id=exercise_id
        )
        db_session.add(heart_log)
        
        # Refill hearts after time has passed
        if user_course.can_refill_hearts():
            hearts_before_refill = user_course.current_hearts
            user_course.refill_hearts()
            
            # Log the refill
            refill_log = UserHeartsLog.log_heart_refill(
                user_id=user_id,
                course_id=course_id,
                hearts_before=hearts_before_refill,
                max_hearts=user_course.max_hearts
            )
            db_session.add(refill_log)
        
        db_session.commit()
        
        # Verify final state
        assert user_course.current_hearts == 5
        assert heart_log.action_type == HeartActionType.LOST.value
        assert refill_log.action_type == HeartActionType.REFILLED.value