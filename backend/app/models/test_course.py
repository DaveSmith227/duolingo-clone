"""
Unit Tests for Course Content Structure Models

Comprehensive test coverage for Language, Course, Section, Unit, Lesson, and LessonPrerequisite models
including validation, constraints, relationships, and business logic.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.models.base import Base
from app.models.course import Language, Course, Section, Unit, Lesson, LessonPrerequisite


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database for testing."""
    # Enable foreign key constraints for SQLite
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_language_data():
    """Sample language data for testing."""
    return {
        'code': 'es',
        'name': 'Spanish',
        'native_name': 'Español',
        'flag_url': 'https://example.com/flags/es.png',
        'sort_order': 1
    }


@pytest.fixture
def sample_languages(db_session):
    """Create sample languages for testing."""
    english = Language(code='en', name='English', native_name='English', sort_order=1)
    spanish = Language(code='es', name='Spanish', native_name='Español', sort_order=2)
    
    db_session.add(english)
    db_session.add(spanish)
    db_session.commit()
    
    return {'english': english, 'spanish': spanish}


@pytest.fixture
def sample_course(db_session, sample_languages):
    """Create a sample course for testing."""
    course = Course(
        from_language_id=str(sample_languages['english'].id),
        to_language_id=str(sample_languages['spanish'].id),
        name='Spanish for English speakers',
        description='Learn Spanish basics',
        difficulty_level='beginner'
    )
    db_session.add(course)
    db_session.commit()
    return course


class TestLanguageModel:
    """Test cases for the Language model."""
    
    def test_language_creation_with_valid_data(self, db_session, sample_language_data):
        """Test creating a language with valid data."""
        language = Language(**sample_language_data)
        db_session.add(language)
        db_session.commit()
        
        assert language.id is not None
        assert language.code == 'es'
        assert language.name == 'Spanish'
        assert language.native_name == 'Español'
        assert language.flag_url == 'https://example.com/flags/es.png'
        assert language.is_active is True
        assert language.sort_order == 1
        assert language.created_at is not None
        assert language.updated_at is not None
    
    def test_language_code_validation_valid_codes(self, db_session):
        """Test language creation with various valid codes."""
        valid_codes = ['en', 'es', 'fr-CA', 'zh_CN', 'pt_BR', 'en-US']
        
        for code in valid_codes:
            language = Language(code=code, name=f'Language {code}')
            db_session.add(language)
            db_session.commit()
            
            assert language.code == code.lower()
            db_session.delete(language)
            db_session.commit()
    
    def test_language_code_validation_invalid_codes(self, db_session):
        """Test language creation with invalid codes."""
        invalid_codes = ['', 'a', 'toolongcode', 'in valid', 'sp@ce', '123!']
        
        for code in invalid_codes:
            with pytest.raises(ValueError, match="Language code|required"):
                Language(code=code, name='Test Language')
    
    def test_language_name_validation(self, db_session):
        """Test language name validation."""
        # Valid names
        valid_names = ['English', 'Español', 'Français', 'X Language', 'A'*99]
        for name in valid_names:
            language = Language(code=f'test{len(name)}', name=name)
            db_session.add(language)
            db_session.commit()
            assert language.name == name
            db_session.delete(language)
            db_session.commit()
        
        # Invalid names
        invalid_names = ['', ' ', None, 'A'*101]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Language name|required"):
                Language(code='test', name=name)
    
    def test_language_native_name_validation(self, db_session):
        """Test native language name validation."""
        # Valid native names (including None)
        language1 = Language(code='test1', name='Test', native_name=None)
        language2 = Language(code='test2', name='Test', native_name='Native Test')
        language3 = Language(code='test3', name='Test', native_name='')
        
        db_session.add_all([language1, language2, language3])
        db_session.commit()
        
        assert language1.native_name is None
        assert language2.native_name == 'Native Test'
        assert language3.native_name is None  # Empty string converted to None
        
        # Invalid native name (too long)
        with pytest.raises(ValueError, match="Native language name"):
            Language(code='test4', name='Test', native_name='A'*101)
    
    def test_language_code_uniqueness(self, db_session, sample_language_data):
        """Test that language codes must be unique."""
        # Create first language
        language1 = Language(**sample_language_data)
        db_session.add(language1)
        db_session.commit()
        
        # Try to create second language with same code
        language2_data = sample_language_data.copy()
        language2_data['name'] = 'Another Spanish'
        language2 = Language(**language2_data)
        db_session.add(language2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_language_display_name_property(self, db_session):
        """Test display name property."""
        # Language with native name
        lang1 = Language(code='es', name='Spanish', native_name='Español')
        assert lang1.display_name == 'Español'
        
        # Language without native name
        lang2 = Language(code='en', name='English', native_name=None)
        assert lang2.display_name == 'English'
        
        # Language with empty native name
        lang3 = Language(code='fr', name='French', native_name='')
        assert lang3.display_name == 'French'
    
    def test_language_string_representation(self, sample_language_data):
        """Test language string representation."""
        language = Language(**sample_language_data)
        language.id = uuid.uuid4()
        
        repr_str = repr(language)
        assert 'Language' in repr_str
        assert str(language.id) in repr_str
        assert language.code in repr_str
        assert language.name in repr_str


class TestCourseModel:
    """Test cases for the Course model."""
    
    def test_course_creation_with_valid_data(self, db_session, sample_languages):
        """Test creating a course with valid data."""
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Spanish for English speakers',
            description='Learn Spanish basics',
            difficulty_level='beginner'
        )
        db_session.add(course)
        db_session.commit()
        
        assert course.id is not None
        assert course.from_language_id == str(sample_languages['english'].id)
        assert course.to_language_id == str(sample_languages['spanish'].id)
        assert course.name == 'Spanish for English speakers'
        assert course.description == 'Learn Spanish basics'
        assert course.difficulty_level == 'beginner'
        assert course.is_active is True
        assert course.sort_order == 0
    
    def test_course_name_validation(self, db_session, sample_languages):
        """Test course name validation."""
        # Valid names
        valid_names = ['Spanish Course', 'A'*254, 'Course 101']
        for name in valid_names:
            course = Course(
                from_language_id=str(sample_languages['english'].id),
                to_language_id=str(sample_languages['spanish'].id),
                name=name
            )
            db_session.add(course)
            db_session.commit()
            assert course.name == name
            db_session.delete(course)
            db_session.commit()
        
        # Invalid names
        invalid_names = ['', ' ', None, 'A'*256]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Course name|required"):
                Course(
                    from_language_id=str(sample_languages['english'].id),
                    to_language_id=str(sample_languages['spanish'].id),
                    name=name
                )
    
    def test_course_difficulty_level_validation(self, db_session, sample_languages):
        """Test difficulty level validation."""
        # Valid levels
        valid_levels = ['beginner', 'intermediate', 'advanced']
        for level in valid_levels:
            course = Course(
                from_language_id=str(sample_languages['english'].id),
                to_language_id=str(sample_languages['spanish'].id),
                name=f'Test Course {level}',
                difficulty_level=level
            )
            db_session.add(course)
            db_session.commit()
            assert course.difficulty_level == level
            db_session.delete(course)
            db_session.commit()
        
        # Invalid levels (empty string defaults to 'beginner' so test separately)
        invalid_levels = ['expert', 'novice', 'hard']
        for level in invalid_levels:
            with pytest.raises(ValueError, match="Difficulty level"):
                Course(
                    from_language_id=str(sample_languages['english'].id),
                    to_language_id=str(sample_languages['spanish'].id),
                    name='Test Course',
                    difficulty_level=level
                )
        
        # Test empty string defaults to 'beginner'
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Test Course Empty',
            difficulty_level=''
        )
        assert course.difficulty_level == 'beginner'
    
    def test_course_language_uniqueness(self, db_session, sample_languages):
        """Test that course language combinations must be unique."""
        # Create first course
        course1 = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Course 1'
        )
        db_session.add(course1)
        db_session.commit()
        
        # Try to create second course with same language combination
        course2 = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Course 2'
        )
        db_session.add(course2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_course_same_language_constraint(self, db_session, sample_languages):
        """Test that from and to languages must be different."""
        with pytest.raises(IntegrityError):
            course = Course(
                from_language_id=str(sample_languages['english'].id),
                to_language_id=str(sample_languages['english'].id),
                name='Same Language Course'
            )
            db_session.add(course)
            db_session.commit()
    
    def test_course_language_relationships(self, db_session, sample_languages):
        """Test course language relationships."""
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Test Course'
        )
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        assert course.from_language == sample_languages['english']
        assert course.to_language == sample_languages['spanish']
        assert course in sample_languages['english'].courses_from
        assert course in sample_languages['spanish'].courses_to
    
    def test_course_full_name_property(self, db_session, sample_languages):
        """Test full name property."""
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Test Course'
        )
        db_session.add(course)
        db_session.commit()
        db_session.refresh(course)
        
        expected_name = "Spanish for English speakers"
        assert course.full_name == expected_name


class TestSectionModel:
    """Test cases for the Section model."""
    
    def test_section_creation_with_valid_data(self, db_session, sample_course):
        """Test creating a section with valid data."""
        section = Section(
            course_id=str(sample_course.id),
            name='Basic 1',
            description='Introduction to Spanish basics',
            sort_order=1,
            cefr_level='A1'
        )
        db_session.add(section)
        db_session.commit()
        
        assert section.id is not None
        assert section.course_id == str(sample_course.id)
        assert section.name == 'Basic 1'
        assert section.description == 'Introduction to Spanish basics'
        assert section.sort_order == 1
        assert section.cefr_level == 'A1'
        assert section.is_active is True
    
    def test_section_name_validation(self, db_session, sample_course):
        """Test section name validation."""
        # Valid names
        valid_names = ['Basic 1', 'A'*255, 'X']
        for name in valid_names:
            section = Section(
                course_id=str(sample_course.id),
                name=name,
                sort_order=1
            )
            db_session.add(section)
            db_session.commit()
            assert section.name == name
            db_session.delete(section)
            db_session.commit()
        
        # Invalid names
        invalid_names = ['', ' ', None, 'A'*256]
        for name in invalid_names:
            with pytest.raises(ValueError, match="Section name|required"):
                Section(
                    course_id=str(sample_course.id),
                    name=name,
                    sort_order=1
                )
    
    def test_section_sort_order_validation(self, db_session, sample_course):
        """Test sort order validation."""
        # Valid sort orders
        valid_orders = [0, 1, 100, 999]
        for order in valid_orders:
            section = Section(
                course_id=str(sample_course.id),
                name=f'Section {order}',
                sort_order=order
            )
            db_session.add(section)
            db_session.commit()
            assert section.sort_order == order
            db_session.delete(section)
            db_session.commit()
        
        # Invalid sort orders
        invalid_orders = [None, -1, 'abc']
        for order in invalid_orders:
            with pytest.raises(ValueError, match="Sort order"):
                Section(
                    course_id=str(sample_course.id),
                    name='Test Section',
                    sort_order=order
                )
        
        # Test that float values are converted to integers
        section = Section(
            course_id=str(sample_course.id),
            name='Float Section',
            sort_order=1.5
        )
        assert section.sort_order == 1
    
    def test_section_cefr_level_validation(self, db_session, sample_course):
        """Test CEFR level validation."""
        # Valid CEFR levels
        valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', None, '']
        for level in valid_levels:
            section = Section(
                course_id=str(sample_course.id),
                name=f'Section {level}',
                sort_order=1,
                cefr_level=level
            )
            db_session.add(section)
            db_session.commit()
            expected_level = None if level == '' else level
            assert section.cefr_level == expected_level
            db_session.delete(section)
            db_session.commit()
        
        # Invalid CEFR levels
        invalid_levels = ['A3', 'D1', 'beginner', 'B']
        for level in invalid_levels:
            with pytest.raises(ValueError, match="CEFR level"):
                Section(
                    course_id=str(sample_course.id),
                    name='Test Section',
                    sort_order=1,
                    cefr_level=level
                )
    
    def test_section_course_sort_order_uniqueness(self, db_session, sample_course):
        """Test that course + sort_order combinations must be unique."""
        # Create first section
        section1 = Section(
            course_id=str(sample_course.id),
            name='Section 1',
            sort_order=1
        )
        db_session.add(section1)
        db_session.commit()
        
        # Try to create second section with same course and sort order
        section2 = Section(
            course_id=str(sample_course.id),
            name='Section 2',
            sort_order=1
        )
        db_session.add(section2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestUnitModel:
    """Test cases for the Unit model."""
    
    def test_unit_creation_with_valid_data(self, db_session, sample_course):
        """Test creating a unit with valid data."""
        # Create section first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        db_session.add(section)
        db_session.commit()
        
        unit = Unit(
            section_id=str(section.id),
            name='Greetings',
            description='Learn basic greetings',
            sort_order=1,
            icon_url='https://example.com/icons/greetings.png',
            color='#FF5722'
        )
        db_session.add(unit)
        db_session.commit()
        
        assert unit.id is not None
        assert unit.section_id == str(section.id)
        assert unit.name == 'Greetings'
        assert unit.description == 'Learn basic greetings'
        assert unit.sort_order == 1
        assert unit.icon_url == 'https://example.com/icons/greetings.png'
        assert unit.color == '#FF5722'
        assert unit.is_active is True
    
    def test_unit_color_validation(self, db_session, sample_course):
        """Test color validation."""
        # Create section first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        db_session.add(section)
        db_session.commit()
        
        # Valid colors
        valid_colors = ['#FF5722', '#000000', '#FFFFFF', '#123ABC', None, '']
        for color in valid_colors:
            unit = Unit(
                section_id=str(section.id),
                name=f'Unit {color or "none"}',
                sort_order=1,
                color=color
            )
            db_session.add(unit)
            db_session.commit()
            expected_color = None if color == '' else (color.upper() if color else None)
            assert unit.color == expected_color
            db_session.delete(unit)
            db_session.commit()
        
        # Invalid colors
        invalid_colors = ['FF5722', '#FF572', '#GG5722', 'red', '#FF5722X']
        for color in invalid_colors:
            with pytest.raises(ValueError, match="Color|hex"):
                Unit(
                    section_id=str(section.id),
                    name='Test Unit',
                    sort_order=1,
                    color=color
                )


class TestLessonModel:
    """Test cases for the Lesson model."""
    
    def test_lesson_creation_with_valid_data(self, db_session, sample_course):
        """Test creating a lesson with valid data."""
        # Create section and unit first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        db_session.add(section)
        db_session.commit()
        
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        db_session.add(unit)
        db_session.commit()
        
        lesson = Lesson(
            unit_id=str(unit.id),
            name='Introduction',
            description='Learn basic vocabulary',
            sort_order=1,
            estimated_minutes=10,
            xp_reward=30
        )
        db_session.add(lesson)
        db_session.commit()
        
        assert lesson.id is not None
        assert lesson.unit_id == str(unit.id)
        assert lesson.name == 'Introduction'
        assert lesson.description == 'Learn basic vocabulary'
        assert lesson.sort_order == 1
        assert lesson.estimated_minutes == 10
        assert lesson.xp_reward == 30
        assert lesson.is_active is True
    
    def test_lesson_estimated_minutes_validation(self, db_session, sample_course):
        """Test estimated minutes validation."""
        # Create section and unit first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        db_session.add_all([section, unit])
        db_session.commit()
        
        # Valid minutes
        valid_minutes = [1, 5, 60, 120]
        for minutes in valid_minutes:
            lesson = Lesson(
                unit_id=str(unit.id),
                name=f'Lesson {minutes}',
                sort_order=1,
                estimated_minutes=minutes
            )
            db_session.add(lesson)
            db_session.commit()
            assert lesson.estimated_minutes == minutes
            db_session.delete(lesson)
            db_session.commit()
        
        # Invalid minutes
        invalid_minutes = [0, -1, 121, 'abc']
        for minutes in invalid_minutes:
            with pytest.raises(ValueError, match="Estimated minutes"):
                Lesson(
                    unit_id=str(unit.id),
                    name='Test Lesson',
                    sort_order=1,
                    estimated_minutes=minutes
                )
    
    def test_lesson_xp_reward_validation(self, db_session, sample_course):
        """Test XP reward validation."""
        # Create section and unit first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        db_session.add_all([section, unit])
        db_session.commit()
        
        # Valid XP rewards
        valid_xp = [0, 10, 50, 1000]
        for xp in valid_xp:
            lesson = Lesson(
                unit_id=str(unit.id),
                name=f'Lesson {xp}',
                sort_order=1,
                xp_reward=xp
            )
            db_session.add(lesson)
            db_session.commit()
            assert lesson.xp_reward == xp
            db_session.delete(lesson)
            db_session.commit()
        
        # Invalid XP rewards
        invalid_xp = [-1, 1001, 'abc']
        for xp in invalid_xp:
            with pytest.raises(ValueError, match="XP reward"):
                Lesson(
                    unit_id=str(unit.id),
                    name='Test Lesson',
                    sort_order=1,
                    xp_reward=xp
                )
    
    def test_lesson_difficulty_score_property(self, db_session, sample_course):
        """Test difficulty score calculation."""
        # Create section and unit first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        db_session.add_all([section, unit])
        db_session.commit()
        
        lesson = Lesson(
            unit_id=str(unit.id),
            name='Test Lesson',
            sort_order=1,
            estimated_minutes=10,
            xp_reward=20
        )
        
        assert lesson.difficulty_score == 2.0  # 20 XP / 10 minutes
        
        # Test with zero minutes
        lesson.estimated_minutes = 0
        assert lesson.difficulty_score == 0.0


class TestLessonPrerequisiteModel:
    """Test cases for the LessonPrerequisite model."""
    
    def test_lesson_prerequisite_creation(self, db_session, sample_course):
        """Test creating lesson prerequisites."""
        # Create section, unit, and lessons first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        lesson1 = Lesson(
            unit_id=str(unit.id),
            name='Lesson 1',
            sort_order=1
        )
        lesson2 = Lesson(
            unit_id=str(unit.id),
            name='Lesson 2',
            sort_order=2
        )
        db_session.add_all([section, unit, lesson1, lesson2])
        db_session.commit()
        
        # Create prerequisite
        prerequisite = LessonPrerequisite(
            lesson_id=str(lesson2.id),
            prerequisite_lesson_id=str(lesson1.id)
        )
        db_session.add(prerequisite)
        db_session.commit()
        
        assert prerequisite.id is not None
        assert prerequisite.lesson_id == str(lesson2.id)
        assert prerequisite.prerequisite_lesson_id == str(lesson1.id)
    
    def test_lesson_prerequisite_validation(self, db_session, sample_course):
        """Test lesson prerequisite validation."""
        # Invalid lesson IDs
        invalid_ids = [None, '', '  ']
        for lesson_id in invalid_ids:
            with pytest.raises(ValueError, match="Lesson ID|required"):
                LessonPrerequisite(
                    lesson_id=lesson_id,
                    prerequisite_lesson_id='valid-id'
                )
        
        for prereq_id in invalid_ids:
            with pytest.raises(ValueError, match="Prerequisite lesson ID|required"):
                LessonPrerequisite(
                    lesson_id='valid-id',
                    prerequisite_lesson_id=prereq_id
                )
    
    def test_lesson_prerequisite_self_reference_constraint(self, db_session, sample_course):
        """Test that lessons cannot be prerequisites of themselves."""
        # Create section, unit, and lesson first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        lesson = Lesson(
            unit_id=str(unit.id),
            name='Test Lesson',
            sort_order=1
        )
        db_session.add_all([section, unit, lesson])
        db_session.commit()
        
        # Try to create self-prerequisite
        with pytest.raises(IntegrityError):
            prerequisite = LessonPrerequisite(
                lesson_id=str(lesson.id),
                prerequisite_lesson_id=str(lesson.id)
            )
            db_session.add(prerequisite)
            db_session.commit()
    
    def test_lesson_prerequisite_relationships(self, db_session, sample_course):
        """Test prerequisite relationships."""
        # Create section, unit, and lessons first
        section = Section(
            course_id=str(sample_course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        lesson1 = Lesson(
            unit_id=str(unit.id),
            name='Lesson 1',
            sort_order=1
        )
        lesson2 = Lesson(
            unit_id=str(unit.id),
            name='Lesson 2',
            sort_order=2
        )
        db_session.add_all([section, unit, lesson1, lesson2])
        db_session.commit()
        
        # Create prerequisite
        prerequisite = LessonPrerequisite(
            lesson_id=str(lesson2.id),
            prerequisite_lesson_id=str(lesson1.id)
        )
        db_session.add(prerequisite)
        db_session.commit()
        db_session.refresh(lesson1)
        db_session.refresh(lesson2)
        
        # Test relationships
        assert len(lesson2.prerequisites) == 1
        assert lesson2.prerequisites[0] == prerequisite
        assert len(lesson1.prerequisite_for) == 1
        assert lesson1.prerequisite_for[0] == prerequisite
        assert prerequisite.lesson == lesson2
        assert prerequisite.prerequisite_lesson == lesson1


class TestCourseModelIntegration:
    """Integration tests for course models working together."""
    
    def test_complete_course_hierarchy(self, db_session, sample_languages):
        """Test creating a complete course hierarchy."""
        # Create course
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Spanish Course'
        )
        
        # Create section
        section = Section(
            course_id=str(course.id),
            name='Basic 1',
            sort_order=1
        )
        
        # Create unit
        unit = Unit(
            section_id=str(section.id),
            name='Greetings',
            sort_order=1,
            color='#FF5722'
        )
        
        # Create lessons
        lesson1 = Lesson(
            unit_id=str(unit.id),
            name='Introduction',
            sort_order=1,
            xp_reward=20
        )
        lesson2 = Lesson(
            unit_id=str(unit.id),
            name='Practice',
            sort_order=2,
            xp_reward=30
        )
        
        # Create prerequisite
        prerequisite = LessonPrerequisite(
            lesson_id=str(lesson2.id),
            prerequisite_lesson_id=str(lesson1.id)
        )
        
        db_session.add_all([course, section, unit, lesson1, lesson2, prerequisite])
        db_session.commit()
        
        # Refresh all objects to load relationships
        for obj in [course, section, unit, lesson1, lesson2]:
            db_session.refresh(obj)
        
        # Test the complete hierarchy
        assert len(course.sections) == 1
        assert course.sections[0] == section
        assert len(section.units) == 1
        assert section.units[0] == unit
        assert len(unit.lessons) == 2
        assert unit.lessons[0] == lesson1
        assert unit.lessons[1] == lesson2
        assert len(lesson2.prerequisites) == 1
        assert lesson2.prerequisites[0].prerequisite_lesson == lesson1
    
    def test_cascade_deletes(self, db_session, sample_languages):
        """Test that cascade deletes work properly."""
        # Create complete hierarchy
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Test Course'
        )
        section = Section(
            course_id=str(course.id),
            name='Test Section',
            sort_order=1
        )
        unit = Unit(
            section_id=str(section.id),
            name='Test Unit',
            sort_order=1
        )
        lesson = Lesson(
            unit_id=str(unit.id),
            name='Test Lesson',
            sort_order=1
        )
        
        db_session.add_all([course, section, unit, lesson])
        db_session.commit()
        
        lesson_id = lesson.id
        unit_id = unit.id
        section_id = section.id
        
        # Delete course - should cascade to all children
        db_session.delete(course)
        db_session.commit()
        
        # Verify all children are deleted
        assert db_session.query(Section).filter_by(id=section_id).first() is None
        assert db_session.query(Unit).filter_by(id=unit_id).first() is None
        assert db_session.query(Lesson).filter_by(id=lesson_id).first() is None
    
    def test_model_to_dict_methods(self, db_session, sample_languages):
        """Test to_dict methods for all models."""
        # Create instances
        language = Language(code='test', name='Test Language')
        course = Course(
            from_language_id=str(sample_languages['english'].id),
            to_language_id=str(sample_languages['spanish'].id),
            name='Test Course'
        )
        
        db_session.add_all([language, course])
        db_session.commit()
        
        # Test language to_dict
        lang_dict = language.to_dict()
        assert lang_dict['code'] == 'test'
        assert lang_dict['name'] == 'Test Language'
        assert 'id' in lang_dict
        assert 'created_at' in lang_dict
        
        # Test course to_dict
        course_dict = course.to_dict()
        assert course_dict['name'] == 'Test Course'
        assert course_dict['difficulty_level'] == 'beginner'
        assert 'id' in course_dict
        assert 'created_at' in course_dict