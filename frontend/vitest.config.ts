/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'
import { loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Only load NEXT_PUBLIC_ and NODE_ENV variables to avoid memory issues
  const env = loadEnv(mode, process.cwd(), 'NEXT_PUBLIC_')
  const filteredEnv = {
    NODE_ENV: process.env.NODE_ENV || 'test',
    ...Object.fromEntries(
      Object.entries(env).filter(([key]) => key.startsWith('NEXT_PUBLIC_'))
    )
  }
  
  return {
  plugins: [react()],
  define: {
    'process.env': filteredEnv
  },
  css: {
    postcss: false
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    testTimeout: 10000,
    retry: 0,
    // Configure jsdom properly for React testing
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
    coverage: {
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
      ],
      thresholds: {
        global: {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src')
    }
  }
  }
})