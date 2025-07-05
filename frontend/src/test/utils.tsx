import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { vi } from 'vitest'

// Mock framer-motion to avoid whileHover/whileTap prop warnings
vi.mock('framer-motion', () => ({
  motion: {
    div: React.forwardRef<HTMLDivElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <div ref={ref} {...props}>{children}</div>
    )),
    button: React.forwardRef<HTMLButtonElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <button ref={ref} {...props}>{children}</button>
    )),
    form: React.forwardRef<HTMLFormElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <form ref={ref} {...props}>{children}</form>
    )),
    h1: React.forwardRef<HTMLHeadingElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <h1 ref={ref} {...props}>{children}</h1>
    )),
    h2: React.forwardRef<HTMLHeadingElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <h2 ref={ref} {...props}>{children}</h2>
    )),
    p: React.forwardRef<HTMLParagraphElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <p ref={ref} {...props}>{children}</p>
    )),
    span: React.forwardRef<HTMLSpanElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <span ref={ref} {...props}>{children}</span>
    )),
    label: React.forwardRef<HTMLLabelElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <label ref={ref} {...props}>{children}</label>
    )),
    input: React.forwardRef<HTMLInputElement, any>(({ whileHover, whileTap, ...props }, ref) => (
      <input ref={ref} {...props} />
    )),
    textarea: React.forwardRef<HTMLTextAreaElement, any>(({ whileHover, whileTap, ...props }, ref) => (
      <textarea ref={ref} {...props} />
    )),
    select: React.forwardRef<HTMLSelectElement, any>(({ whileHover, whileTap, children, ...props }, ref) => (
      <select ref={ref} {...props}>{children}</select>
    )),
    li: React.forwardRef<HTMLLIElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <li ref={ref} {...props}>{children}</li>
    )),
    ul: React.forwardRef<HTMLUListElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <ul ref={ref} {...props}>{children}</ul>
    )),
    nav: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <nav ref={ref} {...props}>{children}</nav>
    )),
    a: React.forwardRef<HTMLAnchorElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <a ref={ref} {...props}>{children}</a>
    )),
    img: React.forwardRef<HTMLImageElement, any>(({ whileHover, whileTap, ...props }, ref) => (
      <img ref={ref} {...props} />
    )),
    section: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <section ref={ref} {...props}>{children}</section>
    )),
    article: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <article ref={ref} {...props}>{children}</article>
    )),
    header: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <header ref={ref} {...props}>{children}</header>
    )),
    footer: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <footer ref={ref} {...props}>{children}</footer>
    )),
    main: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <main ref={ref} {...props}>{children}</main>
    )),
    aside: React.forwardRef<HTMLElement, any>(({ children, whileHover, whileTap, ...props }, ref) => (
      <aside ref={ref} {...props}>{children}</aside>
    ))
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAnimation: () => ({
    start: vi.fn(),
    stop: vi.fn(),
    set: vi.fn()
  }),
  useInView: () => false,
  useMotionValue: (initial: any) => ({ get: () => initial, set: vi.fn() }),
  useSpring: (initial: any) => ({ get: () => initial, set: vi.fn() }),
  useTransform: () => ({ get: () => 0, set: vi.fn() })
}))

// Test user data
export const createMockUser = (overrides = {}) => ({
  id: 'user-123',
  email: 'test@example.com',
  firstName: 'Test',
  lastName: 'User',
  role: 'user',
  isEmailVerified: true,
  aud: 'authenticated',
  app_metadata: {},
  user_metadata: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  ...overrides
})

export const createMockAdminUser = (overrides = {}) => ({
  ...createMockUser(),
  id: 'admin-123',
  email: 'admin@example.com',
  firstName: 'Admin',
  lastName: 'User',
  role: 'admin',
  ...overrides
})

// Mock auth state
export const createMockAuthState = (overrides = {}) => ({
  user: null,
  session: null,
  isLoading: false,
  isInitialized: true,
  error: null,
  isAuthenticated: false,
  signIn: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  setError: vi.fn(),
  updateUserProfile: vi.fn(),
  hasRole: vi.fn(),
  hasPermission: vi.fn(),
  initialize: vi.fn(),
  clearError: vi.fn(),
  isEmailVerified: vi.fn(),
  getUserInitials: vi.fn(),
  getUserDisplayName: vi.fn(),
  needsOnboarding: vi.fn(),
  store: {},
  ...overrides
})

// Mock fetch responses
export const createMockResponse = (data: any, ok = true) => ({
  ok,
  json: vi.fn().mockResolvedValue(data),
  blob: vi.fn().mockResolvedValue(new Blob([JSON.stringify(data)], { type: 'application/json' })),
  text: vi.fn().mockResolvedValue(JSON.stringify(data)),
  status: ok ? 200 : 400,
  statusText: ok ? 'OK' : 'Bad Request'
})

// Setup mock fetch with common responses
export const setupMockFetch = () => {
  const mockFetch = vi.fn()
  global.fetch = mockFetch

  // Default successful response
  mockFetch.mockResolvedValue(createMockResponse({ success: true }))

  return mockFetch
}

// Mock user search response
export const createMockUserSearchResponse = (users: any[] = [], overrides = {}) => ({
  users,
  total_count: users.length,
  page: 1,
  page_size: 20,
  total_pages: Math.ceil(users.length / 20),
  has_next: false,
  has_previous: false,
  ...overrides
})

// Mock audit log response  
export const createMockAuditLogResponse = (logs: any[] = [], overrides = {}) => ({
  logs,
  total_count: logs.length,
  page: 1,
  page_size: 50,
  total_pages: Math.ceil(logs.length / 50),
  has_next: false,
  has_previous: false,
  ...overrides
})

// Mock audit log entry
export const createMockAuditLogEntry = (overrides = {}) => ({
  id: 'log-123',
  event_type: 'login',
  user_id: 'user-123',
  user_email: 'test@example.com',
  success: true,
  ip_address: '192.168.1.1',
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
  details: { login_method: 'email' },
  created_at: '2024-01-01T10:00:00Z',
  ...overrides
})

// Provider wrapper for tests that need auth context
interface TestProviderProps {
  children: React.ReactNode
  authState?: any
}

export const TestProvider: React.FC<TestProviderProps> = ({ 
  children, 
  authState = createMockAuthState() 
}) => {
  // Mock the useAuth hook for components that use it
  const mockUseAuth = vi.fn().mockReturnValue(authState)
  
  // You can add other providers here if needed (Router, etc.)
  return <>{children}</>
}

// Custom render function that includes common providers
export const renderWithProviders = (
  ui: React.ReactElement,
  {
    authState = createMockAuthState(),
    ...renderOptions
  }: { authState?: any } & Omit<RenderOptions, 'wrapper'> = {}
) => {
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <TestProvider authState={authState}>
      {children}
    </TestProvider>
  )

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Custom renderHook function that fixes DOM container issues
export const renderHookWithProviders = <T,>(
  hook: () => T,
  {
    authState = createMockAuthState(),
    ...renderOptions
  }: { authState?: any } & Omit<RenderOptions, 'wrapper'> = {}
) => {
  // Import renderHook dynamically to ensure proper DOM setup
  const { renderHook } = require('@testing-library/react')
  
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <TestProvider authState={authState}>
      {children}
    </TestProvider>
  )

  return renderHook(hook, { wrapper: Wrapper, ...renderOptions })
}

// Utility to wait for async operations in tests
export const waitForOperation = (ms = 0) => 
  new Promise(resolve => setTimeout(resolve, ms))

// Helper to create mock event handlers
export const createMockEventHandlers = () => ({
  onClick: vi.fn(),
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  onFocus: vi.fn(),
  onBlur: vi.fn(),
  onKeyDown: vi.fn(),
  onKeyUp: vi.fn(),
  onMouseEnter: vi.fn(),
  onMouseLeave: vi.fn()
})

// Helper to simulate user input
export const simulateUserInput = async (element: HTMLElement, value: string) => {
  const { fireEvent } = await import('@testing-library/react')
  
  // Clear existing value
  fireEvent.change(element, { target: { value: '' } })
  
  // Type new value
  fireEvent.change(element, { target: { value } })
  
  // Trigger blur to simulate user finishing input
  fireEvent.blur(element)
}

// Helper to simulate form submission
export const simulateFormSubmission = async (form: HTMLElement, data: Record<string, string> = {}) => {
  const { fireEvent } = await import('@testing-library/react')
  
  // Fill form fields
  for (const [name, value] of Object.entries(data)) {
    const field = form.querySelector(`[name="${name}"]`) as HTMLInputElement
    if (field) {
      await simulateUserInput(field, value)
    }
  }
  
  // Submit form
  fireEvent.submit(form)
}

// Helper to create mock timers
export const createMockTimers = () => {
  vi.useFakeTimers()
  
  return {
    advanceTime: (ms: number) => vi.advanceTimersByTime(ms),
    runAllTimers: () => vi.runAllTimers(),
    runOnlyPendingTimers: () => vi.runOnlyPendingTimers(),
    cleanup: () => vi.useRealTimers()
  }
}

// Helper for testing async components
export const testAsyncComponent = async (componentTest: () => Promise<void>) => {
  try {
    await componentTest()
  } catch (error) {
    // Re-throw with additional context
    throw new Error(`Async component test failed: ${error}`)
  }
}

// Helper to mock window.location
export const mockLocation = (url: string = 'http://localhost:3000/') => {
  const location = new URL(url)
  Object.defineProperty(window, 'location', {
    value: {
      href: location.href,
      origin: location.origin,
      protocol: location.protocol,
      host: location.host,
      hostname: location.hostname,
      port: location.port,
      pathname: location.pathname,
      search: location.search,
      hash: location.hash,
      assign: vi.fn(),
      replace: vi.fn(),
      reload: vi.fn()
    },
    writable: true
  })
  
  return window.location
}

// Helper to clean up after tests
export const cleanupTest = () => {
  vi.clearAllMocks()
  vi.clearAllTimers()
  vi.useRealTimers()
  
  // Reset any global state if needed
  if (global.fetch) {
    vi.mocked(global.fetch).mockClear()
  }
}

// Export everything
export * from '@testing-library/react'
export { vi, expect } from 'vitest'