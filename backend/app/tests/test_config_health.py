"""
Tests for Configuration Health Check Endpoints

Tests the configuration health monitoring system including:
- Health check endpoint functionality
- Service connectivity validation
- Configuration validation
- Security compliance checks
- Performance monitoring
- Error handling and edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import Settings
from app.api.config_health import (
    check_database_health, check_redis_health, check_configuration_validity,
    check_security_configuration, check_external_services
)
from app.core.config_rbac_compat import ConfigRole, get_config_rbac


class TestHealthCheckEndpoints:
    """Test the health check API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long",
            database_url="sqlite:///test.db",
            redis_host="localhost",
            redis_port=6379
        )
    
    def test_get_configuration_health_success(self, client):
        """Test successful configuration health check."""
        with patch('app.api.config_health.get_settings') as mock_get_settings:
            mock_settings = Settings(
                app_name="Test App",
                environment="development",
                debug=True,
                secret_key="test-secret-key-32-characters-long"
            )
            mock_get_settings.return_value = mock_settings
            
            # Mock the individual health check functions
            with patch('app.api.config_health.check_configuration_validity') as mock_config, \
                 patch('app.api.config_health.check_database_health') as mock_db, \
                 patch('app.api.config_health.check_redis_health') as mock_redis, \
                 patch('app.api.config_health.check_security_configuration') as mock_security, \
                 patch('app.api.config_health.check_external_services') as mock_external:
                
                # Set up mock returns
                mock_config.return_value = Mock(
                    status="healthy", message="Config OK", details={}, 
                    timestamp=datetime.now(timezone.utc), response_time_ms=10.5
                )
                mock_db.return_value = Mock(
                    status="healthy", message="DB OK", details={}, 
                    timestamp=datetime.now(timezone.utc), response_time_ms=25.2
                )
                mock_redis.return_value = Mock(
                    status="warning", message="Redis unavailable", details={}, 
                    timestamp=datetime.now(timezone.utc), response_time_ms=5000.0
                )
                mock_security.return_value = Mock(
                    status="healthy", message="Security OK", details={}, 
                    timestamp=datetime.now(timezone.utc), response_time_ms=5.1
                )
                mock_external.return_value = Mock(
                    status="healthy", message="External OK", details={}, 
                    timestamp=datetime.now(timezone.utc), response_time_ms=100.0
                )
                
                response = client.get("/config/health")
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["overall_status"] == "warning"  # Due to Redis warning
                assert data["environment"] == "development"
                assert "checks" in data
                assert "summary" in data
                assert "timestamp" in data
                assert "total_response_time_ms" in data
                
                # Check summary counts
                assert data["summary"]["healthy"] == 4
                assert data["summary"]["warning"] == 1
                assert data["summary"]["critical"] == 0
    
    def test_get_quick_health_check(self, client):
        """Test the quick health check endpoint."""
        with patch('app.api.config_health.get_settings') as mock_get_settings:
            mock_settings = Settings(
                app_name="Test App",
                environment="development",
                debug=True,
                secret_key="test-secret-key-32-characters-long"
            )
            mock_get_settings.return_value = mock_settings
            
            response = client.get("/config/health/quick")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "message" in data
            assert "environment" in data
            assert "timestamp" in data
            assert "response_time_ms" in data
            
            assert data["environment"] == "development"
    
    def test_get_services_health_requires_permission(self, client):
        """Test that services health endpoint requires proper permissions."""
        response = client.get("/config/health/services")
        
        # Should require authentication/authorization
        assert response.status_code in [401, 403]
    
    def test_get_security_health_requires_permission(self, client):
        """Test that security health endpoint requires proper permissions."""
        response = client.get("/config/health/security")
        
        # Should require authentication/authorization
        assert response.status_code in [401, 403]
    
    def test_validate_configuration_changes_requires_permission(self, client):
        """Test that configuration validation endpoint requires proper permissions."""
        test_config = {"debug": False, "environment": "production"}
        
        response = client.post("/config/health/validate", json=test_config)
        
        # Should require authentication/authorization
        assert response.status_code in [401, 403]


class TestHealthCheckFunctions:
    """Test the individual health check functions."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        return Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long",
            database_url="sqlite:///test.db",
            redis_host="localhost",
            redis_port=6379
        )
    
    @pytest.mark.asyncio
    async def test_check_database_health_sqlite_success(self, mock_settings):
        """Test database health check with SQLite."""
        # Mock SQLite operations
        with patch('sqlite3.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.execute.return_value = None
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            with patch('os.path.exists', return_value=True), \
                 patch('os.path.getsize', return_value=1024*1024):  # 1MB
                
                result = await check_database_health(mock_settings)
                
                assert result.status == "healthy"
                assert "SQLite database accessible" in result.message
                assert result.details["type"] == "sqlite"
                assert result.details["size_mb"] == 1.0
                assert result.response_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_check_database_health_sqlite_missing(self, mock_settings):
        """Test database health check with missing SQLite file."""
        with patch('os.path.exists', return_value=False):
            result = await check_database_health(mock_settings)
            
            assert result.status == "warning"
            assert "database file not found" in result.message
            assert result.details["type"] == "sqlite"
    
    @pytest.mark.asyncio
    async def test_check_database_health_postgresql_success(self):
        """Test database health check with PostgreSQL."""
        settings = Settings(
            app_name="Test App",
            environment="production",
            debug=False,
            secret_key="test-secret-key-32-characters-long",
            database_url="postgresql://user:pass@localhost:5432/testdb"
        )
        
        # Mock psycopg2 operations
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.side_effect = [
                ("PostgreSQL 14.1",),  # version
                ("testdb",)  # database name
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            
            result = await check_database_health(settings)
            
            assert result.status == "healthy"
            assert "PostgreSQL database accessible" in result.message
            assert result.details["type"] == "postgresql"
            assert result.details["database"] == "testdb"
            assert "14.1" in result.details["version"]
    
    @pytest.mark.asyncio
    async def test_check_database_health_connection_failure(self, mock_settings):
        """Test database health check with connection failure."""
        with patch('sqlite3.connect', side_effect=Exception("Connection failed")):
            result = await check_database_health(mock_settings)
            
            assert result.status == "critical"
            assert "Database connection failed" in result.message
            assert "Connection failed" in result.details["error"]
    
    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, mock_settings):
        """Test Redis health check success."""
        with patch('redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_client.set.return_value = True
            mock_client.get.return_value = b"test_value"
            mock_client.delete.return_value = 1
            mock_client.info.return_value = {
                "redis_version": "6.2.6",
                "used_memory": 1024*1024,  # 1MB
                "connected_clients": 5,
                "uptime_in_seconds": 86400  # 1 day
            }
            mock_redis.return_value = mock_client
            
            result = await check_redis_health(mock_settings)
            
            assert result.status == "healthy"
            assert "Redis accessible and functional" in result.message
            assert result.details["version"] == "6.2.6"
            assert result.details["memory_used_mb"] == 1.0
            assert result.details["connected_clients"] == 5
            assert result.details["uptime_days"] == 1.0
    
    @pytest.mark.asyncio
    async def test_check_redis_health_connection_failure(self, mock_settings):
        """Test Redis health check with connection failure."""
        with patch('redis.from_url', side_effect=Exception("Connection refused")):
            result = await check_redis_health(mock_settings)
            
            assert result.status == "critical"
            assert "Redis health check failed" in result.message
            assert "Connection refused" in result.details["error"]
    
    @pytest.mark.asyncio
    async def test_check_configuration_validity_healthy(self):
        """Test configuration validation with healthy config."""
        settings = Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long",
            cors_origins=["http://localhost:3000"]
        )
        
        result = await check_configuration_validity(settings)
        
        assert result.status == "healthy"
        assert "Configuration is valid" in result.message
        assert result.details["environment"] == "development"
        assert result.details["validation"] == "passed"
    
    @pytest.mark.asyncio
    async def test_check_configuration_validity_production_issues(self):
        """Test configuration validation with production issues."""
        settings = Settings(
            app_name="Test App",
            environment="production",
            debug=True,  # Should be False in production
            secret_key="dev-secret-key-change-in-production",  # Default key
            cors_origins=["http://localhost:3000"]  # Non-HTTPS
        )
        
        result = await check_configuration_validity(settings)
        
        assert result.status == "critical"
        assert "critical issues" in result.message
        assert "DEBUG must be False in production" in result.details["critical_issues"]
        assert "SECRET_KEY must be changed from default value" in result.details["critical_issues"]
    
    @pytest.mark.asyncio
    async def test_check_security_configuration_healthy(self):
        """Test security configuration check with healthy config."""
        settings = Settings(
            app_name="Test App",
            environment="production",
            debug=False,
            secret_key="test-secret-key-32-characters-long",
            password_min_length=12,
            rate_limiting_enabled=True,
            csrf_protection_enabled=True,
            access_token_expire_minutes=30
        )
        
        result = await check_security_configuration(settings)
        
        assert result.status == "healthy"
        assert "Security configuration is compliant" in result.message
        assert result.details["compliance"] == "passed"
    
    @pytest.mark.asyncio
    async def test_check_security_configuration_issues(self):
        """Test security configuration check with issues."""
        settings = Settings(
            app_name="Test App",
            environment="production",
            debug=False,
            secret_key="test-secret-key-32-characters-long",
            password_min_length=6,  # Too short
            rate_limiting_enabled=False,  # Should be enabled in production
            csrf_protection_enabled=False,  # Should be enabled
            access_token_expire_minutes=120  # Too long
        )
        
        result = await check_security_configuration(settings)
        
        assert result.status == "critical"
        assert "critical issues" in result.message
        assert any("Password minimum length" in issue for issue in result.details["critical_issues"])
        assert any("Rate limiting should be enabled" in issue for issue in result.details["critical_issues"])
        assert any("CSRF protection should be enabled" in issue for issue in result.details["critical_issues"])
    
    @pytest.mark.asyncio
    async def test_check_external_services_supabase_success(self):
        """Test external services check with Supabase success."""
        settings = Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long",
            supabase_url="https://test.supabase.co"
        )
        
        # Mock httpx client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 401  # Expected for unauthenticated request
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await check_external_services(settings)
            
            assert result.status == "healthy"
            assert "External services check completed" in result.message
            assert "supabase" in result.details["services"]
            assert result.details["services"]["supabase"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_external_services_connection_failure(self):
        """Test external services check with connection failure."""
        settings = Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long",
            supabase_url="https://test.supabase.co"
        )
        
        # Mock httpx client to raise exception
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await check_external_services(settings)
            
            assert result.status == "critical"
            assert "supabase" in result.details["services"]
            assert result.details["services"]["supabase"] == "critical"


class TestHealthCheckIntegration:
    """Test health check system integration."""
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test that health checks can run concurrently without issues."""
        settings = Settings(
            app_name="Test App",
            environment="development",
            debug=True,
            secret_key="test-secret-key-32-characters-long"
        )
        
        # Mock all external dependencies
        with patch('sqlite3.connect') as mock_sqlite, \
             patch('redis.from_url') as mock_redis, \
             patch('httpx.AsyncClient') as mock_http:
            
            # Set up mocks
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.return_value = mock_conn
            
            mock_redis_client = Mock()
            mock_redis_client.set.return_value = True
            mock_redis_client.get.return_value = b"test"
            mock_redis_client.delete.return_value = 1
            mock_redis_client.info.return_value = {"redis_version": "6.0"}
            mock_redis.return_value = mock_redis_client
            
            mock_http_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_http_client.get.return_value = mock_response
            mock_http.return_value.__aenter__.return_value = mock_http_client
            
            # Run multiple health checks concurrently
            tasks = [
                check_database_health(settings),
                check_redis_health(settings),
                check_configuration_validity(settings),
                check_security_configuration(settings),
                check_external_services(settings)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All checks should complete successfully
            assert len(results) == 5
            for result in results:
                assert hasattr(result, 'status')
                assert hasattr(result, 'message')
                assert hasattr(result, 'timestamp')
                assert hasattr(result, 'response_time_ms')
    
    def test_health_check_performance(self, mock_settings):
        """Test that health checks complete within reasonable time."""
        import time
        
        # Mock external dependencies for fast responses
        with patch('sqlite3.connect') as mock_sqlite, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024):
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_sqlite.return_value = mock_conn
            
            start_time = time.time()
            
            # Run health check (async function, so we need to use asyncio)
            async def run_test():
                return await check_database_health(mock_settings)
            
            result = asyncio.run(run_test())
            
            end_time = time.time()
            
            # Health check should complete quickly (under 100ms for mocked operations)
            assert (end_time - start_time) < 0.1
            assert result.response_time_ms < 100
    
    def test_health_check_error_handling(self):
        """Test that health checks handle errors gracefully."""
        settings = Settings(
            app_name="Test App",
            environment="development", 
            debug=True,
            secret_key="test-secret-key-32-characters-long"
        )
        
        # Test with invalid configuration that should cause errors
        async def run_error_test():
            # This should handle the error gracefully
            result = await check_database_health(settings)
            return result
        
        result = asyncio.run(run_error_test())
        
        # Should return a valid result even if the check fails
        assert hasattr(result, 'status')
        assert hasattr(result, 'message')
        assert hasattr(result, 'timestamp')
        assert result.status in ["healthy", "warning", "critical"]