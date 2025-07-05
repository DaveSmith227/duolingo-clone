import { render, screen, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useRouter } from 'next/navigation'
import { ProtectedRoute, withAuth, AuthGate, AuthSwitch } from './ProtectedRoute'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn()
}))

// Mock the auth hook
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn()
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>
  }
}))

import { useAuth } from '@/hooks/useAuth'

const mockUseRouter = useRouter as any
const mockUseAuth = useAuth as any
const mockPush = vi.fn()

describe('ProtectedRoute', () => {
  const mockAuth = {
    isInitialized: false,
    isAuthenticated: false,
    isLoading: false,
    user: null,
    hasRole: vi.fn(),
    hasPermission: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseRouter.mockReturnValue({ push: mockPush })
    mockUseAuth.mockReturnValue(mockAuth)
    
    // Mock window.location.pathname
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/protected-page'
      },
      writable: true
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Loading States', () => {
    it('shows loading spinner when auth is not initialized', () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: false
      })

      render(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Loading...')).toBeInTheDocument()
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
    })

    it('shows loading spinner when redirecting', () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: false,
        isLoading: false
      })

      render(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Redirecting...')).toBeInTheDocument()
    })

    it('hides loading spinner when showLoadingSpinner is false', () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: false
      })

      render(
        <ProtectedRoute showLoadingSpinner={false}>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })
  })

  describe('Authentication Guards', () => {
    it('redirects to login when user is not authenticated', async () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: false
      })

      render(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/auth/login?redirect=%2Fprotected-page')
      })
    })

    it('redirects to custom fallback path', async () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: false
      })

      render(
        <ProtectedRoute fallbackPath="/custom-login">
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/custom-login?redirect=%2Fprotected-page')
      })
    })

    it('renders children when user is authenticated', () => {
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true
      })

      render(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Protected Content')).toBeInTheDocument()
      expect(mockPush).not.toHaveBeenCalled()
    })
  })

  describe('Role-Based Access Control', () => {
    it('redirects to unauthorized when user lacks required role', async () => {
      const mockHasRole = vi.fn().mockReturnValue(false)
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true,
        hasRole: mockHasRole
      })

      render(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Content</div>
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(mockHasRole).toHaveBeenCalledWith('admin')
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
    })

    it('renders content when user has required role', () => {
      const mockHasRole = vi.fn().mockReturnValue(true)
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true,
        hasRole: mockHasRole
      })

      render(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Admin Content')).toBeInTheDocument()
      expect(mockPush).not.toHaveBeenCalled()
    })

    it('shows unauthorized message when user lacks role and showUnauthorizedMessage is true', () => {
      const mockHasRole = vi.fn().mockReturnValue(false)
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true,
        hasRole: mockHasRole
      })

      render(
        <ProtectedRoute requiredRole="admin" showUnauthorizedMessage={true}>
          <div>Admin Content</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.getByText("You need the 'admin' role to access this page.")).toBeInTheDocument()
    })
  })

  describe('Permission-Based Access Control', () => {
    it('redirects to unauthorized when user lacks required permission', async () => {
      const mockHasPermission = vi.fn().mockReturnValue(false)
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true,
        hasPermission: mockHasPermission
      })

      render(
        <ProtectedRoute requiredPermission="manage_users">
          <div>User Management</div>
        </ProtectedRoute>
      )

      await waitFor(() => {
        expect(mockHasPermission).toHaveBeenCalledWith('manage_users')
        expect(mockPush).toHaveBeenCalledWith('/unauthorized')
      })
    })

    it('renders content when user has required permission', () => {
      const mockHasPermission = vi.fn().mockReturnValue(true)
      mockUseAuth.mockReturnValue({
        ...mockAuth,
        isInitialized: true,
        isAuthenticated: true,
        hasPermission: mockHasPermission
      })

      render(
        <ProtectedRoute requiredPermission="manage_users">
          <div>User Management</div>
        </ProtectedRoute>
      )

      expect(screen.getByText('User Management')).toBeInTheDocument()
      expect(mockPush).not.toHaveBeenCalled()
    })
  })
})

describe('withAuth HOC', () => {
  const TestComponent = ({ title }: { title: string }) => <div>{title}</div>

  it('wraps component with ProtectedRoute', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true
    })

    const ProtectedComponent = withAuth(TestComponent)

    render(<ProtectedComponent title="Test Content" />)

    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('passes options to ProtectedRoute', async () => {
    const mockHasRole = vi.fn().mockReturnValue(false)
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true,
      hasRole: mockHasRole
    })

    const ProtectedComponent = withAuth(TestComponent, { requiredRole: 'admin' })

    render(<ProtectedComponent title="Admin Content" />)

    await waitFor(() => {
      expect(mockHasRole).toHaveBeenCalledWith('admin')
      expect(mockPush).toHaveBeenCalledWith('/unauthorized')
    })
  })
})

describe('AuthGate', () => {
  it('renders children when authenticated', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true
    })

    render(
      <AuthGate>
        <div>Protected Content</div>
      </AuthGate>
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('renders fallback when not authenticated', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: false
    })

    render(
      <AuthGate fallback={<div>Please log in</div>}>
        <div>Protected Content</div>
      </AuthGate>
    )

    expect(screen.getByText('Please log in')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when requireAuth is false', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: false
    })

    render(
      <AuthGate requireAuth={false}>
        <div>Public Content</div>
      </AuthGate>
    )

    expect(screen.getByText('Public Content')).toBeInTheDocument()
  })

  it('checks role requirements', () => {
    const mockHasRole = vi.fn().mockReturnValue(false)
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true,
      hasRole: mockHasRole
    })

    render(
      <AuthGate requiredRole="admin" fallback={<div>Not admin</div>}>
        <div>Admin Content</div>
      </AuthGate>
    )

    expect(screen.getByText('Not admin')).toBeInTheDocument()
    expect(mockHasRole).toHaveBeenCalledWith('admin')
  })

  it('checks permission requirements', () => {
    const mockHasPermission = vi.fn().mockReturnValue(false)
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true,
      hasPermission: mockHasPermission
    })

    render(
      <AuthGate requiredPermission="write" fallback={<div>No permission</div>}>
        <div>Content</div>
      </AuthGate>
    )

    expect(screen.getByText('No permission')).toBeInTheDocument()
    expect(mockHasPermission).toHaveBeenCalledWith('write')
  })

  it('shows loading state when not initialized', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: false
    })

    render(
      <AuthGate>
        <div>Protected Content</div>
      </AuthGate>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('hides loading when showLoading is false', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: false
    })

    render(
      <AuthGate showLoading={false}>
        <div>Protected Content</div>
      </AuthGate>
    )

    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })
})

describe('AuthSwitch', () => {
  it('renders authenticated content when user is authenticated', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true
    })

    render(
      <AuthSwitch
        authenticated={<div>Authenticated</div>}
        unauthenticated={<div>Unauthenticated</div>}
      />
    )

    expect(screen.getByText('Authenticated')).toBeInTheDocument()
    expect(screen.queryByText('Unauthenticated')).not.toBeInTheDocument()
  })

  it('renders unauthenticated content when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: false
    })

    render(
      <AuthSwitch
        authenticated={<div>Authenticated</div>}
        unauthenticated={<div>Unauthenticated</div>}
      />
    )

    expect(screen.getByText('Unauthenticated')).toBeInTheDocument()
    expect(screen.queryByText('Authenticated')).not.toBeInTheDocument()
  })

  it('renders loading content when not initialized', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: false
    })

    render(
      <AuthSwitch
        authenticated={<div>Authenticated</div>}
        unauthenticated={<div>Unauthenticated</div>}
        loading={<div>Loading auth...</div>}
      />
    )

    expect(screen.getByText('Loading auth...')).toBeInTheDocument()
  })

  it('renders unauthorized content when user lacks role', () => {
    const mockHasRole = vi.fn().mockReturnValue(false)
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true,
      hasRole: mockHasRole
    })

    render(
      <AuthSwitch
        authenticated={<div>Authenticated</div>}
        unauthorized={<div>Unauthorized</div>}
        hasRole="admin"
      />
    )

    expect(screen.getByText('Unauthorized')).toBeInTheDocument()
    expect(mockHasRole).toHaveBeenCalledWith('admin')
  })

  it('renders unauthorized content when user lacks permission', () => {
    const mockHasPermission = vi.fn().mockReturnValue(false)
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: true,
      hasPermission: mockHasPermission
    })

    render(
      <AuthSwitch
        authenticated={<div>Authenticated</div>}
        unauthorized={<div>Unauthorized</div>}
        hasPermission="write"
      />
    )

    expect(screen.getByText('Unauthorized')).toBeInTheDocument()
    expect(mockHasPermission).toHaveBeenCalledWith('write')
  })

  it('renders children as fallback', () => {
    mockUseAuth.mockReturnValue({
      ...mockAuth,
      isInitialized: true,
      isAuthenticated: false
    })

    render(
      <AuthSwitch>
        <div>Default Content</div>
      </AuthSwitch>
    )

    expect(screen.getByText('Default Content')).toBeInTheDocument()
  })
})