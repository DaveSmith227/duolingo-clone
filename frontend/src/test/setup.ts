import '@testing-library/jest-dom'
import { vi, afterEach, beforeEach } from 'vitest'
import React from 'react'

// Fix React 18 createRoot issues in tests
if (typeof global.window !== 'undefined') {
  // Ensure document.body exists for React testing
  if (!global.document.body) {
    global.document.body = global.document.createElement('body')
  }
  
  // Ensure proper container for React rendering
  let container = global.document.getElementById('root')
  if (!container) {
    container = global.document.createElement('div')
    container.id = 'root'
    global.document.body.appendChild(container)
  }
}

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock fetch globally with default success response
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: vi.fn().mockResolvedValue({}),
  blob: vi.fn().mockResolvedValue(new Blob()),
  text: vi.fn().mockResolvedValue(''),
  status: 200,
  statusText: 'OK'
})

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock window.location
Object.defineProperty(window, 'location', {
  writable: true,
  value: {
    href: 'http://localhost:3000',
    origin: 'http://localhost:3000',
    protocol: 'http:',
    host: 'localhost:3000',
    hostname: 'localhost',
    port: '3000',
    pathname: '/',
    search: '',
    hash: '',
    assign: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(),
  },
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}
Object.defineProperty(window, 'localStorage', {
  writable: true,
  value: localStorageMock,
})

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}
Object.defineProperty(window, 'sessionStorage', {
  writable: true,
  value: sessionStorageMock,
})

// Mock console methods to avoid noise in tests
const originalConsole = { ...console }
beforeEach(() => {
  // Only suppress expected warnings/logs during tests
  console.warn = vi.fn()
  console.error = vi.fn()
})

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks()
  localStorageMock.clear()
  sessionStorageMock.clear()
  
  // Clean up DOM
  if (typeof global.document !== 'undefined') {
    global.document.body.innerHTML = ''
    
    // Re-create container for next test
    const container = global.document.createElement('div')
    container.id = 'root'
    global.document.body.appendChild(container)
  }
  
  // Restore console
  console.warn = originalConsole.warn
  console.error = originalConsole.error
})

// Mock URL.createObjectURL and revokeObjectURL for file download tests
global.URL.createObjectURL = vi.fn(() => 'mock-blob-url')
global.URL.revokeObjectURL = vi.fn()

// Mock HTMLAnchorElement for download tests
Object.defineProperty(HTMLAnchorElement.prototype, 'click', {
  writable: true,
  value: vi.fn(),
})

// Mock document.createElement for download tests
const originalCreateElement = document.createElement
document.createElement = vi.fn().mockImplementation((tagName: string) => {
  if (tagName === 'a') {
    return {
      href: '',
      download: '',
      click: vi.fn(),
      style: {}
    }
  }
  return originalCreateElement.call(document, tagName)
})

// Mock document.body methods for download tests
document.body.appendChild = vi.fn()
document.body.removeChild = vi.fn()

// Mock framer-motion to avoid animation-related issues in tests
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  return {
    ...actual,
    motion: new Proxy({}, {
      get: (target, prop) => {
        return React.forwardRef((props: any, ref: any) => {
          const { children, whileHover, whileTap, ...restProps } = props
          return React.createElement(prop as string, { ref, ...restProps }, children)
        })
      }
    }),
    AnimatePresence: ({ children }: any) => children,
    useAnimation: () => ({
      start: vi.fn(),
      stop: vi.fn(),
      set: vi.fn()
    }),
    useInView: () => false,
    useMotionValue: (initial: any) => ({ get: () => initial, set: vi.fn() }),
    useSpring: (initial: any) => ({ get: () => initial, set: vi.fn() }),
    useTransform: () => ({ get: () => 0, set: vi.fn() })
  }
})

// Mock environment variables for tests
process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321'
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'

// Mock Supabase
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: {} }, unsubscribe: vi.fn() })),
      updateUser: vi.fn()
    },
    from: vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data: null, error: null }),
      insert: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
      delete: vi.fn().mockReturnThis()
    }))
  }))
}))

// Add React import for framer-motion mock
import React from 'react'