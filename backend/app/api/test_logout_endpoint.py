"""
Integration Tests for Logout API Endpoint

Tests for the logout endpoint including single session logout, logout from all devices,
authentication validation, cookie clearing, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.auth import LogoutRequest
from app.models.auth import AuthSession, SupabaseUser


class TestLogoutEndpoint:
    """Test cases for logout API endpoint."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.valid_logout_data = {
            "logout_all_devices": False
        }
        
        self.valid_logout_all_data = {
            "logout_all_devices": True
        }
        
        # Mock JWT payload
        self.mock_jwt_payload = {
            "sub": "user-123",
            "session_id": "session-123",
            "email": "test@example.com",
            "exp": 1234567890
        }
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_single_session_success(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test successful single session logout."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock client info
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        
        # Mock current user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_manager.invalidate_session.return_value = True
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make logout request
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out from current session."
        assert data["logout_all_devices"] is False
        assert "timestamp" in data
        
        # Verify session was invalidated
        mock_session_manager.invalidate_session.assert_called_once_with(
            session_id="session-123",
            reason="logout"
        )
        
        # Verify cookies were cleared
        mock_cookie_manager.clear_auth_cookies.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.log_authentication_event.assert_called_once()
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_all_devices_success(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test successful logout from all devices."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock client info
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        
        # Mock current user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock session manager
        mock_session_manager = Mock()
        mock_session_manager.invalidate_all_user_sessions.return_value = 3  # 3 sessions invalidated
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make logout all devices request
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_all_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "Successfully logged out from all devices" in data["message"]
        assert "3 sessions invalidated" in data["message"]
        assert data["logout_all_devices"] is True
        assert "timestamp" in data
        
        # Verify all sessions were invalidated
        mock_session_manager.invalidate_all_user_sessions.assert_called_once_with(
            user_id="user-123",
            reason="logout_all_devices"
        )
        
        # Verify cookies were cleared
        mock_cookie_manager.clear_auth_cookies.assert_called_once()
        
        # Verify audit logging
        mock_audit_logger.log_authentication_event.assert_called_once()
    
    def test_logout_without_authentication(self):
        """Test logout without authentication token."""
        # Make logout request without authorization header
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data
        )
        
        # Verify authentication required
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Authentication required"
    
    def test_logout_with_invalid_token(self):
        """Test logout with invalid authentication token."""
        # Make logout request with invalid token
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data,
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        # Verify authentication failed
        assert response.status_code == 401
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_with_missing_user_id_in_token(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test logout with token missing user ID."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock client info
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        
        # Mock current user payload without user ID
        invalid_payload = {
            "session_id": "session-123",
            "email": "test@example.com",
            "exp": 1234567890
            # Missing "sub" field
        }
        mock_get_current_user_payload.return_value = invalid_payload
        
        # Mock services
        mock_get_session_manager.return_value = Mock()
        mock_get_audit_logger.return_value = AsyncMock()
        mock_get_cookie_manager.return_value = Mock()
        
        # Make logout request
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify invalid token response
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "invalid_token"
        assert data["detail"]["message"] == "Invalid token payload."
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_with_session_manager_error(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test logout with session manager error."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock client info
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        
        # Mock current user payload
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        # Mock session manager with error
        mock_session_manager = Mock()
        mock_session_manager.invalidate_session.side_effect = Exception("Database error")
        mock_get_session_manager.return_value = mock_session_manager
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock cookie manager
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make logout request
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["error"] == "internal_error"
        assert data["detail"]["message"] == "Logout failed. Please try again."
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_single_session_without_session_id(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test logout when token doesn't have session_id."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock client info
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        
        # Mock current user payload without session_id
        payload_without_session = {
            "sub": "user-123",
            "email": "test@example.com",
            "exp": 1234567890
            # Missing "session_id" field
        }
        mock_get_current_user_payload.return_value = payload_without_session
        
        # Mock services
        mock_session_manager = Mock()
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        mock_cookie_manager = Mock()
        mock_get_cookie_manager.return_value = mock_cookie_manager
        
        # Make logout request
        response = self.client.post(
            "/auth/logout",
            json=self.valid_logout_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify response (should still succeed)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out from current session."
        
        # Verify session invalidation was not called (no session_id)
        mock_session_manager.invalidate_session.assert_not_called()
        
        # Verify cookies were still cleared
        mock_cookie_manager.clear_auth_cookies.assert_called_once()
    
    def test_logout_with_invalid_json(self):
        """Test logout with invalid JSON payload."""
        # Make logout request with invalid JSON
        response = self.client.post(
            "/auth/logout",
            data="invalid json",
            headers={
                "Authorization": "Bearer valid_token",
                "Content-Type": "application/json"
            }
        )
        
        # Verify validation error
        assert response.status_code == 422
    
    def test_logout_with_missing_fields(self):
        """Test logout with missing required fields."""
        # Make logout request with empty JSON
        response = self.client.post(
            "/auth/logout",
            json={},
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Should still work as logout_all_devices has default value
        # But will fail at authentication level since we don't mock it
        assert response.status_code == 401


class TestLogoutAuditLogging:
    """Test audit logging for logout functionality."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.mock_jwt_payload = {
            "sub": "user-123",
            "session_id": "session-123",
            "email": "test@example.com",
            "exp": 1234567890
        }
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_audit_logging_single_session(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test audit logging for single session logout."""
        # Mock all dependencies
        mock_get_db.return_value = Mock(spec=Session)
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        mock_session_manager = Mock()
        mock_session_manager.invalidate_session.return_value = True
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        mock_get_cookie_manager.return_value = Mock()
        
        # Make logout request
        response = self.client.post(
            "/auth/logout",
            json={"logout_all_devices": False},
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify audit logging was called with correct parameters
        mock_audit_logger.log_authentication_event.assert_called_once()
        
        # Check the audit log call arguments
        call_args = mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is True
        assert call_args[1]["user_id"] == "user-123"
        assert call_args[1]["ip_address"] == "192.168.1.1"
        assert call_args[1]["user_agent"] == "Test Agent"
        assert call_args[1]["session_id"] == "session-123"
        assert call_args[1]["metadata"]["logout_type"] == "current_session"
    
    @patch('app.api.auth.get_current_user_payload')
    @patch('app.api.auth.get_session_manager')
    @patch('app.api.auth.get_audit_logger')
    @patch('app.api.auth.get_cookie_manager')
    @patch('app.api.auth.get_client_info')
    @patch('app.api.deps.get_db')
    def test_logout_audit_logging_all_devices(
        self,
        mock_get_db,
        mock_get_client_info,
        mock_get_cookie_manager,
        mock_get_audit_logger,
        mock_get_session_manager,
        mock_get_current_user_payload
    ):
        """Test audit logging for logout all devices."""
        # Mock all dependencies
        mock_get_db.return_value = Mock(spec=Session)
        mock_get_client_info.return_value = {
            "ip_address": "192.168.1.1",
            "user_agent": "Test Agent"
        }
        mock_get_current_user_payload.return_value = self.mock_jwt_payload
        
        mock_session_manager = Mock()
        mock_session_manager.invalidate_all_user_sessions.return_value = 5
        mock_get_session_manager.return_value = mock_session_manager
        
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        mock_get_cookie_manager.return_value = Mock()
        
        # Make logout all devices request
        response = self.client.post(
            "/auth/logout",
            json={"logout_all_devices": True},
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Verify successful response
        assert response.status_code == 200
        
        # Verify audit logging was called with correct parameters
        mock_audit_logger.log_authentication_event.assert_called_once()
        
        # Check the audit log call arguments
        call_args = mock_audit_logger.log_authentication_event.call_args
        assert call_args[1]["success"] is True
        assert call_args[1]["user_id"] == "user-123"
        assert call_args[1]["metadata"]["logout_type"] == "all_devices"
        assert call_args[1]["metadata"]["sessions_invalidated"] == 5