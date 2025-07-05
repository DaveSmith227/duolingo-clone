"""
Course Content Structure Models

SQLAlchemy models for course content hierarchy, language management, and lesson structure
for the Duolingo clone backend application.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class Language(BaseModel):
    """
    Language model with localization support.
    
    Stores language information including codes, native names, and metadata
    for supporting multiple languages in the course system.
    """
    
    code = Column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
        doc="ISO language code (e.g., 'en', 'es', 'fr')"
    )
    
    name = Column(
        String(100),
        nullable=False,
        doc="English name of the language (e.g., 'Spanish', 'French')"
    )
    
    native_name = Column(
        String(100),
        nullable=True,
        doc="Native name of the language (e.g., 'Español', 'Français')"
    )
    
    flag_url = Column(
        String(500),
        nullable=True,
        doc="URL to the language's flag image"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this language is active and available"
    )
    
    sort_order = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Display order for language lists"
    )
    
    # Relationships
    courses_from = relationship(
        "Course",
        foreign_keys="Course.from_language_id",
        back_populates="from_language",
        doc="Courses that use this language as the source language"
    )
    
    courses_to = relationship(
        "Course",
        foreign_keys="Course.to_language_id", 
        back_populates="to_language",
        doc="Courses that teach this language as the target"
    )
    
    def __init__(self, **kwargs):
        """Initialize Language with validation."""
        # Set defaults
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'sort_order' not in kwargs:
            kwargs['sort_order'] = 0
        
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('code')
    def validate_code(self, key, code):
        """Validate language code format."""
        if not code:
            raise ValueError("Language code is required")
        
        code = str(code).strip().lower()
        if len(code) < 2 or len(code) > 10:
            raise ValueError("Language code must be between 2 and 10 characters")
        
        # Basic format check - alphanumeric and hyphens only
        if not code.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Language code must contain only letters, numbers, hyphens, and underscores")
        
        return code
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate language name."""
        if not name:
            raise ValueError("Language name is required")
        
        name = str(name).strip()
        if len(name) < 2:
            raise ValueError("Language name must be at least 2 characters long")
        if len(name) > 100:
            raise ValueError("Language name must be less than 100 characters")
        
        return name
    
    @validates('native_name')
    def validate_native_name(self, key, native_name):
        """Validate native language name."""
        if native_name is None:
            return None
        
        native_name = str(native_name).strip()
        if len(native_name) == 0:
            return None
        if len(native_name) > 100:
            raise ValueError("Native language name must be less than 100 characters")
        
        return native_name
    
    @property
    def display_name(self) -> str:
        """Get the display name (native name if available, otherwise English name)."""
        return self.native_name if self.native_name else self.name
    
    def __repr__(self) -> str:
        return f"<Language(id={self.id}, code={self.code}, name={self.name})>"


class Course(BaseModel):
    """
    Course model with language relationships.
    
    Represents a course that teaches one language to speakers of another language
    (e.g., "Spanish for English speakers").
    """
    
    from_language_id = Column(
        String(36),  # UUID as string
        ForeignKey('languages.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Source language (what the user speaks)"
    )
    
    to_language_id = Column(
        String(36),  # UUID as string
        ForeignKey('languages.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Target language (what the user is learning)"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Course name (e.g., 'Spanish for English speakers')"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Course description and overview"
    )
    
    difficulty_level = Column(
        String(20),
        default='beginner',
        nullable=False,
        doc="Course difficulty level"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this course is active and available"
    )
    
    sort_order = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Display order for course lists"
    )
    
    # Relationships
    from_language = relationship(
        "Language",
        foreign_keys=[from_language_id],
        back_populates="courses_from",
        doc="Source language for this course"
    )
    
    to_language = relationship(
        "Language",
        foreign_keys=[to_language_id],
        back_populates="courses_to",
        doc="Target language for this course"
    )
    
    sections = relationship(
        "Section",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Section.sort_order",
        doc="Sections within this course"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('from_language_id', 'to_language_id', name='uq_course_languages'),
        CheckConstraint(
            "difficulty_level IN ('beginner', 'intermediate', 'advanced')",
            name="valid_difficulty_level"
        ),
        CheckConstraint(
            "from_language_id != to_language_id",
            name="different_languages"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize Course with validation."""
        # Set defaults
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'sort_order' not in kwargs:
            kwargs['sort_order'] = 0
        if 'difficulty_level' not in kwargs:
            kwargs['difficulty_level'] = 'beginner'
        
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate course name."""
        if not name:
            raise ValueError("Course name is required")
        
        name = str(name).strip()
        if len(name) < 2:
            raise ValueError("Course name must be at least 2 characters long")
        if len(name) > 255:
            raise ValueError("Course name must be less than 255 characters")
        
        return name
    
    @validates('difficulty_level')
    def validate_difficulty_level(self, key, difficulty_level):
        """Validate difficulty level."""
        if not difficulty_level or str(difficulty_level).strip() == '':
            return 'beginner'
        
        valid_levels = ['beginner', 'intermediate', 'advanced']
        difficulty_level = str(difficulty_level).lower().strip()
        
        if difficulty_level not in valid_levels:
            raise ValueError(f"Difficulty level must be one of: {', '.join(valid_levels)}")
        
        return difficulty_level
    
    @property
    def full_name(self) -> str:
        """Get the full course name with language information."""
        if hasattr(self, 'to_language') and hasattr(self, 'from_language'):
            return f"{self.to_language.name} for {self.from_language.name} speakers"
        return self.name
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, name={self.name}, difficulty={self.difficulty_level})>"


class Section(BaseModel):
    """
    Section model with hierarchical structure.
    
    Represents major divisions within courses (e.g., "Basic 1", "Greetings").
    Maintains ordering and hierarchical structure within courses.
    """
    
    course_id = Column(
        String(36),  # UUID as string
        ForeignKey('courses.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Course this section belongs to"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Section name (e.g., 'Basic 1', 'Greetings')"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Section description and learning objectives"
    )
    
    sort_order = Column(
        Integer,
        nullable=False,
        doc="Order of this section within the course"
    )
    
    cefr_level = Column(
        String(10),
        nullable=True,
        doc="CEFR level (A1, A2, B1, B2, C1, C2)"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this section is active and available"
    )
    
    # Relationships
    course = relationship(
        "Course",
        back_populates="sections",
        doc="Course this section belongs to"
    )
    
    units = relationship(
        "Unit",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Unit.sort_order",
        doc="Units within this section"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('course_id', 'sort_order', name='uq_section_course_order'),
        CheckConstraint(
            "cefr_level IS NULL OR cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="valid_cefr_level"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize Section with validation."""
        # Set defaults
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate section name."""
        if not name:
            raise ValueError("Section name is required")
        
        name = str(name).strip()
        if len(name) < 1:
            raise ValueError("Section name must be at least 1 character long")
        if len(name) > 255:
            raise ValueError("Section name must be less than 255 characters")
        
        return name
    
    @validates('sort_order')
    def validate_sort_order(self, key, sort_order):
        """Validate sort order."""
        if sort_order is None:
            raise ValueError("Sort order is required")
        
        try:
            sort_order = int(float(sort_order))  # Handle both int and float inputs
        except (ValueError, TypeError):
            raise ValueError("Sort order must be a valid integer")
        
        if sort_order < 0:
            raise ValueError("Sort order must be non-negative")
        
        return sort_order
    
    @validates('cefr_level')
    def validate_cefr_level(self, key, cefr_level):
        """Validate CEFR level."""
        if cefr_level is None:
            return None
        
        cefr_level = str(cefr_level).upper().strip()
        if len(cefr_level) == 0:
            return None
        
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        if cefr_level not in valid_levels:
            raise ValueError(f"CEFR level must be one of: {', '.join(valid_levels)}")
        
        return cefr_level
    
    def __repr__(self) -> str:
        return f"<Section(id={self.id}, name={self.name}, sort_order={self.sort_order})>"


class Unit(BaseModel):
    """
    Unit model with visual metadata.
    
    Represents individual learning units within sections with visual metadata
    such as icons and colors for the learning path display.
    """
    
    section_id = Column(
        String(36),  # UUID as string
        ForeignKey('sections.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Section this unit belongs to"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Unit name (e.g., 'Greetings', 'Family')"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Unit description and learning objectives"
    )
    
    sort_order = Column(
        Integer,
        nullable=False,
        doc="Order of this unit within the section"
    )
    
    icon_url = Column(
        String(500),
        nullable=True,
        doc="URL to the unit's icon/image"
    )
    
    color = Column(
        String(7),
        nullable=True,
        doc="Hex color code for the unit (e.g., '#FF5722')"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this unit is active and available"
    )
    
    # Relationships
    section = relationship(
        "Section",
        back_populates="units",
        doc="Section this unit belongs to"
    )
    
    lessons = relationship(
        "Lesson",
        back_populates="unit",
        cascade="all, delete-orphan",
        order_by="Lesson.sort_order",
        doc="Lessons within this unit"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('section_id', 'sort_order', name='uq_unit_section_order'),
    )
    
    def __init__(self, **kwargs):
        """Initialize Unit with validation."""
        # Set defaults
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate unit name."""
        if not name:
            raise ValueError("Unit name is required")
        
        name = str(name).strip()
        if len(name) < 1:
            raise ValueError("Unit name must be at least 1 character long")
        if len(name) > 255:
            raise ValueError("Unit name must be less than 255 characters")
        
        return name
    
    @validates('sort_order')
    def validate_sort_order(self, key, sort_order):
        """Validate sort order."""
        if sort_order is None:
            raise ValueError("Sort order is required")
        
        try:
            sort_order = int(float(sort_order))  # Handle both int and float inputs
        except (ValueError, TypeError):
            raise ValueError("Sort order must be a valid integer")
        
        if sort_order < 0:
            raise ValueError("Sort order must be non-negative")
        
        return sort_order
    
    @validates('color')
    def validate_color(self, key, color):
        """Validate hex color code."""
        if color is None:
            return None
        
        color = str(color).strip()
        if len(color) == 0:
            return None
        
        # Check hex color format
        if not color.startswith('#'):
            raise ValueError("Color must be a hex color code starting with #")
        
        if len(color) != 7:
            raise ValueError("Color must be a 7-character hex color code (e.g., #FF5722)")
        
        # Check if the remaining characters are valid hex
        hex_part = color[1:]
        try:
            int(hex_part, 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color code")
        
        return color.upper()
    
    def __repr__(self) -> str:
        return f"<Unit(id={self.id}, name={self.name}, sort_order={self.sort_order})>"


class Lesson(BaseModel):
    """
    Lesson model with XP and timing data.
    
    Represents individual lessons within units with XP rewards and timing estimates.
    Calculates rewards and provides time estimates for completion.
    """
    
    unit_id = Column(
        String(36),  # UUID as string
        ForeignKey('units.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Unit this lesson belongs to"
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Lesson name (e.g., 'Introduction', 'Practice 1')"
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Lesson description and learning objectives"
    )
    
    sort_order = Column(
        Integer,
        nullable=False,
        doc="Order of this lesson within the unit"
    )
    
    estimated_minutes = Column(
        Integer,
        default=5,
        nullable=False,
        doc="Estimated completion time in minutes"
    )
    
    xp_reward = Column(
        Integer,
        default=20,
        nullable=False,
        doc="XP reward for completing this lesson"
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this lesson is active and available"
    )
    
    # Relationships
    unit = relationship(
        "Unit",
        back_populates="lessons",
        doc="Unit this lesson belongs to"
    )
    
    prerequisites = relationship(
        "LessonPrerequisite",
        foreign_keys="LessonPrerequisite.lesson_id",
        back_populates="lesson",
        cascade="all, delete-orphan",
        doc="Prerequisites for this lesson"
    )
    
    prerequisite_for = relationship(
        "LessonPrerequisite",
        foreign_keys="LessonPrerequisite.prerequisite_lesson_id",
        back_populates="prerequisite_lesson",
        doc="Lessons that require this lesson as a prerequisite"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('unit_id', 'sort_order', name='uq_lesson_unit_order'),
        CheckConstraint(
            "estimated_minutes > 0 AND estimated_minutes <= 120",
            name="valid_estimated_minutes"
        ),
        CheckConstraint(
            "xp_reward >= 0 AND xp_reward <= 1000",
            name="valid_xp_reward"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize Lesson with validation."""
        # Set defaults
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'estimated_minutes' not in kwargs:
            kwargs['estimated_minutes'] = 5
        if 'xp_reward' not in kwargs:
            kwargs['xp_reward'] = 20
        
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('name')
    def validate_name(self, key, name):
        """Validate lesson name."""
        if not name:
            raise ValueError("Lesson name is required")
        
        name = str(name).strip()
        if len(name) < 1:
            raise ValueError("Lesson name must be at least 1 character long")
        if len(name) > 255:
            raise ValueError("Lesson name must be less than 255 characters")
        
        return name
    
    @validates('sort_order')
    def validate_sort_order(self, key, sort_order):
        """Validate sort order."""
        if sort_order is None:
            raise ValueError("Sort order is required")
        
        try:
            sort_order = int(float(sort_order))  # Handle both int and float inputs
        except (ValueError, TypeError):
            raise ValueError("Sort order must be a valid integer")
        
        if sort_order < 0:
            raise ValueError("Sort order must be non-negative")
        
        return sort_order
    
    @validates('estimated_minutes')
    def validate_estimated_minutes(self, key, estimated_minutes):
        """Validate estimated completion time."""
        if estimated_minutes is None:
            return 5
        
        try:
            estimated_minutes = int(float(estimated_minutes))  # Handle both int and float inputs
        except (ValueError, TypeError):
            raise ValueError("Estimated minutes must be a valid integer")
        
        if estimated_minutes <= 0:
            raise ValueError("Estimated minutes must be positive")
        if estimated_minutes > 120:
            raise ValueError("Estimated minutes must be 120 or less")
        
        return estimated_minutes
    
    @validates('xp_reward')
    def validate_xp_reward(self, key, xp_reward):
        """Validate XP reward amount."""
        if xp_reward is None:
            return 20
        
        try:
            xp_reward = int(float(xp_reward))  # Handle both int and float inputs
        except (ValueError, TypeError):
            raise ValueError("XP reward must be a valid integer")
        
        if xp_reward < 0:
            raise ValueError("XP reward must be non-negative")
        if xp_reward > 1000:
            raise ValueError("XP reward must be 1000 or less")
        
        return xp_reward
    
    @property
    def difficulty_score(self) -> float:
        """Calculate difficulty score based on time and XP."""
        if self.estimated_minutes == 0:
            return 0.0
        return self.xp_reward / self.estimated_minutes
    
    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, name={self.name}, xp={self.xp_reward})>"


class LessonPrerequisite(BaseModel):
    """
    Lesson prerequisites system.
    
    Manages lesson dependencies and prevents circular dependencies.
    Ensures proper learning progression through the course structure.
    """
    
    lesson_id = Column(
        String(36),  # UUID as string
        ForeignKey('lessons.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Lesson that has the prerequisite"
    )
    
    prerequisite_lesson_id = Column(
        String(36),  # UUID as string
        ForeignKey('lessons.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc="Lesson that must be completed first"
    )
    
    # Relationships
    lesson = relationship(
        "Lesson",
        foreign_keys=[lesson_id],
        back_populates="prerequisites",
        doc="Lesson that has this prerequisite"
    )
    
    prerequisite_lesson = relationship(
        "Lesson",
        foreign_keys=[prerequisite_lesson_id],
        back_populates="prerequisite_for",
        doc="Lesson that must be completed first"
    )
    
    # Table constraints
    __table_args__ = (
        UniqueConstraint('lesson_id', 'prerequisite_lesson_id', name='uq_lesson_prerequisite'),
        CheckConstraint(
            "lesson_id != prerequisite_lesson_id",
            name="no_self_prerequisite"
        ),
    )
    
    def __init__(self, **kwargs):
        """Initialize LessonPrerequisite with validation."""
        # Initialize with all kwargs
        super().__init__(**kwargs)
    
    @validates('lesson_id')
    def validate_lesson_id(self, key, lesson_id):
        """Validate lesson ID."""
        if lesson_id is None or str(lesson_id).strip() == '':
            raise ValueError("Lesson ID is required")
        return str(lesson_id)
    
    @validates('prerequisite_lesson_id')
    def validate_prerequisite_lesson_id(self, key, prerequisite_lesson_id):
        """Validate prerequisite lesson ID."""
        if prerequisite_lesson_id is None or str(prerequisite_lesson_id).strip() == '':
            raise ValueError("Prerequisite lesson ID is required")
        return str(prerequisite_lesson_id)
    
    def __repr__(self) -> str:
        return f"<LessonPrerequisite(lesson_id={self.lesson_id}, prerequisite_id={self.prerequisite_lesson_id})>"