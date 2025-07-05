'use client'

import { useEffect, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRole?: string
  requiredPermission?: string
  fallbackPath?: string
  showLoadingSpinner?: boolean
  showUnauthorizedMessage?: boolean
  className?: string
}

interface LoadingSpinnerProps {
  message?: string
}

interface UnauthorizedMessageProps {
  title?: string
  message?: string
  showLoginButton?: boolean
  onLoginClick?: () => void
}

export function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission,
  fallbackPath = '/auth/login',
  showLoadingSpinner = true,
  showUnauthorizedMessage = true,
  className = ''
}: ProtectedRouteProps) {
  const router = useRouter()
  const auth = useAuth()

  useEffect(() => {
    // Wait for auth to initialize
    if (!auth.isInitialized) {
      return
    }

    // Redirect to login if not authenticated
    if (!auth.isAuthenticated) {
      const currentPath = window.location.pathname
      const redirectUrl = `${fallbackPath}?redirect=${encodeURIComponent(currentPath)}`
      router.push(redirectUrl)
      return
    }

    // Check role requirement
    if (requiredRole && !auth.hasRole(requiredRole)) {
      router.push('/unauthorized')
      return
    }

    // Check permission requirement
    if (requiredPermission && !auth.hasPermission(requiredPermission)) {
      router.push('/unauthorized')
      return
    }
  }, [auth, requiredRole, requiredPermission, router, fallbackPath])

  // Show loading spinner while auth is initializing
  if (!auth.isInitialized && showLoadingSpinner) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${className}`}>
        <LoadingSpinner message="Loading..." />
      </div>
    )
  }

  // Show loading spinner while redirecting
  if (auth.isInitialized && (!auth.isAuthenticated || auth.isLoading) && showLoadingSpinner) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${className}`}>
        <LoadingSpinner message="Redirecting..." />
      </div>
    )
  }

  // Show unauthorized message if user doesn't have required permissions
  if (
    auth.isInitialized &&
    auth.isAuthenticated &&
    ((requiredRole && !auth.hasRole(requiredRole)) ||
     (requiredPermission && !auth.hasPermission(requiredPermission))) &&
    showUnauthorizedMessage
  ) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${className}`}>
        <UnauthorizedMessage
          title="Access Denied"
          message={
            requiredRole
              ? `You need the '${requiredRole}' role to access this page.`
              : `You don't have permission to access this page.`
          }
        />
      </div>
    )
  }

  // Render children if all checks pass
  if (auth.isInitialized && auth.isAuthenticated) {
    // Final permission check
    if (requiredRole && !auth.hasRole(requiredRole)) {
      return null
    }
    if (requiredPermission && !auth.hasPermission(requiredPermission)) {
      return null
    }

    return <div className={className}>{children}</div>
  }

  // Return null during transition states
  return null
}

function LoadingSpinner({ message = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center space-y-4"
    >
      <div className="relative">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <motion.div
          className="absolute inset-0 h-8 w-8 rounded-full border-2 border-blue-200"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
      </div>
      <p className="text-sm text-gray-600 font-medium">{message}</p>
    </motion.div>
  )
}

function UnauthorizedMessage({
  title = 'Access Denied',
  message = 'You do not have permission to access this page.',
  showLoginButton = false,
  onLoginClick
}: UnauthorizedMessageProps) {
  const router = useRouter()

  const handleLoginClick = () => {
    if (onLoginClick) {
      onLoginClick()
    } else {
      router.push('/auth/login')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-md mx-auto text-center p-6"
    >
      <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-4">
        <AlertCircle className="h-8 w-8 text-red-600" />
      </div>
      
      <h2 className="text-2xl font-bold text-gray-900 mb-2">{title}</h2>
      <p className="text-gray-600 mb-6">{message}</p>

      {showLoginButton && (
        <motion.button
          onClick={handleLoginClick}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Sign In
        </motion.button>
      )}
    </motion.div>
  )
}

// Higher-order component for protecting pages
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) {
  const AuthenticatedComponent = (props: P) => {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    )
  }

  AuthenticatedComponent.displayName = `withAuth(${Component.displayName || Component.name})`
  return AuthenticatedComponent
}

// Hook for protecting component sections
export function useAuthGuard(options?: {
  requiredRole?: string
  requiredPermission?: string
  redirectTo?: string
}) {
  const auth = useAuth()
  const router = useRouter()

  const checkAccess = () => {
    if (!auth.isInitialized) {
      return { canAccess: false, isLoading: true, reason: 'initializing' }
    }

    if (!auth.isAuthenticated) {
      return { canAccess: false, isLoading: false, reason: 'unauthenticated' }
    }

    if (options?.requiredRole && !auth.hasRole(options.requiredRole)) {
      return { canAccess: false, isLoading: false, reason: 'insufficient_role' }
    }

    if (options?.requiredPermission && !auth.hasPermission(options.requiredPermission)) {
      return { canAccess: false, isLoading: false, reason: 'insufficient_permission' }
    }

    return { canAccess: true, isLoading: false, reason: null }
  }

  const redirectToLogin = () => {
    const currentPath = window.location.pathname
    const redirectUrl = `${options?.redirectTo || '/auth/login'}?redirect=${encodeURIComponent(currentPath)}`
    router.push(redirectUrl)
  }

  const redirectToUnauthorized = () => {
    router.push('/unauthorized')
  }

  return {
    ...checkAccess(),
    redirectToLogin,
    redirectToUnauthorized,
    auth
  }
}

// Component for conditionally rendering content based on auth status
interface AuthGateProps {
  children: ReactNode
  fallback?: ReactNode
  requireAuth?: boolean
  requiredRole?: string
  requiredPermission?: string
  showLoading?: boolean
}

export function AuthGate({
  children,
  fallback = null,
  requireAuth = true,
  requiredRole,
  requiredPermission,
  showLoading = true
}: AuthGateProps) {
  const auth = useAuth()

  // Show loading state
  if (!auth.isInitialized && showLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <LoadingSpinner message="Loading..." />
      </div>
    )
  }

  // Check authentication requirement
  if (requireAuth && !auth.isAuthenticated) {
    return <>{fallback}</>
  }

  // Check role requirement
  if (requiredRole && !auth.hasRole(requiredRole)) {
    return <>{fallback}</>
  }

  // Check permission requirement
  if (requiredPermission && !auth.hasPermission(requiredPermission)) {
    return <>{fallback}</>
  }

  // Render children if all checks pass
  return <>{children}</>
}

// Component for rendering different content based on auth status
interface AuthSwitchProps {
  children?: ReactNode
  authenticated?: ReactNode
  unauthenticated?: ReactNode
  loading?: ReactNode
  hasRole?: string
  hasPermission?: string
  unauthorized?: ReactNode
}

export function AuthSwitch({
  children,
  authenticated,
  unauthenticated,
  loading,
  hasRole,
  hasPermission,
  unauthorized
}: AuthSwitchProps) {
  const auth = useAuth()

  // Show loading state
  if (!auth.isInitialized) {
    return loading ? <>{loading}</> : (
      <div className="flex items-center justify-center py-4">
        <LoadingSpinner />
      </div>
    )
  }

  // Not authenticated
  if (!auth.isAuthenticated) {
    return unauthenticated ? <>{unauthenticated}</> : <>{children}</>
  }

  // Check role/permission requirements
  if ((hasRole && !auth.hasRole(hasRole)) || (hasPermission && !auth.hasPermission(hasPermission))) {
    return unauthorized ? <>{unauthorized}</> : <>{children}</>
  }

  // Authenticated with proper permissions
  return authenticated ? <>{authenticated}</> : <>{children}</>
}