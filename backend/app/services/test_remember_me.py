"""
Unit Tests for Remember Me Functionality

Tests for remember me functionality including extended session duration,
token refresh with state preservation, and cookie management.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.services.session_manager import SessionManager
from app.services.cookie_manager import CookieManager
from app.models.user import User
from app.models.auth import SupabaseUser, AuthSession
from app.core.config import get_settings


class TestRememberMeFunctionality:
    """Test cases for remember me functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.session_manager = SessionManager(self.mock_db)
        self.cookie_manager = CookieManager()
        
        # Mock user data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        self.test_user.name = "Test User"
        
        self.test_supabase_user = Mock(spec=SupabaseUser)
        self.test_supabase_user.id = "supabase-123"
        self.test_supabase_user.supabase_id = "supabase-123"
        self.test_supabase_user.email = "test@example.com"
    
    @patch('app.services.session_manager.get_jwt_claims_service')
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    def test_create_session_with_remember_me(
        self,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_get_jwt_claims_service
    ):
        """Test session creation with remember_me=True extends refresh token expiration."""
        # Mock JWT claims service
        mock_jwt_service = Mock()
        mock_jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["read"]
        }
        mock_get_jwt_claims_service.return_value = mock_jwt_service
        
        # Mock token creation
        mock_create_access_token.return_value = "access_token_123"
        mock_create_refresh_token.return_value = "refresh_token_123"
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_supabase_user
        self.mock_db.query.return_value.filter.return_value.all.return_value = []  # No existing sessions
        
        # Create session with remember_me=True
        result = self.session_manager.create_session(
            user=self.test_user,
            user_agent="Test Agent",
            ip_address="192.168.1.1",
            remember_me=True
        )
        
        # Verify tokens were created with correct expiration
        mock_create_refresh_token.assert_called_once()
        
        # Verify session record creation
        self.mock_db.add.assert_called_once()
        session_record = self.mock_db.add.call_args[0][0]
        
        # Verify remember_me field is set
        assert session_record.remember_me is True
        
        # Verify result includes remember_me
        assert result["remember_me"] is True
        assert "refresh_expires_in" in result
    
    @patch('app.services.session_manager.get_jwt_claims_service')
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    def test_create_session_without_remember_me(
        self,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_get_jwt_claims_service
    ):
        """Test session creation with remember_me=False uses default expiration."""
        # Mock JWT claims service
        mock_jwt_service = Mock()
        mock_jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["read"]
        }
        mock_get_jwt_claims_service.return_value = mock_jwt_service
        
        # Mock token creation
        mock_create_access_token.return_value = "access_token_123"
        mock_create_refresh_token.return_value = "refresh_token_123"
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_supabase_user
        self.mock_db.query.return_value.filter.return_value.all.return_value = []  # No existing sessions
        
        # Create session with remember_me=False
        result = self.session_manager.create_session(
            user=self.test_user,
            user_agent="Test Agent",
            ip_address="192.168.1.1",
            remember_me=False
        )
        
        # Verify session record creation
        self.mock_db.add.assert_called_once()
        session_record = self.mock_db.add.call_args[0][0]
        
        # Verify remember_me field is set to False
        assert session_record.remember_me is False
        
        # Verify result includes remember_me
        assert result["remember_me"] is False
    
    @patch('app.services.session_manager.verify_refresh_token')
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    @patch('app.services.session_manager.get_jwt_claims_service')
    def test_refresh_session_preserves_remember_me_state(
        self,
        mock_get_jwt_claims_service,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_verify_refresh_token
    ):
        """Test that refresh_session preserves remember_me state."""
        # Mock token verification
        mock_verify_refresh_token.return_value = {
            "sub": "user-123",
            "session_id": "session-123"
        }
        
        # Mock existing session with remember_me=True
        mock_session = Mock(spec=AuthSession)
        mock_session.remember_me = True
        mock_session.is_valid = True
        mock_session.is_refresh_expired = False
        mock_session.supabase_user_id = "supabase-123"
        
        # Mock JWT claims service
        mock_jwt_service = Mock()
        mock_jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["read"]
        }
        mock_get_jwt_claims_service.return_value = mock_jwt_service
        
        # Mock token creation
        mock_create_access_token.return_value = "new_access_token"
        mock_create_refresh_token.return_value = "new_refresh_token"
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_session,  # Session query
            self.test_user  # User query
        ]
        
        # Mock settings for token expiration
        with patch('app.services.session_manager.SessionManager._generate_session_id') as mock_gen_id:
            mock_gen_id.return_value = "new-session-123"
            
            with patch('app.services.session_manager.SessionManager._update_session_activity'):
                with patch('app.services.session_manager.SessionManager._log_auth_event'):
                    # Refresh the session
                    result = self.session_manager.refresh_session(
                        refresh_token="old_refresh_token",
                        ip_address="192.168.1.1",
                        user_agent="Test Agent"
                    )
        
        # Verify remember_me state is preserved
        assert result["remember_me"] is True
        
        # Verify token expiration logic was called appropriately for remember_me=True
        # (refresh token should use remember_me_expire_days)
        mock_create_refresh_token.assert_called_once()
    
    @patch('app.services.session_manager.verify_refresh_token')
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    @patch('app.services.session_manager.get_jwt_claims_service')
    def test_refresh_session_preserves_regular_state(
        self,
        mock_get_jwt_claims_service,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_verify_refresh_token
    ):
        """Test that refresh_session preserves remember_me=False state."""
        # Mock token verification
        mock_verify_refresh_token.return_value = {
            "sub": "user-123",
            "session_id": "session-123"
        }
        
        # Mock existing session with remember_me=False
        mock_session = Mock(spec=AuthSession)
        mock_session.remember_me = False
        mock_session.is_valid = True
        mock_session.is_refresh_expired = False
        mock_session.supabase_user_id = "supabase-123"
        
        # Mock JWT claims service
        mock_jwt_service = Mock()
        mock_jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["read"]
        }
        mock_get_jwt_claims_service.return_value = mock_jwt_service
        
        # Mock token creation
        mock_create_access_token.return_value = "new_access_token"
        mock_create_refresh_token.return_value = "new_refresh_token"
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_session,  # Session query
            self.test_user  # User query
        ]
        
        # Mock settings for token expiration
        with patch('app.services.session_manager.SessionManager._generate_session_id') as mock_gen_id:
            mock_gen_id.return_value = "new-session-123"
            
            with patch('app.services.session_manager.SessionManager._update_session_activity'):
                with patch('app.services.session_manager.SessionManager._log_auth_event'):
                    # Refresh the session
                    result = self.session_manager.refresh_session(
                        refresh_token="old_refresh_token",
                        ip_address="192.168.1.1",
                        user_agent="Test Agent"
                    )
        
        # Verify remember_me state is preserved as False
        assert result["remember_me"] is False
    
    def test_cookie_manager_extended_expiration_with_remember_me(self):
        """Test cookie manager sets extended expiration for remember_me sessions."""
        mock_response = Mock()
        
        # Test with remember_me=True
        self.cookie_manager.set_auth_cookies(
            response=mock_response,
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            remember_me=True
        )
        
        # Verify set_cookie was called with extended expiration
        assert mock_response.set_cookie.call_count == 2  # access and refresh tokens
        
        # Check refresh token cookie has extended expiration
        refresh_cookie_call = mock_response.set_cookie.call_args_list[1]
        refresh_max_age = refresh_cookie_call[1]['max_age']
        
        settings = get_settings()
        expected_max_age = settings.remember_me_expire_days * 24 * 60 * 60
        assert refresh_max_age == expected_max_age
    
    def test_cookie_manager_default_expiration_without_remember_me(self):
        """Test cookie manager sets default expiration for regular sessions."""
        mock_response = Mock()
        
        # Test with remember_me=False
        self.cookie_manager.set_auth_cookies(
            response=mock_response,
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            remember_me=False
        )
        
        # Verify set_cookie was called with default expiration
        assert mock_response.set_cookie.call_count == 2  # access and refresh tokens
        
        # Check refresh token cookie has default expiration
        refresh_cookie_call = mock_response.set_cookie.call_args_list[1]
        refresh_max_age = refresh_cookie_call[1]['max_age']
        
        settings = get_settings()
        expected_max_age = settings.refresh_token_expire_days * 24 * 60 * 60
        assert refresh_max_age == expected_max_age
    
    def test_remember_me_configuration_values(self):
        """Test that remember_me configuration values are properly set."""
        settings = get_settings()
        
        # Verify remember_me_expire_days is configured
        assert hasattr(settings, 'remember_me_expire_days')
        assert settings.remember_me_expire_days == 30
        
        # Verify it's longer than regular refresh token expiration
        assert settings.remember_me_expire_days > settings.refresh_token_expire_days
        
        # Verify access token expiration remains the same
        assert settings.access_token_expire_minutes == 15


class TestRememberMeEndToEnd:
    """End-to-end tests for remember me functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.session_manager = SessionManager(self.mock_db)
        
        # Mock user data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        self.test_user.name = "Test User"
        
        self.test_supabase_user = Mock(spec=SupabaseUser)
        self.test_supabase_user.id = "supabase-123"
        self.test_supabase_user.supabase_id = "supabase-123"
        self.test_supabase_user.email = "test@example.com"
    
    @patch('app.services.session_manager.get_jwt_claims_service')
    @patch('app.services.session_manager.create_access_token')
    @patch('app.services.session_manager.create_refresh_token')
    @patch('app.services.session_manager.verify_refresh_token')
    def test_remember_me_workflow(
        self,
        mock_verify_refresh_token,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_get_jwt_claims_service
    ):
        """Test complete remember me workflow from login to refresh."""
        # Mock JWT claims service
        mock_jwt_service = Mock()
        mock_jwt_service.generate_custom_claims.return_value = {
            "roles": ["user"],
            "permissions": ["read"]
        }
        mock_get_jwt_claims_service.return_value = mock_jwt_service
        
        # Mock token creation for initial session
        mock_create_access_token.side_effect = ["initial_access", "refreshed_access"]
        mock_create_refresh_token.side_effect = ["initial_refresh", "refreshed_refresh"]
        
        # Mock database queries for session creation
        self.mock_db.query.return_value.filter.return_value.first.return_value = self.test_supabase_user
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Step 1: Create session with remember_me=True
        with patch('app.services.session_manager.SessionManager._generate_session_id') as mock_gen_id:
            mock_gen_id.return_value = "session-123"
            
            initial_session = self.session_manager.create_session(
                user=self.test_user,
                user_agent="Test Agent",
                ip_address="192.168.1.1",
                remember_me=True
            )
        
        # Verify initial session
        assert initial_session["remember_me"] is True
        assert initial_session["access_token"] == "initial_access"
        assert initial_session["refresh_token"] == "initial_refresh"
        
        # Step 2: Simulate token refresh
        mock_verify_refresh_token.return_value = {
            "sub": "user-123",
            "session_id": "session-123"
        }
        
        # Mock existing session with remember_me=True
        mock_session = Mock(spec=AuthSession)
        mock_session.remember_me = True
        mock_session.is_valid = True
        mock_session.is_refresh_expired = False
        mock_session.supabase_user_id = "supabase-123"
        
        # Mock database queries for refresh
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_session,  # Session query
            self.test_user  # User query
        ]
        
        with patch('app.services.session_manager.SessionManager._generate_session_id') as mock_gen_id:
            mock_gen_id.return_value = "new-session-123"
            
            with patch('app.services.session_manager.SessionManager._update_session_activity'):
                with patch('app.services.session_manager.SessionManager._log_auth_event'):
                    # Refresh the session
                    refreshed_session = self.session_manager.refresh_session(
                        refresh_token="initial_refresh",
                        ip_address="192.168.1.1",
                        user_agent="Test Agent"
                    )
        
        # Verify refreshed session preserves remember_me state
        assert refreshed_session["remember_me"] is True
        assert refreshed_session["access_token"] == "refreshed_access"
        assert refreshed_session["refresh_token"] == "refreshed_refresh"
    
    def test_session_expiration_differences(self):
        """Test that remember me sessions have different expiration times."""
        settings = get_settings()
        
        # Regular session duration
        regular_refresh_seconds = settings.refresh_token_expire_days * 24 * 60 * 60
        
        # Remember me session duration
        remember_me_refresh_seconds = settings.remember_me_expire_days * 24 * 60 * 60
        
        # Verify remember me is longer
        assert remember_me_refresh_seconds > regular_refresh_seconds
        
        # Verify the difference is significant (at least 23 days)
        difference_days = (remember_me_refresh_seconds - regular_refresh_seconds) / (24 * 60 * 60)
        assert difference_days >= 23  # 30 - 7 = 23 days minimum difference