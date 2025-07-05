"""
Unit Tests for Cookie Manager Service

Tests for secure cookie management, CSRF protection, and token storage.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.services.cookie_manager import (
    CookieManager, 
    CookieHTTPBearer, 
    get_cookie_manager, 
    get_cookie_bearer
)


class TestCookieManager:
    """Test cases for CookieManager class."""
    
    @pytest.fixture
    def cookie_manager(self):
        """CookieManager instance."""
        return CookieManager()
    
    @pytest.fixture
    def mock_response(self):
        """Mock FastAPI Response."""
        return Mock(spec=Response)
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI Request."""
        request = Mock(spec=Request)
        request.cookies = {}
        request.headers = {}
        request.method = "POST"
        return request
    
    def test_init_cookie_manager(self, cookie_manager):
        """Test CookieManager initialization."""
        assert cookie_manager.settings is not None
        assert cookie_manager.access_token_name == "access_token"
        assert cookie_manager.refresh_token_name == "refresh_token"
        assert cookie_manager.csrf_token_name == "csrf_token"
    
    def test_set_auth_cookies_basic(self, cookie_manager, mock_response):
        """Test setting basic authentication cookies."""
        with patch('app.services.cookie_manager.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_development = True
            mock_settings.access_token_expire_minutes = 15
            mock_settings.refresh_token_expire_days = 7
            mock_get_settings.return_value = mock_settings
            
            # Recreate cookie manager with mocked settings
            cookie_manager = CookieManager()
            
            cookie_manager.set_auth_cookies(
                response=mock_response,
                access_token="access_token_123",
                refresh_token="refresh_token_123"
            )
        
        # Verify cookies were set
        assert mock_response.set_cookie.call_count == 2  # access + refresh tokens
        
        # Check access token cookie
        access_call = mock_response.set_cookie.call_args_list[0]
        assert access_call[1]["key"] == "access_token"
        assert access_call[1]["value"] == "access_token_123"
        assert access_call[1]["httponly"] is True
        assert access_call[1]["secure"] is False  # Development mode
        assert access_call[1]["samesite"] == "lax"
        assert access_call[1]["path"] == "/api"
    
    def test_set_auth_cookies_with_csrf(self, cookie_manager, mock_response):
        """Test setting cookies with CSRF token."""
        with patch('app.services.cookie_manager.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_development = True
            mock_settings.access_token_expire_minutes = 15
            mock_settings.refresh_token_expire_days = 7
            mock_get_settings.return_value = mock_settings
            
            cookie_manager = CookieManager()
            cookie_manager.set_auth_cookies(
                response=mock_response,
                access_token="access_token_123",
                refresh_token="refresh_token_123",
                csrf_token="csrf_token_123"
            )
        
        # Verify all cookies were set
        assert mock_response.set_cookie.call_count == 3  # access + refresh + csrf
        
        # Check CSRF token cookie
        csrf_call = mock_response.set_cookie.call_args_list[2]
        assert csrf_call[1]["key"] == "csrf_token"
        assert csrf_call[1]["value"] == "csrf_token_123"
        assert csrf_call[1]["httponly"] is False  # Accessible to JavaScript
        assert csrf_call[1]["path"] == "/"
    
    def test_set_auth_cookies_remember_me(self, mock_response):
        """Test setting cookies with remember me option."""
        with patch('app.services.cookie_manager.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_development = True
            mock_settings.access_token_expire_minutes = 15
            mock_settings.refresh_token_expire_days = 7
            mock_settings.remember_me_expire_days = 30
            mock_get_settings.return_value = mock_settings
            
            cookie_manager = CookieManager()
            cookie_manager.set_auth_cookies(
                response=mock_response,
                access_token="access_token_123",
                refresh_token="refresh_token_123",
                remember_me=True
            )
        
        # Verify cookies were set with extended expiration
        refresh_call = mock_response.set_cookie.call_args_list[1]
        expected_max_age = 30 * 24 * 60 * 60  # 30 days in seconds
        assert refresh_call[1]["max_age"] == expected_max_age
    
    def test_set_auth_cookies_production(self, mock_response):
        """Test setting cookies in production mode."""
        with patch('app.services.cookie_manager.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_development = False
            mock_settings.access_token_expire_minutes = 15
            mock_settings.refresh_token_expire_days = 7
            mock_get_settings.return_value = mock_settings
            
            cookie_manager = CookieManager()
            cookie_manager.set_auth_cookies(
                response=mock_response,
                access_token="access_token_123",
                refresh_token="refresh_token_123"
            )
        
        # Verify secure flag is set in production
        access_call = mock_response.set_cookie.call_args_list[0]
        assert access_call[1]["secure"] is True
    
    def test_clear_auth_cookies(self, mock_response):
        """Test clearing authentication cookies."""
        with patch('app.services.cookie_manager.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_development = True
            mock_get_settings.return_value = mock_settings
            
            cookie_manager = CookieManager()
            cookie_manager.clear_auth_cookies(mock_response)
        
        # Verify all cookies were deleted
        assert mock_response.delete_cookie.call_count == 3
        
        # Check access token deletion
        access_call = mock_response.delete_cookie.call_args_list[0]
        assert access_call[1]["key"] == "access_token"
        assert access_call[1]["path"] == "/api"
    
    def test_get_access_token_from_cookie(self, cookie_manager, mock_request):
        """Test extracting access token from cookies."""
        mock_request.cookies = {"access_token": "token_123"}
        
        token = cookie_manager.get_access_token_from_cookie(mock_request)
        
        assert token == "token_123"
    
    def test_get_access_token_from_cookie_not_found(self, cookie_manager, mock_request):
        """Test extracting access token when not in cookies."""
        mock_request.cookies = {}
        
        token = cookie_manager.get_access_token_from_cookie(mock_request)
        
        assert token is None
    
    def test_get_refresh_token_from_cookie(self, cookie_manager, mock_request):
        """Test extracting refresh token from cookies."""
        mock_request.cookies = {"refresh_token": "refresh_123"}
        
        token = cookie_manager.get_refresh_token_from_cookie(mock_request)
        
        assert token == "refresh_123"
    
    def test_get_csrf_token_from_cookie(self, cookie_manager, mock_request):
        """Test extracting CSRF token from cookies."""
        mock_request.cookies = {"csrf_token": "csrf_123"}
        
        token = cookie_manager.get_csrf_token_from_cookie(mock_request)
        
        assert token == "csrf_123"
    
    def test_get_csrf_token_from_header(self, cookie_manager, mock_request):
        """Test extracting CSRF token from headers."""
        mock_request.headers = {"X-CSRF-Token": "csrf_123"}
        
        token = cookie_manager.get_csrf_token_from_header(mock_request)
        
        assert token == "csrf_123"
    
    def test_get_csrf_token_from_header_lowercase(self, cookie_manager, mock_request):
        """Test extracting CSRF token from lowercase header."""
        mock_request.headers = {"x-csrf-token": "csrf_123"}
        
        token = cookie_manager.get_csrf_token_from_header(mock_request)
        
        assert token == "csrf_123"
    
    def test_validate_csrf_token_success(self, cookie_manager, mock_request):
        """Test successful CSRF token validation."""
        mock_request.cookies = {"csrf_token": "csrf_123"}
        mock_request.headers = {"X-CSRF-Token": "csrf_123"}
        
        is_valid = cookie_manager.validate_csrf_token(mock_request)
        
        assert is_valid is True
    
    def test_validate_csrf_token_mismatch(self, cookie_manager, mock_request):
        """Test CSRF token validation with mismatch."""
        mock_request.cookies = {"csrf_token": "csrf_123"}
        mock_request.headers = {"X-CSRF-Token": "different_token"}
        
        is_valid = cookie_manager.validate_csrf_token(mock_request)
        
        assert is_valid is False
    
    def test_validate_csrf_token_missing_cookie(self, cookie_manager, mock_request):
        """Test CSRF token validation with missing cookie."""
        mock_request.cookies = {}
        mock_request.headers = {"X-CSRF-Token": "csrf_123"}
        
        is_valid = cookie_manager.validate_csrf_token(mock_request)
        
        assert is_valid is False
    
    def test_validate_csrf_token_missing_header(self, cookie_manager, mock_request):
        """Test CSRF token validation with missing header."""
        mock_request.cookies = {"csrf_token": "csrf_123"}
        mock_request.headers = {}
        
        is_valid = cookie_manager.validate_csrf_token(mock_request)
        
        assert is_valid is False
    
    def test_validate_csrf_token_safe_method(self, cookie_manager, mock_request):
        """Test CSRF validation skips safe HTTP methods."""
        mock_request.method = "GET"
        mock_request.cookies = {}
        mock_request.headers = {}
        
        is_valid = cookie_manager.validate_csrf_token(mock_request)
        
        assert is_valid is True  # Safe methods bypass CSRF
    
    def test_generate_secure_cookie_data(self, cookie_manager):
        """Test generating secure cookie data with CSRF token."""
        tokens = {
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "expires_in": 900
        }
        
        cookie_data = cookie_manager.generate_secure_cookie_data(tokens)
        
        assert cookie_data["access_token"] == "access_123"
        assert cookie_data["refresh_token"] == "refresh_123"
        assert cookie_data["expires_in"] == 900
        assert "csrf_token" in cookie_data
        assert len(cookie_data["csrf_token"]) > 0
        assert cookie_data["token_type"] == "bearer"
    
    def test_create_secure_response_with_tokens(self, cookie_manager, mock_response):
        """Test creating secure response with tokens."""
        tokens = {
            "access_token": "access_123",
            "refresh_token": "refresh_123",
            "expires_in": 900,
            "user": {"id": "user-123", "email": "test@example.com"},
            "session_id": "session-123"
        }
        
        with patch.object(cookie_manager, 'set_auth_cookies') as mock_set_cookies, \
             patch.object(cookie_manager, 'generate_secure_cookie_data') as mock_generate:
            
            mock_generate.return_value = {
                "access_token": "access_123",
                "refresh_token": "refresh_123",
                "csrf_token": "csrf_123",
                "expires_in": 900
            }
            
            response_data = cookie_manager.create_secure_response_with_tokens(
                response=mock_response,
                tokens=tokens
            )
            
            # Verify cookies were set
            mock_set_cookies.assert_called_once()
            
            # Verify response data doesn't contain sensitive tokens
            assert "access_token" not in response_data
            assert "refresh_token" not in response_data
            assert response_data["success"] is True
            assert response_data["csrf_token"] == "csrf_123"
            assert response_data["user"]["id"] == "user-123"
            assert response_data["session_id"] == "session-123"


class TestCookieHTTPBearer:
    """Test cases for CookieHTTPBearer class."""
    
    @pytest.fixture
    def cookie_bearer(self):
        """CookieHTTPBearer instance."""
        return CookieHTTPBearer()
    
    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI Request."""
        return Mock(spec=Request)
    
    def test_init_cookie_http_bearer(self, cookie_bearer):
        """Test CookieHTTPBearer initialization."""
        assert cookie_bearer.cookie_manager is not None
        assert cookie_bearer.auto_error is True
    
    @pytest.mark.asyncio
    async def test_call_with_authorization_header(self, cookie_bearer, mock_request):
        """Test authentication with Authorization header."""
        with patch('fastapi.security.HTTPBearer.__call__') as mock_super_call:
            mock_super_call.return_value = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="header_token_123"
            )
            
            credentials = await cookie_bearer(mock_request)
            
            assert credentials.scheme == "Bearer"
            assert credentials.credentials == "header_token_123"
    
    @pytest.mark.asyncio
    async def test_call_with_cookie_fallback(self, cookie_bearer, mock_request):
        """Test authentication fallback to cookies."""
        with patch('fastapi.security.HTTPBearer.__call__') as mock_super_call, \
             patch.object(cookie_bearer.cookie_manager, 'get_access_token_from_cookie') as mock_get_token:
            
            # Simulate no Authorization header
            mock_super_call.side_effect = Exception("No header")
            mock_get_token.return_value = "cookie_token_123"
            
            credentials = await cookie_bearer(mock_request)
            
            assert credentials.scheme == "Bearer"
            assert credentials.credentials == "cookie_token_123"
    
    @pytest.mark.asyncio
    async def test_call_no_token_auto_error_true(self, mock_request):
        """Test authentication with no token and auto_error=True."""
        cookie_bearer = CookieHTTPBearer(auto_error=True)
        
        with patch('fastapi.security.HTTPBearer.__call__') as mock_super_call, \
             patch.object(cookie_bearer.cookie_manager, 'get_access_token_from_cookie') as mock_get_token:
            
            mock_super_call.side_effect = Exception("No header")
            mock_get_token.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await cookie_bearer(mock_request)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Authentication error"
    
    @pytest.mark.asyncio
    async def test_call_no_token_auto_error_false(self, mock_request):
        """Test authentication with no token and auto_error=False."""
        cookie_bearer = CookieHTTPBearer(auto_error=False)
        
        with patch('fastapi.security.HTTPBearer.__call__') as mock_super_call, \
             patch.object(cookie_bearer.cookie_manager, 'get_access_token_from_cookie') as mock_get_token:
            
            mock_super_call.side_effect = Exception("No header")
            mock_get_token.return_value = None
            
            credentials = await cookie_bearer(mock_request)
            
            assert credentials is None
    
    @pytest.mark.asyncio
    async def test_call_error_handling(self, cookie_bearer, mock_request):
        """Test error handling in authentication."""
        with patch('fastapi.security.HTTPBearer.__call__') as mock_super_call, \
             patch.object(cookie_bearer.cookie_manager, 'get_access_token_from_cookie') as mock_get_token:
            
            mock_super_call.side_effect = Exception("Header error")
            mock_get_token.side_effect = Exception("Cookie error")
            
            with pytest.raises(HTTPException) as exc_info:
                await cookie_bearer(mock_request)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Authentication error"


def test_get_cookie_manager():
    """Test get_cookie_manager factory function."""
    manager = get_cookie_manager()
    
    assert isinstance(manager, CookieManager)


def test_get_cookie_bearer():
    """Test get_cookie_bearer factory function."""
    bearer = get_cookie_bearer()
    
    assert isinstance(bearer, CookieHTTPBearer)


class TestCookieManagerIntegration:
    """Integration tests for CookieManager."""
    
    def test_full_cookie_lifecycle(self):
        """Test complete cookie lifecycle with real FastAPI objects."""
        # This would require actual FastAPI Request/Response objects
        pass
    
    def test_csrf_protection_integration(self):
        """Test CSRF protection in full request flow."""
        # This would test CSRF with actual middleware integration
        pass
    
    def test_cookie_security_headers(self):
        """Test cookie security headers in different environments."""
        # This would test security configurations
        pass