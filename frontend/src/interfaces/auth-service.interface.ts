/**
 * Authentication Service Interface
 * 
 * Defines the contract for authentication services, ensuring consistent
 * implementation across different auth providers and testing scenarios.
 */

import type {
  User,
  Session,
  SignInRequest,
  SignUpRequest,
  AuthResponse,
  SessionResponse,
  PasswordResetRequest,
  PasswordResetConfirmRequest,
  MFAVerificationRequest,
  OAuthRequest,
  UserProfileResponse,
  SessionInfo,
  AuditLogEntry
} from '@/types/auth'

// ================== Core Authentication Interface ==================

export interface IAuthService {
  /**
   * Sign in with email and password
   */
  signIn(credentials: SignInRequest): Promise<AuthResponse>
  
  /**
   * Sign up with email and password
   */
  signUp(userData: SignUpRequest): Promise<AuthResponse>
  
  /**
   * Sign out current user
   */
  signOut(): Promise<void>
  
  /**
   * Refresh current session
   */
  refreshSession(): Promise<SessionResponse>
  
  /**
   * Get current session
   */
  getSession(): Promise<Session | null>
  
  /**
   * Get current user
   */
  getCurrentUser(): Promise<User | null>
  
  /**
   * Sign in with OAuth provider
   */
  signInWithOAuth(request: OAuthRequest): Promise<AuthResponse>
  
  /**
   * Request password reset
   */
  requestPasswordReset(request: PasswordResetRequest): Promise<void>
  
  /**
   * Confirm password reset
   */
  confirmPasswordReset(request: PasswordResetConfirmRequest): Promise<void>
  
  /**
   * Verify MFA code
   */
  verifyMFA(request: MFAVerificationRequest): Promise<AuthResponse>
  
  /**
   * Get user profile with preferences
   */
  getUserProfile(): Promise<UserProfileResponse>
  
  /**
   * Update user profile
   */
  updateUserProfile(updates: Partial<User>): Promise<User>
  
  /**
   * Change password
   */
  changePassword(currentPassword: string, newPassword: string): Promise<void>
  
  /**
   * Delete account
   */
  deleteAccount(): Promise<void>
  
  /**
   * Export user data
   */
  exportUserData(): Promise<Blob>
}

// ================== Session Management Interface ==================

export interface ISessionManager {
  /**
   * Get all user sessions
   */
  getUserSessions(): Promise<SessionInfo[]>
  
  /**
   * Invalidate specific session
   */
  invalidateSession(sessionId: string): Promise<void>
  
  /**
   * Invalidate all sessions except current
   */
  invalidateOtherSessions(): Promise<void>
  
  /**
   * Get session activity
   */
  getSessionActivity(sessionId: string): Promise<any[]>
  
  /**
   * Update session preferences
   */
  updateSessionPreferences(preferences: Record<string, any>): Promise<void>
}

// ================== Admin Interface ==================

export interface IAdminService {
  /**
   * Get all users with admin data
   */
  getUsers(page: number, limit: number, search?: string): Promise<{
    users: any[]
    total: number
    page: number
    limit: number
  }>
  
  /**
   * Get specific user details
   */
  getUserDetails(userId: string): Promise<any>
  
  /**
   * Update user status
   */
  updateUserStatus(userId: string, status: string): Promise<void>
  
  /**
   * Suspend user account
   */
  suspendUser(userId: string, reason: string): Promise<void>
  
  /**
   * Unsuspend user account
   */
  unsuspendUser(userId: string): Promise<void>
  
  /**
   * Delete user account
   */
  deleteUser(userId: string): Promise<void>
  
  /**
   * Get audit logs
   */
  getAuditLogs(
    page: number,
    limit: number,
    filters?: {
      userId?: string
      eventType?: string
      startDate?: string
      endDate?: string
    }
  ): Promise<{
    logs: AuditLogEntry[]
    total: number
    page: number
    limit: number
  }>
  
  /**
   * Export audit logs
   */
  exportAuditLogs(filters?: any): Promise<Blob>
  
  /**
   * Get authentication metrics
   */
  getAuthMetrics(timeRange: string): Promise<any>
  
  /**
   * Perform bulk user operations
   */
  bulkUserOperation(
    userIds: string[],
    operation: 'suspend' | 'unsuspend' | 'delete',
    reason?: string
  ): Promise<void>
}

// ================== Authentication State Interface ==================

export interface IAuthState {
  // State properties
  user: User | null
  session: Session | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  
  // Auth status methods
  isAuthenticated(): boolean
  hasRole(role: string): boolean
  hasPermission(permission: string): boolean
  
  // Auth actions
  signIn(email: string, password: string, rememberMe?: boolean): Promise<void>
  signUp(email: string, password: string, firstName: string): Promise<void>
  signOut(): Promise<void>
  refreshSession(): Promise<void>
  
  // State management
  setUser(user: User | null): void
  setSession(session: Session | null): void
  setLoading(loading: boolean): void
  setError(error: string | null): void
  reset(): void
  
  // Initialization
  initialize(): Promise<void>
}

// ================== Form Validation Interface ==================

export interface IFormValidator {
  /**
   * Validate email format
   */
  validateEmail(email: string): { isValid: boolean; error?: string }
  
  /**
   * Validate password strength
   */
  validatePassword(password: string): {
    isValid: boolean
    score: number
    feedback: string[]
    requirements: Record<string, boolean>
  }
  
  /**
   * Validate form data
   */
  validateForm(formData: Record<string, any>, rules: Record<string, any>): {
    isValid: boolean
    errors: Record<string, string>
  }
  
  /**
   * Validate password confirmation
   */
  validatePasswordConfirmation(password: string, confirmPassword: string): {
    isValid: boolean
    error?: string
  }
}

// ================== Security Interface ==================

export interface ISecurityService {
  /**
   * Sanitize input for XSS prevention
   */
  sanitizeInput(input: string): string
  
  /**
   * Generate CSRF token
   */
  generateCSRFToken(): string
  
  /**
   * Validate CSRF token
   */
  validateCSRFToken(token: string): boolean
  
  /**
   * Check rate limit status
   */
  checkRateLimit(action: string): Promise<{
    allowed: boolean
    remaining: number
    resetTime: number
  }>
  
  /**
   * Encrypt sensitive data
   */
  encryptData(data: string): string
  
  /**
   * Decrypt sensitive data
   */
  decryptData(encryptedData: string): string
}

// ================== Storage Interface ==================

export interface ISecureStorage {
  /**
   * Store data securely
   */
  set(key: string, value: any): void
  
  /**
   * Retrieve data securely
   */
  get(key: string): any
  
  /**
   * Remove data
   */
  delete(key: string): void
  
  /**
   * Clear all data
   */
  clear(): void
  
  /**
   * Check if key exists
   */
  has(key: string): boolean
  
  /**
   * Set expiration for data
   */
  setWithExpiry(key: string, value: any, expiryMs: number): void
}

// ================== Export interfaces ==================

export type {
  IAuthService,
  ISessionManager,
  IAdminService,
  IAuthState,
  IFormValidator,
  ISecurityService,
  ISecureStorage
}