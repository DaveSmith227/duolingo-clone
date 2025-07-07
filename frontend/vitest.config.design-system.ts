/// <reference types="vitest" />
import { defineConfig } from 'vite'
import path from 'path'

/**
 * Special configuration for design system tests
 * 
 * These tests have been causing memory issues, so we use:
 * - Node environment (no DOM)
 * - Single fork execution
 * - No isolation
 * - No coverage
 * - Memory monitoring
 */
export default defineConfig({
  test: {
    name: 'design-system',
    root: './src/lib/design-system',
    environment: 'node',
    globals: true,
    include: [
      '**/*.test.ts',
      '**/*.test.tsx'
    ],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/*.d.ts',
      'integration.test.ts' // Run integration tests separately
    ],
    // Use forks with extreme memory optimization
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
        maxForks: 1
      }
    },
    // Disable all parallelism
    maxConcurrency: 1,
    fileParallelism: false,
    maxWorkers: 1,
    minWorkers: 1,
    // Disable isolation to reduce memory overhead
    isolate: false,
    // No coverage to save memory
    coverage: {
      enabled: false
    },
    // Log heap usage to monitor memory
    logHeapUsage: true,
    // Increase timeout for complex tests
    testTimeout: 30000,
    // Reporter
    reporters: ['verbose'],
    // Setup files
    setupFiles: []
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  // Disable optimizations that might increase memory
  optimizeDeps: {
    disabled: true
  },
  build: {
    sourcemap: false
  }
})