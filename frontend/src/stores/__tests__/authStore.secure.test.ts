import { renderHook, act } from '@testing-library/react'
import { useAuthStore } from '../authStore'

// Mock fetch for API calls
global.fetch = jest.fn()

describe('Secure AuthStore - No JWT Parsing', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Reset store state
    useAuthStore.getState().reset()
  })

  it('should NOT parse JWT tokens for role information', async () => {
    const { result } = renderHook(() => useAuthStore())
    
    // Create a mock JWT token with role in payload
    const mockJWT = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEyMyIsInJvbGUiOiJhZG1pbiJ9.fake'
    
    // Verify the store does NOT have a parseRoleFromToken function
    expect(typeof (result.current as any).parseRoleFromToken).toBe('undefined')
    
    // Verify we cannot decode the JWT in the store
    const storeString = result.current.toString()
    expect(storeString).not.toContain('atob')
    expect(storeString).not.toContain('split(\'.\')')
    expect(storeString).not.toContain('JWT')
  })

  it('should fetch user role from server API', async () => {
    const { result } = renderHook(() => useAuthStore())
    
    // Mock session
    const mockSession = {
      access_token: 'mock-token',
      user: { id: 'user-123' }
    }
    
    // Mock API response with server-provided role
    const mockUserData = {
      id: 'user-123',
      email: 'test@example.com',
      role: 'admin',  // This comes from server, not JWT
      firstName: 'Test',
      lastName: 'User',
      isEmailVerified: true
    }
    
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockUserData
    })
    
    // Set session
    act(() => {
      result.current.setSession(mockSession as any)
    })
    
    // Fetch user details
    await act(async () => {
      await result.current.fetchUserDetails()
    })
    
    // Verify API was called with proper auth
    expect(global.fetch).toHaveBeenCalledWith('/api/auth/me', {
      headers: {
        'Authorization': 'Bearer mock-token',
        'Content-Type': 'application/json'
      }
    })
    
    // Verify role was set from server response
    expect(result.current.user?.role).toBe('admin')
  })

  it('should use hasRole method for authorization checks', () => {
    const { result } = renderHook(() => useAuthStore())
    
    // Set user with role
    act(() => {
      result.current.setUser({
        id: 'user-123',
        email: 'test@example.com',
        role: 'editor'
      } as any)
    })
    
    // Test hasRole method
    expect(result.current.hasRole('editor')).toBe(true)
    expect(result.current.hasRole('admin')).toBe(false)
    expect(result.current.hasRole('user')).toBe(false)
  })

  it('should not store role in persistent storage', () => {
    const { result } = renderHook(() => useAuthStore())
    
    // Mock secureSessionStore
    const mockStorage: { [key: string]: any } = {}
    jest.spyOn(Storage.prototype, 'setItem').mockImplementation((key, value) => {
      mockStorage[key] = value
    })
    
    // Set user with remember me
    act(() => {
      result.current.setRememberMe(true)
      result.current.setUser({
        id: 'user-123',
        email: 'test@example.com',
        role: 'admin',
        firstName: 'Test',
        lastName: 'User'
      } as any)
    })
    
    // Check persisted data
    const persistedData = mockStorage['auth-storage'] 
      ? JSON.parse(mockStorage['auth-storage']) 
      : null
    
    if (persistedData?.state?.user) {
      // Role should NOT be persisted
      expect(persistedData.state.user.role).toBeUndefined()
      // But other user data should be
      expect(persistedData.state.user.email).toBe('test@example.com')
      expect(persistedData.state.user.firstName).toBe('Test')
    }
  })

  it('should handle missing role gracefully', async () => {
    const { result } = renderHook(() => useAuthStore())
    
    // Mock API response without role
    const mockUserData = {
      id: 'user-123',
      email: 'test@example.com',
      // role is missing
      firstName: 'Test',
      lastName: 'User'
    }
    
    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockUserData
    })
    
    // Set session and fetch details
    act(() => {
      result.current.setSession({ access_token: 'mock-token' } as any)
    })
    
    await act(async () => {
      await result.current.fetchUserDetails()
    })
    
    // Should handle missing role
    expect(result.current.user?.role).toBeUndefined()
    expect(result.current.hasRole('user')).toBe(false)
  })
})