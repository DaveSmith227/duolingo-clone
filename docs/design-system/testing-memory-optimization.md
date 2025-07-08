# Testing Memory Optimization Guide

## Problem Summary

We were experiencing "JavaScript heap out of memory" errors across our test suite due to:

1. **Happy-DOM Memory Leaks**: Known issue where happy-dom causes memory errors with large test suites
2. **DOM Not Reset**: Vitest doesn't reset DOM between tests, causing memory accumulation
3. **Excessive DOM Usage**: Using DOM environment for tests that don't need it
4. **No Memory Limits**: Tests running without memory constraints

## Solution Architecture

### 1. Separated Test Configurations

We've created specialized Vitest configurations for different test types:

- **`vitest.config.unit.ts`**: For unit tests (lib, stores, utils) using Node environment
- **`vitest.config.dom.ts`**: For DOM tests (components, hooks) using jsdom
- **`vitest.config.design-system.ts`**: For design system tests with extreme memory optimization
- **`vitest.config.integration.ts`**: For integration tests with single-fork execution

### 2. Memory Management Strategies

#### vmThreads Pool with Memory Limits
```javascript
pool: 'vmThreads',
poolOptions: {
  vmThreads: {
    memoryLimit: '512MB', // Limit per worker
    singleThread: true    // Reduce overhead
  }
}
```

#### Single Fork Execution
```javascript
pool: 'forks',
poolOptions: {
  forks: {
    singleFork: true,
    maxForks: 1
  }
}
```

#### Garbage Collection
```bash
node --expose-gc --max-old-space-size=512 ./node_modules/.bin/vitest
```

### 3. Environment Optimization

- **Node Environment**: Default for all non-DOM tests (much lighter)
- **jsdom**: Only for component tests (more stable than happy-dom)
- **No happy-dom**: Removed due to memory leak issues

### 4. Test Scripts

```json
{
  "test": "vitest",
  "test:unit": "vitest run -c vitest.config.unit.ts",
  "test:dom": "vitest run -c vitest.config.dom.ts",
  "test:design": "node --expose-gc --max-old-space-size=512 ./node_modules/.bin/vitest run -c vitest.config.design-system.ts",
  "test:memory": "DEBUG_MEMORY=true npm run test:design"
}
```

## Usage Guidelines

### Running Tests

1. **Unit Tests** (fastest, parallel execution):
   ```bash
   npm run test:unit
   ```

2. **DOM Tests** (slower, sequential):
   ```bash
   npm run test:dom
   ```

3. **Design System Tests** (memory-optimized):
   ```bash
   npm run test:design
   ```

4. **With Memory Debugging**:
   ```bash
   npm run test:memory
   ```

### Writing Tests

1. **Choose the Right Environment**:
   - Use Node environment for logic/utility tests
   - Only use DOM environment when testing actual DOM interactions

2. **Clean Up Resources**:
   ```javascript
   afterEach(() => {
     // Clear timers
     vi.clearAllTimers();
     // Clear mocks
     vi.clearAllMocks();
     // Reset modules
     vi.resetModules();
   });
   ```

3. **Monitor Memory Usage**:
   ```javascript
   const memory = testUtils.getMemoryUsage();
   console.log(`Heap used: ${memory.heapUsedMB}MB`);
   ```

## Troubleshooting

### Still Getting Memory Errors?

1. **Check Test Isolation**:
   - Ensure tests clean up after themselves
   - Look for global state mutations
   - Check for event listener leaks

2. **Reduce Test File Size**:
   - Split large test files
   - Move integration tests to separate files
   - Use `describe.skip` for problematic suites

3. **Use Memory Profiling**:
   ```bash
   node --inspect-brk ./node_modules/.bin/vitest run
   ```
   Then connect Chrome DevTools to profile memory usage.

4. **Adjust Memory Limits**:
   - Increase `memoryLimit` in vmThreads config
   - Increase `--max-old-space-size` for specific test runs

## Performance Tips

1. **Parallel vs Sequential**:
   - Unit tests: Run in parallel (faster)
   - DOM tests: Run sequentially (more stable)
   - Large suites: Use single fork (less memory)

2. **Coverage**:
   - Disable by default (saves ~30% memory)
   - Enable only for CI or specific runs

3. **Test Organization**:
   - Keep test files focused and small
   - Separate unit and integration tests
   - Use proper test categorization

## Configuration Reference

### Base Configuration Options
```javascript
{
  pool: 'vmThreads' | 'threads' | 'forks',
  poolOptions: {
    vmThreads: {
      memoryLimit: string | number, // e.g., '512MB' or 0.5
      singleThread: boolean
    }
  },
  logHeapUsage: boolean,    // Show memory after each test
  isolate: boolean,         // Isolate test files
  maxConcurrency: number,   // Max parallel tests
  fileParallelism: boolean  // Run files in parallel
}
```

### Environment Variables
- `DEBUG_MEMORY=true`: Enable memory logging
- `NODE_OPTIONS='--max-old-space-size=512'`: Set Node heap size
- `VITEST_MAX_THREADS=4`: Limit thread pool size
- `VITEST_MAX_FORKS=1`: Limit fork pool size

## Resources

- [Vitest Memory Management](https://vitest.dev/guide/improving-performance)
- [Node.js Memory Debugging](https://nodejs.org/en/docs/guides/debugging-getting-started/)
- [JavaScript Heap Profiling](https://developer.chrome.com/docs/devtools/memory-problems/)