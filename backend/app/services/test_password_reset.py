"""
Unit Tests for Password Reset Service

Tests for password reset functionality including token generation,
validation, email sending, and password update operations.
"""

import pytest
import hashlib
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta

from app.services.password_reset import PasswordResetService, PasswordResetResult
from app.models.user import User
from app.models.auth import SupabaseUser, PasswordResetToken


class TestPasswordResetService:
    """Test cases for password reset service."""
    
    def setup_method(self):
        """Set up test dependencies."""
        self.mock_db = Mock()
        self.service = PasswordResetService(self.mock_db)
        
        # Mock user data
        self.test_user = Mock(spec=User)
        self.test_user.id = "user-123"
        self.test_user.email = "test@example.com"
        self.test_user.first_name = "Test"
        self.test_user.last_name = "User"
        self.test_user.display_name = "Test User"
        
        self.test_supabase_user = Mock(spec=SupabaseUser)
        self.test_supabase_user.supabase_id = "supabase-123"
        self.test_supabase_user.email = "test@example.com"
    
    @patch('app.services.password_reset.get_email_service')
    @patch('app.services.password_reset.get_audit_logger')
    @patch('app.services.password_reset.get_password_security')
    @patch('app.services.password_reset.get_settings')
    async def test_request_password_reset_success(
        self,
        mock_get_settings,
        mock_get_password_security,
        mock_get_audit_logger,
        mock_get_email_service
    ):
        """Test successful password reset request."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.password_reset_expire_hours = 1
        mock_get_settings.return_value = mock_settings
        
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock email service
        mock_email_service = AsyncMock()
        mock_email_service.send_password_reset_email.return_value = True
        mock_get_email_service.return_value = mock_email_service
        
        # Mock database queries
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock no recent tokens (rate limiting check)
        self.mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        # Mock no existing unused tokens
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Mock token creation
        with patch('app.services.password_reset.PasswordResetToken') as mock_token_class:
            mock_token = Mock()
            mock_token.id = "token-123"
            mock_token_class.create_reset_token.return_value = mock_token
            
            # Request password reset
            result = await self.service.request_password_reset(
                email="test@example.com",
                ip_address="192.168.1.1",
                user_agent="Test Agent"
            )
            
            # Assertions
            assert result.success is True
            assert "password reset link has been sent" in result.message
            assert result.token == "token-123"
            
            # Verify database operations
            self.mock_db.add.assert_called_once_with(mock_token)
            self.mock_db.commit.assert_called_once()
            
            # Verify email sent
            mock_email_service.send_password_reset_email.assert_called_once()
            
            # Verify audit log
            mock_audit_logger.log_authentication_event.assert_called()
    
    @patch('app.services.password_reset.get_audit_logger')
    async def test_request_password_reset_user_not_found(self, mock_get_audit_logger):
        """Test password reset request for non-existent user."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock user not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Request password reset
        result = await self.service.request_password_reset(
            email="nonexistent@example.com",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should still return success to prevent email enumeration
        assert result.success is True
        assert "password reset link has been sent" in result.message
        
        # Verify audit log for failed attempt
        mock_audit_logger.log_authentication_event.assert_called()
    
    @patch('app.services.password_reset.get_audit_logger')
    async def test_request_password_reset_rate_limited(self, mock_get_audit_logger):
        """Test password reset request rate limiting."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock user found
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            self.test_user,  # User query
            self.test_supabase_user  # SupabaseUser query
        ]
        
        # Mock rate limit exceeded (3 recent tokens)
        self.mock_db.query.return_value.filter.return_value.count.return_value = 3
        
        # Request password reset
        result = await self.service.request_password_reset(
            email="test@example.com",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should fail with rate limit error
        assert result.success is False
        assert result.error_code == "rate_limit_exceeded"
        assert "Too many password reset requests" in result.message
    
    @patch('app.services.password_reset.get_password_security')
    @patch('app.services.password_reset.get_audit_logger')
    async def test_confirm_password_reset_success(
        self,
        mock_get_audit_logger,
        mock_get_password_security
    ):
        """Test successful password reset confirmation."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock password security
        mock_password_security = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.violations = []
        mock_password_security.validate_password.return_value = mock_validation_result
        mock_password_security.check_password_history.return_value = False
        
        mock_hash_result = Mock()
        mock_hash_result.hash = "new_hashed_password"
        mock_hash_result.algorithm = "argon2"
        mock_password_security.hash_password.return_value = mock_hash_result
        mock_password_security.update_user_password = AsyncMock()
        
        mock_get_password_security.return_value = mock_password_security
        
        # Mock token found and valid
        mock_token = Mock()
        mock_token.supabase_user_id = "supabase-123"
        mock_token.id = "token-123"
        mock_token.is_expired.return_value = False
        mock_token.mark_as_used = Mock()
        
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_token,  # Token query
            self.test_supabase_user,  # SupabaseUser query
            self.test_user  # User query
        ]
        
        # Confirm password reset
        result = await self.service.confirm_password_reset(
            reset_token="valid_token_123",
            new_password="NewSecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Assertions
        assert result.success is True
        assert "Password has been reset successfully" in result.message
        
        # Verify password update
        mock_password_security.update_user_password.assert_called_once()
        
        # Verify token marked as used
        mock_token.mark_as_used.assert_called_once()
        
        # Verify database commit
        self.mock_db.commit.assert_called_once()
        
        # Verify audit log
        mock_audit_logger.log_authentication_event.assert_called()
    
    @patch('app.services.password_reset.get_audit_logger')
    async def test_confirm_password_reset_invalid_token(self, mock_get_audit_logger):
        """Test password reset confirmation with invalid token."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock token not found
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Confirm password reset
        result = await self.service.confirm_password_reset(
            reset_token="invalid_token",
            new_password="NewSecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should fail with invalid token error
        assert result.success is False
        assert result.error_code == "invalid_token"
        assert "Invalid or expired" in result.message
    
    @patch('app.services.password_reset.get_audit_logger')
    async def test_confirm_password_reset_expired_token(self, mock_get_audit_logger):
        """Test password reset confirmation with expired token."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock expired token
        mock_token = Mock()
        mock_token.is_expired.return_value = True
        mock_token.mark_as_used = Mock()
        
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_token
        
        # Confirm password reset
        result = await self.service.confirm_password_reset(
            reset_token="expired_token",
            new_password="NewSecurePass123!",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should fail with expired token error
        assert result.success is False
        assert result.error_code == "token_expired"
        assert "expired" in result.message
        
        # Verify token marked as used
        mock_token.mark_as_used.assert_called_once()
    
    @patch('app.services.password_reset.get_password_security')
    @patch('app.services.password_reset.get_audit_logger')
    async def test_confirm_password_reset_weak_password(
        self,
        mock_get_audit_logger,
        mock_get_password_security
    ):
        """Test password reset confirmation with weak password."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock password security with validation failure
        mock_password_security = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = False
        mock_validation_result.violations = ["too_short", "no_uppercase"]
        mock_password_security.validate_password.return_value = mock_validation_result
        mock_get_password_security.return_value = mock_password_security
        
        # Mock valid token
        mock_token = Mock()
        mock_token.supabase_user_id = "supabase-123"
        mock_token.is_expired.return_value = False
        
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_token,  # Token query
            self.test_supabase_user,  # SupabaseUser query
            self.test_user  # User query
        ]
        
        # Confirm password reset
        result = await self.service.confirm_password_reset(
            reset_token="valid_token",
            new_password="weak",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should fail with validation error
        assert result.success is False
        assert result.error_code == "password_validation_failed"
        assert "Password validation failed" in result.message
    
    @patch('app.services.password_reset.get_password_security')
    @patch('app.services.password_reset.get_audit_logger')
    async def test_confirm_password_reset_reused_password(
        self,
        mock_get_audit_logger,
        mock_get_password_security
    ):
        """Test password reset confirmation with reused password."""
        # Mock audit logger
        mock_audit_logger = AsyncMock()
        mock_get_audit_logger.return_value = mock_audit_logger
        
        # Mock password security
        mock_password_security = Mock()
        mock_validation_result = Mock()
        mock_validation_result.is_valid = True
        mock_validation_result.violations = []
        mock_password_security.validate_password.return_value = mock_validation_result
        mock_password_security.check_password_history.return_value = True  # Password reused
        mock_get_password_security.return_value = mock_password_security
        
        # Mock valid token
        mock_token = Mock()
        mock_token.supabase_user_id = "supabase-123"
        mock_token.is_expired.return_value = False
        
        self.mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_token,  # Token query
            self.test_supabase_user,  # SupabaseUser query
            self.test_user  # User query
        ]
        
        # Confirm password reset
        result = await self.service.confirm_password_reset(
            reset_token="valid_token",
            new_password="ReusedPassword123!",
            ip_address="192.168.1.1",
            user_agent="Test Agent"
        )
        
        # Should fail with reuse error
        assert result.success is False
        assert result.error_code == "password_reused"
        assert "cannot reuse" in result.message
    
    async def test_cleanup_expired_tokens(self):
        """Test cleanup of expired password reset tokens."""
        # Mock expired tokens
        mock_token1 = Mock()
        mock_token1.mark_as_used = Mock()
        mock_token2 = Mock()
        mock_token2.mark_as_used = Mock()
        
        expired_tokens = [mock_token1, mock_token2]
        
        self.mock_db.query.return_value.filter.return_value.all.return_value = expired_tokens
        
        # Cleanup expired tokens
        count = await self.service.cleanup_expired_tokens()
        
        # Assertions
        assert count == 2
        mock_token1.mark_as_used.assert_called_once()
        mock_token2.mark_as_used.assert_called_once()
        self.mock_db.commit.assert_called_once()


class TestPasswordResetResult:
    """Test cases for password reset result object."""
    
    def test_success_result(self):
        """Test successful result creation."""
        result = PasswordResetResult(
            success=True,
            message="Success",
            token="token-123"
        )
        
        assert result.success is True
        assert result.message == "Success"
        assert result.token == "token-123"
        assert result.error_code is None
    
    def test_error_result(self):
        """Test error result creation."""
        result = PasswordResetResult(
            success=False,
            message="Error occurred",
            error_code="validation_error"
        )
        
        assert result.success is False
        assert result.message == "Error occurred"
        assert result.error_code == "validation_error"
        assert result.token is None