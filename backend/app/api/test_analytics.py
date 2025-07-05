"""
Analytics API Tests

Comprehensive unit tests for analytics endpoints including event tracking,
progress monitoring, and user statistics for the Duolingo clone backend.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.analytics import AnalyticsEvent, UserProgressSnapshot, UserLearningStats, EventType
from app.models.user import User
from app.models.course import Course
from app.models.progress import UserCourse, UserLessonProgress
from app.schemas.analytics import (
    AnalyticsEventRequest,
    EventTypeEnum,
    EventCategoryEnum,
    DeviceTypeEnum,
    PlatformEnum,
)

client = TestClient(app)


class TestAnalyticsEndpoints:
    """Test class for analytics API endpoints."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.user_id = str(uuid.uuid4())
        self.course_id = str(uuid.uuid4())
        self.lesson_id = str(uuid.uuid4())
        self.exercise_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        # Mock user
        self.mock_user = Mock(spec=User)
        self.mock_user.id = self.user_id
        self.mock_user.email = "test@example.com"
        
        # Mock JWT token
        self.valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfaWQiLCJpYXQiOjE2MzI0NjQ0MDB9.test_signature"
        self.auth_headers = {"Authorization": f"Bearer {self.valid_token}"}
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.create_analytics_event')
    def test_track_analytics_event_success(self, mock_create_event, mock_get_db, mock_get_user):
        """Test successful analytics event tracking."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock created event
        mock_event = Mock(spec=AnalyticsEvent)
        mock_event.id = str(uuid.uuid4())
        mock_event.user_id = self.user_id
        mock_event.event_type = EventType.LESSON_START.value
        mock_event.event_name = "Lesson Start"
        mock_event.event_category = "learning"
        mock_event.created_at = datetime.utcnow()
        mock_event.updated_at = datetime.utcnow()
        mock_event.event_timestamp = datetime.utcnow()
        
        mock_create_event.return_value = mock_event
        
        # Test data
        event_data = {
            "event_type": "lesson_start",
            "event_category": "learning",
            "course_id": self.course_id,
            "lesson_id": self.lesson_id,
            "duration": 120,
            "is_success": True,
            "session_id": self.session_id,
            "device_type": "web",
            "platform": "web"
        }
        
        # Make request
        response = client.post(
            "/analytics/events",
            json=event_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "lesson_start"
        assert data["event_category"] == "learning"
        assert data["user_id"] == self.user_id
        mock_create_event.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_track_analytics_event_validation_error(self, mock_get_db, mock_get_user):
        """Test analytics event tracking with validation error."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Test data with invalid event type
        event_data = {
            "event_type": "invalid_event_type",
            "event_category": "learning"
        }
        
        # Make request
        response = client.post(
            "/analytics/events",
            json=event_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 422
        assert "validation_error" in response.json()["error"]["type"]
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_track_analytics_event_unauthorized(self, mock_get_db, mock_get_user):
        """Test analytics event tracking without authorization."""
        # Test data
        event_data = {
            "event_type": "lesson_start",
            "event_category": "learning"
        }
        
        # Make request without auth headers
        response = client.post("/analytics/events", json=event_data)
        
        # Assertions
        assert response.status_code == 401
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.create_analytics_events_batch')
    def test_track_analytics_events_batch_success(self, mock_create_batch, mock_get_db, mock_get_user):
        """Test successful batch analytics event tracking."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock created events
        mock_events = []
        for i in range(3):
            mock_event = Mock(spec=AnalyticsEvent)
            mock_event.id = str(uuid.uuid4())
            mock_event.user_id = self.user_id
            mock_event.event_type = EventType.EXERCISE_ATTEMPT.value
            mock_event.event_name = "Exercise Attempt"
            mock_event.event_category = "learning"
            mock_event.created_at = datetime.utcnow()
            mock_event.updated_at = datetime.utcnow()
            mock_event.event_timestamp = datetime.utcnow()
            mock_events.append(mock_event)
        
        mock_create_batch.return_value = mock_events
        
        # Test data
        batch_data = {
            "events": [
                {
                    "event_type": "exercise_attempt",
                    "event_category": "learning",
                    "exercise_id": self.exercise_id,
                    "is_success": True
                },
                {
                    "event_type": "exercise_attempt",
                    "event_category": "learning",
                    "exercise_id": self.exercise_id,
                    "is_success": False
                },
                {
                    "event_type": "exercise_complete",
                    "event_category": "learning",
                    "exercise_id": self.exercise_id,
                    "is_success": True,
                    "value": 85.5
                }
            ]
        }
        
        # Make request
        response = client.post(
            "/analytics/events/batch",
            json=batch_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 3
        assert all(event["user_id"] == self.user_id for event in data)
        mock_create_batch.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_track_analytics_events_batch_too_many_events(self, mock_get_db, mock_get_user):
        """Test batch analytics event tracking with too many events."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Test data with too many events (over 100 limit)
        batch_data = {
            "events": [
                {
                    "event_type": "exercise_attempt",
                    "event_category": "learning"
                }
            ] * 101
        }
        
        # Make request
        response = client.post(
            "/analytics/events/batch",
            json=batch_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 422
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.get_user_progress')
    def test_get_user_progress_success(self, mock_get_progress, mock_get_db, mock_get_user):
        """Test successful user progress retrieval."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock progress response
        from app.schemas.analytics import UserProgressResponse
        mock_progress = UserProgressResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=2500,
            current_streak=15,
            longest_streak=30,
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
        
        mock_get_progress.return_value = mock_progress
        
        # Make request
        response = client.get(
            f"/analytics/progress?course_id={self.course_id}&include_global_stats=true",
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == self.user_id
        assert data["total_xp"] == 2500
        assert data["current_streak"] == 15
        assert data["accuracy_percentage"] == 87.5
        mock_get_progress.assert_called_once_with(self.user_id, self.course_id, True)
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.track_course_completion')
    def test_track_course_completion_success(self, mock_track_completion, mock_get_db, mock_get_user):
        """Test successful course completion tracking."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock completion result
        mock_result = {
            'event_id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'course_id': self.course_id,
            'completion_date': datetime.utcnow(),
            'final_score': 92.5,
            'total_time_spent': 36000,
            'total_xp_earned': 5000,
            'achievements_unlocked': [],
            'created_at': datetime.utcnow()
        }
        
        mock_track_completion.return_value = mock_result
        
        # Test data
        completion_data = {
            "course_id": self.course_id,
            "final_score": 92.5,
            "total_time_spent": 36000,
            "lessons_completed": 50,
            "exercises_completed": 300,
            "total_xp_earned": 5000
        }
        
        # Make request
        response = client.post(
            "/analytics/course-completion",
            json=completion_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == self.user_id
        assert data["final_score"] == 92.5
        assert data["total_xp_earned"] == 5000
        mock_track_completion.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.track_lesson_completion')
    def test_track_lesson_completion_success(self, mock_track_completion, mock_get_db, mock_get_user):
        """Test successful lesson completion tracking."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock completion result
        mock_result = {
            'event_id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'lesson_id': self.lesson_id,
            'completion_date': datetime.utcnow(),
            'score': 88.0,
            'time_spent': 1200,
            'xp_earned': 150,
            'exercises_completed': 12,
            'exercises_correct': 10,
            'accuracy_percentage': 83.33,
            'hints_used': 2,
            'hearts_lost': 1,
            'achievements_unlocked': [],
            'created_at': datetime.utcnow()
        }
        
        mock_track_completion.return_value = mock_result
        
        # Test data
        completion_data = {
            "lesson_id": self.lesson_id,
            "score": 88.0,
            "time_spent": 1200,
            "xp_earned": 150,
            "exercises_completed": 12,
            "exercises_correct": 10,
            "hints_used": 2,
            "hearts_lost": 1
        }
        
        # Make request
        response = client.post(
            "/analytics/lesson-completion",
            json=completion_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == self.user_id
        assert data["score"] == 88.0
        assert data["xp_earned"] == 150
        assert data["accuracy_percentage"] == 83.33
        mock_track_completion.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_track_lesson_completion_validation_error(self, mock_get_db, mock_get_user):
        """Test lesson completion tracking with validation error."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Test data with invalid score
        completion_data = {
            "lesson_id": self.lesson_id,
            "score": 150.0,  # Invalid score > 100
            "time_spent": 1200,
            "xp_earned": 150,
            "exercises_completed": 12,
            "exercises_correct": 10
        }
        
        # Make request
        response = client.post(
            "/analytics/lesson-completion",
            json=completion_data,
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 422
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.get_user_stats')
    def test_get_user_stats_success(self, mock_get_stats, mock_get_db, mock_get_user):
        """Test successful user statistics retrieval."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock stats response
        from app.schemas.analytics import UserStatsResponse
        mock_stats = UserStatsResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=5000,
            current_streak=25,
            longest_streak=45,
            level=5,
            xp_to_next_level=1000,
            lessons_completed=75,
            exercises_completed=450,
            courses_completed=2,
            completion_percentage=80.0,
            total_study_time=72000,
            avg_daily_study_time=1800.0,
            study_days_count=40,
            total_sessions=120,
            avg_session_duration=600.0,
            overall_accuracy=89.5,
            total_hints_used=25,
            total_exercises_skipped=5,
            last_activity_date=datetime.utcnow(),
            first_activity_date=datetime.utcnow() - timedelta(days=40),
            achievements_earned=15,
            badges_earned=8,
            hearts_remaining=5,
            historical_snapshots=None,
            last_calculated_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        mock_get_stats.return_value = mock_stats
        
        # Make request
        response = client.get(
            f"/analytics/user-stats?course_id={self.course_id}&include_historical=true",
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == self.user_id
        assert data["total_xp"] == 5000
        assert data["overall_accuracy"] == 89.5
        assert data["courses_completed"] == 2
        mock_get_stats.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    @patch('app.services.analytics_service.AnalyticsService.get_analytics_events')
    def test_get_analytics_events_success(self, mock_get_events, mock_get_db, mock_get_user):
        """Test successful analytics events retrieval."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock events
        mock_events = []
        for i in range(5):
            mock_event = Mock(spec=AnalyticsEvent)
            mock_event.id = str(uuid.uuid4())
            mock_event.user_id = self.user_id
            mock_event.event_type = EventType.EXERCISE_ATTEMPT.value
            mock_event.event_name = "Exercise Attempt"
            mock_event.event_category = "learning"
            mock_event.course_id = self.course_id
            mock_event.lesson_id = self.lesson_id
            mock_event.exercise_id = self.exercise_id
            mock_event.value = None
            mock_event.duration = 30
            mock_event.is_success = i % 2 == 0
            mock_event.user_level = 3
            mock_event.user_xp = 2500
            mock_event.user_streak = 15
            mock_event.session_id = self.session_id
            mock_event.device_type = "web"
            mock_event.platform = "web"
            mock_event.event_metadata = None
            mock_event.created_at = datetime.utcnow()
            mock_event.updated_at = datetime.utcnow()
            mock_event.event_timestamp = datetime.utcnow()
            mock_events.append(mock_event)
        
        mock_get_events.return_value = mock_events
        
        # Make request
        response = client.get(
            f"/analytics/events?course_id={self.course_id}&event_type=exercise_attempt&limit=10",
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all(event["user_id"] == self.user_id for event in data)
        assert all(event["event_type"] == "exercise_attempt" for event in data)
        mock_get_events.assert_called_once()
    
    @patch('app.api.deps.get_current_user')
    @patch('app.api.deps.get_db')
    def test_get_analytics_metrics_success(self, mock_get_db, mock_get_user):
        """Test successful analytics metrics retrieval."""
        # Setup mocks
        mock_get_user.return_value = self.mock_user
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.get(
            "/analytics/metrics",
            headers=self.auth_headers
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "events_by_type" in data
        assert "events_by_category" in data
        assert "last_updated" in data
    
    @patch('app.api.deps.get_db')
    def test_analytics_health_check_success(self, mock_get_db):
        """Test successful analytics health check."""
        # Setup mocks
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.count.return_value = 100
        mock_db.query.return_value = mock_query
        mock_get_db.return_value = mock_db
        
        # Make request
        response = client.get("/analytics/health")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analytics"
        assert data["total_events"] == 100
    
    def test_analytics_health_check_database_error(self):
        """Test analytics health check with database error."""
        # Mock database error
        with patch('app.api.deps.get_db') as mock_get_db:
            mock_db = Mock(spec=Session)
            mock_db.query.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_db
            
            # Make request
            response = client.get("/analytics/health")
            
            # Assertions
            assert response.status_code == 503
            assert "Analytics service unhealthy" in response.json()["detail"]


class TestAnalyticsModels:
    """Test class for analytics model validation."""
    
    def test_analytics_event_creation(self):
        """Test AnalyticsEvent model creation."""
        event = AnalyticsEvent(
            user_id=str(uuid.uuid4()),
            event_type=EventType.LESSON_START.value,
            event_name="Lesson Start",
            event_category="learning",
            event_timestamp=datetime.utcnow()
        )
        
        assert event.event_type == EventType.LESSON_START.value
        assert event.event_category == "learning"
        assert event.user_id is not None
    
    def test_analytics_event_metadata(self):
        """Test AnalyticsEvent metadata handling."""
        event = AnalyticsEvent(
            user_id=str(uuid.uuid4()),
            event_type=EventType.EXERCISE_COMPLETE.value,
            event_name="Exercise Complete",
            event_category="learning",
            event_timestamp=datetime.utcnow()
        )
        
        # Test setting metadata
        metadata = {"difficulty": "intermediate", "score": 85.5}
        event.set_metadata_dict(metadata)
        
        # Test getting metadata
        retrieved_metadata = event.get_metadata_dict()
        assert retrieved_metadata["difficulty"] == "intermediate"
        assert retrieved_metadata["score"] == 85.5
    
    def test_user_progress_snapshot_creation(self):
        """Test UserProgressSnapshot model creation."""
        snapshot = UserProgressSnapshot(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            total_xp=2500,
            current_streak=15,
            lessons_completed=25,
            exercises_completed=150,
            accuracy_percentage=87.5,
            snapshot_date=datetime.utcnow()
        )
        
        assert snapshot.total_xp == 2500
        assert snapshot.accuracy_percentage == 87.5
        assert 0.0 <= snapshot.accuracy_percentage <= 100.0
    
    def test_user_learning_stats_creation(self):
        """Test UserLearningStats model creation."""
        stats = UserLearningStats(
            user_id=str(uuid.uuid4()),
            course_id=str(uuid.uuid4()),
            total_xp_earned=5000,
            overall_accuracy=89.5,
            best_streak=30,
            current_streak=15,
            total_study_time=72000,
            last_calculated_at=datetime.utcnow()
        )
        
        assert stats.total_xp_earned == 5000
        assert stats.overall_accuracy == 89.5
        assert stats.best_streak >= stats.current_streak


class TestAnalyticsService:
    """Test class for analytics service methods."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.mock_db = Mock(spec=Session)
        self.user_id = str(uuid.uuid4())
        self.course_id = str(uuid.uuid4())
    
    @patch('app.services.analytics_service.AnalyticsService._get_user_context')
    def test_create_analytics_event(self, mock_get_context):
        """Test AnalyticsService.create_analytics_event method."""
        from app.services.analytics_service import AnalyticsService
        
        # Setup mocks
        mock_get_context.return_value = {'level': 3, 'xp': 2500, 'streak': 15}
        
        service = AnalyticsService(self.mock_db)
        
        # Test data
        event_request = AnalyticsEventRequest(
            event_type=EventTypeEnum.LESSON_START,
            event_category=EventCategoryEnum.LEARNING,
            course_id=self.course_id,
            duration=120,
            is_success=True
        )
        
        # Call method
        result = service.create_analytics_event(self.user_id, event_request)
        
        # Assertions
        assert self.mock_db.add.called
        assert self.mock_db.commit.called
        assert self.mock_db.refresh.called
        mock_get_context.assert_called_once_with(self.user_id, self.course_id)
    
    @patch('app.services.analytics_service.AnalyticsService.get_user_progress')
    def test_get_user_stats_calculation(self, mock_get_progress):
        """Test user statistics calculation."""
        from app.services.analytics_service import AnalyticsService
        from app.schemas.analytics import UserProgressResponse
        
        # Setup mocks
        mock_progress = UserProgressResponse(
            user_id=self.user_id,
            course_id=self.course_id,
            total_xp=2500,
            current_streak=15,
            longest_streak=30,
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
        
        mock_get_progress.return_value = mock_progress
        
        # Mock UserLearningStats query
        mock_stats = Mock()
        mock_stats.total_xp_earned = 2500
        mock_stats.overall_accuracy = 87.5
        mock_stats.best_streak = 30
        mock_stats.current_streak = 15
        mock_stats.total_study_time = 18000
        mock_stats.avg_daily_study_time = 900.0
        mock_stats.study_days_count = 20
        mock_stats.total_sessions = 60
        mock_stats.avg_session_duration = 300.0
        mock_stats.total_hints_used = 10
        mock_stats.total_exercises_skipped = 2
        mock_stats.last_activity_date = datetime.utcnow()
        mock_stats.first_activity_date = datetime.utcnow() - timedelta(days=20)
        mock_stats.last_calculated_at = datetime.utcnow()
        mock_stats.created_at = datetime.utcnow()
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_stats
        
        service = AnalyticsService(self.mock_db)
        
        # Call method
        result = service.get_user_stats(self.user_id, self.course_id)
        
        # Assertions
        assert result.user_id == self.user_id
        assert result.total_xp == 2500
        assert result.overall_accuracy == 87.5
        assert result.best_streak == 30