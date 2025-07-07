/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

/**
 * Base Vitest configuration with memory optimizations
 * 
 * Based on research findings:
 * - Happy-DOM has memory leak issues with large test suites
 * - DOM is not reset between tests in Vitest, causing accumulation
 * - Using 'node' environment for non-DOM tests significantly reduces memory usage
 * - vmThreads pool with memory limits provides better control
 */
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    // Use node environment by default for memory efficiency
    environment: 'node',
    setupFiles: ['./src/test/setup.node.ts'],
    css: false,
    testTimeout: 10000,
    retry: 0,
    
    // Use vmThreads pool with memory limit for better memory control
    pool: 'vmThreads',
    poolOptions: {
      vmThreads: {
        // Set memory limit to 512MB per worker
        memoryLimit: '512MB',
        // Use single thread to reduce overhead
        singleThread: true
      }
    },
    
    // Enable heap usage logging for debugging
    logHeapUsage: true,
    
    // Disable isolation for better performance
    isolate: false,
    
    // Limit concurrency to reduce memory pressure
    maxConcurrency: 4,
    maxWorkers: 2,
    minWorkers: 1,
    
    // Disable coverage by default to save memory
    coverage: {
      enabled: false,
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/coverage/**',
        '**/dist/**',
        '**/.next/**'
      ]
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  },
  // Optimize build for test environment
  optimizeDeps: {
    // Exclude large dependencies from pre-bundling
    exclude: ['@testing-library/react', '@testing-library/dom']
  },
  build: {
    // Disable sourcemaps to reduce memory usage
    sourcemap: false
  }
})