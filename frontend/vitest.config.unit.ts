/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vite'
import baseConfig from './vitest.config.base'

/**
 * Vitest configuration for unit tests (lib, stores, utils)
 * 
 * Uses node environment for maximum performance
 * Runs tests in parallel with memory limits
 */
export default mergeConfig(
  baseConfig,
  defineConfig({
    test: {
      name: 'unit',
      environment: 'node',
      include: [
        'src/lib/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/stores/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/utils/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/services/**/*.{test,spec}.{js,jsx,ts,tsx}'
      ],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/*.d.ts',
        'src/lib/design-system/integration.test.ts'
      ],
      // Use vmThreads for better performance with memory limits
      pool: 'vmThreads',
      poolOptions: {
        vmThreads: {
          // Limit memory per worker
          memoryLimit: '256MB',
          // Allow parallel execution within limits
          singleThread: false,
          maxThreads: 4,
          minThreads: 1
        }
      },
      // Allow some parallelism for unit tests
      maxConcurrency: 8,
      fileParallelism: true,
      // Shorter timeout for unit tests
      testTimeout: 5000
    }
  })
)