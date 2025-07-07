/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vite'
import baseConfig from './vitest.config.base'

/**
 * Vitest configuration for DOM-based tests (components, hooks)
 * 
 * Uses jsdom instead of happy-dom for better stability
 * Runs tests sequentially to prevent memory accumulation
 */
export default mergeConfig(
  baseConfig,
  defineConfig({
    test: {
      name: 'dom',
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: [
        'src/components/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/hooks/**/*.{test,spec}.{js,jsx,ts,tsx}',
        'src/app/**/*.{test,spec}.{js,jsx,ts,tsx}'
      ],
      exclude: [
        '**/node_modules/**',
        '**/dist/**',
        '**/*.d.ts',
        'src/lib/design-system/**'
      ],
      // Use forks pool for DOM tests for better isolation
      pool: 'forks',
      poolOptions: {
        forks: {
          // Run all tests in a single fork to reduce memory overhead
          singleFork: true,
          maxForks: 1
        }
      },
      // Run tests sequentially for DOM tests
      maxConcurrency: 1,
      fileParallelism: false,
      // Increase timeout for DOM tests
      testTimeout: 20000,
      // Environment options for jsdom
      environmentOptions: {
        jsdom: {
          // Limit resources to prevent memory leaks
          resources: 'usable',
          runScripts: 'dangerously',
          pretendToBeVisual: true,
          // Add cleanup between tests
          beforeParse(window: any) {
            // Add cleanup hook
            window._cleanup = () => {
              // Clear all timers
              window.clearTimeout && window.clearTimeout();
              window.clearInterval && window.clearInterval();
              // Clear all event listeners
              if (window.removeEventListener) {
                const events = ['click', 'change', 'input', 'submit', 'focus', 'blur'];
                events.forEach(event => {
                  document.removeEventListener(event, () => {});
                });
              }
            };
          }
        }
      }
    }
  })
)