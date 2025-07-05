"""
Redis Health Service

Service for checking Redis connectivity, performance metrics, and health status.
Provides comprehensive Redis monitoring for health check endpoints.
"""

import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisHealthStatus(Enum):
    """Redis health status states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"


@dataclass
class RedisHealthInfo:
    """Redis health information."""
    status: RedisHealthStatus
    is_connected: bool
    response_time_ms: float
    memory_usage: Optional[Dict[str, Any]] = None
    connection_info: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    last_checked: Optional[datetime] = None


class RedisHealthService:
    """
    Service for Redis health checks and performance monitoring.
    
    Provides comprehensive Redis health status including connectivity,
    performance metrics, memory usage, and connection pool status.
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize Redis health service.
        
        Args:
            redis_client: Optional Redis client instance
        """
        self.settings = get_settings()
        self.redis_client = redis_client or self._create_redis_client()
        self._cache_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_reset": datetime.now(timezone.utc)
        }
    
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client from configuration."""
        try:
            return redis.from_url(
                self.settings.redis_dsn,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
        except Exception as e:
            logger.error(f"Failed to create Redis client: {str(e)}")
            raise
    
    def check_redis_health(self) -> RedisHealthInfo:
        """
        Perform comprehensive Redis health check.
        
        Returns:
            RedisHealthInfo with detailed status and metrics
        """
        start_time = time.time()
        
        try:
            # Test basic connectivity with ping
            response_time = self._test_connectivity()
            
            # Get Redis info and metrics
            redis_info = self._get_redis_info()
            memory_usage = self._get_memory_usage(redis_info)
            connection_info = self._get_connection_info(redis_info)
            performance_metrics = self._get_performance_metrics(redis_info)
            
            # Determine overall health status
            status = self._determine_health_status(response_time, redis_info)
            
            return RedisHealthInfo(
                status=status,
                is_connected=True,
                response_time_ms=response_time,
                memory_usage=memory_usage,
                connection_info=connection_info,
                performance_metrics=performance_metrics,
                last_checked=datetime.now(timezone.utc)
            )
            
        except ConnectionError as e:
            logger.warning(f"Redis connection error: {str(e)}")
            return RedisHealthInfo(
                status=RedisHealthStatus.UNAVAILABLE,
                is_connected=False,
                response_time_ms=-1,
                error_message=f"Connection failed: {str(e)}",
                last_checked=datetime.now(timezone.utc)
            )
            
        except TimeoutError as e:
            logger.warning(f"Redis timeout error: {str(e)}")
            return RedisHealthInfo(
                status=RedisHealthStatus.DEGRADED,
                is_connected=False,
                response_time_ms=-1,
                error_message=f"Connection timeout: {str(e)}",
                last_checked=datetime.now(timezone.utc)
            )
            
        except RedisError as e:
            logger.error(f"Redis error during health check: {str(e)}")
            return RedisHealthInfo(
                status=RedisHealthStatus.UNHEALTHY,
                is_connected=False,
                response_time_ms=-1,
                error_message=f"Redis error: {str(e)}",
                last_checked=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during Redis health check: {str(e)}")
            return RedisHealthInfo(
                status=RedisHealthStatus.UNHEALTHY,
                is_connected=False,
                response_time_ms=-1,
                error_message=f"Unexpected error: {str(e)}",
                last_checked=datetime.now(timezone.utc)
            )
    
    def _test_connectivity(self) -> float:
        """
        Test Redis connectivity and measure response time.
        
        Returns:
            Response time in milliseconds
        """
        start_time = time.time()
        
        # Test ping
        result = self.redis_client.ping()
        if not result:
            raise ConnectionError("Redis ping failed")
        
        # Test basic operations
        test_key = "health_check:test"
        test_value = str(int(time.time()))
        
        # Set and get test value
        self.redis_client.setex(test_key, 10, test_value)
        retrieved_value = self.redis_client.get(test_key)
        
        if retrieved_value != test_value:
            raise RedisError("Redis read/write test failed")
        
        # Clean up test key
        self.redis_client.delete(test_key)
        
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds
    
    def _get_redis_info(self) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Returns:
            Dictionary with Redis server info
        """
        try:
            return self.redis_client.info()
        except Exception as e:
            logger.warning(f"Failed to get Redis info: {str(e)}")
            return {}
    
    def _get_memory_usage(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract memory usage information from Redis info.
        
        Args:
            redis_info: Redis server information
            
        Returns:
            Memory usage metrics
        """
        if not redis_info:
            return {}
        
        return {
            "used_memory": redis_info.get("used_memory", 0),
            "used_memory_human": redis_info.get("used_memory_human", "0B"),
            "used_memory_peak": redis_info.get("used_memory_peak", 0),
            "used_memory_peak_human": redis_info.get("used_memory_peak_human", "0B"),
            "memory_fragmentation_ratio": redis_info.get("mem_fragmentation_ratio", 0),
            "maxmemory": redis_info.get("maxmemory", 0),
            "maxmemory_human": redis_info.get("maxmemory_human", "0B"),
            "maxmemory_policy": redis_info.get("maxmemory_policy", "noeviction")
        }
    
    def _get_connection_info(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract connection information from Redis info.
        
        Args:
            redis_info: Redis server information
            
        Returns:
            Connection information
        """
        if not redis_info:
            return {}
        
        return {
            "connected_clients": redis_info.get("connected_clients", 0),
            "client_recent_max_input_buffer": redis_info.get("client_recent_max_input_buffer", 0),
            "client_recent_max_output_buffer": redis_info.get("client_recent_max_output_buffer", 0),
            "blocked_clients": redis_info.get("blocked_clients", 0),
            "tracking_clients": redis_info.get("tracking_clients", 0),
            "total_connections_received": redis_info.get("total_connections_received", 0),
            "rejected_connections": redis_info.get("rejected_connections", 0)
        }
    
    def _get_performance_metrics(self, redis_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract performance metrics from Redis info.
        
        Args:
            redis_info: Redis server information
            
        Returns:
            Performance metrics
        """
        if not redis_info:
            return self._get_cache_hit_ratio()
        
        metrics = {
            "total_commands_processed": redis_info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": redis_info.get("instantaneous_ops_per_sec", 0),
            "instantaneous_input_kbps": redis_info.get("instantaneous_input_kbps", 0),
            "instantaneous_output_kbps": redis_info.get("instantaneous_output_kbps", 0),
            "keyspace_hits": redis_info.get("keyspace_hits", 0),
            "keyspace_misses": redis_info.get("keyspace_misses", 0),
            "evicted_keys": redis_info.get("evicted_keys", 0),
            "expired_keys": redis_info.get("expired_keys", 0),
            "pubsub_channels": redis_info.get("pubsub_channels", 0),
            "pubsub_patterns": redis_info.get("pubsub_patterns", 0)
        }
        
        # Calculate cache hit ratio
        hits = metrics["keyspace_hits"]
        misses = metrics["keyspace_misses"]
        total_requests = hits + misses
        
        if total_requests > 0:
            metrics["cache_hit_ratio"] = hits / total_requests
        else:
            metrics["cache_hit_ratio"] = 0.0
        
        # Add our internal cache metrics
        internal_metrics = self._get_cache_hit_ratio()
        metrics.update(internal_metrics)
        
        return metrics
    
    def _get_cache_hit_ratio(self) -> Dict[str, Any]:
        """
        Get internal cache hit ratio metrics.
        
        Returns:
            Internal cache metrics
        """
        total_requests = self._cache_metrics["total_requests"]
        hits = self._cache_metrics["cache_hits"]
        misses = self._cache_metrics["cache_misses"]
        
        if total_requests > 0:
            hit_ratio = hits / total_requests
            miss_ratio = misses / total_requests
        else:
            hit_ratio = 0.0
            miss_ratio = 0.0
        
        return {
            "application_cache_hit_ratio": hit_ratio,
            "application_cache_miss_ratio": miss_ratio,
            "application_total_requests": total_requests,
            "application_cache_hits": hits,
            "application_cache_misses": misses,
            "application_metrics_last_reset": self._cache_metrics["last_reset"].isoformat()
        }
    
    def _determine_health_status(
        self, 
        response_time: float, 
        redis_info: Dict[str, Any]
    ) -> RedisHealthStatus:
        """
        Determine overall Redis health status based on metrics.
        
        Args:
            response_time: Response time in milliseconds
            redis_info: Redis server information
            
        Returns:
            Health status
        """
        # Check response time thresholds
        if response_time > 1000:  # > 1 second
            return RedisHealthStatus.UNHEALTHY
        elif response_time > 500:  # > 500ms
            return RedisHealthStatus.DEGRADED
        
        # Check memory usage
        if redis_info:
            memory_ratio = redis_info.get("mem_fragmentation_ratio", 0)
            if memory_ratio > 2.0:  # High fragmentation
                return RedisHealthStatus.DEGRADED
            
            # Check if approaching memory limit
            used_memory = redis_info.get("used_memory", 0)
            max_memory = redis_info.get("maxmemory", 0)
            
            if max_memory > 0:  # If maxmemory is set
                memory_usage_ratio = used_memory / max_memory
                if memory_usage_ratio > 0.9:  # > 90% memory usage
                    return RedisHealthStatus.DEGRADED
                elif memory_usage_ratio > 0.95:  # > 95% memory usage
                    return RedisHealthStatus.UNHEALTHY
        
        return RedisHealthStatus.HEALTHY
    
    def record_cache_hit(self):
        """Record a cache hit for metrics tracking."""
        self._cache_metrics["total_requests"] += 1
        self._cache_metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """Record a cache miss for metrics tracking."""
        self._cache_metrics["total_requests"] += 1
        self._cache_metrics["cache_misses"] += 1
    
    def reset_cache_metrics(self):
        """Reset cache metrics tracking."""
        self._cache_metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_reset": datetime.now(timezone.utc)
        }
    
    def get_redis_server_info(self) -> Dict[str, Any]:
        """
        Get comprehensive Redis server information.
        
        Returns:
            Complete Redis server information
        """
        try:
            info = self.redis_client.info()
            config = self.redis_client.config_get()
            
            return {
                "server_info": info,
                "configuration": config,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get Redis server info: {str(e)}")
            return {"error": str(e)}


# Global Redis health service instance
redis_health_service: Optional[RedisHealthService] = None


def get_redis_health_service() -> RedisHealthService:
    """
    Get Redis health service instance.
    
    Returns:
        Global RedisHealthService instance
    """
    global redis_health_service
    if redis_health_service is None:
        redis_health_service = RedisHealthService()
    return redis_health_service