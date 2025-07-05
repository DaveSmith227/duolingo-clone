"""
Unit Tests for Redis Health Check Integration

Comprehensive test suite for Redis health check endpoints and service,
including mock Redis failures and edge cases.
"""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.health import router
from app.services.redis_health_service import (
    RedisHealthService, 
    RedisHealthInfo, 
    RedisHealthStatus,
    get_redis_health_service
)


class TestRedisHealthService:
    """Test RedisHealthService functionality."""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.get.return_value = "test_value"
        mock_client.delete.return_value = 1
        mock_client.info.return_value = {
            "used_memory": 1024000,
            "used_memory_human": "1.00M",
            "used_memory_peak": 2048000,
            "used_memory_peak_human": "2.00M",
            "mem_fragmentation_ratio": 1.5,
            "maxmemory": 0,
            "maxmemory_human": "0B",
            "maxmemory_policy": "noeviction",
            "connected_clients": 5,
            "total_connections_received": 100,
            "rejected_connections": 0,
            "total_commands_processed": 1000,
            "instantaneous_ops_per_sec": 10,
            "keyspace_hits": 800,
            "keyspace_misses": 200,
            "evicted_keys": 0,
            "expired_keys": 50
        }
        mock_client.config_get.return_value = {"maxmemory": "0"}
        return mock_client
    
    @pytest.fixture
    def redis_service(self, mock_redis_client):
        """Create Redis health service with mock client."""
        return RedisHealthService(redis_client=mock_redis_client)
    
    def test_redis_health_check_success(self, redis_service, mock_redis_client):
        """Test successful Redis health check."""
        # Mock the setex and get operations to return expected values
        test_value = None
        
        def mock_setex(key, ttl, value):
            nonlocal test_value
            test_value = value
            return True
        
        def mock_get(key):
            return test_value
        
        mock_redis_client.setex.side_effect = mock_setex
        mock_redis_client.get.side_effect = mock_get
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.HEALTHY
        assert health_info.is_connected is True
        assert health_info.response_time_ms > 0
        assert health_info.memory_usage is not None
        assert health_info.connection_info is not None
        assert health_info.performance_metrics is not None
        assert health_info.error_message is None
        assert health_info.last_checked is not None
        
        # Verify Redis operations were called
        mock_redis_client.ping.assert_called_once()
        mock_redis_client.info.assert_called_once()
    
    def test_redis_health_check_connection_error(self, redis_service, mock_redis_client):
        """Test Redis health check with connection error."""
        mock_redis_client.ping.side_effect = ConnectionError("Connection refused")
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.UNAVAILABLE
        assert health_info.is_connected is False
        assert health_info.response_time_ms == -1
        assert "Connection failed" in health_info.error_message
        assert health_info.last_checked is not None
    
    def test_redis_health_check_timeout_error(self, redis_service, mock_redis_client):
        """Test Redis health check with timeout error."""
        mock_redis_client.ping.side_effect = TimeoutError("Timeout occurred")
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.DEGRADED
        assert health_info.is_connected is False
        assert health_info.response_time_ms == -1
        assert "Connection timeout" in health_info.error_message
        assert health_info.last_checked is not None
    
    def test_redis_health_check_redis_error(self, redis_service, mock_redis_client):
        """Test Redis health check with Redis error."""
        mock_redis_client.ping.side_effect = RedisError("Redis error")
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.UNHEALTHY
        assert health_info.is_connected is False
        assert health_info.response_time_ms == -1
        assert "Redis error" in health_info.error_message
        assert health_info.last_checked is not None
    
    def test_redis_health_check_slow_response(self, redis_service, mock_redis_client):
        """Test Redis health check with slow response time."""
        # Mock the setex and get operations to return expected values
        test_value = None
        
        def mock_setex(key, ttl, value):
            nonlocal test_value
            test_value = value
            time.sleep(0.6)  # 600ms delay
            return True
        
        def mock_get(key):
            return test_value
        
        # Mock slow response by adding delay
        def slow_ping():
            time.sleep(0.01)  # Small delay for ping
            return True
        
        mock_redis_client.ping.side_effect = slow_ping
        mock_redis_client.setex.side_effect = mock_setex
        mock_redis_client.get.side_effect = mock_get
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.DEGRADED
        assert health_info.is_connected is True
        assert health_info.response_time_ms > 500
    
    def test_redis_health_check_high_memory_fragmentation(self, redis_service, mock_redis_client):
        """Test Redis health check with high memory fragmentation."""
        # Mock the setex and get operations to return expected values
        test_value = None
        
        def mock_setex(key, ttl, value):
            nonlocal test_value
            test_value = value
            return True
        
        def mock_get(key):
            return test_value
        
        mock_redis_client.setex.side_effect = mock_setex
        mock_redis_client.get.side_effect = mock_get
        
        mock_redis_client.info.return_value = {
            "mem_fragmentation_ratio": 2.5,  # High fragmentation
            "used_memory": 1024000,
            "maxmemory": 0,
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200
        }
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.DEGRADED
        assert health_info.memory_usage["memory_fragmentation_ratio"] == 2.5
    
    def test_redis_health_check_high_memory_usage(self, redis_service, mock_redis_client):
        """Test Redis health check with high memory usage."""
        # Mock the setex and get operations to return expected values
        test_value = None
        
        def mock_setex(key, ttl, value):
            nonlocal test_value
            test_value = value
            return True
        
        def mock_get(key):
            return test_value
        
        mock_redis_client.setex.side_effect = mock_setex
        mock_redis_client.get.side_effect = mock_get
        
        mock_redis_client.info.return_value = {
            "used_memory": 950000000,  # 950MB
            "maxmemory": 1000000000,   # 1GB limit
            "mem_fragmentation_ratio": 1.2,
            "connected_clients": 5,
            "total_commands_processed": 1000,
            "keyspace_hits": 800,
            "keyspace_misses": 200
        }
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.DEGRADED
        assert health_info.memory_usage["used_memory"] == 950000000
        assert health_info.memory_usage["maxmemory"] == 1000000000
    
    def test_redis_read_write_test_failure(self, redis_service, mock_redis_client):
        """Test Redis health check with read/write test failure."""
        mock_redis_client.get.return_value = "wrong_value"  # Wrong value returned
        
        health_info = redis_service.check_redis_health()
        
        assert health_info.status == RedisHealthStatus.UNHEALTHY
        assert health_info.is_connected is False
        assert "read/write test failed" in health_info.error_message.lower()
    
    def test_cache_metrics_tracking(self, redis_service):
        """Test cache hit/miss metrics tracking."""
        # Record some cache hits and misses
        redis_service.record_cache_hit()
        redis_service.record_cache_hit()
        redis_service.record_cache_miss()
        
        metrics = redis_service._get_cache_hit_ratio()
        
        assert metrics["application_total_requests"] == 3
        assert metrics["application_cache_hits"] == 2
        assert metrics["application_cache_misses"] == 1
        assert metrics["application_cache_hit_ratio"] == 2/3
        assert metrics["application_cache_miss_ratio"] == 1/3
    
    def test_cache_metrics_reset(self, redis_service):
        """Test cache metrics reset functionality."""
        # Record some metrics
        redis_service.record_cache_hit()
        redis_service.record_cache_miss()
        
        # Reset metrics
        redis_service.reset_cache_metrics()
        
        metrics = redis_service._get_cache_hit_ratio()
        
        assert metrics["application_total_requests"] == 0
        assert metrics["application_cache_hits"] == 0
        assert metrics["application_cache_misses"] == 0
        assert metrics["application_cache_hit_ratio"] == 0.0
    
    def test_memory_usage_extraction(self, redis_service):
        """Test memory usage information extraction."""
        redis_info = {
            "used_memory": 1048576,
            "used_memory_human": "1.00M",
            "used_memory_peak": 2097152,
            "used_memory_peak_human": "2.00M",
            "mem_fragmentation_ratio": 1.5,
            "maxmemory": 0,
            "maxmemory_human": "0B",
            "maxmemory_policy": "noeviction"
        }
        
        memory_usage = redis_service._get_memory_usage(redis_info)
        
        assert memory_usage["used_memory"] == 1048576
        assert memory_usage["used_memory_human"] == "1.00M"
        assert memory_usage["memory_fragmentation_ratio"] == 1.5
        assert memory_usage["maxmemory_policy"] == "noeviction"
    
    def test_connection_info_extraction(self, redis_service):
        """Test connection information extraction."""
        redis_info = {
            "connected_clients": 10,
            "total_connections_received": 500,
            "rejected_connections": 2,
            "blocked_clients": 0
        }
        
        connection_info = redis_service._get_connection_info(redis_info)
        
        assert connection_info["connected_clients"] == 10
        assert connection_info["total_connections_received"] == 500
        assert connection_info["rejected_connections"] == 2
        assert connection_info["blocked_clients"] == 0
    
    def test_performance_metrics_extraction(self, redis_service):
        """Test performance metrics extraction."""
        redis_info = {
            "total_commands_processed": 10000,
            "instantaneous_ops_per_sec": 50,
            "keyspace_hits": 8000,
            "keyspace_misses": 2000,
            "evicted_keys": 10,
            "expired_keys": 100
        }
        
        performance_metrics = redis_service._get_performance_metrics(redis_info)
        
        assert performance_metrics["total_commands_processed"] == 10000
        assert performance_metrics["instantaneous_ops_per_sec"] == 50
        assert performance_metrics["keyspace_hits"] == 8000
        assert performance_metrics["keyspace_misses"] == 2000
        assert performance_metrics["cache_hit_ratio"] == 0.8  # 8000 / (8000 + 2000)


class TestHealthEndpointsWithRedis:
    """Test health check endpoints with Redis integration."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_redis_healthy(self):
        """Mock Redis service returning healthy status."""
        with patch('app.api.health.get_redis_health_service') as mock_service:
            mock_health_service = Mock()
            mock_health_info = RedisHealthInfo(
                status=RedisHealthStatus.HEALTHY,
                is_connected=True,
                response_time_ms=10.5,
                memory_usage={"used_memory": 1024000, "used_memory_human": "1.00M"},
                connection_info={"connected_clients": 5},
                performance_metrics={"cache_hit_ratio": 0.85, "total_commands_processed": 1000},
                last_checked=datetime.now(timezone.utc)
            )
            mock_health_service.check_redis_health.return_value = mock_health_info
            mock_service.return_value = mock_health_service
            yield mock_health_service
    
    @pytest.fixture
    def mock_redis_unhealthy(self):
        """Mock Redis service returning unhealthy status."""
        with patch('app.api.health.get_redis_health_service') as mock_service:
            mock_health_service = Mock()
            mock_health_info = RedisHealthInfo(
                status=RedisHealthStatus.UNAVAILABLE,
                is_connected=False,
                response_time_ms=-1,
                error_message="Connection refused",
                last_checked=datetime.now(timezone.utc)
            )
            mock_health_service.check_redis_health.return_value = mock_health_info
            mock_service.return_value = mock_health_service
            yield mock_health_service
    
    @pytest.fixture
    def mock_database_healthy(self):
        """Mock healthy database connection."""
        with patch('app.api.health.check_database_connection') as mock_check, \
             patch('app.api.health.get_database_info') as mock_info:
            mock_check.return_value = True
            mock_info.return_value = {"status": "connected", "version": "1.0"}
            yield
    
    def test_cache_health_check_success(self, client, mock_redis_healthy, mock_database_healthy):
        """Test successful cache health check endpoint."""
        response = client.get("/health/cache")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["cache_status"] == "healthy"
        assert data["data"]["is_connected"] is True
        assert data["data"]["response_time_ms"] == 10.5
        assert "performance_metrics" in data["data"]
        assert "memory_info" in data["data"]
        assert "connection_pool_info" in data["data"]
    
    def test_cache_health_check_failure(self, client, mock_redis_unhealthy, mock_database_healthy):
        """Test cache health check endpoint with Redis failure."""
        response = client.get("/health/cache")
        
        assert response.status_code == 503
        
        data = response.json()
        assert data["success"] is True  # Response format is still successful, content indicates failure
        assert data["data"]["status"] == "unhealthy"
        assert data["data"]["cache_status"] == "unhealthy"
        assert data["data"]["is_connected"] is False
        assert data["data"]["response_time_ms"] == -1
    
    def test_detailed_health_check_success(self, client, mock_redis_healthy, mock_database_healthy):
        """Test detailed health check endpoint with healthy Redis."""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert "database" in data["data"]
        assert "redis" in data["data"]
        assert "services" in data["data"]
        assert "system_metrics" in data["data"]
        
        # Check Redis section
        redis_data = data["data"]["redis"]
        assert redis_data["healthy"] is True
        assert redis_data["status"] == "healthy"
        assert redis_data["is_connected"] is True
        assert redis_data["response_time_ms"] == 10.5
    
    def test_detailed_health_check_redis_unhealthy(self, client, mock_redis_unhealthy, mock_database_healthy):
        """Test detailed health check endpoint with unhealthy Redis."""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "degraded"  # Overall status degraded due to Redis
        
        # Check Redis section
        redis_data = data["data"]["redis"]
        assert redis_data["healthy"] is False
        assert redis_data["status"] == "unavailable"
        assert redis_data["is_connected"] is False
        assert redis_data["error_message"] == "Connection refused"
    
    def test_system_health_check_with_redis(self, client, mock_redis_healthy, mock_database_healthy):
        """Test system health check endpoint includes Redis status."""
        response = client.get("/health/system")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["redis"] == "healthy"
    
    def test_ready_check_includes_redis(self, client, mock_redis_healthy, mock_database_healthy):
        """Test readiness check includes Redis status."""
        response = client.get("/health/ready")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        assert data["overall"] == "ready"
        assert data["redis"] == "healthy"
        assert data["database"] == "healthy"
    
    def test_metrics_endpoint_includes_redis(self, client, mock_redis_healthy, mock_database_healthy):
        """Test metrics endpoint includes Redis metrics."""
        response = client.get("/health/metrics")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "redis_metrics" in data
        
        redis_metrics = data["redis_metrics"]
        assert redis_metrics["status"] == "healthy"
        assert redis_metrics["is_connected"] is True
        assert redis_metrics["response_time_ms"] == 10.5
        assert "memory_usage" in redis_metrics
        assert "performance_metrics" in redis_metrics
        assert "connection_info" in redis_metrics
    
    def test_cache_health_check_with_custom_request_id(self, client, mock_redis_healthy, mock_database_healthy):
        """Test cache health check with custom request ID."""
        custom_request_id = "test-request-123"
        
        response = client.get(
            "/health/cache",
            headers={"X-Request-ID": custom_request_id}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["request_id"] == custom_request_id
    
    def test_detailed_health_check_system_metrics(self, client, mock_redis_healthy, mock_database_healthy):
        """Test detailed health check includes comprehensive system metrics."""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        
        data = response.json()
        system_metrics = data["data"]["system_metrics"]
        
        assert "uptime_seconds" in system_metrics
        assert "uptime_human" in system_metrics
        assert "redis_response_time_ms" in system_metrics
        assert "memory_info" in system_metrics
        assert "connection_pool_info" in system_metrics
        assert "cache_performance" in system_metrics
    
    @patch('app.api.health.get_settings')
    def test_detailed_health_check_services_status(self, mock_settings, client, mock_redis_healthy, mock_database_healthy):
        """Test detailed health check services status includes all external services."""
        # Mock settings
        mock_settings_obj = Mock()
        mock_settings_obj.openai_api_key = "test-key"
        mock_settings_obj.has_supabase_config = True
        mock_settings_obj.environment = "development"
        mock_settings_obj.app_version = "1.0.0"
        mock_settings.return_value = mock_settings_obj
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        
        data = response.json()
        services = data["data"]["services"]
        
        assert services["redis"] == "healthy"
        assert services["openai"] == "configured"
        assert services["supabase"] == "configured"


class TestRedisHealthServiceGlobal:
    """Test global Redis health service instance."""
    
    def test_get_redis_health_service_singleton(self):
        """Test that get_redis_health_service returns singleton instance."""
        service1 = get_redis_health_service()
        service2 = get_redis_health_service()
        
        assert service1 is service2
        assert isinstance(service1, RedisHealthService)
    
    @patch('app.services.redis_health_service.redis_health_service', None)
    def test_get_redis_health_service_creates_new_instance(self):
        """Test that get_redis_health_service creates new instance when needed."""
        with patch('app.services.redis_health_service.RedisHealthService') as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance
            
            service = get_redis_health_service()
            
            assert service is mock_instance
            mock_service_class.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])