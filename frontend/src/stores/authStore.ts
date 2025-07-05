import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { AuthSession, User } from '@supabase/supabase-js'
import { supabase, auth } from '@/lib/supabase'
import { secureSessionStore, SessionTimeoutManager } from '@/lib/secureStorage'

/**
 * Parse role from JWT token claims
 * This ensures role comes from server-validated token, not client-controlled metadata
 */
function parseRoleFromToken(accessToken: string): string {
  try {
    // JWT structure: header.payload.signature
    const parts = accessToken.split('.')
    if (parts.length !== 3) return 'user'
    
    // Decode base64url payload
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    const claims = JSON.parse(decoded)
    
    // Extract role from token claims (set by backend)
    return claims.role || claims.user_role || 'user'
  } catch (error) {
    console.error('Failed to parse token role:', error)
    return 'user'
  }
}

export interface AuthUser extends User {
  firstName?: string
  lastName?: string
  profilePicture?: string
  role?: string
  isEmailVerified?: boolean
  lastLoginAt?: string
}

export interface AuthState {
  // Core auth state
  user: AuthUser | null
  session: AuthSession | null
  isLoading: boolean
  isInitialized: boolean
  
  // Error state
  error: string | null
  
  // User preferences
  rememberMe: boolean
  
  // Actions
  setUser: (user: AuthUser | null) => void
  setSession: (session: AuthSession | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setRememberMe: (remember: boolean) => void
  
  // Auth methods
  signIn: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  signUp: (email: string, password: string, firstName: string, metadata?: Record<string, unknown>) => Promise<void>
  signOut: () => Promise<void>
  refreshSession: () => Promise<void>
  
  // Utility methods
  initialize: () => Promise<void>
  reset: () => void
  isAuthenticated: () => boolean
  hasRole: (role: string) => boolean
  updateUserProfile: (updates: Partial<AuthUser>) => void
}

const initialState = {
  user: null,
  session: null,
  isLoading: false,
  isInitialized: false,
  error: null,
  rememberMe: false,
}

// Session timeout manager instance
let sessionTimeoutManager: SessionTimeoutManager | null = null

// Custom storage adapter that uses secure session storage
const secureStorage = {
  getItem: (name: string) => {
    const value = secureSessionStore.get(name)
    return value ? JSON.stringify(value) : null
  },
  setItem: (name: string, value: string) => {
    try {
      const parsed = JSON.parse(value)
      // Don't persist sensitive session data
      const { state } = parsed
      if (state?.session) {
        // Only store non-sensitive user info
        const sanitized = {
          ...parsed,
          state: {
            ...state,
            session: null, // Don't persist session
            user: state.user ? {
              id: state.user.id,
              email: state.user.email,
              firstName: state.user.firstName,
              lastName: state.user.lastName,
              role: state.user.role,
              isEmailVerified: state.user.isEmailVerified
            } : null
          }
        }
        secureSessionStore.set(name, sanitized)
      } else {
        secureSessionStore.set(name, parsed)
      }
    } catch (error) {
      console.error('Storage error:', error)
    }
  },
  removeItem: (name: string) => {
    secureSessionStore.delete(name)
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Setters
      setUser: (user) => set({ user }),
      setSession: (session) => set({ session }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setRememberMe: (rememberMe) => set({ rememberMe }),

      // Auth methods
      signIn: async (email: string, password: string, rememberMe = false) => {
        set({ isLoading: true, error: null })
        
        try {
          const { user, session, error } = await auth.signIn({
            email,
            password,
            rememberMe
          })

          if (error) {
            set({ error, isLoading: false })
            throw new Error(error)
          }

          if (user && session) {
            // Role should come from JWT claims, not user metadata
            // The backend should set the role in the token claims
            const tokenRole = session.access_token ? parseRoleFromToken(session.access_token) : 'user'
            
            const authUser: AuthUser = {
              ...user,
              firstName: user.user_metadata?.first_name,
              lastName: user.user_metadata?.last_name,
              profilePicture: user.user_metadata?.avatar_url,
              role: tokenRole, // Use server-validated role from token
              isEmailVerified: user.email_confirmed_at !== null,
              lastLoginAt: new Date().toISOString()
            }

            set({
              user: authUser,
              session,
              isLoading: false,
              error: null,
              rememberMe
            })
            
            // Initialize session timeout (30 min timeout, 5 min warning)
            if (!sessionTimeoutManager) {
              sessionTimeoutManager = new SessionTimeoutManager(
                30, // timeout minutes
                5,  // warning minutes
                async () => {
                  // Session timeout - sign out user
                  console.warn('Session timed out due to inactivity')
                  await get().signOut()
                },
                (remainingTime) => {
                  // Warning callback - could show a warning modal
                  console.warn(`Session will expire in ${Math.ceil(remainingTime / 60000)} minutes`)
                }
              )
            }
            sessionTimeoutManager.start()
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Sign in failed'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      signUp: async (email: string, password: string, firstName: string, metadata = {}) => {
        set({ isLoading: true, error: null })
        
        try {
          const { user, session, error } = await auth.signUp({
            email,
            password,
            firstName,
            metadata: {
              first_name: firstName,
              ...metadata
            }
          })

          if (error) {
            set({ error, isLoading: false })
            throw new Error(error)
          }

          if (user) {
            const authUser: AuthUser = {
              ...user,
              firstName,
              role: 'user',
              isEmailVerified: user.email_confirmed_at !== null
            }

            set({
              user: authUser,
              session,
              isLoading: false,
              error: null
            })
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Sign up failed'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      signOut: async () => {
        set({ isLoading: true, error: null })
        
        try {
          const { error } = await auth.signOut()
          
          if (error) {
            set({ error, isLoading: false })
            throw new Error(error)
          }

          // Stop session timeout
          if (sessionTimeoutManager) {
            sessionTimeoutManager.stop()
            sessionTimeoutManager = null
          }
          
          // Clear all auth state
          set({
            user: null,
            session: null,
            isLoading: false,
            error: null,
            rememberMe: false
          })
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Sign out failed'
          set({ error: errorMessage, isLoading: false })
          throw error
        }
      },

      refreshSession: async () => {
        try {
          const { session, user, error } = await auth.refreshSession()
          
          if (error) {
            console.warn('Session refresh failed:', error)
            // Don't throw error for refresh failures, just clear session
            set({ user: null, session: null })
            return
          }

          if (user && session) {
            const authUser: AuthUser = {
              ...user,
              firstName: user.user_metadata?.first_name,
              lastName: user.user_metadata?.last_name,
              profilePicture: user.user_metadata?.avatar_url,
              role: session ? parseRoleFromToken(session.access_token) : 'user',
              isEmailVerified: user.email_confirmed_at !== null
            }

            set({ user: authUser, session })
          }
        } catch (error) {
          console.warn('Session refresh error:', error)
          set({ user: null, session: null })
        }
      },

      // Initialization
      initialize: async () => {
        if (get().isInitialized) return

        set({ isLoading: true })

        try {
          // Get current session
          const { session, error } = await auth.getSession()
          
          if (error) {
            console.warn('Failed to get session:', error)
            set({ isLoading: false, isInitialized: true })
            return
          }

          if (session?.user) {
            const authUser: AuthUser = {
              ...session.user,
              firstName: session.user.user_metadata?.first_name,
              lastName: session.user.user_metadata?.last_name,
              profilePicture: session.user.user_metadata?.avatar_url,
              role: parseRoleFromToken(session.access_token),
              isEmailVerified: session.user.email_confirmed_at !== null
            }

            set({
              user: authUser,
              session,
              isLoading: false,
              isInitialized: true
            })
          } else {
            set({
              user: null,
              session: null,
              isLoading: false,
              isInitialized: true
            })
          }

          // Set up auth state change listener
          supabase.auth.onAuthStateChange(async (event, session) => {
            console.log('Auth state changed:', event, session?.user?.id)

            if (event === 'SIGNED_IN' && session?.user) {
              const authUser: AuthUser = {
                ...session.user,
                firstName: session.user.user_metadata?.first_name,
                lastName: session.user.user_metadata?.last_name,
                profilePicture: session.user.user_metadata?.avatar_url,
                role: parseRoleFromToken(session.access_token),
                isEmailVerified: session.user.email_confirmed_at !== null
              }

              set({ user: authUser, session, error: null })
            } else if (event === 'SIGNED_OUT') {
              set({ user: null, session: null, error: null })
            } else if (event === 'TOKEN_REFRESHED' && session?.user) {
              const authUser: AuthUser = {
                ...session.user,
                firstName: session.user.user_metadata?.first_name,
                lastName: session.user.user_metadata?.last_name,
                profilePicture: session.user.user_metadata?.avatar_url,
                role: parseRoleFromToken(session.access_token),
                isEmailVerified: session.user.email_confirmed_at !== null
              }

              set({ user: authUser, session })
            } else if (event === 'USER_UPDATED' && session?.user) {
              const authUser: AuthUser = {
                ...session.user,
                firstName: session.user.user_metadata?.first_name,
                lastName: session.user.user_metadata?.last_name,
                profilePicture: session.user.user_metadata?.avatar_url,
                role: parseRoleFromToken(session.access_token),
                isEmailVerified: session.user.email_confirmed_at !== null
              }

              set({ user: authUser, session })
            }
          })

        } catch (error) {
          console.error('Auth initialization failed:', error)
          set({
            user: null,
            session: null,
            isLoading: false,
            isInitialized: true,
            error: error instanceof Error ? error.message : 'Initialization failed'
          })
        }
      },

      // Utility methods
      reset: () => set(initialState),

      isAuthenticated: () => {
        const { user, session } = get()
        return !!(user && session)
      },

      hasRole: (role: string) => {
        const { user } = get()
        return user?.role === role || user?.role === 'admin'
      },

      updateUserProfile: (updates: Partial<AuthUser>) => {
        const { user } = get()
        if (user) {
          set({ user: { ...user, ...updates } })
        }
      }
    }),
    {
      name: 'duolingo-auth-store',
      storage: createJSONStorage(() => secureStorage),
      partialize: (state) => ({
        // Only persist non-sensitive data
        user: state.user ? {
          id: state.user.id,
          email: state.user.email,
          firstName: state.user.firstName,
          lastName: state.user.lastName,
          profilePicture: state.user.profilePicture,
          role: state.user.role,
          isEmailVerified: state.user.isEmailVerified,
          lastLoginAt: state.user.lastLoginAt
        } : null,
        rememberMe: state.rememberMe,
        isInitialized: state.isInitialized
      }),
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...(persistedState as Partial<AuthState>),
        // Always reset loading and error state on hydration
        isLoading: false,
        error: null,
        // Don't persist session for security
        session: null
      })
    }
  )
)

// Selectors for common use cases
export const useAuth = () => {
  const store = useAuthStore()
  return {
    user: store.user,
    session: store.session,
    isLoading: store.isLoading,
    isInitialized: store.isInitialized,
    error: store.error,
    isAuthenticated: store.isAuthenticated(),
    hasRole: store.hasRole,
    signIn: store.signIn,
    signUp: store.signUp,
    signOut: store.signOut,
    initialize: store.initialize,
    setError: store.setError,
    updateUserProfile: store.updateUserProfile
  }
}

export const useAuthUser = () => useAuthStore((state) => state.user)
export const useAuthSession = () => useAuthStore((state) => state.session)
export const useAuthLoading = () => useAuthStore((state) => state.isLoading)
export const useAuthError = () => useAuthStore((state) => state.error)
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated())

// Initialize auth store on module load
if (typeof window !== 'undefined') {
  useAuthStore.getState().initialize()
}