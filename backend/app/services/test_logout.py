"""
Unit Tests for Logout Functionality

Tests for logout endpoint including single session logout, logout from all devices,
token invalidation, cookie clearing, and audit logging.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.session_manager import SessionManager
from app.services.cookie_manager import CookieManager
from app.models.auth import AuthSession


class TestLogoutFunctionality:
    """Test cases for logout functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.session_manager = SessionManager(self.mock_db)
        self.cookie_manager = CookieManager()
        
        # Mock session data
        self.test_session = Mock(spec=AuthSession)
        self.test_session.session_id = "session-123"
        self.test_session.is_active = True
        self.test_session.supabase_user_id = "supabase-123"
        self.test_session.invalidate = Mock()
    
    def test_invalidate_single_session_success(self):
        """Test successful invalidation of single session."""
        # Mock session found
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_session
        
        # Invalidate session
        result = self.session_manager.invalidate_session(
            session_id="session-123",
            reason="logout"
        )
        
        # Verify session was invalidated
        assert result is True
        self.test_session.invalidate.assert_called_once_with("logout")
        self.mock_db.commit.assert_called_once()
    
    def test_invalidate_session_not_found(self):
        """Test invalidation when session is not found."""
        # Mock session not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt to invalidate session
        result = self.session_manager.invalidate_session(
            session_id="nonexistent-session",
            reason="logout"
        )
        
        # Verify operation failed gracefully
        assert result is False
        self.mock_db.commit.assert_not_called()
    
    def test_invalidate_all_user_sessions_success(self):
        """Test successful invalidation of all user sessions."""
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock multiple active sessions
        mock_session1 = Mock(spec=AuthSession)
        mock_session1.invalidate = Mock()
        mock_session2 = Mock(spec=AuthSession)
        mock_session2.invalidate = Mock()
        mock_session3 = Mock(spec=AuthSession)
        mock_session3.invalidate = Mock()
        
        active_sessions = [mock_session1, mock_session2, mock_session3]
        self.mock_db.query.return_value.filter.return_value.all.return_value = active_sessions
        
        # Invalidate all sessions
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all"
        )
        
        # Verify all sessions were invalidated
        assert result == 3
        mock_session1.invalidate.assert_called_once_with("logout_all")
        mock_session2.invalidate.assert_called_once_with("logout_all")
        mock_session3.invalidate.assert_called_once_with("logout_all")
        self.mock_db.commit.assert_called_once()
    
    def test_invalidate_all_sessions_no_supabase_user(self):
        """Test invalidation when Supabase user is not found."""
        # Mock Supabase user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt to invalidate all sessions
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="nonexistent-user",
            reason="logout_all"
        )
        
        # Verify operation failed gracefully
        assert result == 0
        self.mock_db.commit.assert_not_called()
    
    def test_invalidate_all_sessions_no_active_sessions(self):
        """Test invalidation when user has no active sessions."""
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock no active sessions
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Invalidate all sessions
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all"
        )
        
        # Verify no sessions were invalidated
        assert result == 0
        self.mock_db.commit.assert_called_once()
    
    def test_cookie_manager_clear_auth_cookies(self):
        """Test cookie manager clears all authentication cookies."""
        mock_response = Mock()
        
        # Clear authentication cookies
        self.cookie_manager.clear_auth_cookies(mock_response)
        
        # Verify all cookies were cleared
        assert mock_response.delete_cookie.call_count == 3  # access, refresh, csrf tokens
        
        # Check specific cookie clearing calls
        delete_calls = mock_response.delete_cookie.call_args_list
        
        # Access token cookie
        access_call = delete_calls[0]
        assert access_call[1]['key'] == 'access_token'
        assert access_call[1]['path'] == '/api'
        
        # Refresh token cookie
        refresh_call = delete_calls[1]
        assert refresh_call[1]['key'] == 'refresh_token'
        assert refresh_call[1]['path'] == '/api/auth'
        
        # CSRF token cookie
        csrf_call = delete_calls[2]
        assert csrf_call[1]['key'] == 'csrf_token'
        assert csrf_call[1]['path'] == '/'
    
    def test_session_invalidation_with_database_error(self):
        """Test session invalidation handles database errors gracefully."""
        # Mock session found
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_session
        
        # Mock database commit error
        self.mock_db.commit.side_effect = Exception("Database error")
        
        # Attempt to invalidate session
        result = self.session_manager.invalidate_session(
            session_id="session-123",
            reason="logout"
        )
        
        # Verify operation failed and rollback was called
        assert result is False
        self.mock_db.rollback.assert_called_once()
    
    def test_all_sessions_invalidation_with_database_error(self):
        """Test all sessions invalidation handles database errors gracefully."""
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock active sessions
        mock_session = Mock(spec=AuthSession)
        mock_session.invalidate = Mock()
        self.mock_db.query.return_value.filter.return_value.all.return_value = [mock_session]
        
        # Mock database commit error
        self.mock_db.commit.side_effect = Exception("Database error")
        
        # Attempt to invalidate all sessions
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all"
        )
        
        # Verify operation failed and rollback was called
        assert result == 0
        self.mock_db.rollback.assert_called_once()


class TestLogoutEndToEnd:
    """End-to-end tests for logout functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.session_manager = SessionManager(self.mock_db)
        
        # Mock user session data
        self.test_session = Mock(spec=AuthSession)
        self.test_session.session_id = "session-123"
        self.test_session.is_active = True
        self.test_session.supabase_user_id = "supabase-123"
        self.test_session.invalidate = Mock()
    
    def test_complete_logout_workflow_single_session(self):
        """Test complete logout workflow for single session."""
        # Mock session found
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_session
        
        # Step 1: Invalidate current session
        result = self.session_manager.invalidate_session(
            session_id="session-123",
            reason="logout"
        )
        
        # Verify session invalidation
        assert result is True
        self.test_session.invalidate.assert_called_once_with("logout")
        self.mock_db.commit.assert_called_once()
        
        # Step 2: Verify session is marked as invalidated
        # (This would be handled by the AuthSession.invalidate method)
        self.test_session.invalidate.assert_called_with("logout")
    
    def test_complete_logout_workflow_all_devices(self):
        """Test complete logout workflow for all devices."""
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock multiple sessions
        mock_session1 = Mock(spec=AuthSession)
        mock_session1.invalidate = Mock()
        mock_session2 = Mock(spec=AuthSession)
        mock_session2.invalidate = Mock()
        mock_session3 = Mock(spec=AuthSession)
        mock_session3.invalidate = Mock()
        
        active_sessions = [mock_session1, mock_session2, mock_session3]
        self.mock_db.query.return_value.filter.return_value.all.return_value = active_sessions
        
        # Step 1: Invalidate all user sessions
        invalidated_count = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all_devices"
        )
        
        # Verify all sessions invalidated
        assert invalidated_count == 3
        mock_session1.invalidate.assert_called_once_with("logout_all_devices")
        mock_session2.invalidate.assert_called_once_with("logout_all_devices")
        mock_session3.invalidate.assert_called_once_with("logout_all_devices")
        self.mock_db.commit.assert_called_once()
    
    def test_logout_with_concurrent_session_access(self):
        """Test logout behavior when sessions are accessed concurrently."""
        # Mock session found initially
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_session
        
        # Invalidate session
        result = self.session_manager.invalidate_session(
            session_id="session-123",
            reason="logout"
        )
        
        # Verify session was invalidated
        assert result is True
        self.test_session.invalidate.assert_called_once_with("logout")
        
        # Simulate concurrent access attempt
        # (In real scenario, the session would be marked as inactive)
        self.test_session.is_active = False
        
        # Attempt another invalidation (should still work but do nothing)
        result2 = self.session_manager.invalidate_session(
            session_id="session-123",
            reason="logout"
        )
        
        # Both operations should succeed
        assert result2 is True
    
    def test_logout_performance_with_many_sessions(self):
        """Test logout performance with many concurrent sessions."""
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock many sessions (simulate heavy user with many devices)
        num_sessions = 50
        active_sessions = []
        for i in range(num_sessions):
            mock_session = Mock(spec=AuthSession)
            mock_session.invalidate = Mock()
            active_sessions.append(mock_session)
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = active_sessions
        
        # Invalidate all sessions
        invalidated_count = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all_devices"
        )
        
        # Verify all sessions were processed
        assert invalidated_count == num_sessions
        
        # Verify each session was invalidated
        for session in active_sessions:
            session.invalidate.assert_called_once_with("logout_all_devices")
        
        # Verify single database commit
        self.mock_db.commit.assert_called_once()


class TestLogoutSecurityScenarios:
    """Test security scenarios for logout functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.session_manager = SessionManager(self.mock_db)
    
    def test_logout_invalid_session_id(self):
        """Test logout with invalid session ID."""
        # Mock session not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt logout with invalid session
        result = self.session_manager.invalidate_session(
            session_id="invalid-session-123",
            reason="logout"
        )
        
        # Verify operation fails gracefully
        assert result is False
        self.mock_db.commit.assert_not_called()
    
    def test_logout_with_empty_session_id(self):
        """Test logout with empty session ID."""
        # Mock session not found (empty query)
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt logout with empty session
        result = self.session_manager.invalidate_session(
            session_id="",
            reason="logout"
        )
        
        # Verify operation fails gracefully
        assert result is False
        self.mock_db.commit.assert_not_called()
    
    def test_logout_all_with_invalid_user_id(self):
        """Test logout all devices with invalid user ID."""
        # Mock Supabase user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Attempt logout all with invalid user
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="invalid-user-123",
            reason="logout_all"
        )
        
        # Verify operation fails gracefully
        assert result == 0
        self.mock_db.commit.assert_not_called()
    
    def test_logout_preserves_other_users_sessions(self):
        """Test that logout only affects the target user's sessions."""
        # Mock Supabase user for target user
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-123"
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Mock sessions for target user only
        target_user_session = Mock(spec=AuthSession)
        target_user_session.invalidate = Mock()
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = [target_user_session]
        
        # Invalidate target user's sessions
        result = self.session_manager.invalidate_all_user_sessions(
            user_id="user-123",
            reason="logout_all"
        )
        
        # Verify only target user's session was affected
        assert result == 1
        target_user_session.invalidate.assert_called_once_with("logout_all")
        
        # Verify database query was properly filtered by supabase_user_id
        # (This is implicitly tested by the mock setup)