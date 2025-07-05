import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E Testing Configuration
 * 
 * Comprehensive configuration for end-to-end testing of authentication flows
 * and user journeys in the Duolingo clone application.
 */
export default defineConfig({
  // Test directory and patterns
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  
  // Global test settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30 * 1000, // 30 seconds per test
  expect: {
    timeout: 5 * 1000, // 5 seconds for assertions
  },
  
  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'e2e-results' }],
    ['json', { outputFile: 'e2e-results/results.json' }],
    ['line'],
  ],
  
  // Global setup and teardown
  globalSetup: require.resolve('./e2e/setup/global-setup.ts'),
  globalTeardown: require.resolve('./e2e/setup/global-teardown.ts'),
  
  // Test configuration
  use: {
    // Base URL for tests
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    
    // Browser settings
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    // Viewport and user agent
    viewport: { width: 1280, height: 720 },
    
    // Authentication context
    storageState: './e2e/auth/user.json', // Pre-authenticated state
    
    // Network settings
    ignoreHTTPSErrors: true,
    
    // Timeouts
    actionTimeout: 10 * 1000,
    navigationTimeout: 15 * 1000,
  },
  
  // Project configurations for different browsers and scenarios
  projects: [
    // Setup project - authenticate users
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
      teardown: 'cleanup',
    },
    
    // Cleanup project
    {
      name: 'cleanup',
      testMatch: /.*\.cleanup\.ts/,
    },
    
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },
    
    // Mobile browsers
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },
    
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },
    
    // Authenticated user tests
    {
      name: 'authenticated',
      use: {
        ...devices['Desktop Chrome'],
        storageState: './e2e/auth/authenticated-user.json',
      },
      dependencies: ['setup'],
      testMatch: '**/authenticated/**/*.spec.ts',
    },
    
    // Admin user tests
    {
      name: 'admin',
      use: {
        ...devices['Desktop Chrome'],
        storageState: './e2e/auth/admin-user.json',
      },
      dependencies: ['setup'],
      testMatch: '**/admin/**/*.spec.ts',
    },
    
    // Unauthenticated tests
    {
      name: 'unauthenticated',
      use: {
        ...devices['Desktop Chrome'],
        storageState: { cookies: [], origins: [] }, // No auth state
      },
      testMatch: '**/unauthenticated/**/*.spec.ts',
    },
  ],
  
  // Local dev server
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
  
  // Output directories
  outputDir: 'e2e-results',
})