import { useEffect, useCallback } from 'react'
import { useAuthStore, useAuth as useAuthStoreHook } from '@/stores/authStore'

/**
 * Enhanced authentication hook with additional utilities
 * Built on top of the Zustand auth store
 */
export function useAuth() {
  const auth = useAuthStoreHook()

  // Initialize auth on first load
  useEffect(() => {
    if (!auth.isInitialized) {
      auth.initialize()
    }
  }, [auth])

  // Enhanced sign in with better error handling
  const signIn = useCallback(async (email: string, password: string, rememberMe = false) => {
    try {
      await auth.signIn(email, password, rememberMe)
      return { success: true, error: null }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sign in failed'
      return { success: false, error: errorMessage }
    }
  }, [auth])

  // Enhanced sign up with better error handling
  const signUp = useCallback(async (email: string, password: string, firstName: string, metadata?: Record<string, unknown>) => {
    try {
      await auth.signUp(email, password, firstName, metadata)
      return { success: true, error: null }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sign up failed'
      return { success: false, error: errorMessage }
    }
  }, [auth])

  // Enhanced sign out with better error handling
  const signOut = useCallback(async () => {
    try {
      await auth.signOut()
      return { success: true, error: null }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sign out failed'
      return { success: false, error: errorMessage }
    }
  }, [auth])

  // Clear error helper
  const clearError = useCallback(() => {
    auth.setError(null)
  }, [auth])

  // Check if user has specific permissions
  const hasPermission = useCallback((permission: string) => {
    if (!auth.user) return false
    
    // Basic role-based permissions
    const rolePermissions: Record<string, string[]> = {
      admin: ['read', 'write', 'delete', 'manage_users', 'manage_content'],
      moderator: ['read', 'write', 'manage_content'],
      instructor: ['read', 'write', 'manage_lessons'],
      user: ['read', 'write_own']
    }

    const userRole = auth.user.role || 'user'
    const permissions = rolePermissions[userRole] || []
    
    return permissions.includes(permission)
  }, [auth])

  // Check if user email is verified
  const isEmailVerified = useCallback(() => {
    return auth.user?.isEmailVerified || false
  }, [auth])

  // Get user initials for avatar
  const getUserInitials = useCallback(() => {
    if (!auth.user) return ''
    
    const firstName = auth.user.firstName || ''
    const lastName = auth.user.lastName || ''
    
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase()
    } else if (firstName) {
      return firstName[0].toUpperCase()
    } else if (auth.user.email) {
      return auth.user.email[0].toUpperCase()
    }
    
    return ''
  }, [auth])

  // Get user display name
  const getUserDisplayName = useCallback(() => {
    if (!auth.user) return ''
    
    if (auth.user.firstName && auth.user.lastName) {
      return `${auth.user.firstName} ${auth.user.lastName}`
    } else if (auth.user.firstName) {
      return auth.user.firstName
    } else if (auth.user.email) {
      return auth.user.email.split('@')[0]
    }
    
    return 'User'
  }, [auth])

  // Check if user needs to complete onboarding
  const needsOnboarding = useCallback(() => {
    if (!auth.user) return false
    
    // Add your onboarding logic here
    // For example, check if user has completed profile setup
    return !auth.user.firstName || !auth.isEmailVerified()
  }, [auth, isEmailVerified])

  return {
    // Core auth state
    user: auth.user,
    session: auth.session,
    isLoading: auth.isLoading,
    isInitialized: auth.isInitialized,
    error: auth.error,
    isAuthenticated: auth.isAuthenticated,

    // Enhanced auth methods
    signIn,
    signUp,
    signOut,
    clearError,
    updateUserProfile: auth.updateUserProfile,

    // Utility methods
    hasRole: auth.hasRole,
    hasPermission,
    isEmailVerified,
    getUserInitials,
    getUserDisplayName,
    needsOnboarding,

    // Direct store access for advanced use cases
    store: auth
  }
}

/**
 * Hook for requiring authentication
 * Throws error if user is not authenticated
 */
export function useRequireAuth() {
  const auth = useAuth()

  useEffect(() => {
    if (auth.isInitialized && !auth.isAuthenticated) {
      throw new Error('Authentication required')
    }
  }, [auth])

  return auth
}

/**
 * Hook for checking specific role requirements
 */
export function useRequireRole(requiredRole: string) {
  const auth = useAuth()

  useEffect(() => {
    if (auth.isInitialized && (!auth.isAuthenticated || !auth.hasRole(requiredRole))) {
      throw new Error(`Role '${requiredRole}' required`)
    }
  }, [auth, requiredRole])

  return auth
}

/**
 * Hook for checking permission requirements
 */
export function useRequirePermission(permission: string) {
  const auth = useAuth()

  useEffect(() => {
    if (auth.isInitialized && (!auth.isAuthenticated || !auth.hasPermission(permission))) {
      throw new Error(`Permission '${permission}' required`)
    }
  }, [auth, permission])

  return auth
}

/**
 * Hook for getting current user with type safety
 */
export function useCurrentUser() {
  const user = useAuthStore(state => state.user)
  
  if (!user) {
    throw new Error('No authenticated user')
  }
  
  return user
}

/**
 * Hook for auth loading state
 */
export function useAuthLoading() {
  return useAuthStore(state => state.isLoading)
}

/**
 * Hook for auth error state
 */
export function useAuthError() {
  return useAuthStore(state => state.error)
}

/**
 * Hook for authentication status
 */
export function useIsAuthenticated() {
  return useAuthStore(state => state.isAuthenticated())
}

/**
 * Hook for checking if auth is initialized
 */
export function useAuthInitialized() {
  return useAuthStore(state => state.isInitialized)
}