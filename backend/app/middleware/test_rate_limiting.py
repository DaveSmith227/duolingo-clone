"""
Unit Tests for Rate Limiting Middleware

Comprehensive test suite for the rate limiting middleware covering
endpoint type detection, rate limit enforcement, error responses,
and header validation.
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, status, Request, Response
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.middleware.rate_limiting import RateLimitMiddleware
from app.services.rate_limiter import RateLimitInfo, RateLimitResult, RateLimitRule
from app.core.response_formatter import response_formatter


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        @app.get("/api/auth/login")
        async def auth_endpoint():
            return {"message": "auth endpoint"}
        
        @app.get("/api/users/me")
        async def user_endpoint():
            return {"message": "user endpoint"}
        
        @app.get("/api/analytics/events")
        async def analytics_endpoint():
            return {"message": "analytics endpoint"}
        
        @app.get("/api/health/")
        async def health_endpoint():
            return {"message": "health endpoint"}
        
        @app.get("/api/other/endpoint")
        async def general_endpoint():
            return {"message": "general endpoint"}
        
        @app.get("/docs")
        async def docs_endpoint():
            return {"message": "docs endpoint"}
        
        return app
    
    @pytest.fixture
    def mock_rate_limiter(self):
        """Create mock rate limiter."""
        with patch('app.middleware.rate_limiting.get_rate_limiter') as mock:
            rate_limiter = Mock()
            mock.return_value = rate_limiter
            yield rate_limiter
    
    @pytest.fixture
    def middleware(self, mock_rate_limiter):
        """Create rate limiting middleware instance."""
        app = FastAPI()
        return RateLimitMiddleware(app)
    
    def test_endpoint_type_detection(self, middleware):
        """Test endpoint type detection from paths."""
        test_cases = [
            ("/api/auth/login", "auth"),
            ("/api/auth/register", "auth"),
            ("/api/users/me", "user"),
            ("/api/users/preferences", "user"),
            ("/api/analytics/events", "analytics"),
            ("/api/analytics/progress", "analytics"),
            ("/api/health/", "health"),
            ("/health", "health"),
            ("/api/admin/users", "auth"),  # Admin uses auth limits
            ("/api/other/endpoint", "general"),
            ("/unknown/path", "general")
        ]
        
        for path, expected_type in test_cases:
            result = middleware._get_endpoint_type(path)
            assert result == expected_type, f"Path {path} should map to {expected_type}, got {result}"
    
    def test_client_identifier_ip_only(self, middleware):
        """Test client identifier generation with IP only."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user_id = None
        
        identifier = middleware._get_client_identifier(request)
        
        assert identifier == "ip:192.168.1.100"
    
    def test_client_identifier_with_user(self, middleware):
        """Test client identifier generation with authenticated user."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user_id = "user123"
        
        identifier = middleware._get_client_identifier(request)
        
        assert identifier == "ip:192.168.1.100:user:user123"
    
    def test_client_identifier_forwarded_ip(self, middleware):
        """Test client identifier with X-Forwarded-For header."""
        request = Mock()
        request.headers = {"X-Forwarded-For": "203.0.113.195, 192.168.1.100"}
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.state = Mock()
        request.state.user_id = None
        
        identifier = middleware._get_client_identifier(request)
        
        assert identifier == "ip:203.0.113.195"
    
    def test_should_skip_rate_limiting(self, middleware):
        """Test rate limiting exclusion logic."""
        test_cases = [
            ("/docs", True),
            ("/redoc", True),
            ("/openapi.json", True),
            ("/favicon.ico", True),
            ("/static/css/style.css", True),
            ("/image.png", True),
            ("/script.js", True),
            ("/api/users/me", False),
            ("/api/auth/login", False),
            ("/unknown/path", False)
        ]
        
        for path, should_skip in test_cases:
            request = Mock()
            request.url = Mock()
            request.url.path = path
            
            result = middleware._should_skip_rate_limiting(request)
            assert result == should_skip, f"Path {path} skip result should be {should_skip}, got {result}"
    
    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, middleware, mock_rate_limiter):
        """Test request processing when rate limit is not exceeded."""
        # Setup mock rate limiter to allow request
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.ALLOWED,
            remaining=4,
            reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
            total_attempts=1
        )
        mock_rate_limiter.check_rate_limit.return_value = rate_limit_info
        mock_rate_limiter.record_attempt.return_value = rate_limit_info
        
        # Create mock request and response
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.headers = {"X-Request-ID": "test-123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = None
        
        # Mock call_next
        async def mock_call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"message": "success"}, status_code=200)
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify response has rate limit headers
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "X-Processing-Time" in response.headers
        
        # Verify rate limiter was called
        mock_rate_limiter.check_rate_limit.assert_called_once()
        mock_rate_limiter.record_attempt.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, middleware, mock_rate_limiter):
        """Test request processing when rate limit is exceeded."""
        # Setup mock rate limiter to block request
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.RATE_LIMITED,
            remaining=0,
            reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
            retry_after=60,
            total_attempts=5
        )
        mock_rate_limiter.check_rate_limit.return_value = rate_limit_info
        
        # Create mock request
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.headers = {"X-Request-ID": "test-123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = None
        
        # Mock call_next (should not be called)
        async def mock_call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"message": "success"}, status_code=200)
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify rate limit error response
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"
        
        # Verify rate limiter was called for check but not record
        mock_rate_limiter.check_rate_limit.assert_called_once()
        mock_rate_limiter.record_attempt.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_account_blocked(self, middleware, mock_rate_limiter):
        """Test request processing when account is blocked."""
        # Setup mock rate limiter to block account
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.BLOCKED,
            remaining=0,
            reset_time=datetime.now(timezone.utc) + timedelta(hours=1),
            retry_after=3600,
            total_attempts=10,
            lockout_expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        mock_rate_limiter.check_rate_limit.return_value = rate_limit_info
        
        # Create mock request
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.headers = {"X-Request-ID": "test-123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = None
        
        async def mock_call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"message": "success"}, status_code=200)
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify blocked account response
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "3600"
        
        # Parse response content
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert "blocked" in content["message"].lower()
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, middleware, mock_rate_limiter):
        """Test exception handling during request processing."""
        # Setup mock rate limiter to allow request
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.ALLOWED,
            remaining=4,
            reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
            total_attempts=1
        )
        mock_rate_limiter.check_rate_limit.return_value = rate_limit_info
        mock_rate_limiter.record_attempt.return_value = rate_limit_info
        
        # Create mock request
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.headers = {"X-Request-ID": "test-123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = None
        
        # Mock call_next to raise exception
        async def mock_call_next(req):
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError):
            await middleware.dispatch(request, mock_call_next)
        
        # Verify failed attempt was recorded
        mock_rate_limiter.record_attempt.assert_called_once()
        args = mock_rate_limiter.record_attempt.call_args
        assert args[1]["success"] is False
    
    @pytest.mark.asyncio
    async def test_excluded_path_skips_rate_limiting(self, middleware, mock_rate_limiter):
        """Test that excluded paths skip rate limiting."""
        # Create mock request for excluded path
        request = Mock()
        request.url = Mock()
        request.url.path = "/docs"
        
        # Mock call_next
        async def mock_call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"message": "docs"}, status_code=200)
        
        response = await middleware.dispatch(request, mock_call_next)
        
        # Verify response is processed without rate limiting
        assert response.status_code == 200
        
        # Verify rate limiter was not called
        mock_rate_limiter.check_rate_limit.assert_not_called()
        mock_rate_limiter.record_attempt.assert_not_called()
    
    def test_rate_limit_headers_added(self, middleware):
        """Test that proper rate limit headers are added to responses."""
        # Create test response
        response = Response()
        
        # Create test rate limit info
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.ALLOWED,
            remaining=10,
            reset_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            total_attempts=5
        )
        
        # Create test rule
        rule = RateLimitRule(
            key_prefix="rate_limit:test",
            max_attempts=15,
            window_seconds=60
        )
        
        # Add headers
        middleware._add_rate_limit_headers(response, rate_limit_info, rule)
        
        # Verify headers
        assert response.headers["X-RateLimit-Limit"] == "15"
        assert response.headers["X-RateLimit-Remaining"] == "10"
        assert response.headers["X-RateLimit-Reset"] == "1704110400"  # Unix timestamp
        assert response.headers["X-RateLimit-Window"] == "60"
        assert response.headers["X-RateLimit-Type"] == "test"
    
    def test_create_rate_limit_response(self, middleware):
        """Test rate limit error response creation."""
        # Create test rate limit info
        rate_limit_info = RateLimitInfo(
            result=RateLimitResult.RATE_LIMITED,
            remaining=0,
            reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
            retry_after=60,
            total_attempts=5
        )
        
        # Create test rule
        rule = RateLimitRule(
            key_prefix="rate_limit:api_auth",
            max_attempts=5,
            window_seconds=60
        )
        
        # Create mock request
        request = Mock()
        request.url = Mock()
        request.url.path = "/api/auth/login"
        request.headers = {"X-Request-ID": "test-123"}
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user_id = None
        
        response = middleware._create_rate_limit_response(
            rate_limit_info, rule, request
        )
        
        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "Retry-After" in response.headers
        
        # Parse and verify content
        content = json.loads(response.body.decode())
        assert content["success"] is False
        assert "too many requests" in content["message"].lower()


class TestRateLimitMiddlewareIntegration:
    """Integration tests for rate limiting middleware."""
    
    @pytest.fixture
    def app_with_middleware(self):
        """Create FastAPI app with rate limiting middleware."""
        app = FastAPI()
        
        # Add middleware
        app.add_middleware(RateLimitMiddleware)
        
        # Add test endpoints
        @app.get("/api/auth/login")
        async def auth_login():
            return {"message": "login success"}
        
        @app.get("/api/users/me")
        async def get_user():
            return {"message": "user data"}
        
        @app.get("/api/analytics/events")
        async def get_analytics():
            return {"message": "analytics data"}
        
        @app.get("/docs")
        async def docs():
            return {"message": "documentation"}
        
        return app
    
    @pytest.fixture
    def client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware)
    
    def test_different_endpoint_types_have_different_limits(self, client):
        """Test that different endpoint types have different rate limits."""
        with patch('app.middleware.rate_limiting.get_rate_limiter') as mock_limiter:
            # Mock rate limiter to track calls
            rate_limiter = Mock()
            mock_limiter.return_value = rate_limiter
            
            # Setup rate limiter to always allow
            rate_limit_info = RateLimitInfo(
                result=RateLimitResult.ALLOWED,
                remaining=10,
                reset_time=datetime.now(timezone.utc) + timedelta(minutes=1),
                total_attempts=1
            )
            rate_limiter.check_rate_limit.return_value = rate_limit_info
            rate_limiter.record_attempt.return_value = rate_limit_info
            
            # Make requests to different endpoint types
            auth_response = client.get("/api/auth/login")
            user_response = client.get("/api/users/me")
            analytics_response = client.get("/api/analytics/events")
            
            # Verify all responses are successful
            assert auth_response.status_code == 200
            assert user_response.status_code == 200
            assert analytics_response.status_code == 200
            
            # Verify rate limiter was called with different rules
            assert rate_limiter.check_rate_limit.call_count == 3
            
            # Check that different endpoint types used different rate limit rules
            calls = rate_limiter.check_rate_limit.call_args_list
            rule_names = [call[1]["rule_name"] for call in calls]
            
            assert "api_auth" in rule_names
            assert "api_user" in rule_names
            assert "api_analytics" in rule_names
    
    def test_excluded_paths_skip_middleware(self, client):
        """Test that excluded paths skip rate limiting."""
        with patch('app.middleware.rate_limiting.get_rate_limiter') as mock_limiter:
            rate_limiter = Mock()
            mock_limiter.return_value = rate_limiter
            
            # Make request to excluded path
            response = client.get("/docs")
            
            # Verify response is successful
            assert response.status_code == 200
            
            # Verify rate limiter was not called
            rate_limiter.check_rate_limit.assert_not_called()
            rate_limiter.record_attempt.assert_not_called()
    
    def test_rate_limit_headers_in_response(self, client):
        """Test that rate limit headers are included in responses."""
        with patch('app.middleware.rate_limiting.get_rate_limiter') as mock_limiter:
            rate_limiter = Mock()
            mock_limiter.return_value = rate_limiter
            
            # Setup rate limiter to allow with specific info
            rate_limit_info = RateLimitInfo(
                result=RateLimitResult.ALLOWED,
                remaining=4,
                reset_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                total_attempts=1
            )
            rate_limiter.check_rate_limit.return_value = rate_limit_info
            rate_limiter.record_attempt.return_value = rate_limit_info
            
            # Make request
            response = client.get("/api/auth/login")
            
            # Verify rate limit headers are present
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
            assert "X-RateLimit-Window" in response.headers
            assert "X-RateLimit-Type" in response.headers


class TestRateLimitRules:
    """Test rate limit rule configurations."""
    
    def test_endpoint_rule_configurations(self):
        """Test that endpoint rules match PRD specifications."""
        from app.middleware.rate_limiting import RateLimitMiddleware
        
        rules = RateLimitMiddleware.ENDPOINT_RULES
        
        # Verify auth endpoints: 5 requests per minute
        auth_rule = rules["auth"]
        assert auth_rule.max_attempts == 5
        assert auth_rule.window_seconds == 60
        assert auth_rule.lockout_seconds == 300
        
        # Verify user endpoints: 60 requests per minute
        user_rule = rules["user"]
        assert user_rule.max_attempts == 60
        assert user_rule.window_seconds == 60
        assert user_rule.lockout_seconds is None
        
        # Verify analytics endpoints: 100 requests per minute
        analytics_rule = rules["analytics"]
        assert analytics_rule.max_attempts == 100
        assert analytics_rule.window_seconds == 60
        assert analytics_rule.lockout_seconds is None
        
        # Verify health endpoints: 30 requests per minute
        health_rule = rules["health"]
        assert health_rule.max_attempts == 30
        assert health_rule.window_seconds == 60
        assert health_rule.lockout_seconds is None
        
        # Verify general endpoints: 120 requests per minute
        general_rule = rules["general"]
        assert general_rule.max_attempts == 120
        assert general_rule.window_seconds == 60
        assert general_rule.lockout_seconds is None
    
    def test_endpoint_pattern_mappings(self):
        """Test that endpoint patterns map to correct rule types."""
        from app.middleware.rate_limiting import RateLimitMiddleware
        
        patterns = RateLimitMiddleware.ENDPOINT_PATTERNS
        
        # Test auth patterns
        auth_patterns = [k for k, v in patterns.items() if v == "auth"]
        assert "/api/auth/" in auth_patterns
        assert "/api/login" in auth_patterns
        assert "/api/admin/" in auth_patterns
        
        # Test user patterns
        user_patterns = [k for k, v in patterns.items() if v == "user"]
        assert "/api/users/" in user_patterns
        assert "/api/profile/" in user_patterns
        
        # Test analytics patterns
        analytics_patterns = [k for k, v in patterns.items() if v == "analytics"]
        assert "/api/analytics/" in analytics_patterns
        assert "/api/events/" in analytics_patterns
        
        # Test health patterns
        health_patterns = [k for k, v in patterns.items() if v == "health"]
        assert "/api/health/" in health_patterns
        assert "/health" in health_patterns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])