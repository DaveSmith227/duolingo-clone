/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    name: 'integration',
    root: './src/lib/design-system',
    environment: 'node',
    include: ['**/integration.test.ts'],
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/*.d.ts'
    ],
    globals: true,
    testTimeout: 30000, // 30 seconds for integration tests
    hookTimeout: 15000, // 15 seconds for setup/teardown
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true, // Use single fork for memory efficiency
      }
    },
    logHeapUsage: true,
    reporters: ['verbose'],
    coverage: {
      enabled: false, // Disabled for integration tests to save memory
    },
    // Memory optimization settings
    maxConcurrency: 1, // Run tests sequentially
    fileParallelism: false,
    // Custom test environment
    setupFiles: [],
    // Performance monitoring
    benchmark: {
      include: ['**/*.{bench,benchmark}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
      exclude: ['node_modules', 'dist', '.idea', '.git', '.cache']
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '~': path.resolve(__dirname, './src'),
    },
  },
  esbuild: {
    target: 'node18',
    format: 'esm'
  }
});