/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'node', // Use node environment for extractor tests
    setupFiles: [],
    css: false,
    include: ['src/lib/design-system/extractor/**/*.test.ts'],
    testTimeout: 10000,
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
        maxForks: 1,
        isolate: true
      }
    },
    maxWorkers: 1,
    minWorkers: 1,
    // Disable coverage for this config to reduce memory usage
    coverage: {
      enabled: false
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  },
  optimizeDeps: {
    exclude: ['vitest', '@vitest/ui', '@vitest/coverage-v8']
  }
})