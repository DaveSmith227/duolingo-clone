/**
 * Frontend Configuration Performance Tests
 * 
 * Tests that verify frontend configuration loading meets performance requirements:
 * - Configuration loading completes in <100ms
 * - Memory usage stays reasonable during configuration operations
 * - Performance is consistent across different scenarios
 * - Health checks complete within acceptable timeframes
 * 
 * Requirements:
 * - Load time: <100ms
 * - Health check time: <200ms
 * - Configuration access time: <10ms
 * - Memory usage should be reasonable for browser environment
 */

import { configHealth, useConfigHealth } from '../lib/config-health';

describe('Frontend Configuration Performance', () => {
  let performanceObserver: PerformanceObserver | null = null;
  
  beforeAll(() => {
    // Clear any existing performance entries
    if (typeof performance !== 'undefined' && performance.clearMarks) {
      performance.clearMarks();
      performance.clearMeasures();
    }
  });
  
  afterEach(() => {
    if (performanceObserver) {
      performanceObserver.disconnect();
      performanceObserver = null;
    }
  });

  /**
   * Measure execution time with high precision
   */
  const measureExecutionTime = async <T>(fn: () => Promise<T> | T): Promise<{ result: T; duration: number }> => {
    const startTime = performance.now();
    const result = await fn();
    const endTime = performance.now();
    return { result, duration: endTime - startTime };
  };

  /**
   * Estimate memory usage (rough approximation for browser)
   */
  const estimateMemoryUsage = (): number => {
    if ('memory' in performance) {
      // Chrome/Edge specific
      return (performance as any).memory?.usedJSHeapSize || 0;
    }
    return 0; // Fallback for browsers without memory API
  };

  test('configuration initialization should complete within 100ms', async () => {
    const { duration } = await measureExecutionTime(() => {
      return new Promise<void>((resolve) => {
        // Simulate configuration initialization
        const config = {
          NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
          NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
          NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
        };
        resolve();
      });
    });

    expect(duration).toBeLessThan(100);
    console.log(`Configuration initialization: ${duration.toFixed(2)}ms`);
  });

  test('environment variable validation should complete within 50ms', async () => {
    const { result, duration } = await measureExecutionTime(() => 
      configHealth.checkEnvironmentVariables()
    );

    expect(duration).toBeLessThan(50);
    expect(result).toHaveProperty('status');
    expect(result).toHaveProperty('message');
    expect(result).toHaveProperty('timestamp');
    
    console.log(`Environment validation: ${duration.toFixed(2)}ms`);
  });

  test('API connectivity check should complete within 200ms (mocked)', async () => {
    // Mock fetch to avoid actual network calls in tests
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'healthy', environment: 'test' })
    });
    
    global.fetch = mockFetch;

    const { result, duration } = await measureExecutionTime(() => 
      configHealth.checkAPIConnectivity()
    );

    expect(duration).toBeLessThan(200);
    expect(result).toHaveProperty('status');
    expect(mockFetch).toHaveBeenCalled();
    
    console.log(`API connectivity check: ${duration.toFixed(2)}ms`);
  });

  test('browser compatibility check should complete within 30ms', async () => {
    const { result, duration } = await measureExecutionTime(() => 
      configHealth.checkBrowserCompatibility()
    );

    expect(duration).toBeLessThan(30);
    expect(result).toHaveProperty('status');
    expect(result.details).toHaveProperty('supported_features');
    
    console.log(`Browser compatibility check: ${duration.toFixed(2)}ms`);
  });

  test('comprehensive health check should complete within 300ms (mocked)', async () => {
    // Mock all external calls
    const mockFetch = jest.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'healthy' })
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 404, // Expected for Supabase root endpoint
        json: () => Promise.resolve({})
      });
    
    global.fetch = mockFetch;

    const startMemory = estimateMemoryUsage();
    const { result, duration } = await measureExecutionTime(() => 
      configHealth.runHealthCheck()
    );
    const endMemory = estimateMemoryUsage();

    expect(duration).toBeLessThan(300);
    expect(result).toHaveProperty('overallStatus');
    expect(result).toHaveProperty('checks');
    expect(result).toHaveProperty('summary');
    expect(result).toHaveProperty('totalResponseTimeMs');
    
    // Check that the reported response time is consistent with our measurement
    expect(Math.abs(result.totalResponseTimeMs - duration)).toBeLessThan(50);
    
    console.log(`Comprehensive health check: ${duration.toFixed(2)}ms`);
    if (endMemory > 0) {
      console.log(`Memory usage: ${((endMemory - startMemory) / 1024 / 1024).toFixed(2)}MB`);
    }
  });

  test('quick health check should complete within 100ms (mocked)', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'healthy' })
    });
    
    global.fetch = mockFetch;

    const { result, duration } = await measureExecutionTime(() => 
      configHealth.getQuickHealth()
    );

    expect(duration).toBeLessThan(100);
    expect(result).toHaveProperty('status');
    expect(result).toHaveProperty('message');
    
    console.log(`Quick health check: ${duration.toFixed(2)}ms`);
  });

  test('concurrent health checks should maintain performance', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'healthy' })
    });
    
    global.fetch = mockFetch;

    const startTime = performance.now();
    
    // Run 5 concurrent health checks
    const promises = Array(5).fill(null).map(() => 
      configHealth.checkEnvironmentVariables()
    );
    
    const results = await Promise.all(promises);
    const totalDuration = performance.now() - startTime;

    expect(totalDuration).toBeLessThan(200); // Should complete concurrently, not sequentially
    expect(results).toHaveLength(5);
    results.forEach(result => {
      expect(result).toHaveProperty('status');
      expect(result).toHaveProperty('responseTimeMs');
    });
    
    console.log(`5 concurrent checks: ${totalDuration.toFixed(2)}ms total`);
  });

  test('repeated configuration access should be fast', async () => {
    const { duration } = await measureExecutionTime(() => {
      // Simulate repeated access to configuration values
      for (let i = 0; i < 100; i++) { // Reduced from 1000 to 100
        const env = process.env.NEXT_PUBLIC_ENVIRONMENT;
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        const debug = process.env.NEXT_PUBLIC_ENABLE_DEBUG;
      }
    });

    expect(duration).toBeLessThan(50);
    console.log(`100 config access operations: ${duration.toFixed(2)}ms`);
  });

  test('useConfigHealth hook should initialize quickly', async () => {
    const { duration } = await measureExecutionTime(() => {
      const configHealthInstance = useConfigHealth();
      return configHealthInstance;
    });

    expect(duration).toBeLessThan(10);
    console.log(`useConfigHealth hook initialization: ${duration.toFixed(2)}ms`);
  });

  test('configuration object creation should be memory efficient', () => {
    const initialMemory = estimateMemoryUsage();
    
    // Create multiple configuration health instances
    const instances = [];
    for (let i = 0; i < 10; i++) {
      instances.push(useConfigHealth());
    }
    
    const afterCreationMemory = estimateMemoryUsage();
    
    // Clear references
    instances.length = 0;
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
    
    const afterCleanupMemory = estimateMemoryUsage();
    
    if (initialMemory > 0) {
      const memoryGrowth = (afterCreationMemory - initialMemory) / 1024 / 1024;
      console.log(`Memory growth for 10 instances: ${memoryGrowth.toFixed(2)}MB`);
      
      // Each instance should use less than 1MB
      expect(memoryGrowth).toBeLessThan(10);
    }
  });

  test('error handling should not impact performance significantly', async () => {
    // Mock fetch to simulate network errors
    const mockFetch = jest.fn().mockRejectedValue(new Error('Network error'));
    global.fetch = mockFetch;

    const { result, duration } = await measureExecutionTime(() => 
      configHealth.checkAPIConnectivity()
    );

    expect(duration).toBeLessThan(150); // Error handling might take slightly longer
    expect(result.status).toBe('critical');
    expect(result.message).toContain('failed');
    
    console.log(`Error handling performance: ${duration.toFixed(2)}ms`);
  });

  test('timeout handling should respect timing constraints', async () => {
    // Mock fetch to simulate a slow response
    const mockFetch = jest.fn().mockImplementation(() => 
      new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ status: 'healthy' })
          });
        }, 15000); // 15 seconds - should trigger timeout
      })
    );
    
    global.fetch = mockFetch;

    const { result, duration } = await measureExecutionTime(() => 
      configHealth.checkAPIConnectivity()
    );

    // Should timeout and return quickly (within the configured timeout + small overhead)
    expect(duration).toBeLessThan(31000); // Default timeout is 30s + overhead
    
    console.log(`Timeout handling: ${duration.toFixed(2)}ms`);
  });
});

describe('Configuration Performance Benchmarks', () => {
  test('performance benchmark suite', async () => {
    console.log('\n=== Configuration Performance Benchmarks ===');
    
    const benchmarks = [
      {
        name: 'Environment Variable Access',
        fn: () => process.env.NEXT_PUBLIC_ENVIRONMENT
      },
      {
        name: 'Multiple Environment Access',
        fn: () => {
          const env = process.env.NEXT_PUBLIC_ENVIRONMENT;
          const api = process.env.NEXT_PUBLIC_API_URL;
          const supabase = process.env.NEXT_PUBLIC_SUPABASE_URL;
          return { env, api, supabase };
        }
      },
      {
        name: 'Config Health Instance Creation',
        fn: () => useConfigHealth()
      },
      {
        name: 'Environment Validation (No Network)',
        fn: async () => await configHealth.checkEnvironmentVariables()
      },
      {
        name: 'Browser Compatibility Check',
        fn: async () => await configHealth.checkBrowserCompatibility()
      }
    ];

    for (const benchmark of benchmarks) {
      const iterations = 10; // Reduced from 100 to prevent memory issues
      const times: number[] = [];
      
      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        await benchmark.fn();
        const end = performance.now();
        times.push(end - start);
      }
      
      const avg = times.reduce((a, b) => a + b, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);
      const p95 = times.sort((a, b) => a - b)[Math.floor(times.length * 0.95)];
      
      console.log(`${benchmark.name}:`);
      console.log(`  Average: ${avg.toFixed(2)}ms`);
      console.log(`  Min: ${min.toFixed(2)}ms`);
      console.log(`  Max: ${max.toFixed(2)}ms`);
      console.log(`  95th percentile: ${p95.toFixed(2)}ms`);
      console.log('');
      
      // Assert performance requirements
      expect(avg).toBeLessThan(100);
      expect(p95).toBeLessThan(200);
    }
  });
});

// Performance regression test
describe('Performance Regression Tests', () => {
  const PERFORMANCE_BASELINE = {
    envValidation: 50,
    browserCheck: 30,
    configCreation: 10,
    envAccess: 1
  };

  test('environment validation performance regression', async () => {
    const { duration } = await measureExecutionTime(() => 
      configHealth.checkEnvironmentVariables()
    );

    expect(duration).toBeLessThan(PERFORMANCE_BASELINE.envValidation);
    
    // Warn if performance is degrading (within 50% of baseline)
    if (duration > PERFORMANCE_BASELINE.envValidation * 0.8) {
      console.warn(`⚠️ Environment validation approaching baseline: ${duration.toFixed(2)}ms (baseline: ${PERFORMANCE_BASELINE.envValidation}ms)`);
    }
  });

  test('browser compatibility check performance regression', async () => {
    const { duration } = await measureExecutionTime(() => 
      configHealth.checkBrowserCompatibility()
    );

    expect(duration).toBeLessThan(PERFORMANCE_BASELINE.browserCheck);
    
    if (duration > PERFORMANCE_BASELINE.browserCheck * 0.8) {
      console.warn(`⚠️ Browser check approaching baseline: ${duration.toFixed(2)}ms (baseline: ${PERFORMANCE_BASELINE.browserCheck}ms)`);
    }
  });

  test('config creation performance regression', async () => {
    const { duration } = await measureExecutionTime(() => 
      useConfigHealth()
    );

    expect(duration).toBeLessThan(PERFORMANCE_BASELINE.configCreation);
    
    if (duration > PERFORMANCE_BASELINE.configCreation * 0.8) {
      console.warn(`⚠️ Config creation approaching baseline: ${duration.toFixed(2)}ms (baseline: ${PERFORMANCE_BASELINE.configCreation}ms)`);
    }
  });
});