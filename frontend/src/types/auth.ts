/**
 * Authentication Types and Interfaces
 * 
 * Defines all authentication-related types for type-safe API interactions
 * and component interfaces throughout the application.
 */

// ================== Base Types ==================

export interface User {
  id: string
  email: string
  firstName?: string
  lastName?: string
  profilePicture?: string
  role?: string
  isEmailVerified?: boolean
  lastLoginAt?: string
  createdAt: string
  updatedAt: string
}

export interface Session {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  refresh_expires_in: number
  session_id: string
  remember_me: boolean
  user: User
}

// ================== Request Types ==================

export interface SignInRequest {
  email: string
  password: string
  rememberMe?: boolean
}

export interface SignUpRequest {
  email: string
  password: string
  firstName: string
  lastName?: string
  metadata?: Record<string, unknown>
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirmRequest {
  token: string
  newPassword: string
}

export interface MFAVerificationRequest {
  challengeToken: string
  code: string
  method: 'totp' | 'backup_code'
}

export interface RefreshTokenRequest {
  refreshToken: string
}

// ================== Response Types ==================

export interface AuthResponse {
  success: boolean
  user?: User
  session?: Session
  error?: string
  errorCode?: string
  requiresMFA?: boolean
  mfaChallengeToken?: string
}

export interface SessionResponse {
  session: Session
  user: User
}

export interface UserProfileResponse {
  user: User
  preferences: UserPreferences
  securityStatus: SecurityStatus
}

export interface SecurityStatus {
  mfaEnabled: boolean
  lastPasswordChange: string
  activeSessions: number
  lastLogin: string
  accountLocked: boolean
}

export interface UserPreferences {
  language: string
  timezone: string
  emailNotifications: boolean
  marketingEmails: boolean
  theme: 'light' | 'dark' | 'system'
}

// ================== Error Types ==================

export interface AuthError {
  code: string
  message: string
  details?: Record<string, unknown>
}

export enum AuthErrorCode {
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  ACCOUNT_LOCKED = 'ACCOUNT_LOCKED',
  EMAIL_NOT_VERIFIED = 'EMAIL_NOT_VERIFIED',
  MFA_REQUIRED = 'MFA_REQUIRED',
  RATE_LIMITED = 'RATE_LIMITED',
  SESSION_EXPIRED = 'SESSION_EXPIRED',
  INVALID_TOKEN = 'INVALID_TOKEN',
  WEAK_PASSWORD = 'WEAK_PASSWORD',
  EMAIL_ALREADY_EXISTS = 'EMAIL_ALREADY_EXISTS',
  NETWORK_ERROR = 'NETWORK_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

// ================== Utility Types ==================

export interface ClientInfo {
  userAgent: string
  ipAddress: string
  timestamp: string
}

export interface LoginAttempt {
  timestamp: string
  success: boolean
  ipAddress: string
  userAgent: string
  errorCode?: string
}

export interface SessionInfo {
  sessionId: string
  createdAt: string
  expiresAt: string
  lastActivity: string
  userAgent?: string
  ipAddress?: string
  isActive: boolean
  rememberMe: boolean
}

// ================== Form Types ==================

export interface LoginFormData {
  email: string
  password: string
  rememberMe: boolean
}

export interface RegisterFormData {
  email: string
  password: string
  confirmPassword: string
  firstName: string
  lastName?: string
  agreeToTerms: boolean
  agreeToMarketing: boolean
}

export interface PasswordResetFormData {
  email: string
}

export interface PasswordChangeFormData {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

// ================== Validation Types ==================

export interface ValidationError {
  field: string
  message: string
  code?: string
}

export interface PasswordStrength {
  score: number // 0-100
  feedback: string[]
  requirements: {
    minLength: boolean
    hasUppercase: boolean
    hasLowercase: boolean
    hasNumbers: boolean
    hasSymbols: boolean
  }
}

// ================== Admin Types ==================

export interface AdminUserData extends User {
  status: 'active' | 'suspended' | 'deleted'
  loginAttempts: LoginAttempt[]
  sessions: SessionInfo[]
  registrationIp?: string
  registrationDate: string
  lastActivityDate?: string
}

export interface AuditLogEntry {
  id: string
  userId?: string
  eventType: string
  eventResult: 'success' | 'failure' | 'error'
  ipAddress?: string
  userAgent?: string
  timestamp: string
  metadata?: Record<string, unknown>
  riskScore: number
}

// ================== OAuth Types ==================

export interface OAuthProvider {
  name: string
  id: 'google' | 'apple' | 'facebook' | 'github'
  enabled: boolean
  scopes: string[]
}

export interface OAuthRequest {
  provider: string
  redirectUrl?: string
  state?: string
}

export interface OAuthCallback {
  code: string
  state?: string
  error?: string
  errorDescription?: string
}

// ================== Export all types ==================

export type {
  User,
  Session,
  SignInRequest,
  SignUpRequest,
  AuthResponse,
  SessionResponse,
  UserProfileResponse,
  AuthError,
  LoginFormData,
  RegisterFormData,
  ValidationError,
  PasswordStrength,
  AdminUserData,
  AuditLogEntry,
  OAuthProvider,
  OAuthRequest,
  OAuthCallback,
  ClientInfo,
  LoginAttempt,
  SessionInfo,
  SecurityStatus,
  UserPreferences
}