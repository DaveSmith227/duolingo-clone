"""
Unit Tests for Authentication API Endpoints

Tests for user authentication endpoints including registration, login,
password reset, social authentication, and session management.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.auth import UserRegistrationRequest, LoginRequest
from app.models.user import User
from app.models.auth import SupabaseUser


class TestAuthRegistration:
    """Test cases for user registration endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_registration_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
            "language_code": "en",
            "marketing_consent": False,
            "terms_accepted": True
        }
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_user_sync_service')
    @patch('app.api.auth.get_supabase_client')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.deps.get_db')
    def test_register_success(
        self,
        mock_get_db,
        mock_get_cookie_manager,
        mock_get_supabase_client,
        mock_get_user_sync_service,
        mock_get_session_manager,
        mock_get_password_security,
        mock_get_audit_logger,
        mock_get_rate_limiter
    ):
        """Test successful user registration."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock password security
        mock_password_security = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.violations = []
        mock_validation_result.strength_score = 85
        mock_validation_result.suggestions = []
        mock_password_security.validate_password.return_value = mock_validation_result
        
        mock_hash_result = Mock()
        mock_hash_result.hash = "hashed_password"
        mock_hash_result.algorithm = "argon2"
        mock_password_security.hash_password.return_value = mock_hash_result
        mock_get_password_security.return_value = mock_password_security
        
        # Mock Supabase client
        mock_supabase_client = AsyncMock()
        mock_supabase_response = Mock()
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-user-123"
        mock_supabase_user.user_metadata = {"first_name": "John", "last_name": "Doe"}
        mock_supabase_response.user = mock_supabase_user
        mock_supabase_client.auth.sign_up.return_value = mock_supabase_response
        mock_get_supabase_client.return_value = mock_supabase_client
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_result = Mock()
        mock_session_result.session_id = "session-123"
        mock_session_result.access_token = "access-token-123"
        mock_session_result.refresh_token = "refresh-token-123"
        mock_session_result.expires_in = 900  # 15 minutes
        mock_session_result.refresh_expires_in = 604800  # 7 days
        mock_session_manager.create_session.return_value = mock_session_result
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Mock user sync service (not used in registration but imported)
        mock_get_user_sync_service.return_value = Mock()
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing user
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        
        # Mock user creation
        with patch('app.api.auth.User') as mock_user_class, \
             patch('app.api.auth.SupabaseUser') as mock_supabase_user_class, \
             patch('app.models.auth.PasswordHistory') as mock_password_history_class:
            
            # Mock created user
            mock_user = Mock()
            mock_user.id = "user-123"
            mock_user.email = "test@example.com"
            mock_user.first_name = "John"
            mock_user.last_name = "Doe"
            mock_user.display_name = "John Doe"
            mock_user.avatar_url = None
            mock_user.language_code = "en"
            mock_user.is_verified = False
            mock_user.is_premium = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_user.streak_count = 0
            mock_user.total_xp = 0
            mock_user_class.return_value = mock_user
            
            # Mock Supabase user
            mock_supabase_user_instance = Mock()
            mock_supabase_user_instance.email_verified = False
            mock_supabase_user_instance.last_sign_in_at = None
            mock_supabase_user_class.return_value = mock_supabase_user_instance
            
            # Mock password history
            mock_password_history = Mock()
            mock_password_history_class.create_password_entry.return_value = mock_password_history
            
            # Make the API call
            response = self.client.post("/auth/register", json=self.valid_registration_data)
            
            # Assertions
            assert response.status_code == 201
            response_data = response.json()
            
            assert "user" in response_data
            assert "tokens" in response_data
            assert "session_id" in response_data
            assert response_data["user"]["email"] == "test@example.com"
            assert response_data["user"]["first_name"] == "John"
            assert response_data["tokens"]["token_type"] == "bearer"
            assert response_data["session_id"] == "session-123"
            
            # Verify service calls
            mock_rate_limiter.check_rate_limit.assert_called_once()
            mock_password_security.validate_password.assert_called_once()
            mock_password_security.hash_password.assert_called_once()
            mock_supabase_client.auth.sign_up.assert_called_once()
            mock_session_manager.create_session.assert_called_once()
            mock_audit_logger.log_authentication_event.assert_called()
    
    def test_register_invalid_email(self):
        """Test registration with invalid email."""
        invalid_data = self.valid_registration_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = self.client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
    
    def test_register_weak_password(self):
        """Test registration with weak password."""
        invalid_data = self.valid_registration_data.copy()
        invalid_data["password"] = "weak"
        
        response = self.client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
    
    def test_register_terms_not_accepted(self):
        """Test registration without accepting terms."""
        invalid_data = self.valid_registration_data.copy()
        invalid_data["terms_accepted"] = False
        
        response = self.client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
    
    def test_register_missing_required_fields(self):
        """Test registration with missing required fields."""
        invalid_data = {
            "email": "test@example.com",
            # Missing password, first_name, terms_accepted
        }
        
        response = self.client.post("/auth/register", json=invalid_data)
        assert response.status_code == 422
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.deps.get_db')
    def test_register_rate_limit_exceeded(self, mock_get_db, mock_get_rate_limiter):
        """Test registration rate limit exceeded."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter to return rate limit exceeded
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = False
        mock_rate_check.retry_after = 3600
        mock_rate_check.limit = 3
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        with patch('app.api.auth.get_audit_logger') as mock_get_audit_logger:
            mock_audit_logger = AsyncMock()
            mock_get_audit_logger.return_value = mock_audit_logger
            
            response = self.client.post("/auth/register", json=self.valid_registration_data)
            
            assert response.status_code == 429
            response_data = response.json()
            assert "retry_after" in response_data
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.deps.get_db')
    def test_register_email_already_exists(self, mock_get_db, mock_get_audit_logger, mock_get_rate_limiter):
        """Test registration with existing email."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock existing user
        existing_user = Mock()
        existing_user.email = "test@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        
        response = self.client.post("/auth/register", json=self.valid_registration_data)
        
        assert response.status_code == 409
        response_data = response.json()
        assert "email_already_exists" in response_data.get("detail", {}).get("error", "")


class TestAuthSocialAuthentication:
    """Test cases for social authentication endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_social_auth_data = {
            "provider": "google",
            "access_token": "valid_google_token_123",
            "device_name": "iPhone 14",
            "marketing_consent": False
        }
    
    @patch('app.api.auth.verify_oauth_token')
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_user_sync_service')
    @patch('app.api.auth.get_supabase_client')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.deps.get_db')
    def test_social_auth_new_user_success(
        self,
        mock_get_db,
        mock_get_cookie_manager,
        mock_get_supabase_client,
        mock_get_user_sync_service,
        mock_get_session_manager,
        mock_get_audit_logger,
        mock_get_rate_limiter,
        mock_verify_oauth_token
    ):
        """Test successful social authentication for new user."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock OAuth token verification
        mock_oauth_user_info = {
            "email": "google.user@example.com",
            "given_name": "Google",
            "family_name": "User",
            "name": "Google User",
            "picture": "https://example.com/avatar.jpg",
            "email_verified": True,
            "locale": "en"
        }
        mock_verify_oauth_token.return_value = mock_oauth_user_info
        
        # Mock Supabase client
        mock_supabase_client = AsyncMock()
        mock_supabase_response = Mock()
        mock_supabase_user = Mock()
        mock_supabase_user.id = "supabase-google-user-123"
        mock_supabase_response.user = mock_supabase_user
        mock_supabase_client.auth.admin.create_user.return_value = mock_supabase_response
        mock_get_supabase_client.return_value = mock_supabase_client
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_result = Mock()
        mock_session_result.session_id = "social-session-123"
        mock_session_result.access_token = "social-access-token-123"
        mock_session_result.refresh_token = "social-refresh-token-123"
        mock_session_result.expires_in = 900
        mock_session_result.refresh_expires_in = 604800
        mock_session_manager.create_session.return_value = mock_session_result
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Mock user sync service
        mock_get_user_sync_service.return_value = Mock()
        
        # Mock database queries - no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        
        # Mock user creation
        with patch('app.api.auth.User') as mock_user_class, \
             patch('app.api.auth.SupabaseUser') as mock_supabase_user_class:
            
            # Mock created user
            mock_user = Mock()
            mock_user.id = "google-user-123"
            mock_user.email = "google.user@example.com"
            mock_user.first_name = "Google"
            mock_user.last_name = "User"
            mock_user.display_name = "Google User"
            mock_user.avatar_url = "https://example.com/avatar.jpg"
            mock_user.language_code = "en"
            mock_user.is_verified = True
            mock_user.is_premium = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_user.streak_count = 0
            mock_user.total_xp = 0
            mock_user_class.return_value = mock_user
            
            # Mock Supabase user
            mock_supabase_user_instance = Mock()
            mock_supabase_user_instance.email_verified = True
            mock_supabase_user_instance.last_sign_in_at = datetime.now(timezone.utc)
            mock_supabase_user_class.return_value = mock_supabase_user_instance
            
            # Make the API call
            response = self.client.post("/auth/social", json=self.valid_social_auth_data)
            
            # Assertions
            assert response.status_code == 200
            response_data = response.json()
            
            assert "user" in response_data
            assert "tokens" in response_data
            assert "session_id" in response_data
            assert response_data["user"]["email"] == "google.user@example.com"
            assert response_data["user"]["first_name"] == "Google"
            assert response_data["tokens"]["token_type"] == "bearer"
            assert response_data["session_id"] == "social-session-123"
            
            # Verify service calls
            mock_verify_oauth_token.assert_called_once_with("google", "valid_google_token_123")
            mock_supabase_client.auth.admin.create_user.assert_called_once()
            mock_session_manager.create_session.assert_called_once()
            mock_audit_logger.log_authentication_event.assert_called()
    
    @patch('app.api.auth.verify_oauth_token')
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.deps.get_db')
    def test_social_auth_invalid_token(self, mock_get_db, mock_get_rate_limiter, mock_verify_oauth_token):
        """Test social authentication with invalid OAuth token."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        with patch('app.api.auth.get_audit_logger') as mock_get_audit_logger:
            mock_audit_logger = AsyncMock()
            mock_get_audit_logger.return_value = mock_audit_logger
            
            # Mock OAuth token verification - return None for invalid token
            mock_verify_oauth_token.return_value = None
            
            response = self.client.post("/auth/social", json=self.valid_social_auth_data)
            
            assert response.status_code == 401
            response_data = response.json()
            assert "invalid_oauth_token" in response_data.get("detail", {}).get("error", "")
    
    def test_social_auth_invalid_provider(self):
        """Test social authentication with invalid provider."""
        invalid_data = self.valid_social_auth_data.copy()
        invalid_data["provider"] = "invalid_provider"
        
        response = self.client.post("/auth/social", json=invalid_data)
        assert response.status_code == 422
    
    def test_social_auth_missing_token(self):
        """Test social authentication without access token."""
        invalid_data = self.valid_social_auth_data.copy()
        del invalid_data["access_token"]
        
        response = self.client.post("/auth/social", json=invalid_data)
        assert response.status_code == 422


class TestAuthLogin:
    """Test cases for user login endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_login_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "remember_me": False,
            "device_name": "Test Device"
        }
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.auth.get_account_lockout_service')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_user_sync_service')
    @patch('app.api.auth.get_supabase_client')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.deps.get_db')
    def test_login_success(
        self,
        mock_get_db,
        mock_get_cookie_manager,
        mock_get_supabase_client,
        mock_get_user_sync_service,
        mock_get_session_manager,
        mock_get_account_lockout_service,
        mock_get_password_security,
        mock_get_audit_logger,
        mock_get_rate_limiter
    ):
        """Test successful user login."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = True
        mock_get_password_security.return_value = mock_password_security
        
        # Mock account lockout service
        mock_account_lockout_service = AsyncMock()
        mock_lockout_info = Mock()
        mock_lockout_info.is_locked = False
        mock_account_lockout_service.check_account_lockout.return_value = mock_lockout_info
        mock_get_account_lockout_service.return_value = mock_account_lockout_service
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_result = Mock()
        mock_session_result.session_id = "login-session-123"
        mock_session_result.access_token = "login-access-token-123"
        mock_session_result.refresh_token = "login-refresh-token-123"
        mock_session_result.expires_in = 900
        mock_session_result.refresh_expires_in = 604800
        mock_session_manager.create_session.return_value = mock_session_result
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Mock user sync service
        mock_get_user_sync_service.return_value = Mock()
        
        # Mock Supabase client
        mock_get_supabase_client.return_value = Mock()
        
        # Mock existing user
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.display_name = "John Doe"
        mock_user.avatar_url = None
        mock_user.language_code = "en"
        mock_user.is_premium = False
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.streak_count = 5
        mock_user.total_xp = 150
        
        # Mock Supabase user
        mock_supabase_user = Mock()
        mock_supabase_user.supabase_id = "supabase-user-123"
        mock_supabase_user.email_verified = True
        mock_supabase_user.last_sign_in_at = datetime.now(timezone.utc)
        mock_supabase_user.mark_sync_success = Mock()
        
        # Mock password history
        mock_password_history = Mock()
        mock_password_history.password_hash = "hashed_password"
        
        # Setup database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_user,  # User query
            mock_supabase_user,  # SupabaseUser query
            mock_password_history  # PasswordHistory query
        ]
        mock_db.commit = Mock()
        
        # Make the API call
        response = self.client.post("/auth/login", json=self.valid_login_data)
        
        # Assertions
        assert response.status_code == 200
        response_data = response.json()
        
        assert "user" in response_data
        assert "tokens" in response_data
        assert "session_id" in response_data
        assert response_data["user"]["email"] == "test@example.com"
        assert response_data["user"]["first_name"] == "John"
        assert response_data["tokens"]["token_type"] == "bearer"
        assert response_data["session_id"] == "login-session-123"
        assert response_data["remember_me"] == False
        
        # Verify service calls
        mock_rate_limiter.check_rate_limit.assert_called_once()
        mock_account_lockout_service.check_account_lockout.assert_called_once()
        mock_password_security.verify_password.assert_called_once()
        mock_account_lockout_service.clear_failed_attempts.assert_called_once()
        mock_session_manager.create_session.assert_called_once()
        mock_audit_logger.log_authentication_event.assert_called()
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_account_lockout_service')
    @patch('app.api.deps.get_db')
    def test_login_invalid_credentials(self, mock_get_db, mock_get_account_lockout_service, mock_get_audit_logger, mock_get_rate_limiter):
        """Test login with invalid credentials."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock account lockout service
        mock_account_lockout_service = AsyncMock()
        mock_lockout_info = Mock()
        mock_lockout_info.is_locked = False
        mock_account_lockout_service.check_account_lockout.return_value = mock_lockout_info
        mock_get_account_lockout_service.return_value = mock_account_lockout_service
        
        # Mock no user found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = self.client.post("/auth/login", json=self.valid_login_data)
        
        assert response.status_code == 401
        response_data = response.json()
        assert response_data["detail"]["error"] == "invalid_credentials"
        
        # Verify failed attempt was recorded
        mock_account_lockout_service.record_failed_attempt.assert_called_once()
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_account_lockout_service')
    @patch('app.api.deps.get_db')
    def test_login_account_locked(self, mock_get_db, mock_get_account_lockout_service, mock_get_audit_logger, mock_get_rate_limiter):
        """Test login with locked account."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = True
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock account lockout service - account is locked
        mock_account_lockout_service = AsyncMock()
        mock_lockout_info = Mock()
        mock_lockout_info.is_locked = True
        mock_lockout_info.lockout_reason = "too_many_failed_attempts"
        mock_lockout_info.locked_at = datetime.now(timezone.utc)
        mock_lockout_info.unlock_at = datetime.now(timezone.utc)
        mock_lockout_info.can_retry_at = datetime.now(timezone.utc)
        mock_account_lockout_service.check_account_lockout.return_value = mock_lockout_info
        mock_get_account_lockout_service.return_value = mock_account_lockout_service
        
        response = self.client.post("/auth/login", json=self.valid_login_data)
        
        assert response.status_code == 403
        response_data = response.json()
        assert response_data["detail"]["error"] == "account_locked"
        assert "lockout_info" in response_data["detail"]
    
    @patch('app.api.auth.get_rate_limiter')
    @patch('app.api.deps.get_db')
    def test_login_rate_limit_exceeded(self, mock_get_db, mock_get_rate_limiter):
        """Test login rate limit exceeded."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock rate limiter to return rate limit exceeded
        mock_rate_limiter = AsyncMock()
        mock_rate_check = Mock()
        mock_rate_check.allowed = False
        mock_rate_check.retry_after = 900
        mock_rate_check.limit = 5
        mock_rate_limiter.check_rate_limit.return_value = mock_rate_check
        mock_get_rate_limiter.return_value = mock_rate_limiter
        
        # Mock audit logger
        with patch('app.api.auth.get_audit_logger') as mock_get_audit_logger:
            mock_audit_logger = AsyncMock()
            mock_get_audit_logger.return_value = mock_audit_logger
            
            response = self.client.post("/auth/login", json=self.valid_login_data)
            
            assert response.status_code == 429
            response_data = response.json()
            assert response_data["detail"]["error"] == "rate_limit_exceeded"
    
    def test_login_invalid_email(self):
        """Test login with invalid email format."""
        invalid_data = self.valid_login_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = self.client.post("/auth/login", json=invalid_data)
        assert response.status_code == 422
    
    def test_login_missing_password(self):
        """Test login without password."""
        invalid_data = self.valid_login_data.copy()
        del invalid_data["password"]
        
        response = self.client.post("/auth/login", json=invalid_data)
        assert response.status_code == 422


class TestAuthEndpointsNotImplemented:
    """Test cases for not-yet-implemented auth endpoints."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
    
    
    def test_logout_not_implemented(self):
        """Test that logout endpoint returns 501."""
        # This would require authentication, but we're just testing the 501 response
        # The auth dependency will fail first, but that's expected for now
        response = self.client.post("/auth/logout", json={
            "logout_all_devices": False
        })
        # Could be 401 (no auth) or 501 (not implemented) depending on FastAPI's order
        assert response.status_code in [401, 501]


class TestAuthPasswordReset:
    """Test cases for password reset endpoints."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_reset_request = {
            "email": "test@example.com"
        }
        self.valid_confirm_request = {
            "token": "valid_reset_token_123",
            "new_password": "NewSecurePass123!"
        }
    
    @patch('app.api.auth.get_password_reset_service')
    def test_password_reset_request_success(self, mock_get_service):
        """Test successful password reset request."""
        # Mock service
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "If the email address exists, a password reset link has been sent."
        mock_service.request_password_reset.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        response = self.client.post("/auth/password-reset", json=self.valid_reset_request)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "message" in response_data
        assert "email" in response_data
        assert response_data["email"] == "test@example.com"
    
    @patch('app.api.auth.get_password_reset_service')
    def test_password_reset_request_rate_limited(self, mock_get_service):
        """Test password reset request rate limiting."""
        # Mock service with rate limit error
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_code = "rate_limit_exceeded"
        mock_result.message = "Too many password reset requests"
        mock_service.request_password_reset.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        response = self.client.post("/auth/password-reset", json=self.valid_reset_request)
        
        assert response.status_code == 429
        response_data = response.json()
        assert response_data["detail"]["error"] == "rate_limit_exceeded"
    
    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email."""
        invalid_data = {"email": "invalid-email"}
        
        response = self.client.post("/auth/password-reset", json=invalid_data)
        assert response.status_code == 422
    
    @patch('app.api.auth.get_password_reset_service')
    def test_password_reset_confirm_success(self, mock_get_service):
        """Test successful password reset confirmation."""
        # Mock service
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Password has been reset successfully."
        mock_service.confirm_password_reset.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        response = self.client.post("/auth/password-reset/confirm", json=self.valid_confirm_request)
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Password has been reset successfully."
        assert response_data["success"] is True
    
    @patch('app.api.auth.get_password_reset_service')
    def test_password_reset_confirm_invalid_token(self, mock_get_service):
        """Test password reset confirmation with invalid token."""
        # Mock service with invalid token error
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_code = "invalid_token"
        mock_result.message = "Invalid or expired password reset token."
        mock_service.confirm_password_reset.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        response = self.client.post("/auth/password-reset/confirm", json=self.valid_confirm_request)
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["detail"]["error"] == "invalid_token"
    
    @patch('app.api.auth.get_password_reset_service')
    def test_password_reset_confirm_password_validation_failed(self, mock_get_service):
        """Test password reset confirmation with weak password."""
        # Mock service with validation error
        mock_service = Mock()
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_code = "password_validation_failed"
        mock_result.message = "Password validation failed: too_short"
        mock_service.confirm_password_reset.return_value = mock_result
        mock_get_service.return_value = mock_service
        
        response = self.client.post("/auth/password-reset/confirm", json=self.valid_confirm_request)
        
        assert response.status_code == 422
        response_data = response.json()
        assert response_data["detail"]["error"] == "password_validation_failed"
    
    def test_password_reset_confirm_invalid_password(self):
        """Test password reset confirmation with invalid password format."""
        invalid_data = self.valid_confirm_request.copy()
        invalid_data["new_password"] = "weak"
        
        response = self.client.post("/auth/password-reset/confirm", json=invalid_data)
        assert response.status_code == 422


class TestAuthSchemas:
    """Test cases for authentication schemas."""
    
    def test_user_registration_request_valid(self):
        """Test valid user registration request."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "first_name": "John",
            "last_name": "Doe",
            "language_code": "en",
            "marketing_consent": False,
            "terms_accepted": True
        }
        
        request = UserRegistrationRequest(**data)
        assert request.email == "test@example.com"
        assert request.first_name == "John"
        assert request.terms_accepted is True
    
    def test_user_registration_request_password_validation(self):
        """Test password validation in registration request."""
        # Test weak password
        with pytest.raises(ValueError, match="Password must contain at least one uppercase letter"):
            UserRegistrationRequest(
                email="test@example.com",
                password="weakpassword",
                first_name="John",
                terms_accepted=True
            )
        
        # Test password without digit
        with pytest.raises(ValueError, match="Password must contain at least one digit"):
            UserRegistrationRequest(
                email="test@example.com",
                password="WeakPassword!",
                first_name="John",
                terms_accepted=True
            )
        
        # Test password without special character
        with pytest.raises(ValueError, match="Password must contain at least one special character"):
            UserRegistrationRequest(
                email="test@example.com",
                password="WeakPassword123",
                first_name="John",
                terms_accepted=True
            )
    
    def test_user_registration_request_terms_validation(self):
        """Test terms acceptance validation."""
        with pytest.raises(ValueError, match="Terms of service must be accepted"):
            UserRegistrationRequest(
                email="test@example.com",
                password="SecurePass123!",
                first_name="John",
                terms_accepted=False
            )
    
    def test_user_registration_request_language_code_validation(self):
        """Test language code validation."""
        # Valid language codes should work
        request = UserRegistrationRequest(
            email="test@example.com",
            password="SecurePass123!",
            first_name="John",
            terms_accepted=True,
            language_code="en"
        )
        assert request.language_code == "en"
        
        request = UserRegistrationRequest(
            email="test@example.com",
            password="SecurePass123!",
            first_name="John",
            terms_accepted=True,
            language_code="en-US"
        )
        assert request.language_code == "en-US"
        
        # Invalid language code should fail (use shorter invalid code that meets length constraint)
        with pytest.raises(ValueError, match="Language code must be in ISO 639-1 format"):
            UserRegistrationRequest(
                email="test@example.com",
                password="SecurePass123!",
                first_name="John",
                terms_accepted=True,
                language_code="xyz"
            )
    
    def test_login_request_valid(self):
        """Test valid login request."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "remember_me": True,
            "device_name": "iPhone 14"
        }
        
        request = LoginRequest(**data)
        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"
        assert request.remember_me is True
        assert request.device_name == "iPhone 14"
    
    def test_login_request_defaults(self):
        """Test login request with defaults."""
        data = {
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
        
        request = LoginRequest(**data)
        assert request.email == "test@example.com"
        assert request.password == "SecurePass123!"
        assert request.remember_me is False
        assert request.device_name is None