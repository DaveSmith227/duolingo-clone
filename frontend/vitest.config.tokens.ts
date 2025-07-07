import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node', // Use node environment for lighter memory usage
    globals: true,
    setupFiles: './src/test/setup.node.ts',
    include: [
      'src/lib/design-system/tokens/**/*.test.ts',
      'src/lib/design-system/config/**/*.test.ts',
      'src/lib/design-system/docs/**/*.test.ts'
    ],
    coverage: {
      enabled: false // Disable coverage to reduce memory usage
    },
    maxWorkers: 1,
    minWorkers: 1,
    isolate: false, // Disable test isolation to reduce memory usage
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});