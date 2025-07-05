"""
Schema Integration Tests

Comprehensive integration tests for the complete database schema, verifying that
all models work together correctly and foreign key relationships are properly validated.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, event, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models.user import User, OAuthProvider
from app.models.course import Language, Course, Section, Unit, Lesson, LessonPrerequisite
from app.models.exercise import ExerciseType, Exercise, ExerciseOption, LessonExercise, AudioFile
from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction, ProgressStatus, InteractionType
from app.models.gamification import UserDailyXP, UserHeartsLog, Achievement, UserAchievement, AchievementType, HeartActionType
from app.models.audit import UserActivityLog, SystemAuditLog, ActionType, SystemActionType


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session for integration tests."""
    engine = create_engine("sqlite:///:memory:")
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_language(db_session):
    """Create a sample language for testing."""
    language = Language(
        code="en",
        name="English",
        native_name="English",
        flag_url="/flags/en.svg"
    )
    db_session.add(language)
    db_session.commit()
    db_session.refresh(language)
    return language


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        daily_xp_goal=50
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_exercise_type(db_session):
    """Create a sample exercise type for testing."""
    exercise_type = ExerciseType(
        name="translation",
        display_name="Translation",
        description="Translate text from one language to another",
        xp_reward=10
    )
    db_session.add(exercise_type)
    db_session.commit()
    db_session.refresh(exercise_type)
    return exercise_type


class TestCompleteSchemaIntegration:
    """Test complete schema integration scenarios."""
    
    def test_complete_learning_flow(self, db_session, sample_user, sample_language):
        """Test a complete learning flow from course creation to completion."""
        
        # Create language pair
        spanish = Language(
            code="es",
            name="Spanish",
            native_name="Español",
            flag_url="/flags/es.svg"
        )
        db_session.add(spanish)
        db_session.commit()
        
        # Create course
        course = Course(
            from_language_id=str(sample_language.id),
            to_language_id=str(spanish.id),
            name="Spanish for English speakers",
            difficulty_level="beginner"
        )
        db_session.add(course)
        db_session.commit()
        
        # Create section
        section = Section(
            course_id=str(course.id),
            name="Basic 1",
            description="Basic Spanish fundamentals",
            sort_order=1
        )
        db_session.add(section)
        db_session.commit()
        
        # Create unit
        unit = Unit(
            section_id=str(section.id),
            name="Greetings",
            description="Learn basic greetings",
            sort_order=1,
            color="#FF5722"
        )
        db_session.add(unit)
        db_session.commit()
        
        # Create lesson
        lesson = Lesson(
            unit_id=str(unit.id),
            name="Hello and Goodbye",
            description="Basic greeting phrases",
            sort_order=1,
            estimated_minutes=5,
            xp_reward=20
        )
        db_session.add(lesson)
        db_session.commit()
        
        # Create exercise type
        exercise_type = ExerciseType(
            name="translation",
            display_name="Translation",
            description="Translate text",
            xp_reward=10
        )
        db_session.add(exercise_type)
        db_session.commit()
        
        # Create exercise
        exercise = Exercise(
            exercise_type_id=str(exercise_type.id),
            prompt="Translate: Hello",
            correct_answer="Hola",
            difficulty="beginner",
            xp_reward=10
        )
        db_session.add(exercise)
        db_session.commit()
        
        # Link exercise to lesson
        lesson_exercise = LessonExercise(
            lesson_id=str(lesson.id),
            exercise_id=str(exercise.id),
            order_index=1,
            is_required=True
        )
        db_session.add(lesson_exercise)
        db_session.commit()
        
        # User enrolls in course
        user_course = UserCourse(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            total_xp=0,
            current_streak=0,
            current_hearts=5,
            max_hearts=5
        )
        db_session.add(user_course)
        db_session.commit()
        
        # User starts lesson
        lesson_progress = UserLessonProgress(
            user_id=str(sample_user.id),
            lesson_id=str(lesson.id),
            status=ProgressStatus.IN_PROGRESS.value,
            attempts=1
        )
        db_session.add(lesson_progress)
        db_session.commit()
        
        # User attempts exercise
        exercise_interaction = UserExerciseInteraction(
            user_id=str(sample_user.id),
            exercise_id=str(exercise.id),
            lesson_id=str(lesson.id),
            interaction_type=InteractionType.ATTEMPT.value,
            user_answer="Hola",
            is_correct=True,
            time_taken=15,
            xp_earned=10
        )
        db_session.add(exercise_interaction)
        db_session.commit()
        
        # User completes lesson
        lesson_progress.complete_lesson(100.0, 20, 60)
        user_course.add_xp(20)
        db_session.commit()
        
        # Track daily XP
        daily_xp = UserDailyXP(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            date=date.today(),
            xp_earned=20,
            daily_goal=50,
            lessons_completed=1
        )
        db_session.add(daily_xp)
        db_session.commit()
        
        # Log user activity
        activity_log = UserActivityLog(
            user_id=str(sample_user.id),
            action_type=ActionType.LESSON_COMPLETE.value,
            description="Completed lesson: Hello and Goodbye",
            course_id=str(course.id),
            lesson_id=str(lesson.id),
            success=True
        )
        db_session.add(activity_log)
        db_session.commit()
        
        # Verify the complete flow
        db_session.refresh(user_course)
        db_session.refresh(lesson_progress)
        
        assert user_course.total_xp == 20
        assert lesson_progress.status == ProgressStatus.COMPLETED.value
        assert lesson_progress.best_score == 100.0
        assert daily_xp.xp_earned == 20
        assert daily_xp.lessons_completed == 1
        
        # Verify relationships work
        assert course.from_language.code == "en"
        assert course.to_language.code == "es"
        assert section.course == course
        assert unit.section == section
        assert lesson.unit == unit
        assert exercise.exercise_type == exercise_type
    
    def test_foreign_key_constraints(self, db_session, sample_user, sample_language):
        """Test that foreign key constraints are properly enforced."""
        
        # Test invalid user reference
        with pytest.raises(IntegrityError):
            user_course = UserCourse(
                user_id=str(uuid.uuid4()),  # Non-existent user
                course_id=str(uuid.uuid4()),  # Non-existent course
                total_xp=0
            )
            db_session.add(user_course)
            db_session.commit()
        
        db_session.rollback()
        
        # Test cascade deletion
        spanish = Language(code="es", name="Spanish")
        db_session.add(spanish)
        db_session.commit()
        
        course = Course(
            from_language_id=str(sample_language.id),
            to_language_id=str(spanish.id),
            name="Test Course"
        )
        db_session.add(course)
        db_session.commit()
        
        user_course = UserCourse(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            total_xp=0
        )
        db_session.add(user_course)
        db_session.commit()
        
        # Delete course - should cascade to user_course
        db_session.delete(course)
        db_session.commit()
        
        # Verify user_course was deleted due to cascade
        remaining_user_courses = db_session.query(UserCourse).filter(
            UserCourse.course_id == str(course.id)
        ).all()
        assert len(remaining_user_courses) == 0
    
    def test_gamification_integration(self, db_session, sample_user):
        """Test gamification system integration."""
        
        # Create a course for the hearts log test
        language = Language(code="en", name="English")
        db_session.add(language)
        db_session.commit()
        
        spanish = Language(code="es", name="Spanish")
        db_session.add(spanish)
        db_session.commit()
        
        course = Course(
            from_language_id=str(language.id),
            to_language_id=str(spanish.id),
            name="Test Course"
        )
        db_session.add(course)
        db_session.commit()
        
        # Create achievement
        achievement = Achievement(
            name="first_lesson",
            display_name="First Steps",
            description="Complete your first lesson",
            achievement_type=AchievementType.LESSON_COMPLETION.value,
            xp_reward=50,
            hearts_reward=1,
            requirements='{"lessons_completed": 1}'
        )
        db_session.add(achievement)
        db_session.commit()
        
        # User starts working toward achievement
        user_achievement = UserAchievement(
            user_id=str(sample_user.id),
            achievement_id=str(achievement.id),
            progress=0.0,
            current_value=0,
            target_value=1
        )
        db_session.add(user_achievement)
        db_session.commit()
        
        # User completes a lesson (trigger achievement)
        user_achievement.update_progress(1, 1)
        db_session.commit()
        
        # User loses a heart
        hearts_log = UserHeartsLog.log_heart_loss(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            hearts_before=5,
            reason="Incorrect answer"
        )
        db_session.add(hearts_log)
        db_session.commit()
        
        # Track daily XP
        daily_xp = UserDailyXP(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            date=date.today(),
            xp_earned=70,  # Lesson XP + achievement XP
            daily_goal=50,
            lessons_completed=1
        )
        daily_xp.add_xp(70)
        db_session.add(daily_xp)
        db_session.commit()
        
        # Verify gamification integration
        db_session.refresh(user_achievement)
        assert user_achievement.is_completed
        assert user_achievement.progress == 100.0
        assert daily_xp.goal_met
        assert hearts_log.hearts_after == 4
        assert hearts_log.hearts_changed == -1
    
    def test_audit_logging_integration(self, db_session, sample_user):
        """Test audit logging integration with user actions."""
        
        # User activity log
        user_activity = UserActivityLog(
            user_id=str(sample_user.id),
            action_type=ActionType.LOGIN.value,
            description="User logged in",
            ip_address="192.168.1.1",
            success=True
        )
        db_session.add(user_activity)
        db_session.commit()
        
        # System audit log
        system_audit = SystemAuditLog(
            admin_user_id=str(sample_user.id),
            action_type=SystemActionType.USER_UPDATE.value,
            resource_type="user",
            resource_id=str(sample_user.id),
            description="Updated user profile",
            success=True
        )
        db_session.add(system_audit)
        db_session.commit()
        
        # Verify audit logs are properly linked
        assert user_activity.user_id == str(sample_user.id)
        assert system_audit.admin_user_id == str(sample_user.id)
        assert system_audit.resource_id == str(sample_user.id)
    
    def test_exercise_system_integration(self, db_session, sample_exercise_type):
        """Test exercise system integration with lessons and user interactions."""
        
        # Create exercise
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="What is 'hello' in Spanish?",
            correct_answer="hola",
            difficulty="beginner",
            xp_reward=10
        )
        db_session.add(exercise)
        db_session.commit()
        
        # Create exercise options for multiple choice
        options = [
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="hola",
                is_correct=True,
                display_order=1
            ),
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="adiós",
                is_correct=False,
                display_order=2
            ),
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="gracias",
                is_correct=False,
                display_order=3
            )
        ]
        
        for option in options:
            db_session.add(option)
        db_session.commit()
        
        # Verify relationships
        db_session.refresh(exercise)
        assert len(exercise.options) == 3
        assert exercise.exercise_type == sample_exercise_type
        
        # Test correct option identification
        correct_options = [opt for opt in exercise.options if opt.is_correct]
        assert len(correct_options) == 1
        assert correct_options[0].option_text == "hola"
    
    def test_prerequisite_system(self, db_session):
        """Test lesson prerequisite system."""
        
        # Create basic structure
        language = Language(code="en", name="English")
        db_session.add(language)
        db_session.commit()
        
        spanish = Language(code="es", name="Spanish")
        db_session.add(spanish)
        db_session.commit()
        
        course = Course(
            from_language_id=str(language.id),
            to_language_id=str(spanish.id),
            name="Spanish Course"
        )
        db_session.add(course)
        db_session.commit()
        
        section = Section(
            course_id=str(course.id),
            name="Basic",
            sort_order=1
        )
        db_session.add(section)
        db_session.commit()
        
        unit = Unit(
            section_id=str(section.id),
            name="Greetings",
            sort_order=1
        )
        db_session.add(unit)
        db_session.commit()
        
        # Create lessons with prerequisites
        lesson1 = Lesson(
            unit_id=str(unit.id),
            name="Lesson 1",
            sort_order=1
        )
        db_session.add(lesson1)
        db_session.commit()
        
        lesson2 = Lesson(
            unit_id=str(unit.id),
            name="Lesson 2",
            sort_order=2
        )
        db_session.add(lesson2)
        db_session.commit()
        
        lesson3 = Lesson(
            unit_id=str(unit.id),
            name="Lesson 3",
            sort_order=3
        )
        db_session.add(lesson3)
        db_session.commit()
        
        # Set up prerequisites: lesson2 requires lesson1, lesson3 requires lesson2
        prereq1 = LessonPrerequisite(
            lesson_id=str(lesson2.id),
            prerequisite_lesson_id=str(lesson1.id)
        )
        db_session.add(prereq1)
        
        prereq2 = LessonPrerequisite(
            lesson_id=str(lesson3.id),
            prerequisite_lesson_id=str(lesson2.id)
        )
        db_session.add(prereq2)
        db_session.commit()
        
        # Test self-reference prevention
        with pytest.raises(IntegrityError):
            self_prereq = LessonPrerequisite(
                lesson_id=str(lesson1.id),
                prerequisite_lesson_id=str(lesson1.id)
            )
            db_session.add(self_prereq)
            db_session.commit()
        
        db_session.rollback()
        
        # Verify prerequisites are properly set
        assert len(lesson2.prerequisites) == 1
        assert lesson2.prerequisites[0].prerequisite_lesson_id == str(lesson1.id)
        assert len(lesson3.prerequisites) == 1
        assert lesson3.prerequisites[0].prerequisite_lesson_id == str(lesson2.id)
    
    def test_user_oauth_integration(self, db_session, sample_user):
        """Test OAuth provider integration with users."""
        
        # Create OAuth providers
        google_oauth = OAuthProvider(
            user_id=str(sample_user.id),
            provider="google",
            provider_user_id="google_123456"
        )
        db_session.add(google_oauth)
        db_session.commit()
        
        # Verify relationship
        db_session.refresh(sample_user)
        assert len(sample_user.oauth_providers) == 1
        assert sample_user.oauth_providers[0].provider == "google"
        
        # Test unique constraint
        with pytest.raises(IntegrityError):
            duplicate_oauth = OAuthProvider(
                user_id=str(sample_user.id),
                provider="google",  # Same provider + same provider_user_id should fail
                provider_user_id="google_123456"  # Same as above
            )
            db_session.add(duplicate_oauth)
            db_session.commit()
    
    def test_data_consistency_and_validation(self, db_session):
        """Test data consistency and validation across the schema."""
        
        # Test email uniqueness
        user1 = User(
            email="unique@example.com",
            password_hash="hash1",
            name="User 1"
        )
        db_session.add(user1)
        db_session.commit()
        
        with pytest.raises(IntegrityError):
            user2 = User(
                email="unique@example.com",  # Duplicate email
                password_hash="hash2",
                name="User 2"
            )
            db_session.add(user2)
            db_session.commit()
        
        db_session.rollback()
        
        # Test language code uniqueness
        lang1 = Language(code="fr", name="French")
        db_session.add(lang1)
        db_session.commit()
        
        with pytest.raises(IntegrityError):
            lang2 = Language(code="fr", name="Français")  # Duplicate code
            db_session.add(lang2)
            db_session.commit()
        
        db_session.rollback()
        
        # Test exercise type name uniqueness
        type1 = ExerciseType(name="listening", display_name="Listening")
        db_session.add(type1)
        db_session.commit()
        
        with pytest.raises(IntegrityError):
            type2 = ExerciseType(name="listening", display_name="Audio")  # Duplicate name
            db_session.add(type2)
            db_session.commit()
    
    def test_complex_query_scenarios(self, db_session, sample_user, sample_language):
        """Test complex query scenarios across multiple tables."""
        
        # Set up test data
        spanish = Language(code="es", name="Spanish")
        db_session.add(spanish)
        db_session.commit()
        
        course = Course(
            from_language_id=str(sample_language.id),
            to_language_id=str(spanish.id),
            name="Spanish Course"
        )
        db_session.add(course)
        db_session.commit()
        
        user_course = UserCourse(
            user_id=str(sample_user.id),
            course_id=str(course.id),
            total_xp=100,
            current_streak=5
        )
        db_session.add(user_course)
        db_session.commit()
        
        # Create multiple daily XP records
        for days_back in range(7):
            daily_xp = UserDailyXP(
                user_id=str(sample_user.id),
                course_id=str(course.id),
                date=date.today() - timedelta(days=days_back),
                xp_earned=20,
                daily_goal=50,
                goal_met=True
            )
            db_session.add(daily_xp)
        db_session.commit()
        
        # Query: Get user's weekly XP total
        weekly_xp = db_session.query(
            func.sum(UserDailyXP.xp_earned)
        ).filter(
            UserDailyXP.user_id == str(sample_user.id),
            UserDailyXP.course_id == str(course.id)
        ).scalar()
        
        assert weekly_xp == 140  # 7 days * 20 XP
        
        # Query: Get user's streak information with course details
        user_with_course = db_session.query(
            UserCourse, Course, Language
        ).join(
            Course, UserCourse.course_id == Course.id
        ).join(
            Language, Course.to_language_id == Language.id
        ).filter(
            UserCourse.user_id == str(sample_user.id)
        ).first()
        
        assert user_with_course is not None
        user_course_data, course_data, language_data = user_with_course
        assert user_course_data.current_streak == 5
        assert course_data.name == "Spanish Course"
        assert language_data.code == "es"


if __name__ == "__main__":
    pytest.main([__file__])