/**
 * Supabase Client Configuration
 * 
 * Frontend Supabase client initialization and OAuth provider management
 * for the Duolingo clone authentication system.
 */

import { createClient, SupabaseClient, AuthSession, User } from '@supabase/supabase-js'

// Environment variables for Supabase configuration
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// Create Supabase client with enhanced configuration
export const supabase: SupabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    flowType: 'pkce' // Use PKCE for enhanced security
  },
  realtime: {
    params: {
      eventsPerSecond: 10
    }
  }
})

// Types for OAuth providers
export type OAuthProvider = 'google' | 'apple' | 'facebook' | 'github' | 'twitter'

export interface OAuthOptions {
  provider: OAuthProvider
  redirectTo?: string
  scopes?: string
  queryParams?: Record<string, string>
}

export interface AuthState {
  session: AuthSession | null
  user: User | null
  loading: boolean
  error: string | null
}

export interface SignUpData {
  email: string
  password: string
  firstName?: string
  lastName?: string
  metadata?: Record<string, unknown>
}

export interface SignInData {
  email: string
  password: string
  rememberMe?: boolean
}

export interface PasswordResetData {
  email: string
  redirectTo?: string
}

/**
 * Authentication utilities class for frontend Supabase operations
 */
export class SupabaseAuth {
  private client: SupabaseClient

  constructor(client: SupabaseClient) {
    this.client = client
  }

  /**
   * Sign up with email and password
   */
  async signUp(data: SignUpData) {
    try {
      const { user, session, error } = await this.client.auth.signUp({
        email: data.email,
        password: data.password,
        options: {
          data: {
            first_name: data.firstName,
            last_name: data.lastName,
            ...data.metadata
          }
        }
      })

      if (error) throw error

      return { user, session, error: null }
    } catch (error) {
      console.error('Sign up error:', error)
      return { 
        user: null, 
        session: null, 
        error: error instanceof Error ? error.message : 'Sign up failed' 
      }
    }
  }

  /**
   * Sign in with email and password
   */
  async signIn(data: SignInData) {
    try {
      const { user, session, error } = await this.client.auth.signInWithPassword({
        email: data.email,
        password: data.password
      })

      if (error) throw error

      // Handle "Remember Me" functionality by extending session duration
      if (data.rememberMe && session) {
        // Note: Session duration is handled by Supabase configuration
        // This could be enhanced with custom session management if needed
      }

      return { user, session, error: null }
    } catch (error) {
      console.error('Sign in error:', error)
      return { 
        user: null, 
        session: null, 
        error: error instanceof Error ? error.message : 'Sign in failed' 
      }
    }
  }

  /**
   * Sign in with OAuth provider
   */
  async signInWithOAuth(options: OAuthOptions) {
    try {
      const { data, error } = await this.client.auth.signInWithOAuth({
        provider: options.provider,
        options: {
          redirectTo: options.redirectTo || `${window.location.origin}/auth/callback`,
          scopes: options.scopes || this.getDefaultScopes(options.provider),
          queryParams: options.queryParams
        }
      })

      if (error) throw error

      return { data, error: null }
    } catch (error) {
      console.error('OAuth sign in error:', error)
      return { 
        data: null, 
        error: error instanceof Error ? error.message : 'OAuth sign in failed' 
      }
    }
  }

  /**
   * Sign out current user
   */
  async signOut() {
    try {
      const { error } = await this.client.auth.signOut()
      if (error) throw error
      return { error: null }
    } catch (error) {
      console.error('Sign out error:', error)
      return { error: error instanceof Error ? error.message : 'Sign out failed' }
    }
  }

  /**
   * Reset password
   */
  async resetPassword(data: PasswordResetData) {
    try {
      const { error } = await this.client.auth.resetPasswordForEmail(
        data.email,
        {
          redirectTo: data.redirectTo || `${window.location.origin}/auth/reset-password`
        }
      )

      if (error) throw error
      return { error: null }
    } catch (error) {
      console.error('Password reset error:', error)
      return { error: error instanceof Error ? error.message : 'Password reset failed' }
    }
  }

  /**
   * Update password
   */
  async updatePassword(newPassword: string) {
    try {
      const { error } = await this.client.auth.updateUser({
        password: newPassword
      })

      if (error) throw error
      return { error: null }
    } catch (error) {
      console.error('Password update error:', error)
      return { error: error instanceof Error ? error.message : 'Password update failed' }
    }
  }

  /**
   * Get current session
   */
  async getSession() {
    try {
      const { data: { session }, error } = await this.client.auth.getSession()
      if (error) throw error
      return { session, error: null }
    } catch (error) {
      console.error('Get session error:', error)
      return { session: null, error: error instanceof Error ? error.message : 'Failed to get session' }
    }
  }

  /**
   * Get current user
   */
  async getUser() {
    try {
      const { data: { user }, error } = await this.client.auth.getUser()
      if (error) throw error
      return { user, error: null }
    } catch (error) {
      console.error('Get user error:', error)
      return { user: null, error: error instanceof Error ? error.message : 'Failed to get user' }
    }
  }

  /**
   * Refresh session
   */
  async refreshSession() {
    try {
      const { data, error } = await this.client.auth.refreshSession()
      if (error) throw error
      return { session: data.session, user: data.user, error: null }
    } catch (error) {
      console.error('Refresh session error:', error)
      return { 
        session: null, 
        user: null, 
        error: error instanceof Error ? error.message : 'Failed to refresh session' 
      }
    }
  }

  /**
   * Listen to auth state changes
   */
  onAuthStateChange(callback: (event: string, session: AuthSession | null) => void) {
    return this.client.auth.onAuthStateChange(callback)
  }

  /**
   * Get default scopes for OAuth providers
   */
  private getDefaultScopes(provider: OAuthProvider): string {
    const scopesMap: Record<OAuthProvider, string> = {
      google: 'openid email profile',
      facebook: 'email public_profile',
      apple: 'email name',
      github: 'user:email',
      twitter: 'users.read tweet.read'
    }

    return scopesMap[provider] || 'openid email profile'
  }
}

// Export configured auth instance
export const auth = new SupabaseAuth(supabase)

/**
 * Helper function to check if user is authenticated
 */
export const isAuthenticated = async (): Promise<boolean> => {
  const { session } = await auth.getSession()
  return !!session
}

/**
 * Helper function to get user profile from Supabase
 */
export const getUserProfile = async (userId: string) => {
  try {
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('user_id', userId)
      .single()

    if (error) throw error
    return { profile: data, error: null }
  } catch (error) {
    console.error('Get user profile error:', error)
    return { 
      profile: null, 
      error: error instanceof Error ? error.message : 'Failed to get user profile' 
    }
  }
}

/**
 * Helper function to update user profile in Supabase
 */
export const updateUserProfile = async (userId: string, updates: Record<string, unknown>) => {
  try {
    const { data, error } = await supabase
      .from('profiles')
      .update(updates)
      .eq('user_id', userId)
      .select()
      .single()

    if (error) throw error
    return { profile: data, error: null }
  } catch (error) {
    console.error('Update user profile error:', error)
    return { 
      profile: null, 
      error: error instanceof Error ? error.message : 'Failed to update user profile' 
    }
  }
}

/**
 * Helper function to create user profile in Supabase
 */
export const createUserProfile = async (userId: string, profileData: Record<string, unknown>) => {
  try {
    const { data, error } = await supabase
      .from('profiles')
      .insert({
        user_id: userId,
        ...profileData
      })
      .select()
      .single()

    if (error) throw error
    return { profile: data, error: null }
  } catch (error) {
    console.error('Create user profile error:', error)
    return { 
      profile: null, 
      error: error instanceof Error ? error.message : 'Failed to create user profile' 
    }
  }
}

// Environment configuration validation
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables. Please check your .env.local file.')
}