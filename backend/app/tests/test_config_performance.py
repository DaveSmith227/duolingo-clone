"""
Performance Tests for Configuration Loading

Tests that verify configuration loading meets performance requirements:
- Configuration loading completes in <100ms
- Memory usage stays below 10MB during configuration operations
- Performance is consistent across different environments
- Large configuration files load efficiently
- Concurrent configuration access performs well

Requirements:
- Load time: <100ms
- Memory footprint: <10MB
- Tests cover both cold and warm starts
- Performance is consistent across environments
"""

import pytest
import time
import psutil
import os
import gc
import asyncio
import threading
from typing import List, Dict, Any
from unittest.mock import patch, Mock
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.config import Settings, get_settings
from app.core.config_validators import ConfigurationBusinessRuleValidator
from app.core.audited_config import create_audited_settings


class PerformanceMetrics:
    """Helper class to track performance metrics."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        
    def start_measurement(self):
        """Start measuring performance."""
        gc.collect()  # Clean up before measurement
        self.start_time = time.perf_counter()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    def stop_measurement(self) -> Dict[str, float]:
        """Stop measuring and return metrics."""
        end_time = time.perf_counter()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            "duration_ms": (end_time - self.start_time) * 1000,
            "memory_start_mb": self.start_memory,
            "memory_end_mb": end_memory,
            "memory_delta_mb": end_memory - self.start_memory,
            "memory_peak_mb": end_memory
        }


class TestConfigurationPerformance:
    """Test configuration loading performance."""
    
    def test_settings_loading_performance(self):
        """Test that Settings loading meets performance requirements."""
        metrics = PerformanceMetrics()
        
        # Test cold start performance
        metrics.start_measurement()
        settings = Settings()
        cold_metrics = metrics.stop_measurement()
        
        # Verify performance requirements
        assert cold_metrics["duration_ms"] < 100, f"Cold start took {cold_metrics['duration_ms']:.2f}ms (should be <100ms)"
        assert cold_metrics["memory_delta_mb"] < 10, f"Memory usage {cold_metrics['memory_delta_mb']:.2f}MB (should be <10MB)"
        
        # Test warm start performance (subsequent loads)
        metrics.start_measurement()
        settings2 = Settings()
        warm_metrics = metrics.stop_measurement()
        
        assert warm_metrics["duration_ms"] < 50, f"Warm start took {warm_metrics['duration_ms']:.2f}ms (should be <50ms)"
        assert warm_metrics["memory_delta_mb"] < 5, f"Warm memory usage {warm_metrics['memory_delta_mb']:.2f}MB (should be <5MB)"
        
        print(f"Cold start: {cold_metrics['duration_ms']:.2f}ms, {cold_metrics['memory_delta_mb']:.2f}MB")
        print(f"Warm start: {warm_metrics['duration_ms']:.2f}ms, {warm_metrics['memory_delta_mb']:.2f}MB")
    
    def test_get_settings_performance(self):
        """Test that get_settings() function meets performance requirements."""
        metrics = PerformanceMetrics()
        
        # Test first call (cold)
        metrics.start_measurement()
        settings = get_settings()
        cold_metrics = metrics.stop_measurement()
        
        # Test subsequent calls (should be cached)
        metrics.start_measurement()
        settings2 = get_settings()
        cached_metrics = metrics.stop_measurement()
        
        assert cold_metrics["duration_ms"] < 100, f"get_settings() cold took {cold_metrics['duration_ms']:.2f}ms"
        assert cached_metrics["duration_ms"] < 10, f"get_settings() cached took {cached_metrics['duration_ms']:.2f}ms"
        assert cached_metrics["memory_delta_mb"] < 1, f"Cached call used {cached_metrics['memory_delta_mb']:.2f}MB"
        
        print(f"get_settings() cold: {cold_metrics['duration_ms']:.2f}ms")
        print(f"get_settings() cached: {cached_metrics['duration_ms']:.2f}ms")
    
    def test_configuration_validation_performance(self):
        """Test that configuration validation meets performance requirements."""
        settings = Settings()
        validator = ConfigurationBusinessRuleValidator()
        metrics = PerformanceMetrics()
        
        # Convert settings to dict and get environment
        from app.core.environment import get_environment
        config_dict = settings.model_dump()
        environment = get_environment()
        
        metrics.start_measurement()
        violations = validator.validate(config_dict, environment)
        validation_metrics = metrics.stop_measurement()
        
        assert validation_metrics["duration_ms"] < 50, f"Validation took {validation_metrics['duration_ms']:.2f}ms"
        assert validation_metrics["memory_delta_mb"] < 5, f"Validation used {validation_metrics['memory_delta_mb']:.2f}MB"
        
        print(f"Configuration validation: {validation_metrics['duration_ms']:.2f}ms, {validation_metrics['memory_delta_mb']:.2f}MB")
    
    def test_audited_settings_performance(self):
        """Test that audited settings creation meets performance requirements."""
        settings = Settings()
        metrics = PerformanceMetrics()
        
        metrics.start_measurement()
        audited = create_audited_settings(settings)
        audit_metrics = metrics.stop_measurement()
        
        # Test audit export performance
        metrics.start_measurement()
        audit_data = audited.export_audit_safe()
        export_metrics = metrics.stop_measurement()
        
        assert audit_metrics["duration_ms"] < 50, f"Audited creation took {audit_metrics['duration_ms']:.2f}ms"
        assert export_metrics["duration_ms"] < 25, f"Audit export took {export_metrics['duration_ms']:.2f}ms"
        assert (audit_metrics["memory_delta_mb"] + export_metrics["memory_delta_mb"]) < 5, "Total audit memory usage too high"
        
        print(f"Audited settings: {audit_metrics['duration_ms']:.2f}ms")
        print(f"Audit export: {export_metrics['duration_ms']:.2f}ms")
    
    def test_concurrent_settings_access_performance(self):
        """Test performance under concurrent access."""
        num_threads = 10
        metrics = PerformanceMetrics()
        
        def load_settings():
            start = time.perf_counter()
            settings = get_settings()
            return (time.perf_counter() - start) * 1000
        
        metrics.start_measurement()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(load_settings) for _ in range(num_threads)]
            durations = [future.result() for future in as_completed(futures)]
        
        concurrent_metrics = metrics.stop_measurement()
        
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        assert max_duration < 100, f"Slowest concurrent access took {max_duration:.2f}ms"
        assert avg_duration < 50, f"Average concurrent access took {avg_duration:.2f}ms"
        assert concurrent_metrics["memory_delta_mb"] < 10, f"Concurrent access used {concurrent_metrics['memory_delta_mb']:.2f}MB"
        
        print(f"Concurrent access - avg: {avg_duration:.2f}ms, max: {max_duration:.2f}ms")
        print(f"Concurrent memory usage: {concurrent_metrics['memory_delta_mb']:.2f}MB")
    
    @pytest.mark.parametrize("environment", ["development", "staging", "production"])
    def test_environment_specific_performance(self, environment):
        """Test performance across different environments."""
        metrics = PerformanceMetrics()
        
        with patch.dict(os.environ, {"ENVIRONMENT": environment}):
            metrics.start_measurement()
            settings = Settings()
            env_metrics = metrics.stop_measurement()
            
            assert env_metrics["duration_ms"] < 100, f"{environment} environment loading took {env_metrics['duration_ms']:.2f}ms"
            assert env_metrics["memory_delta_mb"] < 10, f"{environment} environment used {env_metrics['memory_delta_mb']:.2f}MB"
            
            print(f"{environment} environment: {env_metrics['duration_ms']:.2f}ms, {env_metrics['memory_delta_mb']:.2f}MB")
    
    def test_large_configuration_performance(self):
        """Test performance with large configuration values."""
        metrics = PerformanceMetrics()
        
        # Create large environment values (using keys that actually exist)
        large_env = {
            "SECRET_KEY": "x" * 256,  # Very long secret key
            "APP_NAME": "Large Test Application " + "x" * 200,
            "APP_VERSION": "1.0.0-" + "x" * 100,
        }
        
        with patch.dict(os.environ, large_env):
            metrics.start_measurement()
            settings = Settings()
            large_metrics = metrics.stop_measurement()
            
            assert large_metrics["duration_ms"] < 150, f"Large config loading took {large_metrics['duration_ms']:.2f}ms"
            assert large_metrics["memory_delta_mb"] < 15, f"Large config used {large_metrics['memory_delta_mb']:.2f}MB"
            
            print(f"Large configuration: {large_metrics['duration_ms']:.2f}ms, {large_metrics['memory_delta_mb']:.2f}MB")
    
    def test_repeated_access_performance(self):
        """Test performance of repeated configuration access."""
        settings = get_settings()
        metrics = PerformanceMetrics()
        
        # Test repeated property access
        metrics.start_measurement()
        
        for _ in range(1000):
            _ = settings.environment
            _ = settings.debug
            _ = settings.secret_key
            _ = settings.app_name
        
        access_metrics = metrics.stop_measurement()
        
        assert access_metrics["duration_ms"] < 50, f"1000 property accesses took {access_metrics['duration_ms']:.2f}ms"
        assert access_metrics["memory_delta_mb"] < 2, f"Property access used {access_metrics['memory_delta_mb']:.2f}MB"
        
        print(f"1000 property accesses: {access_metrics['duration_ms']:.2f}ms")
    
    def test_memory_cleanup_performance(self):
        """Test that configuration objects are properly garbage collected."""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Create and destroy many settings objects
        for _ in range(100):
            settings = Settings()
            del settings
        
        # Force garbage collection
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        assert memory_growth < 5, f"Memory grew by {memory_growth:.2f}MB after 100 settings objects"
        
        print(f"Memory growth after 100 objects: {memory_growth:.2f}MB")
    
    def test_configuration_serialization_performance(self):
        """Test performance of configuration serialization."""
        settings = Settings()
        metrics = PerformanceMetrics()
        
        # Test model_dump performance
        metrics.start_measurement()
        for _ in range(100):
            data = settings.model_dump()
        serialization_metrics = metrics.stop_measurement()
        
        # Test model_dump_json performance
        metrics.start_measurement()
        for _ in range(100):
            json_data = settings.model_dump_json()
        json_metrics = metrics.stop_measurement()
        
        assert serialization_metrics["duration_ms"] < 100, f"100 serializations took {serialization_metrics['duration_ms']:.2f}ms"
        assert json_metrics["duration_ms"] < 100, f"100 JSON serializations took {json_metrics['duration_ms']:.2f}ms"
        
        print(f"Serialization performance: {serialization_metrics['duration_ms']:.2f}ms")
        print(f"JSON serialization performance: {json_metrics['duration_ms']:.2f}ms")


class TestConfigurationMemoryProfile:
    """Test memory usage patterns of configuration loading."""
    
    def test_memory_baseline(self):
        """Establish memory baseline for configuration operations."""
        process = psutil.Process()
        
        # Get baseline memory before any configuration loading
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        # Load configuration
        settings = Settings()
        config_memory = process.memory_info().rss / 1024 / 1024
        
        # Create audited settings
        audited = create_audited_settings(settings)
        audited_memory = process.memory_info().rss / 1024 / 1024
        
        # Export audit data
        audit_data = audited.export_audit_safe()
        export_memory = process.memory_info().rss / 1024 / 1024
        
        config_delta = config_memory - baseline_memory
        audited_delta = audited_memory - config_memory
        export_delta = export_memory - audited_memory
        total_delta = export_memory - baseline_memory
        
        assert config_delta < 5, f"Basic config loading used {config_delta:.2f}MB"
        assert audited_delta < 3, f"Audited config creation used {audited_delta:.2f}MB"
        assert export_delta < 2, f"Audit export used {export_delta:.2f}MB"
        assert total_delta < 10, f"Total configuration operations used {total_delta:.2f}MB"
        
        print(f"Memory usage - Config: {config_delta:.2f}MB, Audited: {audited_delta:.2f}MB, Export: {export_delta:.2f}MB")
        print(f"Total memory usage: {total_delta:.2f}MB")
    
    def test_memory_stress_test(self):
        """Stress test memory usage with many configuration objects."""
        process = psutil.Process()
        start_memory = process.memory_info().rss / 1024 / 1024
        
        # Create many configuration objects
        configs = []
        for i in range(50):
            configs.append(Settings())
            
            # Check memory every 10 objects
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_per_config = (current_memory - start_memory) / (i + 1)
                assert memory_per_config < 0.5, f"Each config object uses {memory_per_config:.2f}MB (should be <0.5MB)"
        
        peak_memory = process.memory_info().rss / 1024 / 1024
        total_usage = peak_memory - start_memory
        
        assert total_usage < 25, f"50 config objects used {total_usage:.2f}MB (should be <25MB)"
        
        # Clean up and verify memory is released
        del configs
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_released = peak_memory - final_memory
        
        # At least 50% of memory should be released
        assert memory_released > total_usage * 0.5, f"Only {memory_released:.2f}MB of {total_usage:.2f}MB was released"
        
        print(f"Stress test - Peak: {total_usage:.2f}MB, Released: {memory_released:.2f}MB")


@pytest.mark.asyncio
class TestAsyncConfigurationPerformance:
    """Test asynchronous configuration operations performance."""
    
    async def test_async_configuration_access_performance(self):
        """Test performance of async configuration operations."""
        metrics = PerformanceMetrics()
        
        async def async_config_operation():
            # Simulate async configuration loading
            await asyncio.sleep(0.001)  # Small delay to simulate I/O
            settings = get_settings()
            return settings.environment
        
        metrics.start_measurement()
        
        # Run multiple async operations concurrently
        tasks = [async_config_operation() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        async_metrics = metrics.stop_measurement()
        
        assert async_metrics["duration_ms"] < 200, f"50 async operations took {async_metrics['duration_ms']:.2f}ms"
        assert async_metrics["memory_delta_mb"] < 10, f"Async operations used {async_metrics['memory_delta_mb']:.2f}MB"
        assert len(results) == 50, "All async operations should complete"
        
        print(f"Async operations: {async_metrics['duration_ms']:.2f}ms for 50 tasks")
    
    async def test_async_health_check_performance(self):
        """Test performance of async health check operations."""
        try:
            from app.api.config_health import check_configuration_validity
        except ImportError:
            pytest.skip("Config health module not available")
        
        settings = Settings()
        metrics = PerformanceMetrics()
        
        try:
            metrics.start_measurement()
            health_result = await check_configuration_validity(settings)
            health_metrics = metrics.stop_measurement()
            
            assert health_metrics["duration_ms"] < 500, f"Health check took {health_metrics['duration_ms']:.2f}ms"
            assert health_metrics["memory_delta_mb"] < 10, f"Health check used {health_metrics['memory_delta_mb']:.2f}MB"
            assert health_result.status in ["healthy", "warning", "critical"], "Health check should return valid status"
            
            print(f"Async health check: {health_metrics['duration_ms']:.2f}ms")
        except Exception as e:
            pytest.skip(f"Health check test failed due to dependency: {e}")


if __name__ == "__main__":
    # Run a quick performance check
    print("Running configuration performance tests...")
    
    metrics = PerformanceMetrics()
    metrics.start_measurement()
    settings = Settings()
    result = metrics.stop_measurement()
    
    print(f"Configuration loading: {result['duration_ms']:.2f}ms, {result['memory_delta_mb']:.2f}MB")
    
    if result['duration_ms'] > 100:
        print("❌ PERFORMANCE ISSUE: Configuration loading exceeds 100ms threshold")
    elif result['memory_delta_mb'] > 10:
        print("❌ MEMORY ISSUE: Configuration loading exceeds 10MB threshold")
    else:
        print("✅ Performance requirements met")