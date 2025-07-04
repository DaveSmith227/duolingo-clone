"""
Unit tests for audit logging models.

Comprehensive test coverage for UserActivityLog and SystemAuditLog models
with validation and business logic testing.
"""

import pytest
import uuid
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.models.audit import (
    UserActivityLog, SystemAuditLog, ActionType, SystemActionType
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


# Test UserActivityLog Model
class TestUserActivityLog:
    """Test cases for UserActivityLog model."""
    
    def test_create_user_activity_log(self, db_session):
        """Test creating a user activity log entry."""
        log_entry = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.LOGIN.value,
            description="User logged in successfully",
            ip_address="192.168.1.1",
            session_id="session_123"
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.id is not None
        assert log_entry.action_type == ActionType.LOGIN.value
        assert log_entry.description == "User logged in successfully"
        assert log_entry.ip_address == "192.168.1.1"
        assert log_entry.session_id == "session_123"
        assert log_entry.success is True
    
    def test_user_activity_log_validation(self, db_session):
        """Test UserActivityLog validation constraints."""
        log_entry = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.LESSON_START.value
        )
        
        # Test invalid action type
        with pytest.raises(ValueError, match="Invalid action type"):
            log_entry.action_type = "invalid_action"
        
        # Test invalid duration
        with pytest.raises(ValueError, match="Duration must be between 0 and 3600000 ms"):
            log_entry.duration_ms = -1
        
        with pytest.raises(ValueError, match="Duration must be between 0 and 3600000 ms"):
            log_entry.duration_ms = 4000000  # > 1 hour
        
        # Test IP address too long
        with pytest.raises(ValueError, match="IP address too long"):
            log_entry.ip_address = "x" * 50
    
    def test_user_activity_log_metadata(self, db_session):
        """Test metadata handling in UserActivityLog."""
        metadata = {
            "device": "mobile",
            "app_version": "1.0.0",
            "lesson_score": 85
        }
        
        log_entry = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.LESSON_COMPLETE.value
        )
        
        # Test setting metadata
        log_entry.set_metadata_dict(metadata)
        assert log_entry.action_metadata is not None
        
        # Test getting metadata
        retrieved_metadata = log_entry.get_metadata_dict()
        assert retrieved_metadata == metadata
        
        # Test empty metadata
        log_entry.set_metadata_dict({})
        assert log_entry.action_metadata is None
        assert log_entry.get_metadata_dict() == {}
    
    def test_user_activity_log_with_context(self, db_session):
        """Test UserActivityLog with course/lesson/exercise context."""
        course_id = str(uuid.uuid4())
        lesson_id = str(uuid.uuid4())
        exercise_id = str(uuid.uuid4())
        
        log_entry = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.EXERCISE_ATTEMPT.value,
            course_id=course_id,
            lesson_id=lesson_id,
            exercise_id=exercise_id,
            duration_ms=15000
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.course_id == course_id
        assert log_entry.lesson_id == lesson_id
        assert log_entry.exercise_id == exercise_id
        assert log_entry.duration_ms == 15000
    
    def test_log_action_factory_method(self, db_session):
        """Test UserActivityLog.log_action factory method."""
        user_id = str(uuid.uuid4())
        metadata = {"score": 95, "hints_used": 0}
        
        log_entry = UserActivityLog.log_action(
            user_id=user_id,
            action_type=ActionType.LESSON_COMPLETE.value,
            description="Lesson completed with high score",
            ip_address="10.0.0.1",
            session_id="session_456",
            success=True,
            duration_ms=1200000,  # 20 minutes
            metadata=metadata
        )
        
        assert log_entry.user_id == user_id
        assert log_entry.action_type == ActionType.LESSON_COMPLETE.value
        assert log_entry.description == "Lesson completed with high score"
        assert log_entry.ip_address == "10.0.0.1"
        assert log_entry.session_id == "session_456"
        assert log_entry.success is True
        assert log_entry.duration_ms == 1200000
        assert log_entry.get_metadata_dict() == metadata
    
    def test_user_activity_log_failure_case(self, db_session):
        """Test logging failed user actions."""
        log_entry = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.LOGIN.value,
            success=False,
            error_message="Invalid password"
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.success is False
        assert log_entry.error_message == "Invalid password"
    
    def test_user_activity_log_indexes(self, db_session):
        """Test that database indexes are created properly."""
        # This test verifies the model can be used for queries that would benefit from indexes
        user_id = str(uuid.uuid4())
        session_id = "test_session"
        
        # Create multiple log entries
        for i in range(5):
            log_entry = UserActivityLog(
                user_id=user_id,
                action_type=ActionType.LESSON_START.value,
                session_id=session_id
            )
            db_session.add(log_entry)
        
        db_session.commit()
        
        # Query by user_id (should use index)
        user_logs = db_session.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id
        ).all()
        assert len(user_logs) == 5
        
        # Query by session_id (should use index)
        session_logs = db_session.query(UserActivityLog).filter(
            UserActivityLog.session_id == session_id
        ).all()
        assert len(session_logs) == 5


# Test SystemAuditLog Model
class TestSystemAuditLog:
    """Test cases for SystemAuditLog model."""
    
    def test_create_system_audit_log(self, db_session):
        """Test creating a system audit log entry."""
        admin_id = str(uuid.uuid4())
        
        log_entry = SystemAuditLog(
            admin_user_id=admin_id,
            action_type=SystemActionType.USER_CREATE.value,
            resource_type="user",
            resource_id=str(uuid.uuid4()),
            description="Created new user account",
            ip_address="192.168.1.100"
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.id is not None
        assert log_entry.admin_user_id == admin_id
        assert log_entry.action_type == SystemActionType.USER_CREATE.value
        assert log_entry.resource_type == "user"
        assert log_entry.description == "Created new user account"
        assert log_entry.success is True
    
    def test_system_audit_log_validation(self, db_session):
        """Test SystemAuditLog validation constraints."""
        log_entry = SystemAuditLog(
            action_type=SystemActionType.USER_UPDATE.value,
            resource_type="user",
            description="Updated user profile"
        )
        
        # Test invalid action type
        with pytest.raises(ValueError, match="Invalid system action type"):
            log_entry.action_type = "invalid_system_action"
        
        # Test empty resource type
        with pytest.raises(ValueError, match="Resource type is required"):
            log_entry.resource_type = ""
        
        # Test resource type too long
        with pytest.raises(ValueError, match="Resource type must be 50 characters or less"):
            log_entry.resource_type = "x" * 51
        
        # Test empty description
        with pytest.raises(ValueError, match="Description is required"):
            log_entry.description = ""
        
        # Test description too short
        with pytest.raises(ValueError, match="Description must be at least 5 characters"):
            log_entry.description = "abc"
    
    def test_system_audit_log_state_tracking(self, db_session):
        """Test before/after state tracking in SystemAuditLog."""
        before_state = {
            "email": "old@example.com",
            "name": "Old Name"
        }
        
        after_state = {
            "email": "new@example.com",
            "name": "New Name"
        }
        
        log_entry = SystemAuditLog(
            action_type=SystemActionType.USER_UPDATE.value,
            resource_type="user",
            resource_id=str(uuid.uuid4()),
            description="Updated user email and name"
        )
        
        # Test setting states
        log_entry.set_before_state_dict(before_state)
        log_entry.set_after_state_dict(after_state)
        
        assert log_entry.before_state is not None
        assert log_entry.after_state is not None
        
        # Test getting states
        retrieved_before = log_entry.get_before_state_dict()
        retrieved_after = log_entry.get_after_state_dict()
        
        assert retrieved_before == before_state
        assert retrieved_after == after_state
        
        # Test empty states
        log_entry.set_before_state_dict({})
        log_entry.set_after_state_dict({})
        
        assert log_entry.before_state is None
        assert log_entry.after_state is None
        assert log_entry.get_before_state_dict() == {}
        assert log_entry.get_after_state_dict() == {}
    
    def test_system_audit_log_metadata(self, db_session):
        """Test metadata handling in SystemAuditLog."""
        metadata = {
            "automated": True,
            "migration_version": "2023.1",
            "affected_records": 1500
        }
        
        log_entry = SystemAuditLog(
            action_type=SystemActionType.DATABASE_MIGRATION.value,
            resource_type="database",
            description="Applied database migration 2023.1"
        )
        
        # Test setting metadata
        log_entry.set_metadata_dict(metadata)
        assert log_entry.audit_metadata is not None
        
        # Test getting metadata
        retrieved_metadata = log_entry.get_metadata_dict()
        assert retrieved_metadata == metadata
    
    def test_log_admin_action_factory_method(self, db_session):
        """Test SystemAuditLog.log_admin_action factory method."""
        admin_id = str(uuid.uuid4())
        resource_id = str(uuid.uuid4())
        
        before_state = {"status": "active"}
        after_state = {"status": "suspended"}
        metadata = {"reason": "Terms violation"}
        
        log_entry = SystemAuditLog.log_admin_action(
            action_type=SystemActionType.USER_SUSPEND.value,
            resource_type="user",
            description="Suspended user for terms violation",
            admin_user_id=admin_id,
            resource_id=resource_id,
            ip_address="10.0.0.1",
            success=True,
            before_state=before_state,
            after_state=after_state,
            metadata=metadata
        )
        
        assert log_entry.admin_user_id == admin_id
        assert log_entry.action_type == SystemActionType.USER_SUSPEND.value
        assert log_entry.resource_type == "user"
        assert log_entry.resource_id == resource_id
        assert log_entry.description == "Suspended user for terms violation"
        assert log_entry.ip_address == "10.0.0.1"
        assert log_entry.success is True
        assert log_entry.get_before_state_dict() == before_state
        assert log_entry.get_after_state_dict() == after_state
        assert log_entry.get_metadata_dict() == metadata
    
    def test_system_audit_log_without_admin(self, db_session):
        """Test SystemAuditLog for automated system actions."""
        log_entry = SystemAuditLog(
            admin_user_id=None,  # System action
            action_type=SystemActionType.DATABASE_MIGRATION.value,
            resource_type="database",
            description="Automated database maintenance"
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.admin_user_id is None
        assert log_entry.action_type == SystemActionType.DATABASE_MIGRATION.value
    
    def test_system_audit_log_failure_case(self, db_session):
        """Test logging failed administrative actions."""
        log_entry = SystemAuditLog(
            admin_user_id=str(uuid.uuid4()),
            action_type=SystemActionType.COURSE_DELETE.value,
            resource_type="course",
            resource_id=str(uuid.uuid4()),
            description="Attempted to delete course",
            success=False,
            error_message="Course has active enrollments"
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.success is False
        assert log_entry.error_message == "Course has active enrollments"
    
    def test_system_audit_log_bulk_operation(self, db_session):
        """Test logging bulk administrative operations."""
        metadata = {
            "operation_type": "bulk_update",
            "affected_count": 250,
            "criteria": {"last_login": "older_than_90_days"}
        }
        
        log_entry = SystemAuditLog.log_admin_action(
            action_type=SystemActionType.BULK_OPERATION.value,
            resource_type="user",
            description="Bulk update of inactive users",
            admin_user_id=str(uuid.uuid4()),
            metadata=metadata
        )
        
        db_session.add(log_entry)
        db_session.commit()
        db_session.refresh(log_entry)
        
        assert log_entry.action_type == SystemActionType.BULK_OPERATION.value
        assert log_entry.get_metadata_dict()["affected_count"] == 250


# Test Integration
class TestAuditModelsIntegration:
    """Test integration between audit models and the system."""
    
    def test_audit_models_creation(self, db_session):
        """Test that both audit models can be created in the same session."""
        user_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())
        
        # Create user activity log
        user_log = UserActivityLog(
            user_id=user_id,
            action_type=ActionType.PROFILE_UPDATE.value,
            description="User updated profile"
        )
        
        # Create system audit log
        system_log = SystemAuditLog(
            admin_user_id=admin_id,
            action_type=SystemActionType.USER_UPDATE.value,
            resource_type="user",
            resource_id=user_id,
            description="Admin reviewed user profile update"
        )
        
        db_session.add(user_log)
        db_session.add(system_log)
        db_session.commit()
        
        # Verify both were created
        assert user_log.id is not None
        assert system_log.id is not None
        
        # Verify they can be queried together
        all_logs = db_session.query(UserActivityLog).count() + db_session.query(SystemAuditLog).count()
        assert all_logs == 2
    
    def test_audit_logs_with_json_data(self, db_session):
        """Test handling of complex JSON data in audit logs."""
        complex_metadata = {
            "nested": {
                "data": [1, 2, 3],
                "settings": {"key": "value"}
            },
            "arrays": ["item1", "item2"],
            "numbers": 42,
            "boolean": True
        }
        
        user_log = UserActivityLog(
            user_id=str(uuid.uuid4()),
            action_type=ActionType.SETTINGS_UPDATE.value
        )
        user_log.set_metadata_dict(complex_metadata)
        
        db_session.add(user_log)
        db_session.commit()
        db_session.refresh(user_log)
        
        retrieved_metadata = user_log.get_metadata_dict()
        assert retrieved_metadata == complex_metadata
        
        # Test that the JSON was properly stored and can be queried
        assert user_log.action_metadata is not None
        assert "nested" in user_log.action_metadata