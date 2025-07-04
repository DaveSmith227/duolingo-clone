"""
Exercise System Models

SQLAlchemy models for exercise types, exercises, options, and audio files
for the Duolingo clone backend application.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSON as PostgresJSON
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class ExerciseTypeEnum(str, Enum):
    """
    Enum for exercise types supported by the application.
    
    Defines the different types of exercises that can be created and completed.
    """
    
    TRANSLATION = "translation"
    MULTIPLE_CHOICE = "multiple_choice"
    LISTENING = "listening"
    SPEAKING = "speaking"
    MATCH_PAIRS = "match_pairs"
    FILL_BLANKS = "fill_blanks"
    SORT_WORDS = "sort_words"


class DifficultyLevel(str, Enum):
    """
    Enum for exercise difficulty levels.
    
    Used to categorize exercises by their complexity and difficulty.
    """
    
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ExerciseType(BaseModel):
    """
    ExerciseType model for exercise categories.
    
    Defines the different types of exercises available in the system,
    including their metadata and configuration.
    """
    
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique name for the exercise type (e.g., 'translation', 'multiple_choice')"
    )
    
    display_name = Column(
        String(100),
        nullable=False,
        doc="Human-readable display name for the exercise type"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Detailed description of the exercise type"
    )
    
    instructions = Column(
        Text,
        nullable=True,
        doc="Instructions for completing this type of exercise"
    )
    
    icon = Column(
        String(50),
        nullable=True,
        doc="Icon identifier for the exercise type (e.g., 'translate', 'microphone')"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this exercise type is currently active and available"
    )
    
    supports_audio = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this exercise type supports audio content"
    )
    
    supports_images = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this exercise type supports image content"
    )
    
    requires_text_input = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this exercise type requires text input from the user"
    )
    
    requires_multiple_choice = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this exercise type uses multiple choice options"
    )
    
    max_options = Column(
        Integer,
        nullable=True,
        doc="Maximum number of options for multiple choice exercises"
    )
    
    default_time_limit = Column(
        Integer,
        nullable=True,
        doc="Default time limit for completing this exercise type (in seconds)"
    )
    
    xp_reward = Column(
        Integer,
        default=10,
        nullable=False,
        doc="XP reward for correctly completing this exercise type"
    )
    
    # Relationships
    exercises = relationship(
        "Exercise",
        back_populates="exercise_type",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "xp_reward >= 0",
            name="ck_exercise_type_xp_reward_non_negative"
        ),
        CheckConstraint(
            "max_options IS NULL OR max_options > 0",
            name="ck_exercise_type_max_options_positive"
        ),
        CheckConstraint(
            "default_time_limit IS NULL OR default_time_limit > 0",
            name="ck_exercise_type_time_limit_positive"
        ),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        """Validate exercise type name."""
        if not value or not value.strip():
            raise ValueError("Exercise type name cannot be empty")
        
        # Check if it's a valid enum value
        valid_names = [e.value for e in ExerciseTypeEnum]
        if value not in valid_names:
            raise ValueError(f"Exercise type name must be one of: {valid_names}")
        
        return value.strip().lower()
    
    @validates('display_name')
    def validate_display_name(self, key, value):
        """Validate display name."""
        if not value or not value.strip():
            raise ValueError("Display name cannot be empty")
        if len(value.strip()) > 100:
            raise ValueError("Display name cannot exceed 100 characters")
        return value.strip()
    
    @validates('xp_reward')
    def validate_xp_reward(self, key, value):
        """Validate XP reward."""
        if value < 0:
            raise ValueError("XP reward cannot be negative")
        if value > 1000:
            raise ValueError("XP reward cannot exceed 1000")
        return value
    
    def __str__(self):
        """String representation of the exercise type."""
        return f"{self.display_name} ({self.name})"
    
    def __repr__(self):
        """Detailed string representation."""
        return f"<ExerciseType(name='{self.name}', display_name='{self.display_name}')>"


class Exercise(BaseModel):
    """
    Exercise model with flexible content storage.
    
    Stores exercise content including prompts, answers, hints, and metadata.
    Supports various exercise types with flexible JSON-based content storage.
    """
    
    exercise_type_id = Column(
        String(36),
        ForeignKey("exercise_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the exercise type this exercise belongs to"
    )
    
    prompt = Column(
        Text,
        nullable=False,
        doc="Main prompt or question for the exercise"
    )
    
    prompt_audio_id = Column(
        String(36),
        ForeignKey("audio_files.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of audio file for the prompt (if applicable)"
    )
    
    correct_answer = Column(
        Text,
        nullable=False,
        doc="Correct answer for the exercise"
    )
    
    alternate_answers = Column(
        Text,
        nullable=True,
        doc="Alternative correct answers (JSON array as text)"
    )
    
    hint = Column(
        Text,
        nullable=True,
        doc="Hint to help users complete the exercise"
    )
    
    explanation = Column(
        Text,
        nullable=True,
        doc="Explanation of the correct answer"
    )
    
    difficulty = Column(
        String(20),
        default=DifficultyLevel.BEGINNER.value,
        nullable=False,
        doc="Difficulty level of the exercise"
    )
    
    estimated_time = Column(
        Integer,
        default=30,
        nullable=False,
        doc="Estimated time to complete the exercise (in seconds)"
    )
    
    xp_reward = Column(
        Integer,
        nullable=True,
        doc="XP reward for this specific exercise (overrides exercise type default)"
    )
    
    content_metadata = Column(
        Text,
        nullable=True,
        doc="Additional metadata for the exercise content (images, audio, etc.) as JSON text"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this exercise is currently active and available"
    )
    
    # Relationships
    exercise_type = relationship(
        "ExerciseType",
        back_populates="exercises"
    )
    
    prompt_audio = relationship(
        "AudioFile",
        foreign_keys=[prompt_audio_id]
    )
    
    options = relationship(
        "ExerciseOption",
        back_populates="exercise",
        cascade="all, delete-orphan"
    )
    
    lesson_exercises = relationship(
        "LessonExercise",
        back_populates="exercise"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "estimated_time > 0",
            name="ck_exercise_estimated_time_positive"
        ),
        CheckConstraint(
            "xp_reward IS NULL OR xp_reward >= 0",
            name="ck_exercise_xp_reward_non_negative"
        ),
        CheckConstraint(
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
            name="ck_exercise_difficulty_valid"
        ),
    )
    
    @validates('prompt')
    def validate_prompt(self, key, value):
        """Validate exercise prompt."""
        if not value or not value.strip():
            raise ValueError("Exercise prompt cannot be empty")
        if len(value.strip()) > 1000:
            raise ValueError("Exercise prompt cannot exceed 1000 characters")
        return value.strip()
    
    @validates('correct_answer')
    def validate_correct_answer(self, key, value):
        """Validate correct answer."""
        if not value or not value.strip():
            raise ValueError("Correct answer cannot be empty")
        if len(value.strip()) > 500:
            raise ValueError("Correct answer cannot exceed 500 characters")
        return value.strip()
    
    @validates('difficulty')
    def validate_difficulty(self, key, value):
        """Validate difficulty level."""
        if value not in [d.value for d in DifficultyLevel]:
            raise ValueError(f"Difficulty must be one of: {[d.value for d in DifficultyLevel]}")
        return value
    
    @validates('estimated_time')
    def validate_estimated_time(self, key, value):
        """Validate estimated time."""
        if value <= 0:
            raise ValueError("Estimated time must be positive")
        if value > 3600:  # 1 hour
            raise ValueError("Estimated time cannot exceed 3600 seconds")
        return value
    
    @validates('xp_reward')
    def validate_xp_reward(self, key, value):
        """Validate XP reward."""
        if value is not None:
            if value < 0:
                raise ValueError("XP reward cannot be negative")
            if value > 1000:
                raise ValueError("XP reward cannot exceed 1000")
        return value
    
    def get_effective_xp_reward(self) -> int:
        """Get the effective XP reward for this exercise."""
        if self.xp_reward is not None:
            return self.xp_reward
        return self.exercise_type.xp_reward if self.exercise_type else 10
    
    def get_alternate_answers_list(self) -> List[str]:
        """Get alternate answers as a list."""
        if self.alternate_answers is None:
            return []
        if isinstance(self.alternate_answers, str):
            import json
            try:
                return json.loads(self.alternate_answers)
            except json.JSONDecodeError:
                return []
        if isinstance(self.alternate_answers, list):
            return self.alternate_answers
        return []
    
    def add_alternate_answer(self, answer: str):
        """Add an alternate answer."""
        if not answer or not answer.strip():
            raise ValueError("Alternate answer cannot be empty")
        
        current_answers = self.get_alternate_answers_list()
        answer = answer.strip()
        
        if answer not in current_answers:
            current_answers.append(answer)
            import json
            self.alternate_answers = json.dumps(current_answers)
    
    def is_correct_answer(self, user_answer: str) -> bool:
        """Check if the user's answer is correct."""
        if not user_answer:
            return False
        
        user_answer = user_answer.strip().lower()
        
        # Check main correct answer
        if user_answer == self.correct_answer.strip().lower():
            return True
        
        # Check alternate answers
        for alt_answer in self.get_alternate_answers_list():
            if user_answer == alt_answer.strip().lower():
                return True
        
        return False
    
    def __str__(self):
        """String representation of the exercise."""
        return f"{self.exercise_type.display_name}: {self.prompt[:50]}..."
    
    def __repr__(self):
        """Detailed string representation."""
        return f"<Exercise(id='{self.id}', type='{self.exercise_type.name}', difficulty='{self.difficulty}')>"


class ExerciseOption(BaseModel):
    """
    ExerciseOption model for multiple choice exercises.
    
    Stores individual options for multiple choice exercises,
    including correct answer tracking and display metadata.
    """
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the exercise this option belongs to"
    )
    
    option_text = Column(
        String(500),
        nullable=False,
        doc="Text content of the option"
    )
    
    is_correct = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this option is a correct answer"
    )
    
    display_order = Column(
        Integer,
        nullable=False,
        doc="Order in which this option should be displayed"
    )
    
    option_audio_id = Column(
        String(36),
        ForeignKey("audio_files.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of audio file for this option (if applicable)"
    )
    
    explanation = Column(
        Text,
        nullable=True,
        doc="Explanation for why this option is correct or incorrect"
    )
    
    # Relationships
    exercise = relationship(
        "Exercise",
        back_populates="options"
    )
    
    option_audio = relationship(
        "AudioFile",
        foreign_keys=[option_audio_id]
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "display_order > 0",
            name="ck_exercise_option_display_order_positive"
        ),
        UniqueConstraint(
            "exercise_id", "display_order",
            name="uq_exercise_option_display_order"
        ),
    )
    
    @validates('option_text')
    def validate_option_text(self, key, value):
        """Validate option text."""
        if not value or not value.strip():
            raise ValueError("Option text cannot be empty")
        if len(value.strip()) > 500:
            raise ValueError("Option text cannot exceed 500 characters")
        return value.strip()
    
    @validates('display_order')
    def validate_display_order(self, key, value):
        """Validate display order."""
        if value <= 0:
            raise ValueError("Display order must be positive")
        return value
    
    def __str__(self):
        """String representation of the option."""
        correct_indicator = "✓" if self.is_correct else "✗"
        return f"{correct_indicator} {self.option_text}"
    
    def __repr__(self):
        """Detailed string representation."""
        return f"<ExerciseOption(id='{self.id}', text='{self.option_text[:30]}...', is_correct={self.is_correct})>"


class LessonExercise(BaseModel):
    """
    LessonExercise junction model for many-to-many relationship.
    
    Handles the relationship between lessons and exercises,
    including exercise ordering and metadata.
    """
    
    lesson_id = Column(
        String(36),
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the lesson this exercise belongs to"
    )
    
    exercise_id = Column(
        String(36),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the exercise in this lesson"
    )
    
    order_index = Column(
        Integer,
        nullable=False,
        doc="Order of this exercise within the lesson"
    )
    
    is_required = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this exercise is required to complete the lesson"
    )
    
    weight = Column(
        Integer,
        default=1,
        nullable=False,
        doc="Weight of this exercise in lesson scoring"
    )
    
    # Relationships
    exercise = relationship(
        "Exercise",
        back_populates="lesson_exercises"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "order_index >= 0",
            name="ck_lesson_exercise_order_index_non_negative"
        ),
        CheckConstraint(
            "weight > 0",
            name="ck_lesson_exercise_weight_positive"
        ),
        UniqueConstraint(
            "lesson_id", "exercise_id",
            name="uq_lesson_exercise_unique"
        ),
        UniqueConstraint(
            "lesson_id", "order_index",
            name="uq_lesson_exercise_order"
        ),
    )
    
    @validates('order_index')
    def validate_order_index(self, key, value):
        """Validate order index."""
        if value < 0:
            raise ValueError("Order index cannot be negative")
        return value
    
    @validates('weight')
    def validate_weight(self, key, value):
        """Validate weight."""
        if value <= 0:
            raise ValueError("Weight must be positive")
        return value
    
    def __str__(self):
        """String representation of the lesson-exercise relationship."""
        return f"Lesson {self.lesson_id} - Exercise {self.exercise_id} (order: {self.order_index})"
    
    def __repr__(self):
        """Detailed string representation."""
        return f"<LessonExercise(lesson_id='{self.lesson_id}', exercise_id='{self.exercise_id}', order={self.order_index})>"


class AudioFile(BaseModel):
    """
    AudioFile model for listening exercises and audio content.
    
    Stores audio file metadata and supports multiple quality levels
    for different device capabilities and network conditions.
    """
    
    filename = Column(
        String(255),
        nullable=False,
        doc="Original filename of the audio file"
    )
    
    file_path = Column(
        String(500),
        nullable=False,
        doc="Path to the audio file in storage"
    )
    
    url = Column(
        String(500),
        nullable=True,
        doc="Public URL to access the audio file"
    )
    
    mime_type = Column(
        String(100),
        nullable=False,
        doc="MIME type of the audio file (e.g., 'audio/mp3', 'audio/wav')"
    )
    
    file_size = Column(
        Integer,
        nullable=False,
        doc="Size of the audio file in bytes"
    )
    
    duration = Column(
        Integer,
        nullable=True,
        doc="Duration of the audio file in seconds"
    )
    
    quality = Column(
        String(20),
        default="standard",
        nullable=False,
        doc="Quality level of the audio file (low, standard, high)"
    )
    
    bitrate = Column(
        Integer,
        nullable=True,
        doc="Bitrate of the audio file in kbps"
    )
    
    sample_rate = Column(
        Integer,
        nullable=True,
        doc="Sample rate of the audio file in Hz"
    )
    
    language_code = Column(
        String(10),
        nullable=True,
        doc="Language code for the audio content"
    )
    
    speaker_gender = Column(
        String(10),
        nullable=True,
        doc="Gender of the speaker (male, female, other)"
    )
    
    speaker_accent = Column(
        String(50),
        nullable=True,
        doc="Accent of the speaker (e.g., 'american', 'british', 'mexican')"
    )
    
    transcript = Column(
        Text,
        nullable=True,
        doc="Transcript of the audio content"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this audio file is currently available"
    )
    
    # Relationships
    exercise_prompts = relationship(
        "Exercise",
        foreign_keys="Exercise.prompt_audio_id",
        back_populates="prompt_audio"
    )
    
    exercise_options = relationship(
        "ExerciseOption",
        foreign_keys="ExerciseOption.option_audio_id",
        back_populates="option_audio"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "file_size > 0",
            name="ck_audio_file_size_positive"
        ),
        CheckConstraint(
            "duration IS NULL OR duration > 0",
            name="ck_audio_file_duration_positive"
        ),
        CheckConstraint(
            "quality IN ('low', 'standard', 'high')",
            name="ck_audio_file_quality_valid"
        ),
        CheckConstraint(
            "bitrate IS NULL OR bitrate > 0",
            name="ck_audio_file_bitrate_positive"
        ),
        CheckConstraint(
            "sample_rate IS NULL OR sample_rate > 0",
            name="ck_audio_file_sample_rate_positive"
        ),
        CheckConstraint(
            "speaker_gender IS NULL OR speaker_gender IN ('male', 'female', 'other')",
            name="ck_audio_file_speaker_gender_valid"
        ),
    )
    
    @validates('filename')
    def validate_filename(self, key, value):
        """Validate filename."""
        if not value or not value.strip():
            raise ValueError("Filename cannot be empty")
        if len(value.strip()) > 255:
            raise ValueError("Filename cannot exceed 255 characters")
        return value.strip()
    
    @validates('file_path')
    def validate_file_path(self, key, value):
        """Validate file path."""
        if not value or not value.strip():
            raise ValueError("File path cannot be empty")
        if len(value.strip()) > 500:
            raise ValueError("File path cannot exceed 500 characters")
        return value.strip()
    
    @validates('mime_type')
    def validate_mime_type(self, key, value):
        """Validate MIME type."""
        if not value or not value.strip():
            raise ValueError("MIME type cannot be empty")
        
        valid_mime_types = [
            'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/ogg',
            'audio/m4a', 'audio/aac', 'audio/webm'
        ]
        
        if value.strip().lower() not in valid_mime_types:
            raise ValueError(f"MIME type must be one of: {valid_mime_types}")
        
        return value.strip().lower()
    
    @validates('file_size')
    def validate_file_size(self, key, value):
        """Validate file size."""
        if value <= 0:
            raise ValueError("File size must be positive")
        if value > 50 * 1024 * 1024:  # 50MB
            raise ValueError("File size cannot exceed 50MB")
        return value
    
    @validates('quality')
    def validate_quality(self, key, value):
        """Validate quality level."""
        valid_qualities = ['low', 'standard', 'high']
        if value not in valid_qualities:
            raise ValueError(f"Quality must be one of: {valid_qualities}")
        return value
    
    def get_file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)
    
    def get_duration_minutes(self) -> Optional[float]:
        """Get duration in minutes."""
        if self.duration is None:
            return None
        return self.duration / 60.0
    
    def __str__(self):
        """String representation of the audio file."""
        return f"{self.filename} ({self.quality} quality)"
    
    def __repr__(self):
        """Detailed string representation."""
        return f"<AudioFile(filename='{self.filename}', quality='{self.quality}', size={self.file_size})>"