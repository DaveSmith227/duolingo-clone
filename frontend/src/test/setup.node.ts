/**
 * Test setup for Node environment tests
 * 
 * This setup file is used for tests that don't need DOM APIs,
 * such as configuration and utility tests.
 */

import { vi } from 'vitest'

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
}

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks()
})

// Clean up after tests
afterEach(() => {
  vi.resetModules()
})