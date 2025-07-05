"""
Analytics Service Tests

Unit tests for the AnalyticsService class including business logic validation,
data processing, and integration testing for the Duolingo clone backend.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.analytics_service import AnalyticsService
from app.models.analytics import AnalyticsEvent, UserProgressSnapshot, UserLearningStats, EventType
from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction
from app.models.user import User
from app.models.course import Course, Lesson, Exercise
from app.schemas.analytics import (
    AnalyticsEventRequest,
    UserProgressResponse,
    CourseCompletionRequest,
    LessonCompletionRequest,
    AnalyticsQueryParams,
    EventTypeEnum,
    EventCategoryEnum,
)


class TestAnalyticsService:
    """Test class for AnalyticsService business logic."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.mock_db = Mock(spec=Session)
        self.service = AnalyticsService(self.mock_db)
        
        self.user_id = str(uuid.uuid4())
        self.course_id = str(uuid.uuid4())
        self.lesson_id = str(uuid.uuid4())
        self.exercise_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
    
    def test_create_analytics_event_success(self):
        """Test successful analytics event creation."""
        # Setup mock for user context
        mock_user_context = {'level': 3, 'xp': 2500, 'streak': 15}
        
        with patch.object(self.service, '_get_user_context', return_value=mock_user_context):
            # Test data
            event_request = AnalyticsEventRequest(
                event_type=EventTypeEnum.LESSON_START,
                event_category=EventCategoryEnum.LEARNING,
                course_id=self.course_id,
                lesson_id=self.lesson_id,
                duration=120,
                is_success=True,
                session_id=self.session_id,
                event_metadata={"difficulty": "intermediate"}
            )
            
            # Call method
            result = self.service.create_analytics_event(self.user_id, event_request)
            
            # Assertions
            assert isinstance(result, AnalyticsEvent)
            assert result.user_id == self.user_id
            assert result.event_type == EventTypeEnum.LESSON_START.value
            assert result.event_category == EventCategoryEnum.LEARNING.value
            assert result.course_id == self.course_id
            assert result.lesson_id == self.lesson_id
            assert result.duration == 120
            assert result.is_success is True
            assert result.user_level == 3
            assert result.user_xp == 2500
            assert result.user_streak == 15
            assert result.session_id == self.session_id
            
            # Verify database operations
            self.mock_db.add.assert_called_once_with(result)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(result)
    
    def test_create_analytics_events_batch(self):
        """Test batch analytics event creation."""
        # Setup mock for user context
        mock_user_context = {'level': 2, 'xp': 1500, 'streak': 8}
        
        with patch.object(self.service, '_get_user_context', return_value=mock_user_context):
            with patch.object(self.service, 'create_analytics_event') as mock_create:
                # Setup mock events
                mock_events = [Mock(spec=AnalyticsEvent) for _ in range(3)]
                mock_create.side_effect = mock_events
                
                # Test data
                events = [
                    AnalyticsEventRequest(
                        event_type=EventTypeEnum.EXERCISE_ATTEMPT,
                        event_category=EventCategoryEnum.LEARNING,
                        exercise_id=self.exercise_id,
                        is_success=True
                    ),
                    AnalyticsEventRequest(
                        event_type=EventTypeEnum.EXERCISE_ATTEMPT,
                        event_category=EventCategoryEnum.LEARNING,
                        exercise_id=self.exercise_id,
                        is_success=False
                    ),
                    AnalyticsEventRequest(
                        event_type=EventTypeEnum.EXERCISE_COMPLETE,
                        event_category=EventCategoryEnum.LEARNING,
                        exercise_id=self.exercise_id,
                        is_success=True,
                        value=85.5
                    )
                ]
                
                # Call method
                result = self.service.create_analytics_events_batch(self.user_id, events)
                
                # Assertions
                assert len(result) == 3
                assert mock_create.call_count == 3
                assert all(event == mock_events[i] for i, event in enumerate(result))
    
    def test_get_user_progress_with_course_id(self):
        """Test user progress retrieval for specific course."""
        # Setup mock UserCourse
        mock_user_course = Mock(spec=UserCourse)
        mock_user_course.total_xp = 2500
        mock_user_course.current_streak = 15
        mock_user_course.longest_streak = 30
        mock_user_course.current_hearts = 4
        mock_user_course.completion_percentage = 75.0
        
        # Setup database query mocks
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user_course
        
        # Setup helper method mocks
        with patch.object(self.service, '_get_lessons_completed', return_value=25):
            with patch.object(self.service, '_get_exercises_completed', return_value=150):
                with patch.object(self.service, '_get_total_study_time', return_value=18000):
                    with patch.object(self.service, '_calculate_accuracy', return_value=87.5):
                        with patch.object(self.service, '_get_days_active', return_value=20):
                            with patch.object(self.service, '_calculate_level', return_value=3):
                                with patch.object(self.service, '_calculate_xp_to_next_level', return_value=500):
                                    with patch.object(self.service, '_get_last_activity_date', return_value=datetime.utcnow()):
                                        
                                        # Call method
                                        result = self.service.get_user_progress(
                                            self.user_id,
                                            self.course_id,
                                            include_global_stats=False
                                        )
                                        
                                        # Assertions
                                        assert isinstance(result, UserProgressResponse)
                                        assert result.user_id == self.user_id
                                        assert result.course_id == self.course_id
                                        assert result.total_xp == 2500
                                        assert result.current_streak == 15
                                        assert result.longest_streak == 30
                                        assert result.lessons_completed == 25
                                        assert result.exercises_completed == 150
                                        assert result.total_study_time == 18000
                                        assert result.accuracy_percentage == 87.5
                                        assert result.days_active == 20
                                        assert result.hearts_remaining == 4
                                        assert result.level == 3
                                        assert result.xp_to_next_level == 500
                                        assert result.completion_percentage == 75.0
    
    def test_get_user_progress_global_stats(self):
        """Test user progress retrieval with global statistics."""
        # Setup mock UserCourse objects
        mock_user_courses = [
            Mock(total_xp=1500, current_streak=10, longest_streak=20, current_hearts=3),
            Mock(total_xp=2000, current_streak=15, longest_streak=25, current_hearts=5),
            Mock(total_xp=500, current_streak=5, longest_streak=10, current_hearts=2)
        ]
        
        # Setup database query mocks
        self.mock_db.query.return_value.filter.return_value.all.return_value = mock_user_courses
        
        # Setup helper method mocks
        with patch.object(self.service, '_get_lessons_completed', return_value=75):
            with patch.object(self.service, '_get_exercises_completed', return_value=450):
                with patch.object(self.service, '_get_total_study_time', return_value=54000):
                    with patch.object(self.service, '_calculate_accuracy', return_value=89.2):
                        with patch.object(self.service, '_get_days_active', return_value=60):
                            with patch.object(self.service, '_calculate_level', return_value=4):
                                with patch.object(self.service, '_calculate_xp_to_next_level', return_value=1000):
                                    with patch.object(self.service, '_calculate_completion_percentage', return_value=80.0):
                                        with patch.object(self.service, '_get_last_activity_date', return_value=datetime.utcnow()):
                                            
                                            # Call method
                                            result = self.service.get_user_progress(
                                                self.user_id,
                                                include_global_stats=True
                                            )
                                            
                                            # Assertions
                                            assert result.total_xp == 4000  # Sum of all courses
                                            assert result.current_streak == 15  # Max of all courses
                                            assert result.longest_streak == 25  # Max of all courses
                                            assert result.hearts_remaining == 10  # Sum of all courses
    
    def test_track_course_completion(self):
        """Test course completion tracking."""
        # Setup mock UserCourse
        mock_user_course = Mock(spec=UserCourse)
        mock_user_course.completion_percentage = 95.0
        mock_user_course.total_xp = 4500
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user_course
        
        # Setup mock create_analytics_event
        mock_event = Mock(spec=AnalyticsEvent)
        mock_event.id = str(uuid.uuid4())
        mock_event.created_at = datetime.utcnow()
        
        with patch.object(self.service, 'create_analytics_event', return_value=mock_event):
            with patch.object(self.service, '_create_progress_snapshot') as mock_snapshot:
                
                # Test data
                completion_request = CourseCompletionRequest(
                    course_id=self.course_id,
                    final_score=92.5,
                    total_time_spent=36000,
                    lessons_completed=50,
                    exercises_completed=300,
                    total_xp_earned=1000
                )
                
                # Call method
                result = self.service.track_course_completion(self.user_id, completion_request)
                
                # Assertions
                assert result['user_id'] == self.user_id
                assert result['course_id'] == completion_request.course_id
                assert result['final_score'] == 92.5
                assert result['total_xp_earned'] == 1000
                assert 'event_id' in result
                assert 'completion_date' in result
                
                # Verify user course update
                assert mock_user_course.completion_percentage == 100.0
                assert mock_user_course.total_xp == 5500  # 4500 + 1000
                self.mock_db.commit.assert_called()
                
                # Verify snapshot creation
                mock_snapshot.assert_called_once_with(self.user_id, self.course_id)
    
    def test_track_lesson_completion(self):
        """Test lesson completion tracking."""
        # Setup mock UserLessonProgress
        mock_lesson_progress = Mock(spec=UserLessonProgress)
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_lesson_progress
        
        # Setup mock create_analytics_event
        mock_event = Mock(spec=AnalyticsEvent)
        mock_event.id = str(uuid.uuid4())
        mock_event.created_at = datetime.utcnow()
        
        with patch.object(self.service, 'create_analytics_event', return_value=mock_event):
            
            # Test data
            completion_request = LessonCompletionRequest(
                lesson_id=self.lesson_id,
                score=88.0,
                time_spent=1200,
                xp_earned=150,
                exercises_completed=12,
                exercises_correct=10,
                hints_used=2,
                hearts_lost=1
            )
            
            # Call method
            result = self.service.track_lesson_completion(self.user_id, completion_request)
            
            # Assertions
            assert result['user_id'] == self.user_id
            assert result['lesson_id'] == completion_request.lesson_id
            assert result['score'] == 88.0
            assert result['xp_earned'] == 150
            assert result['accuracy_percentage'] == 83.33  # 10/12 * 100
            assert 'event_id' in result
            assert 'completion_date' in result
            
            # Verify lesson progress update
            mock_lesson_progress.complete_lesson.assert_called_once_with(88.0, 150, 1200)
            self.mock_db.commit.assert_called()
    
    def test_get_user_stats(self):
        """Test comprehensive user statistics retrieval."""
        # Setup mock UserLearningStats
        mock_user_stats = Mock(spec=UserLearningStats)
        mock_user_stats.total_xp_earned = 5000
        mock_user_stats.current_streak = 25
        mock_user_stats.best_streak = 45
        mock_user_stats.total_lessons_completed = 75
        mock_user_stats.total_exercises_completed = 450
        mock_user_stats.total_study_time = 72000
        mock_user_stats.avg_daily_study_time = 1800.0
        mock_user_stats.study_days_count = 40
        mock_user_stats.total_sessions = 120
        mock_user_stats.avg_session_duration = 600.0
        mock_user_stats.overall_accuracy = 89.5
        mock_user_stats.total_hints_used = 25
        mock_user_stats.total_exercises_skipped = 5
        mock_user_stats.last_activity_date = datetime.utcnow()
        mock_user_stats.first_activity_date = datetime.utcnow() - timedelta(days=40)
        mock_user_stats.last_calculated_at = datetime.utcnow()
        mock_user_stats.created_at = datetime.utcnow()
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user_stats
        
        # Setup mock progress data
        mock_progress = UserProgressResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=5000,
            current_streak=25,
            longest_streak=45,
            lessons_completed=75,
            exercises_completed=450,
            total_study_time=72000,
            accuracy_percentage=89.5,
            days_active=40,
            hearts_remaining=5,
            level=5,
            xp_to_next_level=1000,
            completion_percentage=80.0,
            last_activity_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        with patch.object(self.service, 'get_user_progress', return_value=mock_progress):
            with patch.object(self.service, '_get_courses_completed', return_value=2):
                with patch.object(self.service, '_calculate_level', return_value=5):
                    with patch.object(self.service, '_calculate_xp_to_next_level', return_value=1000):
                        
                        # Call method
                        result = self.service.get_user_stats(
                            self.user_id,
                            self.course_id,
                            include_global_stats=True,
                            include_historical=False
                        )
                        
                        # Assertions
                        assert result.user_id == self.user_id
                        assert result.course_id == self.course_id
                        assert result.total_xp == 5000
                        assert result.current_streak == 25
                        assert result.longest_streak == 45
                        assert result.level == 5
                        assert result.xp_to_next_level == 1000
                        assert result.courses_completed == 2
                        assert result.overall_accuracy == 89.5
                        assert result.historical_snapshots is None
    
    def test_get_analytics_events_with_filters(self):
        """Test analytics events retrieval with filtering."""
        # Setup mock events
        mock_events = [Mock(spec=AnalyticsEvent) for _ in range(5)]
        
        # Setup query chain mock
        mock_query = Mock()
        mock_filter_chain = Mock()
        mock_filter_chain.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_events
        mock_query.filter.return_value = mock_filter_chain
        self.mock_db.query.return_value = mock_query
        
        # Test data
        query_params = AnalyticsQueryParams(
            course_id=self.course_id,
            event_type=EventTypeEnum.EXERCISE_ATTEMPT,
            event_category=EventCategoryEnum.LEARNING,
            date_start=datetime.utcnow() - timedelta(days=7),
            date_end=datetime.utcnow(),
            limit=10,
            offset=0
        )
        
        # Call method
        result = self.service.get_analytics_events(self.user_id, query_params)
        
        # Assertions
        assert len(result) == 5
        assert result == mock_events
        
        # Verify query was called with user filter
        self.mock_db.query.assert_called_once()
        assert mock_query.filter.call_count >= 1  # At least user_id filter
    
    def test_get_user_context(self):
        """Test user context retrieval for analytics events."""
        # Setup mock UserCourse
        mock_user_course = Mock(spec=UserCourse)
        mock_user_course.total_xp = 2500
        mock_user_course.current_streak = 15
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_user_course
        
        with patch.object(self.service, '_calculate_level', return_value=3):
            
            # Call method
            result = self.service._get_user_context(self.user_id, self.course_id)
            
            # Assertions
            assert result['xp'] == 2500
            assert result['streak'] == 15
            assert result['level'] == 3
    
    def test_get_user_context_no_course(self):
        """Test user context retrieval without course ID."""
        # Call method
        result = self.service._get_user_context(self.user_id)
        
        # Assertions
        assert result['level'] == 1
        assert result['xp'] == 0
        assert result['streak'] == 0
    
    def test_calculate_level(self):
        """Test level calculation based on XP."""
        # Test cases
        test_cases = [
            (0, 1),
            (500, 1),
            (999, 1),
            (1000, 2),
            (1500, 2),
            (2000, 3),
            (5000, 6)
        ]
        
        for xp, expected_level in test_cases:
            result = self.service._calculate_level(xp)
            assert result == expected_level, f"XP {xp} should be level {expected_level}, got {result}"
    
    def test_calculate_xp_to_next_level(self):
        """Test XP to next level calculation."""
        # Test cases
        test_cases = [
            (0, 1000),      # Level 1, need 1000 XP for level 2
            (500, 500),     # Level 1, need 500 more XP for level 2
            (1000, 1000),   # Level 2, need 1000 XP for level 3
            (1500, 500),    # Level 2, need 500 more XP for level 3
            (2000, 1000),   # Level 3, need 1000 XP for level 4
        ]
        
        for xp, expected_xp_needed in test_cases:
            result = self.service._calculate_xp_to_next_level(xp)
            assert result == expected_xp_needed, f"XP {xp} should need {expected_xp_needed} XP to next level, got {result}"
    
    def test_get_lessons_completed(self):
        """Test lessons completed count retrieval."""
        # Setup mock query
        mock_query = Mock()
        mock_query.scalar.return_value = 25
        self.mock_db.query.return_value.filter.return_value = mock_query
        
        # Call method
        result = self.service._get_lessons_completed(self.user_id, self.course_id)
        
        # Assertions
        assert result == 25
        
        # Verify query structure
        assert self.mock_db.query.called
        assert mock_query.scalar.called
    
    def test_get_exercises_completed(self):
        """Test exercises completed count retrieval."""
        # Setup mock query
        mock_query = Mock()
        mock_query.scalar.return_value = 150
        self.mock_db.query.return_value.filter.return_value = mock_query
        
        # Call method
        result = self.service._get_exercises_completed(self.user_id, self.course_id)
        
        # Assertions
        assert result == 150
    
    def test_calculate_accuracy(self):
        """Test accuracy percentage calculation."""
        # Setup mock query result
        mock_result = Mock()
        mock_result.total = 100
        mock_result.correct = 85
        
        mock_query = Mock()
        mock_query.first.return_value = mock_result
        self.mock_db.query.return_value.filter.return_value = mock_query
        
        # Call method
        result = self.service._calculate_accuracy(self.user_id, self.course_id)
        
        # Assertions
        assert result == 85.0  # 85/100 * 100
    
    def test_calculate_accuracy_no_attempts(self):
        """Test accuracy calculation with no attempts."""
        # Setup mock query result
        mock_result = Mock()
        mock_result.total = 0
        mock_result.correct = 0
        
        mock_query = Mock()
        mock_query.first.return_value = mock_result
        self.mock_db.query.return_value.filter.return_value = mock_query
        
        # Call method
        result = self.service._calculate_accuracy(self.user_id, self.course_id)
        
        # Assertions
        assert result == 0.0
    
    def test_create_progress_snapshot(self):
        """Test progress snapshot creation."""
        # Setup mock progress data
        mock_progress = UserProgressResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=2500,
            current_streak=15,
            lessons_completed=25,
            exercises_completed=150,
            total_study_time=18000,
            accuracy_percentage=87.5,
            days_active=20,
            hearts_remaining=4,
            level=3,
            xp_to_next_level=500,
            completion_percentage=60.0,
            last_activity_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        with patch.object(self.service, 'get_user_progress', return_value=mock_progress):
            
            # Call method
            result = self.service._create_progress_snapshot(self.user_id, self.course_id)
            
            # Assertions
            assert isinstance(result, UserProgressSnapshot)
            assert result.user_id == self.user_id
            assert result.course_id == self.course_id
            assert result.total_xp == 2500
            assert result.current_streak == 15
            assert result.lessons_completed == 25
            assert result.exercises_completed == 150
            assert result.accuracy_percentage == 87.5
            assert result.snapshot_type == 'daily'
            
            # Verify database operations
            self.mock_db.add.assert_called_once_with(result)
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(result)


class TestAnalyticsServiceEdgeCases:
    """Test class for analytics service edge cases and error handling."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.mock_db = Mock(spec=Session)
        self.service = AnalyticsService(self.mock_db)
        self.user_id = str(uuid.uuid4())
        self.course_id = str(uuid.uuid4())
    
    def test_create_analytics_event_metadata_handling(self):
        """Test analytics event creation with metadata."""
        # Setup mock for user context
        mock_user_context = {'level': 1, 'xp': 0, 'streak': 0}
        
        with patch.object(self.service, '_get_user_context', return_value=mock_user_context):
            
            # Test data with metadata
            metadata = {
                "difficulty": "beginner",
                "lesson_type": "vocabulary",
                "user_agent": "Mozilla/5.0...",
                "custom_data": {"score": 85.5, "attempts": 3}
            }
            
            event_request = AnalyticsEventRequest(
                event_type=EventTypeEnum.LESSON_COMPLETE,
                event_category=EventCategoryEnum.LEARNING,
                course_id=self.course_id,
                value=85.5,
                event_metadata=metadata
            )
            
            # Call method
            result = self.service.create_analytics_event(self.user_id, event_request)
            
            # Assertions
            assert result.get_metadata_dict() == metadata
    
    def test_track_course_completion_no_user_course(self):
        """Test course completion tracking when user course doesn't exist."""
        # Setup mock to return None for user course
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Setup mock create_analytics_event
        mock_event = Mock(spec=AnalyticsEvent)
        mock_event.id = str(uuid.uuid4())
        mock_event.created_at = datetime.utcnow()
        
        with patch.object(self.service, 'create_analytics_event', return_value=mock_event):
            with patch.object(self.service, '_create_progress_snapshot') as mock_snapshot:
                
                # Test data
                completion_request = CourseCompletionRequest(
                    course_id=self.course_id,
                    final_score=92.5,
                    total_time_spent=36000
                )
                
                # Call method
                result = self.service.track_course_completion(self.user_id, completion_request)
                
                # Assertions - should still work without user course
                assert result['user_id'] == self.user_id
                assert result['course_id'] == completion_request.course_id
                assert 'event_id' in result
                
                # Verify snapshot creation still called
                mock_snapshot.assert_called_once()
    
    def test_get_user_progress_no_data(self):
        """Test user progress retrieval with no existing data."""
        # Setup mocks to return None/0 for all data
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Setup helper method mocks to return zeros
        with patch.object(self.service, '_get_lessons_completed', return_value=0):
            with patch.object(self.service, '_get_exercises_completed', return_value=0):
                with patch.object(self.service, '_get_total_study_time', return_value=0):
                    with patch.object(self.service, '_calculate_accuracy', return_value=0.0):
                        with patch.object(self.service, '_get_days_active', return_value=0):
                            with patch.object(self.service, '_calculate_level', return_value=1):
                                with patch.object(self.service, '_calculate_xp_to_next_level', return_value=1000):
                                    with patch.object(self.service, '_calculate_completion_percentage', return_value=0.0):
                                        with patch.object(self.service, '_get_last_activity_date', return_value=None):
                                            
                                            # Call method
                                            result = self.service.get_user_progress(self.user_id)
                                            
                                            # Assertions - should return valid response with zeros
                                            assert result.user_id == self.user_id
                                            assert result.total_xp == 0
                                            assert result.current_streak == 0
                                            assert result.lessons_completed == 0
                                            assert result.level == 1
                                            assert result.xp_to_next_level == 1000
    
    def test_get_user_stats_creates_new_stats(self):
        """Test user stats retrieval when stats don't exist yet."""
        # Setup mock to return None for existing stats
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Setup mock progress data
        mock_progress = UserProgressResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=1000,
            current_streak=5,
            longest_streak=10,
            lessons_completed=10,
            exercises_completed=50,
            total_study_time=7200,
            accuracy_percentage=85.0,
            days_active=10,
            hearts_remaining=5,
            level=2,
            xp_to_next_level=1000,
            completion_percentage=20.0,
            last_activity_date=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        with patch.object(self.service, 'get_user_progress', return_value=mock_progress):
            with patch.object(self.service, '_calculate_user_stats') as mock_calculate:
                
                # Setup mock calculated stats
                mock_calculated_stats = Mock(spec=UserLearningStats)
                mock_calculated_stats.total_xp_earned = 1000
                mock_calculated_stats.current_streak = 5
                mock_calculated_stats.best_streak = 10
                mock_calculated_stats.total_lessons_completed = 10
                mock_calculated_stats.total_exercises_completed = 50
                mock_calculated_stats.total_study_time = 7200
                mock_calculated_stats.avg_daily_study_time = 720.0
                mock_calculated_stats.study_days_count = 10
                mock_calculated_stats.total_sessions = 30
                mock_calculated_stats.avg_session_duration = 240.0
                mock_calculated_stats.overall_accuracy = 85.0
                mock_calculated_stats.total_hints_used = 5
                mock_calculated_stats.total_exercises_skipped = 1
                mock_calculated_stats.last_activity_date = datetime.utcnow()
                mock_calculated_stats.first_activity_date = datetime.utcnow() - timedelta(days=10)
                mock_calculated_stats.last_calculated_at = datetime.utcnow()
                mock_calculated_stats.created_at = datetime.utcnow()
                
                mock_calculate.return_value = mock_calculated_stats
                
                with patch.object(self.service, '_get_courses_completed', return_value=0):
                    with patch.object(self.service, '_calculate_level', return_value=2):
                        with patch.object(self.service, '_calculate_xp_to_next_level', return_value=1000):
                            
                            # Call method
                            result = self.service.get_user_stats(self.user_id, self.course_id)
                            
                            # Assertions
                            assert result.user_id == self.user_id
                            assert result.total_xp == 1000
                            assert result.current_streak == 5
                            
                            # Verify stats calculation was called
                            mock_calculate.assert_called_once_with(self.user_id, self.course_id)