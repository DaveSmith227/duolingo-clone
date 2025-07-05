"""
Unit Tests for GDPR Service

Tests for GDPR compliance functionality including account deletion,
data export, and data retention policies.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
import json

from app.services.gdpr_service import GDPRService
from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthSession, AuthAuditLog, PasswordHistory, PasswordResetToken
from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction
from app.models.gamification import UserDailyXP, UserHeartsLog, UserAchievement
from app.models.rbac import UserRoleAssignment


class TestGDPRService:
    """Test cases for GDPR service functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.mock_audit_logger = AsyncMock()
        self.mock_supabase_client = Mock()
        
        # Mock the audit logger dependency during initialization
        with patch('app.services.gdpr_service.get_audit_logger', return_value=self.mock_audit_logger):
            self.gdpr_service = GDPRService(self.mock_db)
        
        # Mock additional dependencies
        self.gdpr_service.supabase_client = self.mock_supabase_client
        
        # Test user data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        self.test_user.name = "Test User"
        self.test_user.created_at = datetime.now(timezone.utc)
        self.test_user.updated_at = datetime.now(timezone.utc)
        
        self.test_supabase_user = Mock(spec=SupabaseUser)
        self.test_supabase_user.id = "supabase-123"
        self.test_supabase_user.supabase_id = "supabase-abc-123"
        self.test_supabase_user.app_user_id = "user-123"
        self.test_supabase_user.email = "test@example.com"
    
    @pytest.mark.asyncio
    async def test_delete_user_account_success(self):
        """Test successful complete account deletion."""
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock count queries for deletion statistics
        count_queries = [
            2,  # OAuth providers
            3,  # Auth sessions
            1,  # Password history
            1,  # Password reset tokens
            5,  # Auth audit logs
            2,  # User courses
            10, # Lesson progress
            50, # Exercise interactions
            30, # Daily XP
            15, # Hearts log
            3,  # Achievements
            1,  # Role assignments
        ]
        count_iter = iter(count_queries)
        self.mock_db.query.return_value.filter.return_value.count.side_effect = lambda: next(count_iter)
        
        # Mock transaction
        self.mock_db.begin.return_value.__enter__ = Mock()
        self.mock_db.begin.return_value.__exit__ = Mock(return_value=None)
        
        # Mock Supabase deletion
        self.gdpr_service._delete_from_supabase_auth = AsyncMock(return_value={"success": True})
        
        # Execute deletion
        result = await self.gdpr_service.delete_user_account(
            user_id="user-123",
            ip_address="192.168.1.1",
            user_agent="Test Agent",
            reason="user_request"
        )
        
        # Verify result
        assert result["user_id"] == "user-123"
        assert result["email"] == "test@example.com"
        assert result["reason"] == "user_request"
        assert result["total_records_deleted"] == sum(count_queries) + 2  # +2 for supabase_user and main_user
        assert result["supabase_auth_deleted"] is True
        assert len(result["tables_processed"]) > 10
        
        # Verify audit logging
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is True
        assert call_args[1]["user_id"] == "user-123"
        assert "deletion_stats" in call_args[1]["metadata"]
        
        # Verify database operations
        self.mock_db.commit.assert_called()
        self.mock_db.delete.assert_called()  # For supabase_user and main user
    
    @pytest.mark.asyncio
    async def test_delete_user_account_user_not_found(self):
        """Test account deletion when user is not found."""
        # Mock user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test deletion attempt
        with pytest.raises(ValueError, match="User not found: user-123"):
            await self.gdpr_service.delete_user_account(
                user_id="user-123",
                ip_address="192.168.1.1",
                user_agent="Test Agent"
            )
        
        # Verify audit logging for failure
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is False
        assert "User not found" in call_args[1]["error_message"]
    
    @pytest.mark.asyncio
    async def test_delete_user_account_database_error(self):
        """Test account deletion with database error."""
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock database error during transaction
        self.mock_db.begin.side_effect = Exception("Database connection failed")
        
        # Test deletion attempt
        with pytest.raises(Exception, match="Database connection failed"):
            await self.gdpr_service.delete_user_account(
                user_id="user-123",
                ip_address="192.168.1.1",
                user_agent="Test Agent"
            )
        
        # Verify rollback and audit logging
        self.mock_db.rollback.assert_called_once()
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is False
    
    @pytest.mark.asyncio
    async def test_delete_user_account_without_supabase_user(self):
        """Test account deletion when no Supabase user exists."""
        # Mock user found but no supabase user
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            None  # SupabaseUser query - not found
        ]
        
        # Mock count queries (only user-related data, no auth data)
        count_queries = [
            1,  # OAuth providers
            2,  # User courses
            5,  # Lesson progress
            20, # Exercise interactions
            10, # Daily XP
            5,  # Hearts log
            2,  # Achievements
            0,  # Role assignments
        ]
        count_iter = iter(count_queries)
        self.mock_db.query.return_value.filter.return_value.count.side_effect = lambda: next(count_iter)
        
        # Mock transaction
        self.mock_db.begin.return_value.__enter__ = Mock()
        self.mock_db.begin.return_value.__exit__ = Mock(return_value=None)
        
        # Execute deletion
        result = await self.gdpr_service.delete_user_account(
            user_id="user-123",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify result
        assert result["user_id"] == "user-123"
        assert result["supabase_auth_deleted"] is None or result["supabase_auth_deleted"] is False
        assert "supabase_users" not in result["tables_processed"]
        assert result["total_records_deleted"] == sum(count_queries) + 1  # +1 for main_user only
    
    @pytest.mark.asyncio
    async def test_export_user_data_success(self):
        """Test successful user data export."""
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock related data queries
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # OAuth providers
            [],  # User courses
            [],  # Lesson progress
            [],  # Exercise interactions
            [],  # Daily XP
            [],  # Achievements
            []   # Role assignments
        ]
        
        # Mock order_by and limit for exercise interactions
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        # Execute export
        result = await self.gdpr_service.export_user_data(
            user_id="user-123",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify result structure
        assert "export_info" in result
        assert "personal_data" in result
        assert result["export_info"]["user_id"] == "user-123"
        assert result["export_info"]["gdpr_compliance"] is True
        assert result["personal_data"]["profile"]["id"] == "user-123"
        assert result["personal_data"]["profile"]["email"] == "test@example.com"
        assert result["personal_data"]["authentication"]["supabase_id"] == "supabase-abc-123"
        
        # Verify audit logging
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[0][0] == "data_export"  # event_type
        assert call_args[1]["success"] is True
        assert call_args[1]["user_id"] == "user-123"
    
    @pytest.mark.asyncio
    async def test_export_user_data_with_learning_data(self):
        """Test user data export with learning progress data."""
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock user courses data
        mock_course = Mock()
        mock_course.course_id = "course-123"
        mock_course.total_xp = 500
        mock_course.current_streak = 5
        mock_course.longest_streak = 10
        mock_course.enrolled_at = datetime.now(timezone.utc)
        
        # Mock lesson progress data
        mock_lesson_progress = Mock()
        mock_lesson_progress.lesson_id = "lesson-123"
        mock_lesson_progress.status = "completed"
        mock_lesson_progress.attempts = 2
        mock_lesson_progress.best_score = 95.0
        mock_lesson_progress.xp_earned = 50
        
        # Mock related data queries
        self.mock_db.query.return_value.filter.return_value.all.side_effect = [
            [],  # OAuth providers
            [mock_course],  # User courses
            [mock_lesson_progress],  # Lesson progress
            [],  # Daily XP
            [],  # Achievements
            []   # Role assignments
        ]
        
        # Mock exercise interactions with order_by and limit
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        
        # Execute export
        result = await self.gdpr_service.export_user_data(
            user_id="user-123",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Verify learning data is included
        assert "learning_data" in result
        assert "course_enrollments" in result["learning_data"]
        assert len(result["learning_data"]["course_enrollments"]) == 1
        assert result["learning_data"]["course_enrollments"][0]["course_id"] == "course-123"
        assert result["learning_data"]["course_enrollments"][0]["total_xp"] == 500
        
        assert "lesson_progress" in result["learning_data"]
        assert len(result["learning_data"]["lesson_progress"]) == 1
        assert result["learning_data"]["lesson_progress"][0]["lesson_id"] == "lesson-123"
        assert result["learning_data"]["lesson_progress"][0]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_export_user_data_user_not_found(self):
        """Test data export when user is not found."""
        # Mock user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test export attempt
        with pytest.raises(ValueError, match="User not found: user-123"):
            await self.gdpr_service.export_user_data(
                user_id="user-123",
                ip_address="192.168.1.1",
                user_agent="Test Agent"
            )
        
        # Verify audit logging for failure
        self.mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = self.mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is False
        assert "User not found" in call_args[1]["error_message"]
    
    def test_find_inactive_users_success(self):
        """Test finding inactive users for data retention."""
        # Mock inactive users
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=730)
        
        inactive_user1 = Mock(spec=User)
        inactive_user1.id = "user-inactive-1"
        inactive_user1.email = "inactive1@example.com"
        inactive_user1.updated_at = cutoff_date - timedelta(days=100)
        inactive_user1.created_at = cutoff_date - timedelta(days=800)
        
        inactive_user2 = Mock(spec=User)
        inactive_user2.id = "user-inactive-2"
        inactive_user2.email = "inactive2@example.com"
        inactive_user2.updated_at = cutoff_date - timedelta(days=200)
        inactive_user2.created_at = cutoff_date - timedelta(days=900)
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            inactive_user1, inactive_user2
        ]
        
        # Mock no recent activity for both users
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute find inactive users
        result = self.gdpr_service.find_inactive_users(inactive_days=730)
        
        # Verify results
        assert len(result) == 2
        assert result[0]["user_id"] == "user-inactive-1"
        assert result[0]["email"] == "inactive1@example.com"
        assert result[0]["inactive_days"] is not None
        assert result[1]["user_id"] == "user-inactive-2"
        assert result[1]["email"] == "inactive2@example.com"
    
    def test_find_inactive_users_with_recent_activity(self):
        """Test finding inactive users excludes those with recent activity."""
        # Mock users that appear inactive but have recent activity
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=730)
        
        user_with_activity = Mock(spec=User)
        user_with_activity.id = "user-active"
        user_with_activity.email = "active@example.com"
        user_with_activity.updated_at = cutoff_date - timedelta(days=100)
        
        truly_inactive_user = Mock(spec=User)
        truly_inactive_user.id = "user-truly-inactive"
        truly_inactive_user.email = "inactive@example.com"
        truly_inactive_user.updated_at = cutoff_date - timedelta(days=100)
        truly_inactive_user.created_at = cutoff_date - timedelta(days=800)
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            user_with_activity, truly_inactive_user
        ]
        
        # Mock recent activity for first user, none for second
        mock_course_activity = Mock()
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_course_activity,  # Recent course activity for first user
            None,  # No recent course activity for second user
            None   # No recent XP activity for second user
        ]
        
        # Execute find inactive users
        result = self.gdpr_service.find_inactive_users(inactive_days=730)
        
        # Verify only truly inactive user is returned
        assert len(result) == 1
        assert result[0]["user_id"] == "user-truly-inactive"
        assert result[0]["email"] == "inactive@example.com"
    
    @pytest.mark.asyncio
    async def test_delete_from_supabase_auth_success(self):
        """Test successful deletion from Supabase Auth."""
        # Mock successful Supabase deletion
        self.mock_supabase_client.auth.admin.delete_user.return_value = {"success": True}
        
        # Execute Supabase deletion
        result = await self.gdpr_service._delete_from_supabase_auth("supabase-123")
        
        # Verify result
        assert result["success"] is True
        self.mock_supabase_client.auth.admin.delete_user.assert_called_once_with("supabase-123")
    
    @pytest.mark.asyncio
    async def test_delete_from_supabase_auth_failure(self):
        """Test failure during Supabase Auth deletion."""
        # Mock Supabase deletion error
        self.mock_supabase_client.auth.admin.delete_user.side_effect = Exception("Supabase API error")
        
        # Test deletion attempt
        with pytest.raises(Exception, match="Supabase API error"):
            await self.gdpr_service._delete_from_supabase_auth("supabase-123")
        
        # Verify API call was made
        self.mock_supabase_client.auth.admin.delete_user.assert_called_once_with("supabase-123")


class TestGDPRServiceIntegration:
    """Integration tests for GDPR service."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.mock_audit_logger = AsyncMock()
        
        # Mock the audit logger dependency during initialization
        with patch('app.services.gdpr_service.get_audit_logger', return_value=self.mock_audit_logger):
            self.gdpr_service = GDPRService(self.mock_db)
    
    @pytest.mark.asyncio
    async def test_complete_account_deletion_workflow(self):
        """Test complete account deletion workflow with all data types."""
        # This would be a more comprehensive integration test
        # that verifies the complete deletion workflow
        # In a real scenario, this would use a test database
        pass
    
    @pytest.mark.asyncio
    async def test_data_export_performance_large_dataset(self):
        """Test data export performance with large datasets."""
        # This would test export functionality with large amounts of data
        # to ensure performance is acceptable and memory usage is controlled
        pass