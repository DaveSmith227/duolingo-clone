/**
 * Test setup for Node environment tests
 * 
 * This setup file is used for tests that don't need DOM APIs,
 * such as configuration and utility tests.
 * 
 * Includes memory management optimizations to prevent heap overflow.
 */

import { vi } from 'vitest'

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
  // Keep log, debug, and info for debugging
  log: console.log,
  debug: console.debug,
  info: console.info
}

// Force garbage collection after each test if available
if (typeof global !== 'undefined' && global.gc) {
  afterEach(() => {
    global.gc()
  })
}

// Log memory usage in debug mode
if (process.env.DEBUG_MEMORY === 'true') {
  const logMemoryUsage = (label: string) => {
    const used = process.memoryUsage()
    console.log(`[Memory ${label}]`, {
      rss: `${Math.round(used.rss / 1024 / 1024)}MB`,
      heapTotal: `${Math.round(used.heapTotal / 1024 / 1024)}MB`,
      heapUsed: `${Math.round(used.heapUsed / 1024 / 1024)}MB`,
      external: `${Math.round(used.external / 1024 / 1024)}MB`
    })
  }

  beforeAll(() => logMemoryUsage('Start'))
  afterAll(() => logMemoryUsage('End'))
}

// Reset mocks between tests
beforeEach(() => {
  vi.clearAllMocks()
})

// Clean up after tests
afterEach(() => {
  vi.resetModules()
  // Clear all timers
  vi.clearAllTimers()
  // Restore all mocks
  vi.restoreAllMocks()
})

// Add global test utilities
declare global {
  var testUtils: {
    nextTick: () => Promise<void>
    wait: (ms: number) => Promise<void>
    getMemoryUsage: () => { heapUsedMB: number; heapTotalMB: number }
  }
}

global.testUtils = {
  nextTick: () => new Promise(resolve => process.nextTick(resolve)),
  wait: (ms: number) => new Promise(resolve => setTimeout(resolve, ms)),
  getMemoryUsage: () => {
    const used = process.memoryUsage()
    return {
      heapUsedMB: Math.round(used.heapUsed / 1024 / 1024),
      heapTotalMB: Math.round(used.heapTotal / 1024 / 1024)
    }
  }
}