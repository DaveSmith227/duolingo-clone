"""
Unit Tests for Session Manager Service

Tests for JWT session management, token rotation, and secure session handling.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.session_manager import SessionManager, get_session_manager
from app.models.user import User
from app.models.auth import AuthSession, SupabaseUser, AuthAuditLog
from app.core.config import get_settings


class TestSessionManager:
    """Test cases for SessionManager class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user instance."""
        user = Mock(spec=User)
        user.id = "user-123"
        user.email = "test@example.com"
        user.name = "Test User"
        return user
    
    @pytest.fixture
    def mock_supabase_user(self):
        """Mock Supabase user instance."""
        supabase_user = Mock(spec=SupabaseUser)
        supabase_user.id = "supabase-123"
        supabase_user.app_user_id = "user-123"
        return supabase_user
    
    @pytest.fixture
    def session_manager(self, mock_db):
        """SessionManager instance with mocked dependencies."""
        with patch('app.services.session_manager.get_jwt_claims_service'):
            return SessionManager(mock_db)
    
    def test_init_session_manager(self, mock_db):
        """Test SessionManager initialization."""
        with patch('app.services.session_manager.get_jwt_claims_service'):
            manager = SessionManager(mock_db)
            assert manager.db == mock_db
            assert manager.settings is not None
    
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    def test_create_session_success(self, mock_refresh_token, mock_access_token, 
                                   session_manager, mock_user, mock_supabase_user):
        """Test successful session creation."""
        # Setup mocks
        mock_access_token.return_value = "access_token_123"
        mock_refresh_token.return_value = "refresh_token_123"
        session_manager.jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["profile.view"]
        }
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        
        # Test session creation
        result = session_manager.create_session(
            user=mock_user,
            user_agent="test-agent",
            ip_address="127.0.0.1",
            remember_me=False
        )
        
        # Verify result
        assert result["access_token"] == "access_token_123"
        assert result["refresh_token"] == "refresh_token_123"
        assert result["token_type"] == "bearer"
        assert "expires_in" in result
        assert "session_id" in result
        assert result["user"]["id"] == "user-123"
        assert result["user"]["email"] == "test@example.com"
        
        # Verify database operations
        session_manager.db.add.assert_called()
        session_manager.db.commit.assert_called()
    
    def test_create_session_no_supabase_user(self, session_manager, mock_user):
        """Test session creation failure when no Supabase user found."""
        # Setup mock
        session_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        # Test session creation
        with pytest.raises(ValueError, match="No Supabase user found"):
            session_manager.create_session(mock_user)
    
    def test_create_session_with_remember_me(self, session_manager, mock_user, mock_supabase_user):
        """Test session creation with remember me option."""
        with patch('app.services.session_manager.create_access_token') as mock_access, \
             patch('app.services.session_manager.create_refresh_token') as mock_refresh:
            
            mock_access.return_value = "access_token_123"
            mock_refresh.return_value = "refresh_token_123"
            session_manager.jwt_service.generate_custom_claims.return_value = {
                "roles": ["user"],
                "permissions": ["profile.view"]
            }
            session_manager.db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
            
            result = session_manager.create_session(
                user=mock_user,
                remember_me=True
            )
            
            # Verify remember me affects token expiration
            assert "expires_in" in result
            # Verify refresh token call used remember_me expiration
            mock_refresh.assert_called_once()
    
    def test_create_session_single_session_mode(self, session_manager, mock_user, mock_supabase_user):
        """Test session creation with single session enforcement."""
        with patch('app.services.session_manager.create_access_token'), \
             patch('app.services.session_manager.create_refresh_token'), \
             patch.object(session_manager, '_invalidate_user_sessions') as mock_invalidate:
            
            session_manager.jwt_service.generate_custom_claims.return_value = {
                "roles": ["user"],
                "permissions": ["profile.view"]
            }
            session_manager.db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
            
            session_manager.create_session(
                user=mock_user,
                single_session=True
            )
            
            # Verify other sessions were invalidated
            mock_invalidate.assert_called_once_with("user-123", "single_session_login")
    
    @patch('app.services.session_manager.verify_refresh_token')
    def test_refresh_session_success(self, mock_verify_token, session_manager, mock_user):
        """Test successful session refresh."""
        # Setup mocks
        mock_verify_token.return_value = {
            "sub": "user-123",
            "session_id": "session-123"
        }
        
        mock_session = Mock(spec=AuthSession)
        mock_session.session_id = "session-123"
        mock_session.is_active = True
        mock_session.is_valid = True
        mock_session.is_refresh_expired = False
        mock_session.supabase_user_id = "supabase-123"
        
        session_manager.db.query.return_value.filter.return_value.first.side_effect = [
            mock_session,  # session lookup
            mock_user      # user lookup
        ]
        
        session_manager.jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["profile.view"]
        }
        
        with patch('app.services.session_manager.create_access_token') as mock_access, \
             patch('app.services.session_manager.create_refresh_token') as mock_refresh, \
             patch.object(session_manager, '_update_session_activity'), \
             patch.object(session_manager, '_generate_session_id', return_value="new-session-123"):
            
            mock_access.return_value = "new_access_token"
            mock_refresh.return_value = "new_refresh_token"
            
            result = session_manager.refresh_session("refresh_token_123")
            
            # Verify result
            assert result["access_token"] == "new_access_token"
            assert result["refresh_token"] == "new_refresh_token"
            assert result["session_id"] == "new-session-123"
            
            # Verify session was updated
            assert mock_session.session_id == "new-session-123"
            session_manager.db.commit.assert_called()
    
    @patch('app.services.session_manager.verify_refresh_token')
    def test_refresh_session_invalid_token(self, mock_verify_token, session_manager):
        """Test session refresh with invalid token."""
        mock_verify_token.return_value = None
        
        result = session_manager.refresh_session("invalid_token")
        
        assert result is None
    
    @patch('app.services.session_manager.verify_refresh_token')
    def test_refresh_session_expired(self, mock_verify_token, session_manager):
        """Test session refresh with expired session."""
        mock_verify_token.return_value = {
            "sub": "user-123",
            "session_id": "session-123"
        }
        
        mock_session = Mock(spec=AuthSession)
        mock_session.is_active = True
        mock_session.is_valid = False
        mock_session.is_refresh_expired = True
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_session
        
        result = session_manager.refresh_session("expired_token")
        
        assert result is None
        # Verify session was invalidated
        mock_session.invalidate.assert_called_once_with("refresh_token_expired")
    
    def test_invalidate_session_success(self, session_manager):
        """Test successful session invalidation."""
        mock_session = Mock(spec=AuthSession)
        mock_session.supabase_user_id = "supabase-123"
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_session
        
        result = session_manager.invalidate_session("session-123", "logout")
        
        assert result is True
        mock_session.invalidate.assert_called_once_with("logout")
        session_manager.db.commit.assert_called()
    
    def test_invalidate_session_not_found(self, session_manager):
        """Test session invalidation when session not found."""
        session_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        result = session_manager.invalidate_session("nonexistent-session")
        
        assert result is False
    
    def test_invalidate_all_user_sessions(self, session_manager, mock_supabase_user):
        """Test invalidating all user sessions."""
        mock_session1 = Mock(spec=AuthSession)
        mock_session2 = Mock(spec=AuthSession)
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        session_manager.db.query.return_value.filter.return_value.all.return_value = [mock_session1, mock_session2]
        
        count = session_manager.invalidate_all_user_sessions("user-123", "logout_all")
        
        assert count == 2
        mock_session1.invalidate.assert_called_once_with("logout_all")
        mock_session2.invalidate.assert_called_once_with("logout_all")
        session_manager.db.commit.assert_called()
    
    def test_invalidate_all_user_sessions_no_supabase_user(self, session_manager):
        """Test invalidating all sessions when no Supabase user found."""
        session_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        count = session_manager.invalidate_all_user_sessions("user-123")
        
        assert count == 0
    
    def test_get_user_sessions(self, session_manager):
        """Test getting user sessions."""
        # Test the no Supabase user case
        session_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        sessions = session_manager.get_user_sessions("user-123")
        
        assert sessions == []
    
    def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions."""
        expired_session = Mock(spec=AuthSession)
        inactive_session = Mock(spec=AuthSession)
        
        session_manager.db.query.return_value.filter.return_value.all.side_effect = [
            [expired_session],    # expired sessions
            [inactive_session]    # inactive sessions
        ]
        
        count = session_manager.cleanup_expired_sessions()
        
        assert count == 2
        expired_session.invalidate.assert_called_once_with("token_expired")
        inactive_session.invalidate.assert_called_once_with("inactivity_timeout")
        session_manager.db.commit.assert_called()
    
    def test_verify_session_success(self, session_manager):
        """Test successful session verification."""
        mock_session = Mock(spec=AuthSession)
        mock_session.session_id = "session-123"
        mock_session.is_valid = True
        mock_session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_session.supabase_user.app_user_id = "user-123"
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_session
        
        result = session_manager.verify_session("session-123")
        
        assert result is not None
        assert result["session_id"] == "session-123"
        assert result["user_id"] == "user-123"
        assert result["is_valid"] is True
        
        # Verify activity was updated
        session_manager.db.commit.assert_called()
    
    def test_verify_session_invalid(self, session_manager):
        """Test verification of invalid session."""
        mock_session = Mock(spec=AuthSession)
        mock_session.is_valid = False
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_session
        
        result = session_manager.verify_session("session-123")
        
        assert result is None
    
    def test_verify_session_not_found(self, session_manager):
        """Test verification of non-existent session."""
        session_manager.db.query.return_value.filter.return_value.first.return_value = None
        
        result = session_manager.verify_session("nonexistent-session")
        
        assert result is None
    
    def test_generate_session_id(self, session_manager):
        """Test session ID generation."""
        session_id = session_manager._generate_session_id()
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_enforce_session_limit(self, session_manager, mock_supabase_user):
        """Test session limit enforcement."""
        # Create more sessions than the limit
        mock_sessions = [Mock(spec=AuthSession) for _ in range(6)]
        
        session_manager.db.query.return_value.filter.return_value.first.return_value = mock_supabase_user
        session_manager.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_sessions
        
        session_manager._enforce_session_limit("user-123")
        
        # Verify oldest sessions were invalidated
        mock_sessions[-2].invalidate.assert_called_once_with("session_limit_exceeded")
        session_manager.db.commit.assert_called()
    
    def test_update_session_activity(self, session_manager):
        """Test session activity update."""
        mock_session = Mock(spec=AuthSession)
        
        session_manager._update_session_activity(
            mock_session,
            ip_address="192.168.1.1",
            user_agent="new-agent"
        )
        
        assert mock_session.ip_address == "192.168.1.1"
        assert mock_session.user_agent == "new-agent"
        assert mock_session.updated_at is not None


def test_get_session_manager():
    """Test get_session_manager factory function."""
    mock_db = Mock(spec=Session)
    
    with patch('app.services.session_manager.get_jwt_claims_service'):
        manager = get_session_manager(mock_db)
        
        assert isinstance(manager, SessionManager)
        assert manager.db == mock_db


class TestSessionManagerIntegration:
    """Integration tests for SessionManager with real database operations."""
    
    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        # This would require actual database setup
        # Implementation depends on test database configuration
        pass
    
    def test_concurrent_session_access(self):
        """Test concurrent session operations."""
        # This would test thread safety and concurrent access
        pass
    
    def test_session_cleanup_performance(self):
        """Test performance of session cleanup operations."""
        # This would test cleanup with large numbers of sessions
        pass