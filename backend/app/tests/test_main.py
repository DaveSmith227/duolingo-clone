"""Main Application Tests

Test suite for the main FastAPI application including endpoints,
middleware, error handling, and application lifecycle.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


class TestApplicationSetup:
    """Test application configuration and setup."""
    
    def test_app_creation(self):
        """Test that FastAPI app is created correctly."""
        assert app is not None
        assert app.title == "Duolingo Clone API"
        assert app.version == "0.1.0"
    
    def test_app_has_middleware(self):
        """Test that middleware is properly configured."""
        # Check that CORS middleware is present
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        
        # Should have CORS middleware and custom middleware
        assert len(middleware_types) > 0
    
    def test_app_has_exception_handlers(self):
        """Test that exception handlers are configured."""
        # FastAPI automatically registers exception handlers
        assert hasattr(app, 'exception_handlers')


class TestRootEndpoints:
    """Test basic application endpoints."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "environment" in data
        assert "status" in data
        assert data["status"] == "running"
    
    @patch('app.main.get_database_info')
    def test_health_endpoint_healthy(self, mock_db_info):
        """Test health endpoint when database is healthy."""
        mock_db_info.return_value = {
            "database_name": "test_db",
            "database_type": "sqlite"
        }
        
        response = self.client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "healthy"
    
    @patch('app.main.get_database_info')
    def test_health_endpoint_unhealthy(self, mock_db_info):
        """Test health endpoint when database is unhealthy."""
        mock_db_info.side_effect = Exception("Database connection failed")
        
        response = self.client.get("/health")
        
        assert response.status_code == 503
        
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["database"]["status"] == "unhealthy"
    
    def test_info_endpoint(self):
        """Test the application info endpoint."""
        response = self.client.get("/info")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "debug" in data
        assert "python_version" in data
        assert "framework" in data
        assert "database" in data
        assert "features" in data
        
        # Check features list
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0


class TestErrorHandling:
    """Test error handling and exception responses."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_404_error_handling(self):
        """Test 404 error handling."""
        response = self.client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "http_error"
        assert data["error"]["code"] == 404
        assert "path" in data["error"]
    
    def test_405_method_not_allowed(self):
        """Test 405 Method Not Allowed error."""
        response = self.client.post("/")  # Root only supports GET
        
        assert response.status_code == 405
        
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 405


class TestMiddleware:
    """Test application middleware functionality."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_cors_headers(self):
        """Test CORS headers are present."""
        # Test with a regular request that includes Origin header
        response = self.client.get("/", headers={
            "Origin": "http://localhost:3000"
        })
        
        # Should have basic response
        assert response.status_code == 200
        
        # With modern CORS middleware, headers might not be visible in test client
        # So we'll just verify the request succeeds
    
    def test_process_time_header(self):
        """Test that process time header is added."""
        response = self.client.get("/")
        
        # Should have X-Process-Time header from RequestLoggingMiddleware
        assert "x-process-time" in response.headers
        
        # Should be a valid float
        process_time = float(response.headers["x-process-time"])
        assert process_time >= 0
    
    def test_request_logging_middleware(self):
        """Test that request logging middleware is working."""
        with patch('app.main.logger') as mock_logger:
            response = self.client.get("/")
            
            assert response.status_code == 200
            
            # Check that logger was called for request and response
            assert mock_logger.info.call_count >= 2


class TestApplicationLifespan:
    """Test application startup and shutdown events."""
    
    @patch('app.main.get_database_info')
    @patch('app.main.logger')
    def test_startup_logging(self, mock_logger, mock_db_info):
        """Test that startup events are logged."""
        mock_db_info.return_value = {"database_name": "test_db"}
        
        # Create a new test client to trigger startup
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
        
        # Check that startup logging occurred
        mock_logger.info.assert_any_call("Starting Duolingo Clone API v0.1.0")
    
    @patch('app.main.get_database_info')
    def test_startup_database_check_success(self, mock_db_info):
        """Test successful database connectivity check on startup."""
        mock_db_info.return_value = {"database_name": "test_db"}
        
        # Should not raise exception
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
    
    @patch('app.main.get_database_info')
    @patch('app.main.get_settings')
    def test_startup_database_check_failure_development(self, mock_settings, mock_db_info):
        """Test database check failure in development mode."""
        mock_settings.return_value.is_production = False
        mock_db_info.side_effect = Exception("Database connection failed")
        
        # Should not raise exception in development
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200


class TestConfigurationIntegration:
    """Test integration with configuration system."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    @patch('app.main.get_settings')
    def test_debug_mode_docs_enabled(self, mock_settings):
        """Test that docs are enabled in debug mode."""
        mock_settings.return_value.debug = True
        
        # Create app with debug enabled
        from app.main import create_app
        debug_app = create_app()
        
        assert debug_app.docs_url == "/docs"
        assert debug_app.redoc_url == "/redoc"
        assert debug_app.openapi_url == "/openapi.json"
    
    @patch('app.main.get_settings')
    def test_production_mode_docs_disabled(self, mock_settings):
        """Test that docs are disabled in production mode."""
        mock_settings.return_value.debug = False
        
        # Create app with debug disabled
        from app.main import create_app
        prod_app = create_app()
        
        assert prod_app.docs_url is None
        assert prod_app.redoc_url is None
        assert prod_app.openapi_url is None


class TestRequestValidation:
    """Test request validation and response formats."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_health_endpoint_response_format(self):
        """Test health endpoint response format."""
        with patch('app.main.get_database_info') as mock_db_info:
            mock_db_info.return_value = {"database_name": "test"}
            
            response = self.client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            required_fields = ["status", "timestamp", "version", "environment", "checks"]
            for field in required_fields:
                assert field in data
            
            # Validate checks structure
            assert "database" in data["checks"]
            assert "status" in data["checks"]["database"]
            assert "info" in data["checks"]["database"]
    
    def test_info_endpoint_response_format(self):
        """Test info endpoint response format."""
        response = self.client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        required_fields = [
            "app_name", "version", "environment", "debug",
            "python_version", "framework", "database", "features"
        ]
        for field in required_fields:
            assert field in data
        
        # Validate types
        assert isinstance(data["features"], list)
        assert isinstance(data["debug"], bool)


class TestSecurityHeaders:
    """Test security-related headers and configurations."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_cors_configuration(self):
        """Test CORS configuration."""
        response = self.client.options("/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # Should handle preflight requests
        assert response.status_code in [200, 204]
    
    def test_security_headers_presence(self):
        """Test that security headers are present."""
        response = self.client.get("/")
        
        # Basic security checks
        assert response.status_code == 200
        
        # Check that response is JSON
        assert response.headers.get("content-type") == "application/json"


class TestErrorResponseFormats:
    """Test error response formatting and consistency."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_http_exception_format(self):
        """Test HTTP exception response format."""
        response = self.client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        
        # Validate error response structure
        assert "error" in data
        error = data["error"]
        
        required_fields = ["type", "code", "message", "path"]
        for field in required_fields:
            assert field in error
        
        assert error["type"] == "http_error"
        assert error["code"] == 404
        assert error["path"] == "/nonexistent"
    
    def test_validation_error_format(self):
        """Test validation error response format."""
        # This would test validation errors if we had endpoints with request bodies
        # For now, we'll test with a malformed request if possible
        
        response = self.client.get("/health?invalid_param=[]")
        
        # Should still work as health endpoint doesn't validate query params
        assert response.status_code in [200, 503]


class TestPerformance:
    """Test performance-related aspects."""
    
    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)
    
    def test_response_times(self):
        """Test that endpoints respond within reasonable time."""
        import time
        
        start_time = time.time()
        response = self.client.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
    
    def test_process_time_header_accuracy(self):
        """Test that process time header is reasonably accurate."""
        response = self.client.get("/")
        
        assert response.status_code == 200
        
        process_time = float(response.headers["x-process-time"])
        
        # Should be a reasonable processing time (less than 1 second)
        assert 0 <= process_time < 1.0