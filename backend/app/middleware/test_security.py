"""
Unit Tests for Security Middleware

Tests for security headers, CSRF protection, rate limiting, and authentication security.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.middleware.security import (
    SecurityHeadersMiddleware,
    CSRFProtectionMiddleware,
    RateLimitMiddleware,
    AuthenticationSecurityMiddleware,
    add_security_middleware,
    validate_origin,
    generate_csrf_token,
    is_secure_context
)


class TestSecurityHeadersMiddleware:
    """Test cases for SecurityHeadersMiddleware."""
    
    @pytest.fixture
    def app(self):
        """FastAPI app with security headers middleware."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Test client."""
        return TestClient(app)
    
    def test_security_headers_added(self, client):
        """Test that security headers are added to responses."""
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check required security headers
        headers = response.headers
        assert "X-Content-Type-Options" in headers
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Frame-Options" in headers
        assert headers["X-Frame-Options"] == "DENY"
        assert "X-XSS-Protection" in headers
        assert "Referrer-Policy" in headers
        assert "Content-Security-Policy" in headers
        assert "Permissions-Policy" in headers
    
    def test_csp_header_development(self, client):
        """Test CSP header in development mode."""
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.is_development = True
            mock_settings.return_value.is_production = False
            
            response = client.get("/test")
            
            csp = response.headers["Content-Security-Policy"]
            assert "'unsafe-inline'" in csp
            assert "'unsafe-eval'" in csp
    
    def test_hsts_header_production(self, client):
        """Test HSTS header is added in production."""
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.is_development = False
            mock_settings.return_value.is_production = True
            
            response = client.get("/test")
            
            assert "Strict-Transport-Security" in response.headers
            hsts = response.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts


class TestCSRFProtectionMiddleware:
    """Test cases for CSRFProtectionMiddleware."""
    
    @pytest.fixture
    def app(self):
        """FastAPI app with CSRF protection middleware."""
        app = FastAPI()
        app.add_middleware(CSRFProtectionMiddleware)
        
        @app.get("/api/auth/profile")
        async def get_profile():
            return {"message": "profile"}
        
        @app.post("/api/auth/login")
        async def login():
            return {"message": "login"}
        
        @app.post("/api/other/endpoint")
        async def other_endpoint():
            return {"message": "other"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Test client."""
        return TestClient(app)
    
    def test_safe_methods_allowed(self, client):
        """Test that safe methods bypass CSRF protection."""
        response = client.get("/api/auth/profile")
        
        assert response.status_code == 200
    
    def test_non_protected_paths_allowed(self, client):
        """Test that non-protected paths bypass CSRF protection."""
        response = client.post("/api/other/endpoint")
        
        assert response.status_code == 200
    
    def test_protected_path_requires_csrf(self, client):
        """Test that protected paths require CSRF token."""
        with patch('app.middleware.security.get_cookie_manager') as mock_manager:
            mock_cookie_manager = Mock()
            mock_cookie_manager.validate_csrf_token.return_value = False
            mock_manager.return_value = mock_cookie_manager
            
            # The middleware should raise HTTPException, which FastAPI converts to HTTP response
            with pytest.raises(Exception):  # HTTPException will be raised by middleware
                response = client.post("/api/auth/login")
    
    def test_valid_csrf_token_allowed(self, client):
        """Test that valid CSRF token allows request."""
        # Mock successful CSRF validation
        with patch('app.middleware.security.get_cookie_manager') as mock_manager:
            mock_cookie_manager = Mock()
            mock_cookie_manager.validate_csrf_token.return_value = True
            mock_manager.return_value = mock_cookie_manager
            
            response = client.post("/api/auth/login")
            
            assert response.status_code == 200
    
    def test_csrf_disabled_in_development(self, client):
        """Test CSRF protection can be disabled in development."""
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.is_development = True
            mock_settings.return_value.csrf_protection_enabled = False
            
            response = client.post("/api/auth/login")
            
            assert response.status_code == 200


class TestRateLimitMiddleware:
    """Test cases for RateLimitMiddleware."""
    
    def test_rate_limiting_disabled(self):
        """Test behavior when rate limiting is disabled."""
        app = FastAPI()
        
        @app.post("/api/auth/login")
        async def login():
            return {"message": "login"}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.rate_limiting_enabled = False
            
            app.add_middleware(RateLimitMiddleware)
            client = TestClient(app)
            
            response = client.post("/api/auth/login")
            assert response.status_code == 200
    
    def test_non_rate_limited_paths(self):
        """Test that non-rate-limited paths are not affected."""
        app = FastAPI()
        
        @app.post("/api/other/endpoint")
        async def other_endpoint():
            return {"message": "other"}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.rate_limiting_enabled = True
            
            app.add_middleware(RateLimitMiddleware)
            client = TestClient(app)
            
            response = client.post("/api/other/endpoint")
            assert response.status_code == 200


class TestAuthenticationSecurityMiddleware:
    """Test cases for AuthenticationSecurityMiddleware."""
    
    @pytest.fixture
    def app(self):
        """FastAPI app with authentication security middleware."""
        app = FastAPI()
        app.add_middleware(AuthenticationSecurityMiddleware)
        
        @app.post("/api/auth/login")
        async def login():
            return {"message": "login"}
        
        @app.get("/api/users/profile")
        async def profile():
            return {"message": "profile"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Test client."""
        return TestClient(app)
    
    def test_request_metadata_added(self, client):
        """Test that request metadata is added to request state."""
        # This is difficult to test directly, but we can verify no errors occur
        response = client.post("/api/auth/login")
        
        assert response.status_code == 200
    
    def test_client_ip_detection(self, client):
        """Test client IP detection with various headers."""
        headers = {"X-Forwarded-For": "192.168.1.100"}
        response = client.post("/api/auth/login", headers=headers)
        
        assert response.status_code == 200
    
    def test_non_auth_endpoints_ignored(self, client):
        """Test that non-auth endpoints don't trigger auth logging."""
        response = client.get("/api/users/profile")
        
        assert response.status_code == 200


class TestSecurityUtilities:
    """Test cases for security utility functions."""
    
    def test_validate_origin_allowed(self):
        """Test origin validation with allowed origin."""
        request = Mock(spec=Request)
        request.headers = {"Origin": "http://localhost:3000"}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.cors_origins = ["http://localhost:3000"]
            
            assert validate_origin(request) is True
    
    def test_validate_origin_denied(self):
        """Test origin validation with disallowed origin."""
        request = Mock(spec=Request)
        request.headers = {"Origin": "http://malicious.com"}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.cors_origins = ["http://localhost:3000"]
            
            assert validate_origin(request) is False
    
    def test_validate_origin_no_origin(self):
        """Test origin validation with no origin header."""
        request = Mock(spec=Request)
        request.headers = {}
        
        assert validate_origin(request, ["http://localhost:3000"]) is False
    
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        token = generate_csrf_token()
        
        assert isinstance(token, str)
        assert len(token) > 20  # Should be reasonably long
        
        # Tokens should be unique
        token2 = generate_csrf_token()
        assert token != token2
    
    def test_is_secure_context_https(self):
        """Test secure context detection with HTTPS."""
        request = Mock(spec=Request)
        request.url.scheme = "https"
        request.headers = {}
        
        assert is_secure_context(request) is True
    
    def test_is_secure_context_proxy_headers(self):
        """Test secure context detection with proxy headers."""
        request = Mock(spec=Request)
        request.url.scheme = "http"
        request.headers = {"X-Forwarded-Proto": "https"}
        
        assert is_secure_context(request) is True
    
    def test_is_secure_context_development(self):
        """Test secure context allows insecure in development."""
        request = Mock(spec=Request)
        request.url.scheme = "http"
        request.headers = {}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.is_development = True
            
            assert is_secure_context(request) is True
    
    def test_is_secure_context_insecure_production(self):
        """Test secure context denies insecure in production."""
        request = Mock(spec=Request)
        request.url.scheme = "http"
        request.headers = {}
        
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.return_value.is_development = False
            
            assert is_secure_context(request) is False


class TestAddSecurityMiddleware:
    """Test cases for add_security_middleware function."""
    
    def test_add_security_middleware(self):
        """Test adding all security middleware to app."""
        app = FastAPI()
        
        # Mock the problematic imports
        with patch('app.middleware.security.get_rate_limiter'):
            # Should not raise any exceptions
            add_security_middleware(app)
            
            # Verify middleware was added (difficult to test directly)
            assert len(app.middleware_stack.middleware) > 0


class TestMiddlewareIntegration:
    """Integration tests for multiple middleware working together."""
    
    @pytest.fixture
    def app(self):
        """FastAPI app with all security middleware."""
        app = FastAPI()
        
        with patch('app.middleware.security.get_rate_limiter'):
            add_security_middleware(app)
        
        @app.get("/api/auth/profile")
        async def get_profile():
            return {"message": "profile"}
        
        @app.post("/api/auth/login") 
        async def login():
            return {"message": "login"}
        
        return app
    
    @pytest.fixture  
    def client(self, app):
        """Test client."""
        return TestClient(app)
    
    def test_multiple_middleware_working(self, client):
        """Test that multiple middleware work together."""
        # This tests the complete middleware stack
        response = client.get("/api/auth/profile")
        
        assert response.status_code == 200
        # Should have security headers
        assert "X-Content-Type-Options" in response.headers
    
    def test_middleware_error_handling(self):
        """Test middleware error handling."""
        # Test that middleware initialization handles errors gracefully
        with patch('app.middleware.security.get_settings') as mock_settings:
            mock_settings.side_effect = Exception("Settings error")
            
            # Should raise the exception during middleware initialization
            app = FastAPI()
            
            @app.get("/test")
            async def test_endpoint():
                return {"message": "test"}
            
            with pytest.raises(Exception):
                app.add_middleware(SecurityHeadersMiddleware)