"""
Unit Tests for Admin API Endpoints

Tests for admin dashboard functionality including user management,
audit log viewing, and analytics.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
import json

from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models.user import User
from app.models.auth import AuthAuditLog, AuthSession
from app.models.rbac import Role, UserRoleAssignment
from app.schemas.admin import UserSummary, AdminAnalyticsResponse


class TestAdminEndpoints:
    """Test cases for admin API endpoints."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.client = TestClient(app)
        self.admin_token = "admin_test_token"
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Mock admin user
        self.admin_user_id = "admin-123"
        
        # Test data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        self.test_user.name = "Test User"
        self.test_user.is_active = True
        self.test_user.deleted_at = None
        self.test_user.created_at = datetime.now(timezone.utc)
        self.test_user.updated_at = datetime.now(timezone.utc)
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_search_users_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful user search."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock query chain
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [self.test_user]
        mock_session.query.return_value = mock_query
        
        # Mock role and statistics queries
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            Mock(name="user")
        ]
        mock_session.query.return_value.filter.return_value.count.side_effect = [5, 2]  # login count, failed count
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = Mock(
            created_at=datetime.now(timezone.utc)
        )
        mock_session.query.return_value.filter.return_value.first.return_value = Mock(id="supabase-123")
        
        # Make request
        response = self.client.get(
            "/admin/users/search?query=test&page=1&page_size=10",
            headers=self.admin_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert data["total_count"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_search_users_unauthorized(self, mock_audit_logger, mock_db, mock_admin):
        """Test user search without admin privileges."""
        # Make request without authorization
        response = self.client.get("/admin/users/search")
        
        # Verify unauthorized response
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_get_user_detail_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful user detail retrieval."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock user query
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            Mock(id="supabase-123"),  # Supabase user query
        ]
        
        # Mock role queries
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            Mock(name="user")
        ]
        
        # Mock statistics queries
        mock_session.query.return_value.filter.return_value.count.side_effect = [5, 2]  # login/failed counts
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = Mock(
            created_at=datetime.now(timezone.utc)
        )
        mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.side_effect = [
            [],  # sessions
            []   # audit events
        ]
        
        # Mock privacy service
        with patch('app.api.admin.PrivacyService') as mock_privacy:
            mock_privacy.return_value.check_consent_compliance.return_value = {
                "overall_compliant": True
            }
            
            # Make request
            response = self.client.get(
                f"/admin/users/{self.test_user.id}",
                headers=self.admin_headers
            )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user" in data
        assert data["user"]["id"] == self.test_user.id
        assert data["user"]["email"] == self.test_user.email
        assert "permissions" in data
        assert "account_statistics" in data
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_get_user_detail_not_found(self, mock_audit_logger, mock_db, mock_admin):
        """Test user detail retrieval for non-existent user."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock user not found
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Make request
        response = self.client.get(
            "/admin/users/nonexistent",
            headers=self.admin_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_get_admin_analytics_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful admin analytics retrieval."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock count queries
        mock_session.query.return_value.count.side_effect = [
            100,  # total users
            90,   # active users
            5,    # suspended users
            5,    # deleted users
            10,   # new users last 30 days
            50,   # total login attempts
            40,   # successful logins
            10,   # failed logins
        ]
        
        # Mock distinct count query
        mock_session.query.return_value.filter.return_value.distinct.return_value.count.return_value = 25
        
        # Make request
        response = self.client.get(
            "/admin/analytics",
            headers=self.admin_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metrics" in data
        assert "recent_alerts" in data
        assert "login_success_rate_last_24h" in data
        assert "failed_login_rate_last_24h" in data
        assert "generated_at" in data
        
        # Verify metrics
        metrics = data["metrics"]
        assert metrics["total_users"] == 100
        assert metrics["active_users"] == 90
        assert metrics["suspended_users"] == 5
        assert metrics["deleted_users"] == 5
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_get_audit_logs_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful audit logs retrieval."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock audit log
        mock_log = Mock(spec=AuthAuditLog)
        mock_log.id = "log-123"
        mock_log.event_type = "login"
        mock_log.user_id = "user-123"
        mock_log.success = True
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Test Agent"
        mock_log.created_at = datetime.now(timezone.utc)
        mock_log.get_metadata_dict.return_value = {"test": "data"}
        
        # Mock query chain
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_session.query.return_value = mock_query
        
        # Mock user email query
        mock_session.query.return_value.filter.return_value.first.return_value = Mock(
            email="test@example.com"
        )
        
        # Make request
        response = self.client.get(
            "/admin/audit-logs?page=1&page_size=10",
            headers=self.admin_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert data["total_count"] == 1
        assert len(data["logs"]) == 1
        
        # Verify log entry
        log_entry = data["logs"][0]
        assert log_entry["id"] == "log-123"
        assert log_entry["event_type"] == "login"
        assert log_entry["user_id"] == "user-123"
        assert log_entry["success"] is True
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_export_audit_logs_json_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful audit logs export in JSON format."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock audit log
        mock_log = Mock(spec=AuthAuditLog)
        mock_log.id = "log-123"
        mock_log.event_type = "login"
        mock_log.user_id = "user-123"
        mock_log.success = True
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Test Agent"
        mock_log.created_at = datetime.now(timezone.utc)
        mock_log.get_metadata_dict.return_value = {"test": "data"}
        
        # Mock query chain
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_session.query.return_value = mock_query
        
        # Make request
        export_request = {
            "format": "json",
            "include_details": True
        }
        
        response = self.client.post(
            "/admin/audit-logs/export",
            headers=self.admin_headers,
            json=export_request
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")
        
        # Verify JSON content can be parsed
        content = response.content.decode()
        export_data = json.loads(content)
        assert isinstance(export_data, list)
        assert len(export_data) == 1
        assert export_data[0]["id"] == "log-123"
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_export_audit_logs_csv_success(self, mock_audit_logger, mock_db, mock_admin):
        """Test successful audit logs export in CSV format."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock audit log
        mock_log = Mock(spec=AuthAuditLog)
        mock_log.id = "log-123"
        mock_log.event_type = "login"
        mock_log.user_id = "user-123"
        mock_log.success = True
        mock_log.ip_address = "192.168.1.1"
        mock_log.user_agent = "Test Agent"
        mock_log.created_at = datetime.now(timezone.utc)
        mock_log.get_metadata_dict.return_value = {"test": "data"}
        
        # Mock query chain
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_log]
        mock_session.query.return_value = mock_query
        
        # Make request
        export_request = {
            "format": "csv",
            "include_details": False
        }
        
        response = self.client.post(
            "/admin/audit-logs/export",
            headers=self.admin_headers,
            json=export_request
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")
        
        # Verify CSV content
        content = response.content.decode()
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # Header + at least one data row
        assert "id,event_type,user_id" in lines[0]  # Header
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_search_users_with_filters(self, mock_audit_logger, mock_db, mock_admin):
        """Test user search with various filters."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [self.test_user]
        mock_session.query.return_value = mock_query
        
        # Mock additional queries
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.count.side_effect = [0, 0]
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Make request with filters
        response = self.client.get(
            "/admin/users/search?status=active&sort_by=email&sort_order=asc&created_after=2023-01-01T00:00:00Z",
            headers=self.admin_headers
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        
        # Verify filter methods were called
        assert mock_query.filter.call_count >= 1
    
    @patch('app.api.admin.get_current_admin_user')
    @patch('app.api.admin.get_db')
    @patch('app.api.admin.get_audit_logger')
    def test_admin_endpoints_error_handling(self, mock_audit_logger, mock_db, mock_admin):
        """Test error handling in admin endpoints."""
        # Mock dependencies
        mock_admin.return_value = self.admin_user_id
        mock_audit_logger.return_value = AsyncMock()
        
        # Mock database error
        mock_db.side_effect = Exception("Database error")
        
        # Make request
        response = self.client.get(
            "/admin/users/search",
            headers=self.admin_headers
        )
        
        # Verify error response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to search users" in response.json()["detail"]