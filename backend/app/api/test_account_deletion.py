"""
Integration Tests for Account Deletion API Endpoint

Tests for the account deletion and data export endpoints including
validation, authentication, and GDPR compliance functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.auth import AccountDeletionRequest, DataExportRequest
from app.models.user import User


class TestAccountDeletionEndpoint:
    """Test cases for account deletion API endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_deletion_data = {
            "confirmation": "DELETE MY ACCOUNT",
            "password": "validpassword123",
            "reason": "No longer needed"
        }
        
        self.valid_oauth_deletion_data = {
            "confirmation": "DELETE MY ACCOUNT",
            "reason": "Switching platforms"
        }
        
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
        self.mock_user.password_hash = "$2b$12$hashedpassword"
        
        self.mock_oauth_user = Mock(spec=User)
        self.mock_oauth_user.id = "user-123"
        self.mock_oauth_user.email = "test@example.com"
        self.mock_oauth_user.password_hash = None  # OAuth-only user
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.deps.get_db')
    def test_delete_account_success_with_password(
        self,
        mock_get_db,
        mock_get_cookie_manager,
        mock_get_password_security,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test successful account deletion with password verification."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = True
        mock_get_password_security.return_value = mock_password_security
        
        # Mock GDPR service
        mock_gdpr_service = Mock()
        mock_gdpr_service.delete_user_account = AsyncMock(return_value={
            "user_id": "user-123",
            "email": "test@example.com",
            "total_records_deleted": 42,
            "supabase_auth_deleted": True
        })
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make deletion request
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Your account has been successfully deleted. All your data has been permanently removed."
        assert data["user_id"] == "user-123"
        assert data["email"] == "test@example.com"
        assert data["records_deleted"] == 42
        assert data["supabase_auth_deleted"] is True
        assert "deleted_at" in data
        
        # Verify password was verified
        mock_password_security.verify_password.assert_called_once_with(
            "validpassword123", "$2b$12$hashedpassword"
        )
        
        # Verify GDPR service was called
        mock_gdpr_service.delete_user_account.assert_called_once()
        call_args = mock_gdpr_service.delete_user_account.call_args
        assert call_args[1]["user_id"] == "user-123"
        assert call_args[1]["reason"] == "No longer needed"
        
        # Verify cookies were cleared
        mock_cookie_manager.clear_auth_cookies.assert_called_once()
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.deps.get_db')
    def test_delete_account_success_oauth_user(
        self,
        mock_get_db,
        mock_get_cookie_manager,
        mock_get_password_security,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test successful account deletion for OAuth-only user."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock OAuth user found in database (no password hash)
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_oauth_user
        
        # Mock GDPR service
        mock_gdpr_service = Mock()
        mock_gdpr_service.delete_user_account = AsyncMock(return_value={
            "user_id": "user-123",
            "email": "test@example.com",
            "total_records_deleted": 25,
            "supabase_auth_deleted": True
        })
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make deletion request (OAuth user, no password needed)
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_oauth_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-123"
        assert data["records_deleted"] == 25
        
        # Verify password verification was skipped
        mock_get_password_security.assert_not_called()
        
        # Verify GDPR service was called
        mock_gdpr_service.delete_user_account.assert_called_once()
    
    def test_delete_account_invalid_confirmation(self):
        """Test account deletion with invalid confirmation phrase."""
        invalid_data = {
            "confirmation": "delete my account",  # Wrong case
            "password": "validpassword123"
        }
        
        response = self.client.post(
            "/auth/delete-account",
            json=invalid_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify validation error
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_confirmation"
        assert "DELETE MY ACCOUNT" in data["detail"]["message"]
    
    def test_delete_account_without_authentication(self):
        """Test account deletion without authentication token."""
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data
        )
        
        # Verify authentication required
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
    
    @patch('app.api.auth.get_current_user_payload')
    def test_delete_account_invalid_token_payload(self, mock_get_current_user_payload):
        """Test account deletion with invalid token payload."""
        # Mock invalid token payload (missing sub)
        mock_get_current_user_payload.return_value = {
            "email": "test@example.com",
            "exp": 1234567890
            # Missing "sub" field
        }
        
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify authentication error
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "invalid_token"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.deps.get_db')
    def test_delete_account_user_not_found(self, mock_get_db, mock_get_current_user_payload):
        """Test account deletion when user is not found in database."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify user not found error
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "user_not_found"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.deps.get_db')
    def test_delete_account_wrong_password(
        self,
        mock_get_db,
        mock_get_password_security,
        mock_get_current_user_payload
    ):
        """Test account deletion with wrong password."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock password verification failure
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = False
        mock_get_password_security.return_value = mock_password_security
        
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify password error
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "invalid_password"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.deps.get_db')
    def test_delete_account_password_required_missing(
        self,
        mock_get_db,
        mock_get_current_user_payload
    ):
        """Test account deletion missing password for non-OAuth user."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock user found in database with password hash
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Request without password for user who has password hash
        data_without_password = {
            "confirmation": "DELETE MY ACCOUNT",
            "reason": "No longer needed"
        }
        
        response = self.client.post(
            "/auth/delete-account",
            json=data_without_password,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify password required error
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "password_required"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.auth.get_password_security')
    @patch('app.api.deps.get_db')
    def test_delete_account_gdpr_service_error(
        self,
        mock_get_db,
        mock_get_password_security,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test account deletion when GDPR service fails."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock user found in database
        mock_db.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock password security
        mock_password_security = Mock()
        mock_password_security.verify_password.return_value = True
        mock_get_password_security.return_value = mock_password_security
        
        # Mock GDPR service failure
        mock_gdpr_service = Mock()
        mock_gdpr_service.delete_user_account = AsyncMock(side_effect=Exception("Database error"))
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        response = self.client.post(
            "/auth/delete-account",
            json=self.valid_deletion_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify internal server error
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "deletion_failed"


class TestDataExportEndpoint:
    """Test cases for data export API endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_export_data = {
            "format": "json",
            "include_sections": ["personal_data", "learning_data"]
        }
        
        # Mock JWT payload
        self.mock_jwt_payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": 1234567890
        }
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.deps.get_db')
    def test_export_data_success(
        self,
        mock_get_db,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test successful data export."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock GDPR service
        mock_gdpr_service = Mock()
        mock_export_data = {
            "export_info": {
                "user_id": "user-123",
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "gdpr_compliance": True
            },
            "personal_data": {
                "profile": {
                    "id": "user-123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
            },
            "learning_data": {
                "course_enrollments": []
            }
        }
        mock_gdpr_service.export_user_data = AsyncMock(return_value=mock_export_data)
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        # Make export request
        response = self.client.post(
            "/auth/export-data",
            json=self.valid_export_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["export_info"]["user_id"] == "user-123"
        assert data["export_info"]["gdpr_compliance"] is True
        assert data["personal_data"]["profile"]["email"] == "test@example.com"
        assert "learning_data" in data
        
        # Verify GDPR service was called
        mock_gdpr_service.export_user_data.assert_called_once()
        call_args = mock_gdpr_service.export_user_data.call_args
        assert call_args[1]["user_id"] == "user-123"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.deps.get_db')
    def test_export_data_filtered_sections(
        self,
        mock_get_db,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test data export with filtered sections."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock GDPR service with full data
        mock_gdpr_service = Mock()
        mock_full_data = {
            "export_info": {"user_id": "user-123"},
            "personal_data": {"profile": {"id": "user-123"}},
            "learning_data": {"courses": []},
            "gamification_data": {"achievements": []},
            "access_data": {"roles": []}
        }
        mock_gdpr_service.export_user_data = AsyncMock(return_value=mock_full_data)
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        # Request only specific sections
        export_request = {
            "format": "json",
            "include_sections": ["personal_data", "learning_data"]
        }
        
        response = self.client.post(
            "/auth/export-data",
            json=export_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response contains only requested sections
        assert response.status_code == 200
        data = response.json()
        assert "export_info" in data
        assert "personal_data" in data
        assert "learning_data" in data
        assert "gamification_data" not in data
        assert "access_data" not in data
    
    def test_export_data_invalid_format(self):
        """Test data export with invalid format."""
        invalid_data = {
            "format": "xml",  # Invalid format
            "include_sections": ["personal_data"]
        }
        
        response = self.client.post(
            "/auth/export-data",
            json=invalid_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify format validation error
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_format"
        assert "JSON format" in data["detail"]["message"]
    
    def test_export_data_without_authentication(self):
        """Test data export without authentication token."""
        response = self.client.post(
            "/auth/export-data",
            json=self.valid_export_data
        )
        
        # Verify authentication required
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
    
    @patch('app.api.auth.get_current_user_payload')
    def test_export_data_invalid_token_payload(self, mock_get_current_user_payload):
        """Test data export with invalid token payload."""
        # Mock invalid token payload (missing sub)
        mock_get_current_user_payload.return_value = {
            "email": "test@example.com",
            "exp": 1234567890
            # Missing "sub" field
        }
        
        response = self.client.post(
            "/auth/export-data",
            json=self.valid_export_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify authentication error
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "invalid_token"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_gdpr_service')
    @patch('app.api.deps.get_db')
    def test_export_data_gdpr_service_error(
        self,
        mock_get_db,
        mock_get_gdpr_service,
        mock_get_current_user_payload
    ):
        """Test data export when GDPR service fails."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock GDPR service failure
        mock_gdpr_service = Mock()
        mock_gdpr_service.export_user_data = AsyncMock(side_effect=Exception("Database error"))
        mock_get_gdpr_service.return_value = mock_gdpr_service
        
        response = self.client.post(
            "/auth/export-data",
            json=self.valid_export_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify internal server error
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "export_failed"