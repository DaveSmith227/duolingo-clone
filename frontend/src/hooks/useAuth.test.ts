import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'

// Create a mock implementation of the auth store
const mockAuthState = {
  user: null,
  session: null,
  isLoading: false,
  isInitialized: false,
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
  needsOnboarding: vi.fn()
}

// Mock the auth store module
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn(() => mockAuthState),
  useAuth: vi.fn(() => mockAuthState)
}))

describe.skip('useAuth Hook', () => {
  const mockUser = {
    id: '123',
    email: 'test@example.com',
    firstName: 'John',
    lastName: 'Doe',
    role: 'user',
    isEmailVerified: true
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Reset to default state
    Object.assign(mockAuthState, {
      user: null,
      session: null,
      isLoading: false,
      isInitialized: false,
      error: null,
      isAuthenticated: false
    })
    
    // Reset all function mocks
    Object.values(mockAuthState).forEach(value => {
      if (typeof value === 'function') {
        vi.mocked(value).mockReset()
      }
    })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Basic Functionality', () => {
    it('returns auth state and methods', async () => {
      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      expect(result.current.user).toBeNull()
      expect(result.current.session).toBeNull()
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isAuthenticated).toBe(false)
      expect(typeof result.current.signIn).toBe('function')
      expect(typeof result.current.signUp).toBe('function')
      expect(typeof result.current.signOut).toBe('function')
    })

    it('initializes auth when not initialized', async () => {
      const mockInitialize = vi.fn()
      
      // Set state to not initialized
      mockAuthState.isInitialized = false
      mockAuthState.initialize = mockInitialize

      const { useAuth } = await import('./useAuth')
      renderHook(() => useAuth())

      expect(mockInitialize).toHaveBeenCalled()
    })

    it('does not initialize auth when already initialized', async () => {
      const mockInitialize = vi.fn()
      
      // Set state to initialized
      mockAuthState.isInitialized = true
      mockAuthState.initialize = mockInitialize

      const { useAuth } = await import('./useAuth')
      renderHook(() => useAuth())

      expect(mockInitialize).not.toHaveBeenCalled()
    })
  })

  describe('Enhanced Auth Methods', () => {
    it('handles successful sign in', async () => {
      const mockSignIn = vi.fn().mockResolvedValue(undefined)
      
      mockAuthState.signIn = mockSignIn

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      let response
      await act(async () => {
        response = await result.current.signIn('test@example.com', 'password', true)
      })

      expect(response).toEqual({ success: true, error: null })
      expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'password', true)
    })

    it('handles sign in errors', async () => {
      const mockSignIn = vi.fn().mockRejectedValue(new Error('Invalid credentials'))
      
      mockAuthState.signIn = mockSignIn

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      let response
      await act(async () => {
        response = await result.current.signIn('test@example.com', 'wrongpassword')
      })

      expect(response).toEqual({ success: false, error: 'Invalid credentials' })
      expect(mockSignIn).toHaveBeenCalledWith('test@example.com', 'wrongpassword', false)
    })

    it('handles successful sign up', async () => {
      const mockSignUp = vi.fn().mockResolvedValue(undefined)
      
      mockAuthState.signUp = mockSignUp

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      let response
      await act(async () => {
        response = await result.current.signUp('test@example.com', 'password123', 'John', { lastName: 'Doe' })
      })

      expect(response).toEqual({ success: true, error: null })
      expect(mockSignUp).toHaveBeenCalledWith('test@example.com', 'password123', 'John', { lastName: 'Doe' })
    })

    it('handles sign up errors', async () => {
      const mockSignUp = vi.fn().mockRejectedValue(new Error('Email already exists'))
      
      mockAuthState.signUp = mockSignUp

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      let response
      await act(async () => {
        response = await result.current.signUp('test@example.com', 'password123', 'John')
      })

      expect(response).toEqual({ success: false, error: 'Email already exists' })
      expect(mockSignUp).toHaveBeenCalledWith('test@example.com', 'password123', 'John', undefined)
    })

    it('handles successful sign out', async () => {
      const mockSignOut = vi.fn().mockResolvedValue(undefined)
      
      mockAuthState.signOut = mockSignOut

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      let response
      await act(async () => {
        response = await result.current.signOut()
      })

      expect(response).toEqual({ success: true, error: null })
      expect(mockSignOut).toHaveBeenCalled()
    })

    it('clears errors', async () => {
      const mockClearError = vi.fn()
      
      mockAuthState.clearError = mockClearError

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      act(() => {
        result.current.clearError()
      })

      expect(mockClearError).toHaveBeenCalled()
    })
  })

  describe('Utility Methods', () => {
    it('checks permissions correctly', async () => {
      const mockHasPermission = vi.fn().mockReturnValue(true)
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.hasPermission = mockHasPermission

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const hasPermission = result.current.hasPermission('admin.read')

      expect(hasPermission).toBe(true)
      expect(mockHasPermission).toHaveBeenCalledWith('admin.read')
    })

    it('checks user role permissions', async () => {
      const mockHasRole = vi.fn().mockReturnValue(false)
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.hasRole = mockHasRole

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const hasRole = result.current.hasRole('admin')

      expect(hasRole).toBe(false)
      expect(mockHasRole).toHaveBeenCalledWith('admin')
    })

    it('returns false for permissions when user is null', async () => {
      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const hasPermission = result.current.hasPermission('admin.read')
      const hasRole = result.current.hasRole('admin')

      expect(hasPermission).toBe(false)
      expect(hasRole).toBe(false)
    })

    it('checks email verification status', async () => {
      const mockIsEmailVerified = vi.fn().mockReturnValue(true)
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.isEmailVerified = mockIsEmailVerified

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const isVerified = result.current.isEmailVerified()

      expect(isVerified).toBe(true)
      expect(mockIsEmailVerified).toHaveBeenCalled()
    })

    it('returns false for email verification when user is null', async () => {
      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const isVerified = result.current.isEmailVerified()

      expect(isVerified).toBe(false)
    })

    it('gets user initials correctly', async () => {
      const mockGetUserInitials = vi.fn().mockReturnValue('JD')
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserInitials = mockGetUserInitials

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const initials = result.current.getUserInitials()

      expect(initials).toBe('JD')
      expect(mockGetUserInitials).toHaveBeenCalled()
    })

    it('gets user initials from first name only', async () => {
      const mockGetUserInitials = vi.fn().mockReturnValue('J')
      
      mockAuthState.user = { ...mockUser, lastName: '' }
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserInitials = mockGetUserInitials

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const initials = result.current.getUserInitials()

      expect(initials).toBe('J')
      expect(mockGetUserInitials).toHaveBeenCalled()
    })

    it('gets user initials from email when no name', async () => {
      const mockGetUserInitials = vi.fn().mockReturnValue('T')
      
      mockAuthState.user = { ...mockUser, firstName: '', lastName: '' }
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserInitials = mockGetUserInitials

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const initials = result.current.getUserInitials()

      expect(initials).toBe('T')
      expect(mockGetUserInitials).toHaveBeenCalled()
    })

    it('returns empty string for initials when user is null', async () => {
      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const initials = result.current.getUserInitials()

      expect(initials).toBe('')
    })

    it('gets user display name correctly', async () => {
      const mockGetUserDisplayName = vi.fn().mockReturnValue('John Doe')
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserDisplayName = mockGetUserDisplayName

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const displayName = result.current.getUserDisplayName()

      expect(displayName).toBe('John Doe')
      expect(mockGetUserDisplayName).toHaveBeenCalled()
    })

    it('gets display name from first name only', async () => {
      const mockGetUserDisplayName = vi.fn().mockReturnValue('John')
      
      mockAuthState.user = { ...mockUser, lastName: '' }
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserDisplayName = mockGetUserDisplayName

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const displayName = result.current.getUserDisplayName()

      expect(displayName).toBe('John')
      expect(mockGetUserDisplayName).toHaveBeenCalled()
    })

    it('gets display name from email when no name', async () => {
      const mockGetUserDisplayName = vi.fn().mockReturnValue('test@example.com')
      
      mockAuthState.user = { ...mockUser, firstName: '', lastName: '' }
      mockAuthState.isAuthenticated = true
      mockAuthState.getUserDisplayName = mockGetUserDisplayName

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const displayName = result.current.getUserDisplayName()

      expect(displayName).toBe('test@example.com')
      expect(mockGetUserDisplayName).toHaveBeenCalled()
    })

    it('checks onboarding needs correctly', async () => {
      const mockNeedsOnboarding = vi.fn().mockReturnValue(false)
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true
      mockAuthState.needsOnboarding = mockNeedsOnboarding

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const needsOnboarding = result.current.needsOnboarding()

      expect(needsOnboarding).toBe(false)
      expect(mockNeedsOnboarding).toHaveBeenCalled()
    })

    it('returns false for onboarding when user is complete', async () => {
      const completeUser = { ...mockUser, firstName: 'John', lastName: 'Doe' }
      const mockNeedsOnboarding = vi.fn().mockReturnValue(false)
      
      mockAuthState.user = completeUser
      mockAuthState.isAuthenticated = true
      mockAuthState.needsOnboarding = mockNeedsOnboarding

      const { useAuth } = await import('./useAuth')
      const { result } = renderHook(() => useAuth())

      const needsOnboarding = result.current.needsOnboarding()

      expect(needsOnboarding).toBe(false)
      expect(mockNeedsOnboarding).toHaveBeenCalled()
    })
  })

  describe('useRequireAuth', () => {
    it('does not throw when user is authenticated', async () => {
      mockAuthState.isAuthenticated = true
      mockAuthState.isInitialized = true

      const { useRequireAuth } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireAuth())
      }).not.toThrow()
    })

    it('throws when user is not authenticated', async () => {
      mockAuthState.isAuthenticated = false
      mockAuthState.isInitialized = true

      const { useRequireAuth } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireAuth())
      }).toThrow('Authentication required')
    })

    it('does not throw when auth is not initialized yet', async () => {
      mockAuthState.isAuthenticated = false
      mockAuthState.isInitialized = false

      const { useRequireAuth } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireAuth())
      }).not.toThrow()
    })
  })

  describe('useRequireRole', () => {
    it('does not throw when user has required role', async () => {
      const mockHasRole = vi.fn().mockReturnValue(true)
      
      mockAuthState.isAuthenticated = true
      mockAuthState.isInitialized = true
      mockAuthState.hasRole = mockHasRole

      const { useRequireRole } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireRole('admin'))
      }).not.toThrow()
    })

    it('throws when user does not have required role', async () => {
      const mockHasRole = vi.fn().mockReturnValue(false)
      
      mockAuthState.isAuthenticated = true
      mockAuthState.isInitialized = true
      mockAuthState.hasRole = mockHasRole

      const { useRequireRole } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireRole('admin'))
      }).toThrow('Role \'admin\' required')
    })

    it('throws when user is not authenticated', async () => {
      const mockHasRole = vi.fn().mockReturnValue(false)
      
      mockAuthState.isAuthenticated = false
      mockAuthState.isInitialized = true
      mockAuthState.hasRole = mockHasRole

      const { useRequireRole } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useRequireRole('admin'))
      }).toThrow('Role \'admin\' required')
    })
  })

  describe('useCurrentUser', () => {
    it('returns user when authenticated', async () => {
      const { useAuthStore } = await import('@/stores/authStore')
      
      mockAuthState.user = mockUser
      mockAuthState.isAuthenticated = true

      const { useCurrentUser } = await import('./useAuth')
      const { result } = renderHook(() => useCurrentUser())

      expect(result.current).toEqual(mockUser)
    })

    it('throws when no user', async () => {
      const { useAuthStore } = await import('@/stores/authStore')
      
      mockAuthState.user = null
      mockAuthState.isAuthenticated = false

      const { useCurrentUser } = await import('./useAuth')
      
      expect(() => {
        renderHook(() => useCurrentUser())
      }).toThrow('No authenticated user')
    })
  })
})