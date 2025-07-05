"""
Unit Tests for Data Retention Service

Tests for data retention policy enforcement, automatic cleanup,
and user notification functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.services.data_retention_service import DataRetentionService
from app.models.user import User
from app.models.auth import SupabaseUser, AuthSession
from app.models.progress import UserCourse, UserDailyXP
from app.models.privacy import ConsentAuditLog


class TestDataRetentionService:
    """Test cases for data retention service functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.mock_audit_logger = AsyncMock()
        self.mock_gdpr_service = Mock()
        
        # Mock the audit logger dependency during initialization
        with patch('app.services.data_retention_service.get_audit_logger', return_value=self.mock_audit_logger):
            self.retention_service = DataRetentionService(self.mock_db)
        
        # Mock GDPR service dependency
        self.retention_service.gdpr_service = self.mock_gdpr_service
        
        # Test dates
        self.now = datetime.now(timezone.utc)
        self.cutoff_2_years = self.now - timedelta(days=730)
        self.cutoff_22_months = self.now - timedelta(days=660)
        
        # Test user data
        self.inactive_user = Mock(spec=User)
        self.inactive_user.id = "user-inactive"
        self.inactive_user.email = "inactive@example.com"
        self.inactive_user.name = "Inactive User"
        self.inactive_user.created_at = self.now - timedelta(days=800)
        self.inactive_user.updated_at = self.cutoff_2_years - timedelta(days=10)
        self.inactive_user.deleted_at = None
        
        self.active_user = Mock(spec=User)
        self.active_user.id = "user-active"
        self.active_user.email = "active@example.com"
        self.active_user.name = "Active User"
        self.active_user.created_at = self.now - timedelta(days=100)
        self.active_user.updated_at = self.now - timedelta(days=1)
        self.active_user.deleted_at = None
    
    def test_find_inactive_accounts_success(self):
        """Test successful identification of inactive accounts."""
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.return_value = [
            self.inactive_user, self.active_user
        ]
        
        # Mock no recent activity for inactive user
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No recent course activity for inactive user
            None,  # No recent XP for inactive user
            None,  # No supabase user for inactive user
            Mock(),  # Recent course activity for active user
        ]
        
        # Find inactive accounts
        result = self.retention_service.find_inactive_accounts(inactive_days=730)
        
        # Verify result
        assert len(result) == 1
        assert result[0]["user_id"] == "user-inactive"
        assert result[0]["email"] == "inactive@example.com"
        assert result[0]["inactive_days"] is not None
        assert result[0]["account_age_days"] is not None
    
    def test_find_inactive_accounts_with_recent_auth(self):
        """Test inactive account detection with recent authentication activity."""
        # Mock user that appears inactive but has recent auth
        user_with_auth = Mock(spec=User)
        user_with_auth.id = "user-with-auth"
        user_with_auth.email = "hasauth@example.com"
        user_with_auth.updated_at = self.cutoff_2_years - timedelta(days=10)
        user_with_auth.deleted_at = None
        
        # Mock supabase user and recent session
        mock_supabase_user = Mock(spec=SupabaseUser)
        mock_supabase_user.id = "supabase-123"
        
        mock_recent_session = Mock(spec=AuthSession)
        mock_recent_session.created_at = self.now - timedelta(days=1)
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.all.return_value = [user_with_auth]
        
        # Mock query sequence: no course activity, no XP, but has supabase user and recent auth
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No recent course activity
            None,  # No recent XP
            mock_supabase_user,  # Has supabase user
            mock_recent_session  # Has recent authentication
        ]
        
        # Find inactive accounts
        result = self.retention_service.find_inactive_accounts(
            inactive_days=730,
            include_recent_auth=True
        )
        
        # Verify user is not considered inactive due to recent auth
        assert len(result) == 0
    
    def test_find_accounts_for_warning(self):
        """Test finding accounts that need inactivity warnings."""
        # Mock find_inactive_accounts to return warning candidates
        warning_candidate = {
            "user_id": "user-warning",
            "email": "warning@example.com",
            "inactive_days": 670  # Between 22 months and 2 years
        }
        
        with patch.object(self.retention_service, 'find_inactive_accounts', return_value=[warning_candidate]):
            result = self.retention_service.find_accounts_for_warning(warning_days=660)
            
            assert len(result) == 1
            assert result[0]["user_id"] == "user-warning"
            assert result[0]["inactive_days"] == 670
    
    @pytest.mark.asyncio
    async def test_send_inactivity_warnings_success(self):
        """Test successful sending of inactivity warnings."""
        # Mock accounts needing warnings
        warning_accounts = [
            {
                "user_id": "user-1",
                "email": "user1@example.com",
                "inactive_days": 670
            },
            {
                "user_id": "user-2", 
                "email": "user2@example.com",
                "inactive_days": 680
            }
        ]
        
        # Mock _send_warning_email method
        self.retention_service._send_warning_email = AsyncMock()
        
        # Send warnings
        result = await self.retention_service.send_inactivity_warnings(
            accounts=warning_accounts,
            dry_run=False
        )
        
        # Verify results
        assert result["total_accounts"] == 2
        assert result["warnings_sent"] == 2
        assert result["warnings_failed"] == 0
        assert result["dry_run"] is False
        assert len(result["results"]) == 2
        
        # Verify audit logging
        assert self.mock_audit_logger.log_authentication_event.call_count == 2
        
        # Verify email sending was called
        assert self.retention_service._send_warning_email.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_inactivity_warnings_dry_run(self):
        """Test inactivity warnings in dry run mode."""
        warning_accounts = [
            {
                "user_id": "user-1",
                "email": "user1@example.com",
                "inactive_days": 670
            }
        ]
        
        # Mock _send_warning_email method
        self.retention_service._send_warning_email = AsyncMock()
        
        # Send warnings in dry run
        result = await self.retention_service.send_inactivity_warnings(
            accounts=warning_accounts,
            dry_run=True
        )
        
        # Verify results
        assert result["total_accounts"] == 1
        assert result["warnings_sent"] == 1
        assert result["dry_run"] is True
        assert result["results"][0]["status"] == "would_send"
        
        # Verify email was not actually sent in dry run
        self.retention_service._send_warning_email.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_inactivity_warnings_with_failure(self):
        """Test inactivity warning sending with some failures."""
        warning_accounts = [
            {"user_id": "user-1", "email": "user1@example.com", "inactive_days": 670},
            {"user_id": "user-2", "email": "user2@example.com", "inactive_days": 680}
        ]
        
        # Mock _send_warning_email to fail for second user
        async def mock_send_email(user_id, email, inactive_days):
            if user_id == "user-2":
                raise Exception("Email service error")
        
        self.retention_service._send_warning_email = AsyncMock(side_effect=mock_send_email)
        
        # Send warnings
        result = await self.retention_service.send_inactivity_warnings(
            accounts=warning_accounts,
            dry_run=False
        )
        
        # Verify results
        assert result["warnings_sent"] == 1
        assert result["warnings_failed"] == 1
        assert result["results"][0]["status"] == "sent"
        assert result["results"][1]["status"] == "failed"
        assert "error" in result["results"][1]
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_accounts_success(self):
        """Test successful cleanup of inactive accounts."""
        # Mock find_inactive_accounts
        inactive_accounts = [
            {
                "user_id": "user-1",
                "email": "user1@example.com",
                "inactive_days": 750
            },
            {
                "user_id": "user-2",
                "email": "user2@example.com", 
                "inactive_days": 800
            }
        ]
        
        with patch.object(self.retention_service, 'find_inactive_accounts', return_value=inactive_accounts):
            # Mock GDPR service deletion
            self.mock_gdpr_service.delete_user_account = AsyncMock(return_value={
                "user_id": "user-1",
                "total_records_deleted": 42
            })
            
            # Run cleanup
            result = await self.retention_service.cleanup_inactive_accounts(
                inactive_days=730,
                dry_run=False,
                max_deletions=5
            )
            
            # Verify results
            assert result["total_inactive_found"] == 2
            assert result["accounts_to_delete"] == 2
            assert result["accounts_deleted"] == 2
            assert result["deletions_failed"] == 0
            assert result["dry_run"] is False
            
            # Verify GDPR service was called
            assert self.mock_gdpr_service.delete_user_account.call_count == 2
            
            # Verify audit logging
            assert self.mock_audit_logger.log_authentication_event.call_count == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_accounts_dry_run(self):
        """Test inactive account cleanup in dry run mode."""
        inactive_accounts = [
            {"user_id": "user-1", "email": "user1@example.com", "inactive_days": 750}
        ]
        
        with patch.object(self.retention_service, 'find_inactive_accounts', return_value=inactive_accounts):
            # Run cleanup in dry run
            result = await self.retention_service.cleanup_inactive_accounts(
                dry_run=True
            )
            
            # Verify results
            assert result["accounts_deleted"] == 0
            assert result["dry_run"] is True
            assert result["results"][0]["status"] == "would_delete"
            
            # Verify GDPR service was not called
            self.mock_gdpr_service.delete_user_account.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_accounts_with_max_limit(self):
        """Test inactive account cleanup with maximum deletion limit."""
        # Mock many inactive accounts
        inactive_accounts = [
            {"user_id": f"user-{i}", "email": f"user{i}@example.com", "inactive_days": 750}
            for i in range(10)
        ]
        
        with patch.object(self.retention_service, 'find_inactive_accounts', return_value=inactive_accounts):
            self.mock_gdpr_service.delete_user_account = AsyncMock(return_value={
                "total_records_deleted": 10
            })
            
            # Run cleanup with limit
            result = await self.retention_service.cleanup_inactive_accounts(
                max_deletions=3,
                dry_run=False
            )
            
            # Verify only 3 accounts were processed due to limit
            assert result["total_inactive_found"] == 10
            assert result["accounts_to_delete"] == 3
            assert result["accounts_deleted"] == 3
    
    def test_cleanup_expired_sessions_success(self):
        """Test successful cleanup of expired sessions."""
        # Mock expired sessions query
        mock_query = self.mock_db.query.return_value.filter.return_value
        mock_query.count.return_value = 5
        mock_query.delete.return_value = 5
        
        # Run cleanup
        result = self.retention_service.cleanup_expired_sessions(
            expired_days=30,
            dry_run=False
        )
        
        # Verify results
        assert result["expired_sessions_found"] == 5
        assert result["sessions_deleted"] == 5
        assert result["dry_run"] is False
        
        # Verify database operations
        mock_query.delete.assert_called_once_with(synchronize_session=False)
        self.mock_db.commit.assert_called_once()
    
    def test_cleanup_expired_sessions_dry_run(self):
        """Test expired session cleanup in dry run mode."""
        # Mock expired sessions query
        mock_query = self.mock_db.query.return_value.filter.return_value
        mock_query.count.return_value = 3
        
        # Run cleanup in dry run
        result = self.retention_service.cleanup_expired_sessions(
            expired_days=30,
            dry_run=True
        )
        
        # Verify results
        assert result["expired_sessions_found"] == 3
        assert result["sessions_deleted"] == 0
        assert result["dry_run"] is True
        
        # Verify no deletion occurred
        mock_query.delete.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_cleanup_old_audit_logs_success(self):
        """Test successful cleanup of old audit logs."""
        # Mock old audit logs query
        mock_query = self.mock_db.query.return_value.filter.return_value
        mock_query.count.return_value = 10
        mock_query.delete.return_value = 10
        
        # Run cleanup
        result = self.retention_service.cleanup_old_audit_logs(
            retention_days=2555,
            dry_run=False
        )
        
        # Verify results
        assert result["old_logs_found"] == 10
        assert result["logs_deleted"] == 10
        assert result["retention_days"] == 2555
        assert result["dry_run"] is False
        
        # Verify database operations
        mock_query.delete.assert_called_once_with(synchronize_session=False)
        self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_full_retention_cleanup_success(self):
        """Test successful full retention cleanup."""
        # Mock all cleanup methods
        with patch.object(self.retention_service, 'send_inactivity_warnings', new_callable=AsyncMock) as mock_warnings:
            with patch.object(self.retention_service, 'cleanup_inactive_accounts', new_callable=AsyncMock) as mock_accounts:
                with patch.object(self.retention_service, 'cleanup_expired_sessions') as mock_sessions:
                    with patch.object(self.retention_service, 'cleanup_old_audit_logs') as mock_logs:
                        
                        # Set up mock returns
                        mock_warnings.return_value = {"warnings_sent": 5, "warnings_failed": 0}
                        mock_accounts.return_value = {"accounts_deleted": 3, "deletions_failed": 0}
                        mock_sessions.return_value = {"sessions_deleted": 10}
                        mock_logs.return_value = {"logs_deleted": 20}
                        
                        # Run full cleanup
                        result = await self.retention_service.run_full_retention_cleanup(dry_run=False)
                        
                        # Verify results
                        assert result["success"] is True
                        assert "started_at" in result
                        assert "completed_at" in result
                        assert len(result["cleanup_tasks"]) == 4
                        
                        # Verify all cleanup methods were called
                        mock_warnings.assert_called_once_with(dry_run=False)
                        mock_accounts.assert_called_once_with(dry_run=False)
                        mock_sessions.assert_called_once_with(dry_run=False)
                        mock_logs.assert_called_once_with(dry_run=False)
    
    @pytest.mark.asyncio
    async def test_run_full_retention_cleanup_with_error(self):
        """Test full retention cleanup with error handling."""
        # Mock cleanup method to raise error
        with patch.object(self.retention_service, 'send_inactivity_warnings', new_callable=AsyncMock) as mock_warnings:
            mock_warnings.side_effect = Exception("Cleanup error")
            
            # Run full cleanup and expect error
            with pytest.raises(Exception, match="Cleanup error"):
                await self.retention_service.run_full_retention_cleanup(dry_run=False)
    
    def test_get_retention_statistics_success(self):
        """Test successful generation of retention statistics."""
        # Mock database queries for statistics
        self.mock_db.query.return_value.filter.return_value.count.side_effect = [
            100,  # Total users
            50,   # Total sessions
            200   # Total audit logs
        ]
        
        # Mock find_inactive_accounts
        with patch.object(self.retention_service, 'find_inactive_accounts') as mock_find_inactive:
            mock_find_inactive.side_effect = [
                [{"user_id": "1"}, {"user_id": "2"}],  # 2 years inactive
                [{"user_id": "1"}, {"user_id": "2"}, {"user_id": "3"}]  # 22 months inactive
            ]
            
            # Get statistics
            result = self.retention_service.get_retention_statistics()
            
            # Verify results
            assert "generated_at" in result
            assert "user_statistics" in result
            assert "session_statistics" in result
            assert "audit_statistics" in result
            
            # Verify user statistics
            user_stats = result["user_statistics"]
            assert user_stats["total_active_users"] == 100
            assert user_stats["inactive_2_years"] == 2
            assert user_stats["inactive_22_months"] == 3
            assert user_stats["eligible_for_deletion"] == 2
            assert user_stats["eligible_for_warning"] == 1  # 3 - 2
    
    def test_get_retention_statistics_database_error(self):
        """Test retention statistics with database error."""
        # Mock database error
        self.mock_db.query.side_effect = Exception("Database error")
        
        # Test statistics generation
        with pytest.raises(Exception, match="Database error"):
            self.retention_service.get_retention_statistics()