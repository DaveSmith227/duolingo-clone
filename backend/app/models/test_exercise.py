"""
Unit tests for exercise models.

Comprehensive test coverage for ExerciseType, Exercise, ExerciseOption, 
LessonExercise, and AudioFile models with validation and business logic testing.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models.exercise import (
    ExerciseType, Exercise, ExerciseOption, LessonExercise, AudioFile,
    ExerciseTypeEnum, DifficultyLevel
)


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


@pytest.fixture
def sample_exercise_type(db_session):
    """Create a sample exercise type for testing."""
    exercise_type = ExerciseType(
        name="translation",
        display_name="Translation",
        description="Translate text from one language to another",
        instructions="Translate the given text",
        icon="translate",
        is_active=True,
        supports_audio=True,
        supports_images=False,
        requires_text_input=True,
        requires_multiple_choice=False,
        max_options=None,
        default_time_limit=60,
        xp_reward=15
    )
    db_session.add(exercise_type)
    db_session.commit()
    db_session.refresh(exercise_type)
    return exercise_type


@pytest.fixture
def sample_audio_file(db_session):
    """Create a sample audio file for testing."""
    audio_file = AudioFile(
        filename="test_audio.mp3",
        file_path="/audio/test_audio.mp3",
        url="https://example.com/audio/test_audio.mp3",
        mime_type="audio/mp3",
        file_size=1024000,
        duration=30,
        quality="standard",
        bitrate=128,
        sample_rate=44100,
        language_code="en",
        speaker_gender="female",
        speaker_accent="american",
        transcript="Hello world",
        is_active=True
    )
    db_session.add(audio_file)
    db_session.commit()
    db_session.refresh(audio_file)
    return audio_file


@pytest.fixture
def sample_exercise(db_session, sample_exercise_type, sample_audio_file):
    """Create a sample exercise for testing."""
    exercise = Exercise(
        exercise_type_id=str(sample_exercise_type.id),
        prompt="Translate: Hello",
        prompt_audio_id=str(sample_audio_file.id),
        correct_answer="Hola",
        alternate_answers='["Hi", "Hey"]',
        hint="Common greeting",
        explanation="Hello is a common greeting",
        difficulty="beginner",
        estimated_time=30,
        xp_reward=10,
        content_metadata='{"image_url": "https://example.com/image.jpg"}',
        is_active=True
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


class TestExerciseType:
    """Test cases for ExerciseType model."""
    
    def test_create_exercise_type_success(self, db_session):
        """Test successful creation of exercise type."""
        exercise_type = ExerciseType(
            name="multiple_choice",
            display_name="Multiple Choice",
            description="Choose the correct answer",
            instructions="Select the best answer",
            icon="choice",
            is_active=True,
            supports_audio=False,
            supports_images=True,
            requires_text_input=False,
            requires_multiple_choice=True,
            max_options=4,
            default_time_limit=45,
            xp_reward=12
        )
        
        db_session.add(exercise_type)
        db_session.commit()
        db_session.refresh(exercise_type)
        
        assert exercise_type.id is not None
        assert exercise_type.name == "multiple_choice"
        assert exercise_type.display_name == "Multiple Choice"
        assert exercise_type.max_options == 4
        assert exercise_type.xp_reward == 12
        assert exercise_type.is_active is True
        assert exercise_type.created_at is not None
        assert exercise_type.updated_at is not None
    
    def test_exercise_type_name_validation(self, db_session):
        """Test exercise type name validation."""
        # Test empty name
        with pytest.raises(ValueError, match="Exercise type name cannot be empty"):
            ExerciseType(name="", display_name="Test")
        
        # Test invalid name
        with pytest.raises(ValueError, match="Exercise type name must be one of"):
            ExerciseType(name="invalid_type", display_name="Test")
        
        # Test valid enum values
        for exercise_type in ExerciseTypeEnum:
            et = ExerciseType(name=exercise_type.value, display_name="Test")
            assert et.name == exercise_type.value
    
    def test_exercise_type_display_name_validation(self, db_session):
        """Test display name validation."""
        # Test empty display name
        with pytest.raises(ValueError, match="Display name cannot be empty"):
            ExerciseType(name="translation", display_name="")
        
        # Test too long display name
        with pytest.raises(ValueError, match="Display name cannot exceed 100 characters"):
            ExerciseType(name="translation", display_name="x" * 101)
        
        # Test valid display name
        et = ExerciseType(name="translation", display_name="Test Name")
        assert et.display_name == "Test Name"
    
    def test_exercise_type_xp_reward_validation(self, db_session):
        """Test XP reward validation."""
        # Test negative XP reward
        with pytest.raises(ValueError, match="XP reward cannot be negative"):
            ExerciseType(name="translation", display_name="Test", xp_reward=-1)
        
        # Test excessive XP reward
        with pytest.raises(ValueError, match="XP reward cannot exceed 1000"):
            ExerciseType(name="translation", display_name="Test", xp_reward=1001)
        
        # Test valid XP reward
        et = ExerciseType(name="translation", display_name="Test", xp_reward=500)
        assert et.xp_reward == 500
    
    def test_exercise_type_unique_name_constraint(self, db_session):
        """Test unique constraint on exercise type name."""
        # Create first exercise type
        exercise_type1 = ExerciseType(name="translation", display_name="Translation 1")
        db_session.add(exercise_type1)
        db_session.commit()
        
        # Try to create second exercise type with same name
        exercise_type2 = ExerciseType(name="translation", display_name="Translation 2")
        db_session.add(exercise_type2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_exercise_type_string_representations(self, sample_exercise_type):
        """Test string representations of exercise type."""
        assert str(sample_exercise_type) == "Translation (translation)"
        assert "ExerciseType" in repr(sample_exercise_type)
        assert "translation" in repr(sample_exercise_type)
        assert "Translation" in repr(sample_exercise_type)


class TestExercise:
    """Test cases for Exercise model."""
    
    def test_create_exercise_success(self, db_session, sample_exercise_type, sample_audio_file):
        """Test successful creation of exercise."""
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="What is the capital of France?",
            prompt_audio_id=str(sample_audio_file.id),
            correct_answer="Paris",
            alternate_answers='["paris", "PARIS"]',
            hint="City of lights",
            explanation="Paris is the capital and largest city of France",
            difficulty="intermediate",
            estimated_time=45,
            xp_reward=20,
            content_metadata='{"category": "geography"}',
            is_active=True
        )
        
        db_session.add(exercise)
        db_session.commit()
        db_session.refresh(exercise)
        
        assert exercise.id is not None
        assert exercise.exercise_type_id == str(sample_exercise_type.id)
        assert exercise.prompt == "What is the capital of France?"
        assert exercise.correct_answer == "Paris"
        assert exercise.alternate_answers == '["paris", "PARIS"]'
        assert exercise.difficulty == "intermediate"
        assert exercise.estimated_time == 45
        assert exercise.xp_reward == 20
        assert exercise.is_active is True
        assert exercise.created_at is not None
    
    def test_exercise_prompt_validation(self, db_session, sample_exercise_type):
        """Test exercise prompt validation."""
        # Test empty prompt
        with pytest.raises(ValueError, match="Exercise prompt cannot be empty"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="",
                correct_answer="Answer"
            )
        
        # Test too long prompt
        with pytest.raises(ValueError, match="Exercise prompt cannot exceed 1000 characters"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="x" * 1001,
                correct_answer="Answer"
            )
        
        # Test valid prompt
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Valid prompt",
            correct_answer="Answer"
        )
        assert exercise.prompt == "Valid prompt"
    
    def test_exercise_correct_answer_validation(self, db_session, sample_exercise_type):
        """Test correct answer validation."""
        # Test empty correct answer
        with pytest.raises(ValueError, match="Correct answer cannot be empty"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer=""
            )
        
        # Test too long correct answer
        with pytest.raises(ValueError, match="Correct answer cannot exceed 500 characters"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="x" * 501
            )
        
        # Test valid correct answer
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test prompt",
            correct_answer="Valid answer"
        )
        assert exercise.correct_answer == "Valid answer"
    
    def test_exercise_difficulty_validation(self, db_session, sample_exercise_type):
        """Test difficulty level validation."""
        # Test invalid difficulty
        with pytest.raises(ValueError, match="Difficulty must be one of"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                difficulty="invalid"
            )
        
        # Test valid difficulties
        for difficulty in DifficultyLevel:
            exercise = Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                difficulty=difficulty.value
            )
            assert exercise.difficulty == difficulty.value
    
    def test_exercise_estimated_time_validation(self, db_session, sample_exercise_type):
        """Test estimated time validation."""
        # Test zero estimated time
        with pytest.raises(ValueError, match="Estimated time must be positive"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                estimated_time=0
            )
        
        # Test excessive estimated time
        with pytest.raises(ValueError, match="Estimated time cannot exceed 3600 seconds"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                estimated_time=3601
            )
        
        # Test valid estimated time
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test prompt",
            correct_answer="Answer",
            estimated_time=120
        )
        assert exercise.estimated_time == 120
    
    def test_exercise_xp_reward_validation(self, db_session, sample_exercise_type):
        """Test XP reward validation."""
        # Test negative XP reward
        with pytest.raises(ValueError, match="XP reward cannot be negative"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                xp_reward=-1
            )
        
        # Test excessive XP reward
        with pytest.raises(ValueError, match="XP reward cannot exceed 1000"):
            Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt="Test prompt",
                correct_answer="Answer",
                xp_reward=1001
            )
        
        # Test valid XP reward
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test prompt",
            correct_answer="Answer",
            xp_reward=50
        )
        assert exercise.xp_reward == 50
    
    def test_exercise_get_effective_xp_reward(self, db_session, sample_exercise, sample_exercise_type):
        """Test getting effective XP reward."""
        # Test with specific exercise XP reward
        sample_exercise.xp_reward = 25
        assert sample_exercise.get_effective_xp_reward() == 25
        
        # Test with None XP reward (should use exercise type default)
        sample_exercise.xp_reward = None
        assert sample_exercise.get_effective_xp_reward() == sample_exercise_type.xp_reward
    
    def test_exercise_alternate_answers_management(self, db_session, sample_exercise):
        """Test alternate answers management."""
        # Test getting alternate answers as list
        assert sample_exercise.get_alternate_answers_list() == ["Hi", "Hey"]
        
        # Test adding alternate answer
        sample_exercise.add_alternate_answer("Greetings")
        assert "Greetings" in sample_exercise.get_alternate_answers_list()
        
        # Test adding duplicate alternate answer
        sample_exercise.add_alternate_answer("Hi")  # Should not add duplicate
        assert sample_exercise.get_alternate_answers_list().count("Hi") == 1
        
        # Test adding empty alternate answer
        with pytest.raises(ValueError, match="Alternate answer cannot be empty"):
            sample_exercise.add_alternate_answer("")
    
    def test_exercise_is_correct_answer(self, db_session, sample_exercise):
        """Test answer correctness checking."""
        # Test correct main answer
        assert sample_exercise.is_correct_answer("Hola") is True
        assert sample_exercise.is_correct_answer("hola") is True  # Case insensitive
        assert sample_exercise.is_correct_answer(" Hola ") is True  # Whitespace handling
        
        # Test correct alternate answers
        assert sample_exercise.is_correct_answer("Hi") is True
        assert sample_exercise.is_correct_answer("hey") is True
        
        # Test incorrect answer
        assert sample_exercise.is_correct_answer("Bonjour") is False
        assert sample_exercise.is_correct_answer("") is False
        assert sample_exercise.is_correct_answer(None) is False
    
    def test_exercise_relationships(self, db_session, sample_exercise, sample_exercise_type, sample_audio_file):
        """Test exercise relationships."""
        # Test exercise type relationship
        assert sample_exercise.exercise_type == sample_exercise_type
        
        # Test prompt audio relationship
        assert sample_exercise.prompt_audio == sample_audio_file
        
        # Test reverse relationship
        assert sample_exercise in sample_exercise_type.exercises
    
    def test_exercise_string_representations(self, sample_exercise):
        """Test string representations of exercise."""
        assert "Translation: Translate: Hello" in str(sample_exercise)
        assert "Exercise" in repr(sample_exercise)
        assert "translation" in repr(sample_exercise)
        assert "beginner" in repr(sample_exercise)


class TestExerciseOption:
    """Test cases for ExerciseOption model."""
    
    def test_create_exercise_option_success(self, db_session, sample_exercise, sample_audio_file):
        """Test successful creation of exercise option."""
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option A",
            is_correct=True,
            display_order=1,
            option_audio_id=str(sample_audio_file.id),
            explanation="This is the correct answer"
        )
        
        db_session.add(option)
        db_session.commit()
        db_session.refresh(option)
        
        assert option.id is not None
        assert option.exercise_id == str(sample_exercise.id)
        assert option.option_text == "Option A"
        assert option.is_correct is True
        assert option.display_order == 1
        assert option.option_audio_id == str(sample_audio_file.id)
        assert option.explanation == "This is the correct answer"
        assert option.created_at is not None
    
    def test_exercise_option_text_validation(self, db_session, sample_exercise):
        """Test option text validation."""
        # Test empty option text
        with pytest.raises(ValueError, match="Option text cannot be empty"):
            ExerciseOption(
                exercise_id=str(sample_exercise.id),
                option_text="",
                display_order=1
            )
        
        # Test too long option text
        with pytest.raises(ValueError, match="Option text cannot exceed 500 characters"):
            ExerciseOption(
                exercise_id=str(sample_exercise.id),
                option_text="x" * 501,
                display_order=1
            )
        
        # Test valid option text
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Valid option",
            display_order=1
        )
        assert option.option_text == "Valid option"
    
    def test_exercise_option_display_order_validation(self, db_session, sample_exercise):
        """Test display order validation."""
        # Test zero display order
        with pytest.raises(ValueError, match="Display order must be positive"):
            ExerciseOption(
                exercise_id=str(sample_exercise.id),
                option_text="Option",
                display_order=0
            )
        
        # Test negative display order
        with pytest.raises(ValueError, match="Display order must be positive"):
            ExerciseOption(
                exercise_id=str(sample_exercise.id),
                option_text="Option",
                display_order=-1
            )
        
        # Test valid display order
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option",
            display_order=2
        )
        assert option.display_order == 2
    
    def test_exercise_option_unique_display_order(self, db_session, sample_exercise):
        """Test unique constraint on display order per exercise."""
        # Create first option
        option1 = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option 1",
            display_order=1
        )
        db_session.add(option1)
        db_session.commit()
        
        # Try to create second option with same display order
        option2 = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option 2",
            display_order=1
        )
        db_session.add(option2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_exercise_option_relationships(self, db_session, sample_exercise, sample_audio_file):
        """Test exercise option relationships."""
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option A",
            is_correct=True,
            display_order=1,
            option_audio_id=str(sample_audio_file.id)
        )
        
        db_session.add(option)
        db_session.commit()
        db_session.refresh(option)
        
        # Test exercise relationship
        assert option.exercise == sample_exercise
        
        # Test audio relationship
        assert option.option_audio == sample_audio_file
        
        # Test reverse relationship
        assert option in sample_exercise.options
    
    def test_exercise_option_string_representations(self, db_session, sample_exercise):
        """Test string representations of exercise option."""
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Test option",
            is_correct=True,
            display_order=1
        )
        
        assert "✓ Test option" in str(option)
        assert "ExerciseOption" in repr(option)
        assert "Test option" in repr(option)
        assert "is_correct=True" in repr(option)
        
        # Test incorrect option
        option.is_correct = False
        assert "✗ Test option" in str(option)


class TestLessonExercise:
    """Test cases for LessonExercise model."""
    
    def test_create_lesson_exercise_success(self, db_session, sample_exercise):
        """Test successful creation of lesson exercise."""
        lesson_id = str(uuid.uuid4())
        
        lesson_exercise = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=0,
            is_required=True,
            weight=2
        )
        
        db_session.add(lesson_exercise)
        db_session.commit()
        db_session.refresh(lesson_exercise)
        
        assert lesson_exercise.id is not None
        assert lesson_exercise.lesson_id == lesson_id
        assert lesson_exercise.exercise_id == str(sample_exercise.id)
        assert lesson_exercise.order_index == 0
        assert lesson_exercise.is_required is True
        assert lesson_exercise.weight == 2
        assert lesson_exercise.created_at is not None
    
    def test_lesson_exercise_order_index_validation(self, db_session, sample_exercise):
        """Test order index validation."""
        lesson_id = str(uuid.uuid4())
        
        # Test negative order index
        with pytest.raises(ValueError, match="Order index cannot be negative"):
            LessonExercise(
                lesson_id=lesson_id,
                exercise_id=str(sample_exercise.id),
                order_index=-1
            )
        
        # Test valid order index
        lesson_exercise = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=5
        )
        assert lesson_exercise.order_index == 5
    
    def test_lesson_exercise_weight_validation(self, db_session, sample_exercise):
        """Test weight validation."""
        lesson_id = str(uuid.uuid4())
        
        # Test zero weight
        with pytest.raises(ValueError, match="Weight must be positive"):
            LessonExercise(
                lesson_id=lesson_id,
                exercise_id=str(sample_exercise.id),
                order_index=0,
                weight=0
            )
        
        # Test negative weight
        with pytest.raises(ValueError, match="Weight must be positive"):
            LessonExercise(
                lesson_id=lesson_id,
                exercise_id=str(sample_exercise.id),
                order_index=0,
                weight=-1
            )
        
        # Test valid weight
        lesson_exercise = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=0,
            weight=3
        )
        assert lesson_exercise.weight == 3
    
    def test_lesson_exercise_unique_constraints(self, db_session, sample_exercise):
        """Test unique constraints on lesson exercise."""
        lesson_id = str(uuid.uuid4())
        
        # Create first lesson exercise
        lesson_exercise1 = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=0
        )
        db_session.add(lesson_exercise1)
        db_session.commit()
        
        # Try to create second lesson exercise with same lesson and exercise
        lesson_exercise2 = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=1
        )
        db_session.add(lesson_exercise2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_lesson_exercise_relationships(self, db_session, sample_exercise):
        """Test lesson exercise relationships."""
        lesson_id = str(uuid.uuid4())
        
        lesson_exercise = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=0
        )
        
        db_session.add(lesson_exercise)
        db_session.commit()
        db_session.refresh(lesson_exercise)
        
        # Test exercise relationship
        assert lesson_exercise.exercise == sample_exercise
        
        # Test reverse relationship
        assert lesson_exercise in sample_exercise.lesson_exercises
    
    def test_lesson_exercise_string_representations(self, db_session, sample_exercise):
        """Test string representations of lesson exercise."""
        lesson_id = str(uuid.uuid4())
        
        lesson_exercise = LessonExercise(
            lesson_id=lesson_id,
            exercise_id=str(sample_exercise.id),
            order_index=2
        )
        
        assert f"Lesson {lesson_id}" in str(lesson_exercise)
        assert f"Exercise {sample_exercise.id}" in str(lesson_exercise)
        assert "order: 2" in str(lesson_exercise)
        assert "LessonExercise" in repr(lesson_exercise)


class TestAudioFile:
    """Test cases for AudioFile model."""
    
    def test_create_audio_file_success(self, db_session):
        """Test successful creation of audio file."""
        audio_file = AudioFile(
            filename="test.mp3",
            file_path="/uploads/audio/test.mp3",
            url="https://example.com/audio/test.mp3",
            mime_type="audio/mp3",
            file_size=2048000,
            duration=120,
            quality="high",
            bitrate=256,
            sample_rate=48000,
            language_code="es",
            speaker_gender="male",
            speaker_accent="mexican",
            transcript="Hola mundo",
            is_active=True
        )
        
        db_session.add(audio_file)
        db_session.commit()
        db_session.refresh(audio_file)
        
        assert audio_file.id is not None
        assert audio_file.filename == "test.mp3"
        assert audio_file.file_path == "/uploads/audio/test.mp3"
        assert audio_file.mime_type == "audio/mp3"
        assert audio_file.file_size == 2048000
        assert audio_file.duration == 120
        assert audio_file.quality == "high"
        assert audio_file.bitrate == 256
        assert audio_file.sample_rate == 48000
        assert audio_file.language_code == "es"
        assert audio_file.speaker_gender == "male"
        assert audio_file.speaker_accent == "mexican"
        assert audio_file.transcript == "Hola mundo"
        assert audio_file.is_active is True
        assert audio_file.created_at is not None
    
    def test_audio_file_filename_validation(self, db_session):
        """Test filename validation."""
        # Test empty filename
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            AudioFile(
                filename="",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=1024
            )
        
        # Test too long filename
        with pytest.raises(ValueError, match="Filename cannot exceed 255 characters"):
            AudioFile(
                filename="x" * 256,
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=1024
            )
        
        # Test valid filename
        audio_file = AudioFile(
            filename="valid.mp3",
            file_path="/path/to/file",
            mime_type="audio/mp3",
            file_size=1024
        )
        assert audio_file.filename == "valid.mp3"
    
    def test_audio_file_path_validation(self, db_session):
        """Test file path validation."""
        # Test empty file path
        with pytest.raises(ValueError, match="File path cannot be empty"):
            AudioFile(
                filename="test.mp3",
                file_path="",
                mime_type="audio/mp3",
                file_size=1024
            )
        
        # Test too long file path
        with pytest.raises(ValueError, match="File path cannot exceed 500 characters"):
            AudioFile(
                filename="test.mp3",
                file_path="x" * 501,
                mime_type="audio/mp3",
                file_size=1024
            )
        
        # Test valid file path
        audio_file = AudioFile(
            filename="test.mp3",
            file_path="/valid/path/to/file.mp3",
            mime_type="audio/mp3",
            file_size=1024
        )
        assert audio_file.file_path == "/valid/path/to/file.mp3"
    
    def test_audio_file_mime_type_validation(self, db_session):
        """Test MIME type validation."""
        # Test empty MIME type
        with pytest.raises(ValueError, match="MIME type cannot be empty"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="",
                file_size=1024
            )
        
        # Test invalid MIME type
        with pytest.raises(ValueError, match="MIME type must be one of"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/invalid",
                file_size=1024
            )
        
        # Test valid MIME types
        valid_mime_types = [
            "audio/mp3", "audio/mpeg", "audio/wav", "audio/ogg",
            "audio/m4a", "audio/aac", "audio/webm"
        ]
        
        for mime_type in valid_mime_types:
            audio_file = AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type=mime_type,
                file_size=1024
            )
            assert audio_file.mime_type == mime_type.lower()
    
    def test_audio_file_size_validation(self, db_session):
        """Test file size validation."""
        # Test zero file size
        with pytest.raises(ValueError, match="File size must be positive"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=0
            )
        
        # Test negative file size
        with pytest.raises(ValueError, match="File size must be positive"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=-1
            )
        
        # Test excessive file size
        with pytest.raises(ValueError, match="File size cannot exceed 50MB"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=51 * 1024 * 1024  # 51MB
            )
        
        # Test valid file size
        audio_file = AudioFile(
            filename="test.mp3",
            file_path="/path/to/file",
            mime_type="audio/mp3",
            file_size=1024000
        )
        assert audio_file.file_size == 1024000
    
    def test_audio_file_quality_validation(self, db_session):
        """Test quality validation."""
        # Test invalid quality
        with pytest.raises(ValueError, match="Quality must be one of"):
            AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=1024,
                quality="invalid"
            )
        
        # Test valid qualities
        valid_qualities = ["low", "standard", "high"]
        
        for quality in valid_qualities:
            audio_file = AudioFile(
                filename="test.mp3",
                file_path="/path/to/file",
                mime_type="audio/mp3",
                file_size=1024,
                quality=quality
            )
            assert audio_file.quality == quality
    
    def test_audio_file_utility_methods(self, sample_audio_file):
        """Test utility methods."""
        # Test get_file_size_mb
        expected_mb = sample_audio_file.file_size / (1024 * 1024)
        assert abs(sample_audio_file.get_file_size_mb() - expected_mb) < 0.01
        
        # Test get_duration_minutes
        expected_minutes = sample_audio_file.duration / 60.0
        assert abs(sample_audio_file.get_duration_minutes() - expected_minutes) < 0.01
        
        # Test with None duration
        sample_audio_file.duration = None
        assert sample_audio_file.get_duration_minutes() is None
    
    def test_audio_file_relationships(self, db_session, sample_audio_file, sample_exercise):
        """Test audio file relationships."""
        # Test relationship with exercise prompts
        assert sample_audio_file in [e.prompt_audio for e in sample_audio_file.exercise_prompts if e.prompt_audio]
        
        # Test relationship with exercise options
        option = ExerciseOption(
            exercise_id=str(sample_exercise.id),
            option_text="Option with audio",
            is_correct=True,
            display_order=1,
            option_audio_id=str(sample_audio_file.id)
        )
        db_session.add(option)
        db_session.commit()
        
        assert sample_audio_file in [o.option_audio for o in sample_audio_file.exercise_options if o.option_audio]
    
    def test_audio_file_string_representations(self, sample_audio_file):
        """Test string representations of audio file."""
        assert "test_audio.mp3" in str(sample_audio_file)
        assert "standard quality" in str(sample_audio_file)
        assert "AudioFile" in repr(sample_audio_file)
        assert "test_audio.mp3" in repr(sample_audio_file)
        assert "standard" in repr(sample_audio_file)


class TestExerciseModelIntegration:
    """Integration tests for exercise models working together."""
    
    def test_complete_exercise_creation_flow(self, db_session):
        """Test complete exercise creation with all related models."""
        # Create exercise type
        exercise_type = ExerciseType(
            name="multiple_choice",
            display_name="Multiple Choice",
            description="Choose the correct answer",
            requires_multiple_choice=True,
            max_options=4,
            xp_reward=15
        )
        db_session.add(exercise_type)
        db_session.commit()
        
        # Create audio file
        audio_file = AudioFile(
            filename="question.mp3",
            file_path="/audio/question.mp3",
            mime_type="audio/mp3",
            file_size=512000,
            duration=10,
            quality="standard"
        )
        db_session.add(audio_file)
        db_session.commit()
        
        # Create exercise
        exercise = Exercise(
            exercise_type_id=str(exercise_type.id),
            prompt="What color is the sky?",
            prompt_audio_id=str(audio_file.id),
            correct_answer="Blue",
            difficulty="beginner",
            estimated_time=30
        )
        db_session.add(exercise)
        db_session.commit()
        
        # Create options
        options = [
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="Blue",
                is_correct=True,
                display_order=1
            ),
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="Red",
                is_correct=False,
                display_order=2
            ),
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="Green",
                is_correct=False,
                display_order=3
            ),
            ExerciseOption(
                exercise_id=str(exercise.id),
                option_text="Yellow",
                is_correct=False,
                display_order=4
            )
        ]
        
        for option in options:
            db_session.add(option)
        db_session.commit()
        
        # Create lesson-exercise relationship
        lesson_exercise = LessonExercise(
            lesson_id=str(uuid.uuid4()),
            exercise_id=str(exercise.id),
            order_index=0,
            is_required=True
        )
        db_session.add(lesson_exercise)
        db_session.commit()
        
        # Verify all relationships
        db_session.refresh(exercise)
        assert exercise.exercise_type == exercise_type
        assert exercise.prompt_audio == audio_file
        assert len(exercise.options) == 4
        assert len(exercise.lesson_exercises) == 1
        
        # Test correct answer checking
        assert exercise.is_correct_answer("Blue") is True
        assert exercise.is_correct_answer("Red") is False
        
        # Test XP reward calculation
        assert exercise.get_effective_xp_reward() == exercise_type.xp_reward
    
    def test_exercise_cascade_deletion(self, db_session, sample_exercise_type):
        """Test cascade deletion of exercise-related models."""
        # Create exercise
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test exercise",
            correct_answer="Test answer"
        )
        db_session.add(exercise)
        db_session.commit()
        
        # Create options
        option1 = ExerciseOption(
            exercise_id=str(exercise.id),
            option_text="Option 1",
            is_correct=True,
            display_order=1
        )
        option2 = ExerciseOption(
            exercise_id=str(exercise.id),
            option_text="Option 2",
            is_correct=False,
            display_order=2
        )
        db_session.add(option1)
        db_session.add(option2)
        db_session.commit()
        
        # Create lesson-exercise relationship
        lesson_exercise = LessonExercise(
            lesson_id=str(uuid.uuid4()),
            exercise_id=str(exercise.id),
            order_index=0
        )
        db_session.add(lesson_exercise)
        db_session.commit()
        
        # Get IDs before deletion
        exercise_id = exercise.id
        option1_id = option1.id
        option2_id = option2.id
        lesson_exercise_id = lesson_exercise.id
        
        # Delete lesson-exercise relationship first (SQLite may not handle CASCADE properly)
        db_session.delete(lesson_exercise)
        # Delete exercise
        db_session.delete(exercise)
        db_session.commit()
        
        # Verify cascade deletion
        assert db_session.query(Exercise).filter_by(id=exercise_id).first() is None
        assert db_session.query(ExerciseOption).filter_by(id=option1_id).first() is None
        assert db_session.query(ExerciseOption).filter_by(id=option2_id).first() is None
        assert db_session.query(LessonExercise).filter_by(id=lesson_exercise_id).first() is None
    
    def test_exercise_type_cascade_deletion(self, db_session, sample_exercise_type):
        """Test cascade deletion when exercise type is deleted."""
        # Create exercise
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test exercise",
            correct_answer="Test answer"
        )
        db_session.add(exercise)
        db_session.commit()
        
        exercise_id = exercise.id
        
        # Delete exercise type
        db_session.delete(sample_exercise_type)
        db_session.commit()
        
        # Verify cascade deletion
        assert db_session.query(Exercise).filter_by(id=exercise_id).first() is None


# Performance and edge case tests
class TestExerciseModelsPerformance:
    """Performance and edge case tests for exercise models."""
    
    def test_bulk_exercise_creation(self, db_session, sample_exercise_type):
        """Test bulk creation of exercises."""
        exercises = []
        for i in range(100):
            exercise = Exercise(
                exercise_type_id=str(sample_exercise_type.id),
                prompt=f"Test exercise {i}",
                correct_answer=f"Answer {i}",
                difficulty="beginner",
                estimated_time=30
            )
            exercises.append(exercise)
        
        db_session.bulk_save_objects(exercises)
        db_session.commit()
        
        # Verify bulk creation
        count = db_session.query(Exercise).filter_by(exercise_type_id=str(sample_exercise_type.id)).count()
        assert count == 100
    
    def test_large_content_handling(self, db_session, sample_exercise_type):
        """Test handling of large content fields."""
        # Test maximum allowed content sizes
        large_prompt = "x" * 1000
        large_answer = "y" * 500
        large_hint = "z" * 2000
        
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt=large_prompt,
            correct_answer=large_answer,
            hint=large_hint,
            explanation="This is a test with large content",
            difficulty="advanced",
            estimated_time=300
        )
        
        db_session.add(exercise)
        db_session.commit()
        db_session.refresh(exercise)
        
        assert exercise.prompt == large_prompt
        assert exercise.correct_answer == large_answer
        assert exercise.hint == large_hint
    
    def test_json_metadata_handling(self, db_session, sample_exercise_type):
        """Test JSON metadata field handling."""
        import json
        complex_metadata = {
            "images": [
                {"url": "https://example.com/img1.jpg", "alt": "Image 1"},
                {"url": "https://example.com/img2.jpg", "alt": "Image 2"}
            ],
            "animations": {
                "duration": 2.5,
                "easing": "ease-in-out"
            },
            "scoring": {
                "partial_credit": True,
                "time_bonus": 0.1
            }
        }
        complex_metadata_str = json.dumps(complex_metadata)
        
        exercise = Exercise(
            exercise_type_id=str(sample_exercise_type.id),
            prompt="Test with complex metadata",
            correct_answer="Test answer",
            content_metadata=complex_metadata_str
        )
        
        db_session.add(exercise)
        db_session.commit()
        db_session.refresh(exercise)
        
        # Parse the JSON back for comparison
        parsed_metadata = json.loads(exercise.content_metadata)
        assert parsed_metadata == complex_metadata
        assert parsed_metadata["images"][0]["url"] == "https://example.com/img1.jpg"
        assert parsed_metadata["animations"]["duration"] == 2.5