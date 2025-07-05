import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAuthStore, useAuth } from './authStore'

// Mock the auth module
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } }))
    }
  },
  auth: {
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    getSession: vi.fn(),
    refreshSession: vi.fn()
  }
}))

import { auth, supabase } from '@/lib/supabase'

const mockAuth = auth as any
const mockSupabase = supabase as any

describe('AuthStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset store state
    useAuthStore.getState().reset()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  const mockUser = {
    id: '123',
    email: 'test@example.com',
    user_metadata: {
      first_name: 'John',
      last_name: 'Doe',
      role: 'user'
    },
    email_confirmed_at: '2023-01-01T00:00:00Z',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    aud: 'authenticated',
    app_metadata: {}
  }

  const mockSession = {
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    expires_in: 3600,
    expires_at: Date.now() / 1000 + 3600,
    token_type: 'bearer',
    user: mockUser
  }

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const store = useAuthStore.getState()
      
      expect(store.user).toBeNull()
      expect(store.session).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.isInitialized).toBe(false)
      expect(store.error).toBeNull()
      expect(store.rememberMe).toBe(false)
    })

    it('has utility methods available', () => {
      const store = useAuthStore.getState()
      
      expect(typeof store.signIn).toBe('function')
      expect(typeof store.signUp).toBe('function')
      expect(typeof store.signOut).toBe('function')
      expect(typeof store.initialize).toBe('function')
      expect(typeof store.isAuthenticated).toBe('function')
      expect(typeof store.hasRole).toBe('function')
    })
  })

  describe('useAuth Hook', () => {
    it('returns auth state and methods', () => {
      const { result } = renderHook(() => useAuth())
      
      expect(result.current.user).toBeNull()
      expect(result.current.session).toBeNull()
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isAuthenticated).toBe(false)
      expect(typeof result.current.signIn).toBe('function')
      expect(typeof result.current.signUp).toBe('function')
      expect(typeof result.current.signOut).toBe('function')
    })
  })

  describe('Sign In', () => {
    it('signs in successfully', async () => {
      mockAuth.signIn.mockResolvedValue({
        user: mockUser,
        session: mockSession,
        error: null
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.signIn('test@example.com', 'password', true)
      })

      expect(mockAuth.signIn).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
        rememberMe: true
      })

      expect(result.current.user).toEqual(expect.objectContaining({
        id: '123',
        email: 'test@example.com',
        firstName: 'John',
        lastName: 'Doe',
        role: 'user',
        isEmailVerified: true
      }))
      expect(result.current.session).toEqual(mockSession)
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.isLoading).toBe(false)
    })

    it('handles sign in errors', async () => {
      const errorMessage = 'Invalid credentials'
      mockAuth.signIn.mockResolvedValue({
        user: null,
        session: null,
        error: errorMessage
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        try {
          await result.current.signIn('test@example.com', 'wrongpassword')
        } catch (error) {
          expect(error).toBeInstanceOf(Error)
          expect((error as Error).message).toBe(errorMessage)
        }
      })

      expect(result.current.user).toBeNull()
      expect(result.current.session).toBeNull()
      expect(result.current.error).toBe(errorMessage)
      expect(result.current.isLoading).toBe(false)
    })

    it('handles sign in exceptions', async () => {
      mockAuth.signIn.mockRejectedValue(new Error('Network error'))

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        try {
          await result.current.signIn('test@example.com', 'password')
        } catch (error) {
          expect(error).toBeInstanceOf(Error)
          expect((error as Error).message).toBe('Network error')
        }
      })

      expect(result.current.error).toBe('Network error')
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('Sign Up', () => {
    it('signs up successfully', async () => {
      mockAuth.signUp.mockResolvedValue({
        user: mockUser,
        session: mockSession,
        error: null
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.signUp('test@example.com', 'password', 'John')
      })

      expect(mockAuth.signUp).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password',
        firstName: 'John',
        metadata: {
          first_name: 'John'
        }
      })

      expect(result.current.user).toEqual(expect.objectContaining({
        id: '123',
        email: 'test@example.com',
        firstName: 'John',
        role: 'user',
        isEmailVerified: true
      }))
      expect(result.current.session).toEqual(mockSession)
      expect(result.current.isLoading).toBe(false)
    })

    it('handles sign up errors', async () => {
      const errorMessage = 'Email already exists'
      mockAuth.signUp.mockResolvedValue({
        user: null,
        session: null,
        error: errorMessage
      })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        try {
          await result.current.signUp('test@example.com', 'password', 'John')
        } catch (error) {
          expect(error).toBeInstanceOf(Error)
          expect((error as Error).message).toBe(errorMessage)
        }
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('Sign Out', () => {
    beforeEach(async () => {
      // Set up signed in state
      mockAuth.signIn.mockResolvedValue({
        user: mockUser,
        session: mockSession,
        error: null
      })

      const { result } = renderHook(() => useAuth())
      await act(async () => {
        await result.current.signIn('test@example.com', 'password')
      })
    })

    it('signs out successfully', async () => {
      mockAuth.signOut.mockResolvedValue({ error: null })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        await result.current.signOut()
      })

      expect(mockAuth.signOut).toHaveBeenCalled()
      expect(result.current.user).toBeNull()
      expect(result.current.session).toBeNull()
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.isLoading).toBe(false)
    })

    it('handles sign out errors', async () => {
      const errorMessage = 'Sign out failed'
      mockAuth.signOut.mockResolvedValue({ error: errorMessage })

      const { result } = renderHook(() => useAuth())

      await act(async () => {
        try {
          await result.current.signOut()
        } catch (error) {
          expect(error).toBeInstanceOf(Error)
          expect((error as Error).message).toBe(errorMessage)
        }
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.isLoading).toBe(false)
    })
  })

  describe('Session Management', () => {
    it('refreshes session successfully', async () => {
      const updatedUser = { ...mockUser, user_metadata: { ...mockUser.user_metadata, last_name: 'Smith' } }
      const updatedSession = { ...mockSession, user: updatedUser }

      mockAuth.refreshSession.mockResolvedValue({
        user: updatedUser,
        session: updatedSession,
        error: null
      })

      const store = useAuthStore.getState()

      await act(async () => {
        await store.refreshSession()
      })

      expect(store.user?.lastName).toBe('Smith')
      expect(store.session).toEqual(updatedSession)
    })

    it('handles refresh session errors gracefully', async () => {
      mockAuth.refreshSession.mockResolvedValue({
        user: null,
        session: null,
        error: 'Session expired'
      })

      const store = useAuthStore.getState()

      // Set initial state
      store.setUser(mockUser as any)
      store.setSession(mockSession as any)

      await act(async () => {
        await store.refreshSession()
      })

      // Should clear session on refresh failure
      expect(store.user).toBeNull()
      expect(store.session).toBeNull()
    })
  })

  describe('Initialization', () => {
    it('initializes with existing session', async () => {
      mockAuth.getSession.mockResolvedValue({
        session: mockSession,
        error: null
      })

      const store = useAuthStore.getState()

      await act(async () => {
        await store.initialize()
      })

      expect(store.user).toEqual(expect.objectContaining({
        id: '123',
        email: 'test@example.com',
        firstName: 'John'
      }))
      expect(store.session).toEqual(mockSession)
      expect(store.isInitialized).toBe(true)
      expect(store.isLoading).toBe(false)
    })

    it('initializes without session', async () => {
      mockAuth.getSession.mockResolvedValue({
        session: null,
        error: null
      })

      const store = useAuthStore.getState()

      await act(async () => {
        await store.initialize()
      })

      expect(store.user).toBeNull()
      expect(store.session).toBeNull()
      expect(store.isInitialized).toBe(true)
      expect(store.isLoading).toBe(false)
    })

    it('handles initialization errors', async () => {
      mockAuth.getSession.mockResolvedValue({
        session: null,
        error: 'Failed to get session'
      })

      const store = useAuthStore.getState()

      await act(async () => {
        await store.initialize()
      })

      expect(store.isInitialized).toBe(true)
      expect(store.isLoading).toBe(false)
    })

    it('sets up auth state change listener', async () => {
      mockAuth.getSession.mockResolvedValue({ session: null, error: null })

      const store = useAuthStore.getState()

      await act(async () => {
        await store.initialize()
      })

      expect(mockSupabase.auth.onAuthStateChange).toHaveBeenCalled()
    })
  })

  describe('Utility Methods', () => {
    it('isAuthenticated returns correct value', () => {
      const store = useAuthStore.getState()
      
      expect(store.isAuthenticated()).toBe(false)
      
      // Set authenticated state
      store.setUser(mockUser as any)
      store.setSession(mockSession as any)
      
      expect(store.isAuthenticated()).toBe(true)
    })

    it('hasRole returns correct value', () => {
      const store = useAuthStore.getState()
      
      expect(store.hasRole('admin')).toBe(false)
      
      // Set user with role
      const userWithRole = { ...mockUser, user_metadata: { ...mockUser.user_metadata, role: 'admin' } }
      store.setUser(userWithRole as any)
      
      expect(store.hasRole('admin')).toBe(true)
      expect(store.hasRole('user')).toBe(true) // Admin should have user access too
    })

    it('updateUserProfile updates user data', () => {
      const store = useAuthStore.getState()
      
      // Set initial user
      store.setUser(mockUser as any)
      
      // Update profile
      act(() => {
        store.updateUserProfile({ firstName: 'Jane', profilePicture: 'avatar.jpg' })
      })
      
      expect(store.user?.firstName).toBe('Jane')
      expect(store.user?.profilePicture).toBe('avatar.jpg')
    })

    it('reset clears all state', () => {
      const store = useAuthStore.getState()
      
      // Set some state
      store.setUser(mockUser as any)
      store.setSession(mockSession as any)
      store.setError('Some error')
      store.setLoading(true)
      
      // Reset
      act(() => {
        store.reset()
      })
      
      expect(store.user).toBeNull()
      expect(store.session).toBeNull()
      expect(store.error).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.isInitialized).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('sets and clears errors correctly', () => {
      const store = useAuthStore.getState()
      
      // Set error
      act(() => {
        store.setError('Test error')
      })
      
      expect(store.error).toBe('Test error')
      
      // Clear error
      act(() => {
        store.setError(null)
      })
      
      expect(store.error).toBeNull()
    })
  })

  describe('Selectors', () => {
    it('useAuthUser returns user', () => {
      const store = useAuthStore.getState()
      store.setUser(mockUser as any)
      
      const { result } = renderHook(() => useAuthStore(state => state.user))
      
      expect(result.current).toEqual(mockUser)
    })

    it('useAuthSession returns session', () => {
      const store = useAuthStore.getState()
      store.setSession(mockSession as any)
      
      const { result } = renderHook(() => useAuthStore(state => state.session))
      
      expect(result.current).toEqual(mockSession)
    })

    it('useAuthLoading returns loading state', () => {
      const store = useAuthStore.getState()
      store.setLoading(true)
      
      const { result } = renderHook(() => useAuthStore(state => state.isLoading))
      
      expect(result.current).toBe(true)
    })

    it('useIsAuthenticated returns authentication status', () => {
      const store = useAuthStore.getState()
      
      const { result } = renderHook(() => useAuthStore(state => state.isAuthenticated()))
      
      expect(result.current).toBe(false)
      
      // Set authenticated state
      act(() => {
        store.setUser(mockUser as any)
        store.setSession(mockSession as any)
      })
      
      expect(result.current).toBe(true)
    })
  })
})