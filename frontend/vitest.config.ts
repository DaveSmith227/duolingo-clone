/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

/**
 * Default Vitest configuration
 * 
 * This config is used when running `npm test` without specific config.
 * For better memory management, use specific configs:
 * - npm run test:unit - for unit tests (lib, stores, utils)
 * - npm run test:dom - for component tests
 * - npm run test:design - for design system tests
 */
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    // Default to node environment for better performance
    environment: 'node',
    setupFiles: ['./src/test/setup.node.ts'],
    css: false,
    testTimeout: 10000,
    retry: 0,
    // Use vmThreads with memory limits by default
    pool: 'vmThreads',
    poolOptions: {
      vmThreads: {
        memoryLimit: '512MB',
        singleThread: false,
        maxThreads: 4
      }
    },
    // Log heap usage to detect memory issues
    logHeapUsage: true,
    // Limit concurrency
    maxConcurrency: 8,
    maxWorkers: 2,
    minWorkers: 1,
    // Exclude problematic files by default
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/*.d.ts',
      '**/coverage/**',
      '**/.next/**',
      // Exclude design system tests that need special handling
      'src/lib/design-system/**/*.test.ts'
    ],
    coverage: {
      enabled: false, // Disable by default, enable with --coverage
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
  // Optimize for test environment
  optimizeDeps: {
    exclude: ['@testing-library/react', '@testing-library/dom']
  },
  build: {
    sourcemap: false
  }
})