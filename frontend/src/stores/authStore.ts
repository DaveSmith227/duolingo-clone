import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { createSupabaseClient } from '@/lib/supabase/client'
import { SessionTimeoutManager } from '@/lib/auth/session-timeout'
import { secureSessionStore } from '@/lib/auth/secure-storage'
import type { Session, User } from '@supabase/supabase-js'

const { auth } = createSupabaseClient()

// SECURITY FIX: Remove client-side JWT parsing
// User roles and permissions should ONLY come from the server

export interface AuthUser extends User {
  firstName?: string
  lastName?: string
  profilePicture?: string
  role?: string  // This should come from server response, not JWT parsing
  isEmailVerified?: boolean
  lastLoginAt?: string
}

export interface AuthState {
  // State
  user: AuthUser | null
  session: Session | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  rememberMe: boolean
  
  // Actions
  setUser: (user: AuthUser | null) => void
  setSession: (session: Session | null) => void
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
  
  // NEW: Secure method to fetch user details from server
  fetchUserDetails: () => Promise<void>
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
              // Don't store role - fetch from server
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

      // Actions
      setUser: (user) => set({ user }),
      setSession: (session) => set({ session }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setRememberMe: (rememberMe) => set({ rememberMe }),

      // SECURE: Fetch user details from server
      fetchUserDetails: async () => {
        const { session } = get()
        if (!session) return

        try {
          // Make authenticated request to get user details including role
          const response = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
              'Content-Type': 'application/json'
            }
          })

          if (response.ok) {
            const userData = await response.json()
            
            // Update user with server-provided data
            set({
              user: {
                ...get().user,
                role: userData.role,  // Role from server, not JWT
                firstName: userData.firstName,
                lastName: userData.lastName,
                isEmailVerified: userData.isEmailVerified
              } as AuthUser
            })
          }
        } catch (error) {
          console.error('Failed to fetch user details:', error)
        }
      },

      signIn: async (email: string, password: string, rememberMe = false) => {
        set({ isLoading: true, error: null, rememberMe })
        
        try {
          const { user, session, error } = await auth.signIn({ email, password })
          
          if (error) {
            set({ error, isLoading: false })
            throw new Error(error)
          }

          if (user && session) {
            // Create initial user object
            const authUser: AuthUser = {
              ...user,
              firstName: user.user_metadata?.first_name,
              lastName: user.user_metadata?.last_name,
              profilePicture: user.user_metadata?.avatar_url,
              // Don't parse role from JWT
              isEmailVerified: user.email_confirmed_at !== null
            }

            set({
              user: authUser,
              session,
              isLoading: false,
              error: null
            })

            // Fetch full user details from server
            await get().fetchUserDetails()

            // Setup session timeout if remember me is not enabled
            if (!rememberMe && session) {
              sessionTimeoutManager = new SessionTimeoutManager({
                timeout: 30 * 60 * 1000, // 30 minutes
                warningTime: 5 * 60 * 1000, // 5 minute warning
                onTimeout: () => {
                  get().signOut()
                },
                onWarning: () => {
                  // Could show a warning modal here
                  console.warn('Session will expire soon')
                }
              })
              sessionTimeoutManager.start()
            }
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
              role: 'user',  // Default role for new users
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
              // Don't parse role from JWT
              isEmailVerified: user.email_confirmed_at !== null
            }

            set({ user: authUser, session })
            
            // Fetch updated user details from server
            await get().fetchUserDetails()
          }
        } catch (error) {
          console.warn('Session refresh error:', error)
          set({ user: null, session: null })
        }
      },

      initialize: async () => {
        if (get().isInitialized) return
        
        set({ isLoading: true })
        
        try {
          // Check for existing session
          const { data: { session, user } } = await auth.getSession()
          
          if (session && user) {
            const authUser: AuthUser = {
              ...user,
              firstName: user.user_metadata?.first_name,
              lastName: user.user_metadata?.last_name,
              profilePicture: user.user_metadata?.avatar_url,
              // Don't parse role from JWT
              isEmailVerified: user.email_confirmed_at !== null
            }

            set({ 
              user: authUser, 
              session,
              isInitialized: true,
              isLoading: false
            })
            
            // Fetch full user details from server
            await get().fetchUserDetails()
            
            // Setup session timeout if not remember me
            const { rememberMe } = get()
            if (!rememberMe && session) {
              sessionTimeoutManager = new SessionTimeoutManager({
                timeout: 30 * 60 * 1000,
                warningTime: 5 * 60 * 1000,
                onTimeout: () => {
                  get().signOut()
                },
                onWarning: () => {
                  console.warn('Session will expire soon')
                }
              })
              sessionTimeoutManager.start()
            }
          } else {
            set({ isInitialized: true, isLoading: false })
          }

          // Listen for auth state changes
          auth.onAuthStateChange(async (event, session) => {
            if (event === 'SIGNED_IN' && session) {
              const user = session.user
              const authUser: AuthUser = {
                ...user,
                firstName: user.user_metadata?.first_name,
                lastName: user.user_metadata?.last_name,
                profilePicture: user.user_metadata?.avatar_url,
                // Don't parse role from JWT
                isEmailVerified: user.email_confirmed_at !== null
              }

              set({ user: authUser, session })
              
              // Fetch full user details from server
              await get().fetchUserDetails()
            } else if (event === 'SIGNED_OUT') {
              set({ user: null, session: null })
            } else if (event === 'TOKEN_REFRESHED' && session) {
              set({ session })
              
              // Fetch updated user details from server
              await get().fetchUserDetails()
            }
          })
        } catch (error) {
          console.error('Auth initialization error:', error)
          set({ error: 'Failed to initialize auth', isLoading: false, isInitialized: true })
        }
      },

      reset: () => {
        set(initialState)
      },

      isAuthenticated: () => {
        const { user, session } = get()
        return !!(user && session)
      },

      hasRole: (role: string) => {
        const { user } = get()
        return user?.role === role
      },

      updateUserProfile: (updates: Partial<AuthUser>) => {
        const { user } = get()
        if (user) {
          set({ user: { ...user, ...updates } })
        }
      }
    }),
    {
      name: 'auth-storage',
      storage: secureStorage,
      partialize: (state) => ({
        rememberMe: state.rememberMe,
        // Only persist minimal user info if remember me is enabled
        ...(state.rememberMe && state.user ? {
          user: {
            id: state.user.id,
            email: state.user.email,
            firstName: state.user.firstName,
            lastName: state.user.lastName,
            isEmailVerified: state.user.isEmailVerified
          }
        } : {})
      })
    }
  )
)