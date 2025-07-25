/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Only load necessary env vars to prevent memory issues
  const env = loadEnv(mode, process.cwd(), 'NEXT_PUBLIC_')
  const filteredEnv = {
    NODE_ENV: 'test',
    ...Object.fromEntries(
      Object.entries(env).filter(([key]) => key.startsWith('NEXT_PUBLIC_'))
    )
  }
  
  return {
  // Remove react plugin for node tests
  define: {
    'process.env': filteredEnv
  },
  test: {
    globals: true,
    environment: 'node', // Use node environment by default
    environmentMatchGlobs: [
      // Only use jsdom for component tests that need DOM
      ['src/components/**/*.test.{ts,tsx}', 'jsdom'],
      ['src/hooks/**/*.test.{ts,tsx}', 'jsdom'],
      // Use node for utility/store tests
      ['src/lib/**/*.test.ts', 'node'],
      ['src/stores/**/*.test.ts', 'node'],
      ['src/utils/**/*.test.ts', 'node']
    ],
    setupFiles: ['./src/test/setup.node.ts'],
    pool: 'threads',
    poolOptions: {
      threads: {
        minThreads: 1,
        maxThreads: 2, // Limit concurrent threads
        useAtomics: true,
        isolate: true
      }
    },
    isolate: true, // Isolate tests to prevent memory buildup
    testTimeout: 30000,
    hookTimeout: 30000,
    teardownTimeout: 10000,
    // Disable coverage temporarily to reduce memory usage
    coverage: {
      enabled: false
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  }
  }
})