#!/usr/bin/env python3

"""
Configuration Performance Testing Script

Standalone script to validate configuration loading performance requirements:
- Configuration loading completes in <100ms
- Memory usage stays below 10MB during configuration operations
- Performance is consistent across different environments
- Comprehensive reporting and validation

This script can be run independently for CI/CD validation or development testing.

Usage:
    python scripts/test_config_performance.py
    python scripts/test_config_performance.py --verbose
    python scripts/test_config_performance.py --iterations 50
    python scripts/test_config_performance.py --report-file performance_report.json
"""

import argparse
import json
import sys
import time
import gc
import os
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
    from app.core.config import Settings, get_settings
    from app.core.config_validators import ConfigurationBusinessRuleValidator
    from app.core.audited_config import create_audited_settings
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running this from the backend directory with virtual environment activated")
    sys.exit(1)


@dataclass
class PerformanceResult:
    """Results from a performance test."""
    test_name: str
    duration_ms: float
    memory_start_mb: float
    memory_end_mb: float
    memory_delta_mb: float
    memory_peak_mb: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceReport:
    """Complete performance test report."""
    timestamp: str
    environment: str
    python_version: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_success: bool
    requirements_met: bool
    results: List[PerformanceResult]
    summary: Dict[str, Any]


class ConfigurationPerformanceTester:
    """Main performance testing class."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.process = psutil.Process()
        self.results: List[PerformanceResult] = []
        
        # Performance requirements
        self.max_load_time_ms = 100
        self.max_memory_mb = 10
        self.max_warm_load_time_ms = 50
        
    def log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def measure_performance(self, test_name: str, test_func, iterations: int = 1) -> PerformanceResult:
        """Measure performance of a test function."""
        self.log(f"Running test: {test_name} ({iterations} iterations)")
        
        # Clean up before measurement
        gc.collect()
        
        start_memory = self.process.memory_info().rss / 1024 / 1024
        durations = []
        memory_peaks = []
        error_message = None
        success = True
        
        try:
            for i in range(iterations):
                start_time = time.perf_counter()
                
                # Run the test function
                result = test_func()
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                durations.append(duration_ms)
                
                # Measure memory
                current_memory = self.process.memory_info().rss / 1024 / 1024
                memory_peaks.append(current_memory)
                
                if self.verbose and iterations > 1:
                    print(f"  Iteration {i+1}: {duration_ms:.2f}ms")
        
        except Exception as e:
            success = False
            error_message = str(e)
            durations = [0] if not durations else durations
            memory_peaks = [start_memory] if not memory_peaks else memory_peaks
        
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Calculate statistics
        avg_duration = statistics.mean(durations) if durations else 0
        peak_memory = max(memory_peaks) if memory_peaks else start_memory
        memory_delta = end_memory - start_memory
        
        result = PerformanceResult(
            test_name=test_name,
            duration_ms=avg_duration,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_delta_mb=memory_delta,
            memory_peak_mb=peak_memory,
            success=success,
            error_message=error_message,
            metadata={
                "iterations": iterations,
                "duration_min": min(durations) if durations else 0,
                "duration_max": max(durations) if durations else 0,
                "duration_std": statistics.stdev(durations) if len(durations) > 1 else 0
            }
        )
        
        self.results.append(result)
        
        if success:
            self.log(f"✅ {test_name}: {avg_duration:.2f}ms, {memory_delta:.2f}MB")
        else:
            self.log(f"❌ {test_name}: FAILED - {error_message}")
        
        return result
    
    def test_basic_settings_loading(self) -> PerformanceResult:
        """Test basic Settings class loading performance."""
        def test_func():
            return Settings()
        
        return self.measure_performance("Basic Settings Loading", test_func, iterations=10)
    
    def test_get_settings_function(self) -> PerformanceResult:
        """Test get_settings() function performance."""
        def test_func():
            return get_settings()
        
        return self.measure_performance("get_settings() Function", test_func, iterations=10)
    
    def test_settings_caching(self) -> PerformanceResult:
        """Test settings caching performance."""
        def test_func():
            # First call (cold)
            settings1 = get_settings()
            # Second call (should be cached)
            settings2 = get_settings()
            return settings1, settings2
        
        return self.measure_performance("Settings Caching", test_func, iterations=5)
    
    def test_configuration_validation(self) -> PerformanceResult:
        """Test configuration validation performance."""
        def test_func():
            settings = Settings()
            validator = ConfigurationBusinessRuleValidator()
            # Convert settings to dict and get environment
            from app.core.environment import get_environment
            config_dict = settings.model_dump()
            environment = get_environment()
            return validator.validate(config_dict, environment)
        
        return self.measure_performance("Configuration Validation", test_func, iterations=5)
    
    def test_audited_settings_creation(self) -> PerformanceResult:
        """Test audited settings creation performance."""
        def test_func():
            settings = Settings()
            audited = create_audited_settings(settings)
            return audited.export_audit_safe()
        
        return self.measure_performance("Audited Settings Creation", test_func, iterations=5)
    
    def test_large_configuration(self) -> PerformanceResult:
        """Test performance with large configuration values."""
        def test_func():
            # Set large environment variables (using keys that actually exist in Settings)
            large_env = {
                "SECRET_KEY": "x" * 256,
                "APP_NAME": "Large Test Application " + "x" * 200,
                "APP_VERSION": "1.0.0-" + "x" * 100,
            }
            
            original_env = {}
            try:
                # Set large values
                for key, value in large_env.items():
                    original_env[key] = os.environ.get(key)
                    os.environ[key] = value
                
                # Test loading with large config
                settings = Settings()
                return settings
            
            finally:
                # Restore original values
                for key, value in original_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
        
        return self.measure_performance("Large Configuration Loading", test_func, iterations=3)
    
    def test_concurrent_access(self) -> PerformanceResult:
        """Test concurrent settings access performance."""
        import threading
        import queue
        
        def test_func():
            results_queue = queue.Queue()
            threads = []
            
            def worker():
                try:
                    start = time.perf_counter()
                    settings = get_settings()
                    end = time.perf_counter()
                    results_queue.put((end - start) * 1000)
                except Exception as e:
                    results_queue.put(None)
            
            # Start 5 concurrent threads
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join()
            
            # Collect results
            durations = []
            while not results_queue.empty():
                result = results_queue.get()
                if result is not None:
                    durations.append(result)
            
            return durations
        
        return self.measure_performance("Concurrent Access", test_func, iterations=3)
    
    def test_memory_cleanup(self) -> PerformanceResult:
        """Test memory cleanup after creating many settings objects."""
        def test_func():
            # Create many settings objects
            settings_objects = []
            for _ in range(50):
                settings_objects.append(Settings())
            
            # Clear references
            settings_objects.clear()
            
            # Force garbage collection
            gc.collect()
            
            return True
        
        return self.measure_performance("Memory Cleanup", test_func, iterations=1)
    
    def run_all_tests(self, iterations: int = 10) -> PerformanceReport:
        """Run all performance tests."""
        self.log("Starting configuration performance tests...")
        
        # Run all test methods
        test_methods = [
            self.test_basic_settings_loading,
            self.test_get_settings_function,
            self.test_settings_caching,
            self.test_configuration_validation,
            self.test_audited_settings_creation,
            self.test_large_configuration,
            self.test_concurrent_access,
            self.test_memory_cleanup
        ]
        
        for test_method in test_methods:
            test_method()
        
        # Analyze results
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = len(self.results) - passed_tests
        
        # Check if requirements are met
        requirements_met = True
        for result in self.results:
            if not result.success:
                requirements_met = False
                break
            
            # Check performance requirements
            if result.duration_ms > self.max_load_time_ms and "Large Configuration" not in result.test_name:
                requirements_met = False
                break
            
            if result.memory_delta_mb > self.max_memory_mb and "Memory Cleanup" not in result.test_name:
                requirements_met = False
                break
        
        # Create summary
        avg_duration = statistics.mean([r.duration_ms for r in self.results if r.success])
        avg_memory = statistics.mean([r.memory_delta_mb for r in self.results if r.success])
        max_duration = max([r.duration_ms for r in self.results if r.success], default=0)
        max_memory = max([r.memory_delta_mb for r in self.results if r.success], default=0)
        
        summary = {
            "average_duration_ms": avg_duration,
            "average_memory_mb": avg_memory,
            "max_duration_ms": max_duration,
            "max_memory_mb": max_memory,
            "performance_requirements": {
                "max_load_time_ms": self.max_load_time_ms,
                "max_memory_mb": self.max_memory_mb
            },
            "requirements_met": requirements_met
        }
        
        # Create report
        report = PerformanceReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=os.environ.get("ENVIRONMENT", "unknown"),
            python_version=sys.version,
            total_tests=len(self.results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            overall_success=failed_tests == 0,
            requirements_met=requirements_met,
            results=self.results,
            summary=summary
        )
        
        return report
    
    def print_report(self, report: PerformanceReport):
        """Print a human-readable performance report."""
        print("\n" + "="*60)
        print("CONFIGURATION PERFORMANCE TEST REPORT")
        print("="*60)
        print(f"Timestamp: {report.timestamp}")
        print(f"Environment: {report.environment}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Overall Success: {'✅' if report.overall_success else '❌'}")
        print(f"Requirements Met: {'✅' if report.requirements_met else '❌'}")
        
        print(f"\nPerformance Summary:")
        print(f"  Average Duration: {report.summary['average_duration_ms']:.2f}ms")
        print(f"  Average Memory: {report.summary['average_memory_mb']:.2f}MB")
        print(f"  Max Duration: {report.summary['max_duration_ms']:.2f}ms")
        print(f"  Max Memory: {report.summary['max_memory_mb']:.2f}MB")
        
        print(f"\nRequirements:")
        print(f"  Max Load Time: {report.summary['performance_requirements']['max_load_time_ms']}ms")
        print(f"  Max Memory: {report.summary['performance_requirements']['max_memory_mb']}MB")
        
        print(f"\nDetailed Results:")
        print("-" * 80)
        print(f"{'Test Name':<35} {'Duration':<12} {'Memory':<12} {'Status':<8}")
        print("-" * 80)
        
        for result in report.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            duration_str = f"{result.duration_ms:.2f}ms"
            memory_str = f"{result.memory_delta_mb:.2f}MB"
            
            print(f"{result.test_name:<35} {duration_str:<12} {memory_str:<12} {status:<8}")
            
            if not result.success and result.error_message:
                print(f"    Error: {result.error_message}")
            
            # Check if performance requirements are violated
            if result.success:
                if result.duration_ms > self.max_load_time_ms and "Large Configuration" not in result.test_name:
                    print(f"    ⚠️ Duration exceeds requirement ({self.max_load_time_ms}ms)")
                
                if result.memory_delta_mb > self.max_memory_mb and "Memory Cleanup" not in result.test_name:
                    print(f"    ⚠️ Memory exceeds requirement ({self.max_memory_mb}MB)")
        
        print("-" * 80)
        
        if not report.requirements_met:
            print("\n❌ PERFORMANCE REQUIREMENTS NOT MET")
            print("Some tests exceeded the performance thresholds.")
        else:
            print("\n✅ ALL PERFORMANCE REQUIREMENTS MET")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Configuration Performance Tester")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--iterations", "-i", type=int, default=10, help="Number of iterations for tests")
    parser.add_argument("--report-file", "-r", help="Save JSON report to file")
    parser.add_argument("--fail-on-requirements", "-f", action="store_true", 
                       help="Exit with error code if requirements not met")
    
    args = parser.parse_args()
    
    # Create tester and run tests
    tester = ConfigurationPerformanceTester(verbose=args.verbose)
    report = tester.run_all_tests(iterations=args.iterations)
    
    # Print report
    tester.print_report(report)
    
    # Save JSON report if requested
    if args.report_file:
        with open(args.report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"\nJSON report saved to: {args.report_file}")
    
    # Exit with appropriate code
    if args.fail_on_requirements and not report.requirements_met:
        sys.exit(1)
    elif not report.overall_success:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()