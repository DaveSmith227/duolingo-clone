"""
Integration Tests for Profile Management API Endpoints

Tests for user profile management including profile updates, privacy settings,
and account security functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, OAuthProvider
from app.models.auth import SupabaseUser, AuthSession
from app.models.progress import UserCourse, UserLessonProgress
from app.models.gamification import UserAchievement


class TestProfileEndpoints:
    """Test cases for profile management API endpoints."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        
        # Mock JWT payload
        self.mock_jwt_payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": 1234567890
        }
        
        # Mock user data
        self.mock_user = Mock(spec=User)
        self.mock_user.id = "user-123"
        self.mock_user.email = "test@example.com"
        self.mock_user.name = "Test User"
        self.mock_user.avatar_url = "https://example.com/avatar.jpg"
        self.mock_user.is_email_verified = True
        self.mock_user.daily_xp_goal = 20
        self.mock_user.timezone = "UTC"
        self.mock_user.password_hash = "$2b$12$hashedpassword"
        self.mock_user.created_at = datetime.now(timezone.utc)
        self.mock_user.updated_at = datetime.now(timezone.utc)
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_get_user_profile_success(self, mock_get_db, mock_get_current_user_id):
        """Test successful user profile retrieval."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Make request
        response = self.client.get(
            "/profile/me",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user-123"
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
        assert data["is_email_verified"] is True
        assert data["daily_xp_goal"] == 20
        assert "privacy_settings" in data
        assert "notification_settings" in data
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_get_user_profile_not_found(self, mock_get_db, mock_get_current_user_id):
        """Test user profile retrieval when user not found."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Make request
        response = self.client.get(
            "/profile/me",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify error response
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "user_not_found"
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.profile.get_audit_logger')
    @patch('app.api.deps.get_db')
    def test_update_user_profile_success(
        self,
        mock_get_db,
        mock_get_audit_logger,
        mock_get_current_user_id
    ):
        """Test successful user profile update."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Update data
        update_data = {
            "name": "Updated Name",
            "daily_xp_goal": 30,
            "timezone": "America/New_York"
        }
        
        # Make request
        response = self.client.put(
            "/profile/me",
            json=update_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Profile updated successfully."
        assert "name" in data["updated_fields"]
        assert "daily_xp_goal" in data["updated_fields"]
        assert "timezone" in data["updated_fields"]
        
        # Verify user was updated
        assert self.mock_user.name == "Updated Name"
        assert self.mock_user.daily_xp_goal == 30
        assert self.mock_user.timezone == "America/New_York"
        
        # Verify database commit
        mock_db.commit.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["event_type"] == "profile_updated"
        assert call_args[1]["success"] is True
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_update_user_profile_no_changes(self, mock_get_db, mock_get_current_user_id):
        """Test profile update with no changes."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Empty update data
        update_data = {}
        
        # Make request
        response = self.client.put(
            "/profile/me",
            json=update_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "No changes were made."
        assert data["updated_fields"] == []
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.profile.get_password_security')
    @patch('app.api.profile.get_audit_logger')
    @patch('app.api.deps.get_db')
    def test_change_email_success(
        self,
        mock_get_db,
        mock_get_audit_logger,
        mock_get_password_security,
        mock_get_current_user_id
    ):
        """Test successful email change."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = True
        mock_get_password_security.return_value = mock_password_security
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_user,  # First query for current user
            None  # Second query to check if new email exists
        ]
        
        # Email change data
        email_data = {
            "new_email": "newemail@example.com",
            "password": "currentpassword123"
        }
        
        # Make request
        response = self.client.post(
            "/profile/change-email",
            json=email_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "Email address updated successfully" in data["message"]
        assert "email" in data["updated_fields"]
        
        # Verify user email was updated
        assert self.mock_user.email == "newemail@example.com"
        assert self.mock_user.is_email_verified is False
        
        # Verify password verification was called
        mock_password_security.verify_password.assert_called_once_with(
            "currentpassword123", "$2b$12$hashedpassword"
        )
        
        # Verify audit logging
        mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["event_type"] == "email_changed"
        assert call_args[1]["success"] is True
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.profile.get_password_security')
    @patch('app.api.deps.get_db')
    def test_change_email_invalid_password(
        self,
        mock_get_db,
        mock_get_password_security,
        mock_get_current_user_id
    ):
        """Test email change with invalid password."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock password security - invalid password
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = False
        mock_get_password_security.return_value = mock_password_security
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Email change data
        email_data = {
            "new_email": "newemail@example.com",
            "password": "wrongpassword"
        }
        
        # Make request
        response = self.client.post(
            "/profile/change-email",
            json=email_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify error response
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "invalid_password"
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_change_email_already_exists(self, mock_get_db, mock_get_current_user_id):
        """Test email change when new email already exists."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock existing user with new email
        existing_user = Mock(spec=User)
        existing_user.id = "other-user"
        existing_user.email = "newemail@example.com"
        
        # Mock password security
        with patch('app.api.profile.get_password_security') as mock_get_password_security:
            mock_password_security = Mock()
            mock_password_security.verify_password.return_value = True
            mock_get_password_security.return_value = mock_password_security
            
            # Mock database queries
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                self.mock_user,  # Current user query
                existing_user  # Email exists query
            ]
            
            # Email change data
            email_data = {
                "new_email": "newemail@example.com",
                "password": "currentpassword123"
            }
            
            # Make request
            response = self.client.post(
                "/profile/change-email",
                json=email_data,
                headers={"Authorization": "Bearer valid_token"}
            )
            
            # Verify error response
            assert response.status_code == 409
            data = response.json()
            assert data["detail"]["error"] == "email_already_exists"
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.profile.get_password_security')
    @patch('app.api.profile.get_audit_logger')
    @patch('app.api.deps.get_db')
    def test_change_password_success(
        self,
        mock_get_db,
        mock_get_audit_logger,
        mock_get_password_security,
        mock_get_current_user_id
    ):
        """Test successful password change."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.side_effect = [True, False]  # Current valid, new different
        mock_password_security.validate_password_strength.return_value = True
        mock_password_security.hash_password.return_value = "$2b$12$newhashedpassword"
        mock_get_password_security.return_value = mock_password_security
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Password change data
        password_data = {
            "current_password": "currentpassword123",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123"
        }
        
        # Make request
        response = self.client.post(
            "/profile/change-password",
            json=password_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password changed successfully."
        assert "password" in data["updated_fields"]
        
        # Verify password was updated
        assert self.mock_user.password_hash == "$2b$12$newhashedpassword"
        
        # Verify password security methods were called
        mock_password_security.verify_password.assert_called()
        mock_password_security.validate_password_strength.assert_called_once_with("newpassword123")
        mock_password_security.hash_password.assert_called_once_with("newpassword123")
        
        # Verify audit logging
        mock_audit_logger.log_authentication_event.assert_called_once()
        call_args = mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["event_type"] == "password_changed"
        assert call_args[1]["success"] is True
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.profile.get_password_security')
    @patch('app.api.deps.get_db')
    def test_change_password_weak_password(
        self,
        mock_get_db,
        mock_get_password_security,
        mock_get_current_user_id
    ):
        """Test password change with weak new password."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = True
        mock_password_security.validate_password_strength.return_value = False  # Weak password
        mock_get_password_security.return_value = mock_password_security
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Password change data with weak password
        password_data = {
            "current_password": "currentpassword123",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        # Make request
        response = self.client.post(
            "/profile/change-password",
            json=password_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify error response
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "weak_password"
    
    def test_update_privacy_settings_success(self):
        """Test successful privacy settings update."""
        # Privacy settings data
        privacy_data = {
            "profile_visibility": "friends",
            "show_email": False,
            "data_processing_consent": True,
            "marketing_consent": False
        }
        
        # Make request
        with patch('app.api.profile.get_current_user_id', return_value="user-123"):
            with patch('app.api.deps.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                response = self.client.put(
                    "/profile/privacy-settings",
                    json=privacy_data,
                    headers={"Authorization": "Bearer valid_token"}
                )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Privacy settings updated successfully."
                assert len(data["updated_fields"]) == 4
    
    def test_update_notification_settings_success(self):
        """Test successful notification settings update."""
        # Notification settings data
        notification_data = {
            "email_notifications": True,
            "push_notifications": False,
            "lesson_reminders": True,
            "marketing_emails": False
        }
        
        # Make request
        with patch('app.api.profile.get_current_user_id', return_value="user-123"):
            with patch('app.api.deps.get_db') as mock_get_db:
                mock_db = Mock()
                mock_get_db.return_value = mock_db
                
                response = self.client.put(
                    "/profile/notification-settings",
                    json=notification_data,
                    headers={"Authorization": "Bearer valid_token"}
                )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Notification settings updated successfully."
                assert len(data["updated_fields"]) == 4
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_get_account_security_success(self, mock_get_db, mock_get_current_user_id):
        """Test successful account security information retrieval."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock OAuth providers
        mock_oauth_provider = Mock(spec=OAuthProvider)
        mock_oauth_provider.provider = "google"
        
        # Mock supabase user and sessions
        mock_supabase_user = Mock(spec=SupabaseUser)
        mock_supabase_user.id = "supabase-123"
        mock_supabase_user.last_sign_in_at = datetime.now(timezone.utc)
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.mock_user,  # User query
            mock_supabase_user  # Supabase user query
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_oauth_provider]
        mock_db.query.return_value.filter.return_value.count.return_value = 2  # Active sessions
        
        # Make request
        response = self.client.get(
            "/profile/security",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["email_verified"] is True
        assert data["has_password"] is True
        assert "google" in data["oauth_providers"]
        assert data["active_sessions"] == 2
    
    @patch('app.api.profile.get_current_user_id')
    @patch('app.api.deps.get_db')
    def test_get_account_stats_success(self, mock_get_db, mock_get_current_user_id):
        """Test successful account statistics retrieval."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock current user ID
        mock_get_current_user_id.return_value = "user-123"
        
        # Mock user courses
        mock_course = Mock(spec=UserCourse)
        mock_course.total_xp = 500
        mock_course.current_streak = 10
        mock_course.longest_streak = 15
        
        # Mock database queries and counts
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        mock_db.query.return_value.filter.return_value.count.side_effect = [2, 25, 3, 5]  # courses, lessons, achievements, sessions
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_course]
        
        # Make request
        response = self.client.get(
            "/profile/stats",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["courses_enrolled"] == 2
        assert data["lessons_completed"] == 25
        assert data["total_xp_earned"] == 500
        assert data["current_streak"] == 10
        assert data["longest_streak"] == 15
        assert data["achievements_earned"] == 3
        assert data["total_logins"] == 5