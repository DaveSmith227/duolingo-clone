'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertTriangle, 
  UserX, 
  UserCheck, 
  Trash2, 
  X,
  Loader2,
  RefreshCw,
  Key,
  LogOut,
  ShieldCheck
} from 'lucide-react'

export type UserActionType = 'suspend' | 'unsuspend' | 'delete' | 'reset_password' | 'force_logout' | 'change_role'

interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  is_suspended: boolean
  roles: string[]
}

interface UserActionDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (action: UserActionType, reason: string, additionalData?: any) => Promise<void>
  user: User | null
  action: UserActionType | null
  loading?: boolean
}

const ACTION_CONFIG = {
  suspend: {
    title: 'Suspend User',
    description: 'This will prevent the user from logging in and terminate all active sessions.',
    icon: UserX,
    color: 'orange',
    buttonText: 'Suspend User',
    severity: 'warning' as const,
    requiresReason: true
  },
  unsuspend: {
    title: 'Unsuspend User',
    description: 'This will restore the user\'s access and allow them to log in.',
    icon: UserCheck,
    color: 'green',
    buttonText: 'Unsuspend User',
    severity: 'info' as const,
    requiresReason: true
  },
  delete: {
    title: 'Delete User Account',
    description: 'This will permanently delete the user account and all associated data. This action cannot be undone.',
    icon: Trash2,
    color: 'red',
    buttonText: 'Delete Account',
    severity: 'danger' as const,
    requiresReason: true,
    requiresConfirmation: true
  },
  reset_password: {
    title: 'Reset Password',
    description: 'This will send a password reset email to the user and invalidate their current password.',
    icon: Key,
    color: 'blue',
    buttonText: 'Reset Password',
    severity: 'info' as const,
    requiresReason: true
  },
  force_logout: {
    title: 'Force Logout',
    description: 'This will immediately terminate all active sessions for this user.',
    icon: LogOut,
    color: 'yellow',
    buttonText: 'Force Logout',
    severity: 'warning' as const,
    requiresReason: true
  },
  change_role: {
    title: 'Change User Role',
    description: 'This will update the user\'s role and permissions.',
    icon: ShieldCheck,
    color: 'purple',
    buttonText: 'Change Role',
    severity: 'info' as const,
    requiresReason: true,
    hasAdditionalFields: true
  }
}

const AVAILABLE_ROLES = ['user', 'instructor', 'moderator', 'admin']

export function UserActionDialog({
  isOpen,
  onClose,
  onConfirm,
  user,
  action,
  loading = false
}: UserActionDialogProps) {
  const [reason, setReason] = useState('')
  const [confirmationText, setConfirmationText] = useState('')
  const [selectedRole, setSelectedRole] = useState('')
  const [errors, setErrors] = useState<{ reason?: string; confirmation?: string; role?: string }>({})

  if (!isOpen || !user || !action) return null

  const config = ACTION_CONFIG[action]
  const Icon = config.icon

  const validateForm = (): boolean => {
    const newErrors: typeof errors = {}

    if (config.requiresReason && !reason.trim()) {
      newErrors.reason = 'Reason is required'
    }

    if (config.requiresConfirmation && confirmationText !== user.email) {
      newErrors.confirmation = 'Please type the user\'s email address to confirm'
    }

    if (action === 'change_role' && !selectedRole) {
      newErrors.role = 'Please select a role'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) return

    const additionalData: any = {}
    
    if (action === 'change_role') {
      additionalData.new_role = selectedRole
    }

    try {
      await onConfirm(action, reason.trim(), additionalData)
      handleClose()
    } catch (error) {
      // Error handling is done by parent component
    }
  }

  const handleClose = () => {
    setReason('')
    setConfirmationText('')
    setSelectedRole('')
    setErrors({})
    onClose()
  }

  const getSeverityStyles = (severity: 'info' | 'warning' | 'danger') => {
    switch (severity) {
      case 'info':
        return {
          headerBg: 'bg-blue-50',
          headerText: 'text-blue-900',
          iconColor: 'text-blue-600',
          button: 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
        }
      case 'warning':
        return {
          headerBg: 'bg-orange-50',
          headerText: 'text-orange-900',
          iconColor: 'text-orange-600',
          button: 'bg-orange-600 hover:bg-orange-700 focus:ring-orange-500'
        }
      case 'danger':
        return {
          headerBg: 'bg-red-50',
          headerText: 'text-red-900',
          iconColor: 'text-red-600',
          button: 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
        }
    }
  }

  const styles = getSeverityStyles(config.severity)

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
          {/* Background overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            onClick={handleClose}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="inline-block transform overflow-hidden rounded-lg bg-white text-left align-bottom shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:align-middle"
          >
            {/* Header */}
            <div className={`px-6 py-4 ${styles.headerBg} border-b border-gray-200`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Icon className={`w-6 h-6 mr-3 ${styles.iconColor}`} />
                  <div>
                    <h3 className={`text-lg font-medium ${styles.headerText}`}>
                      {config.title}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {user.name} ({user.email})
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  disabled={loading}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-4">
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-4">
                  {config.description}
                </p>

                {config.severity === 'danger' && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex">
                      <AlertTriangle className="w-5 h-5 text-red-400 mr-2 mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="text-sm font-medium text-red-800 mb-1">
                          Warning: This action is irreversible
                        </h4>
                        <p className="text-sm text-red-600">
                          All user data, including profile information, progress, and preferences will be permanently deleted.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Reason field */}
              {config.requiresReason && (
                <div className="mb-4">
                  <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-2">
                    Reason for this action *
                  </label>
                  <textarea
                    id="reason"
                    rows={3}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
                      errors.reason ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder="Please provide a detailed reason for this action..."
                    disabled={loading}
                  />
                  {errors.reason && (
                    <p className="mt-1 text-sm text-red-600">{errors.reason}</p>
                  )}
                </div>
              )}

              {/* Role selection for change_role action */}
              {action === 'change_role' && (
                <div className="mb-4">
                  <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-2">
                    New Role *
                  </label>
                  <select
                    id="role"
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.role ? 'border-red-300' : 'border-gray-300'
                    }`}
                    disabled={loading}
                  >
                    <option value="">Select a role...</option>
                    {AVAILABLE_ROLES.filter(role => !user.roles.includes(role)).map(role => (
                      <option key={role} value={role}>
                        {role.charAt(0).toUpperCase() + role.slice(1)}
                      </option>
                    ))}
                  </select>
                  {errors.role && (
                    <p className="mt-1 text-sm text-red-600">{errors.role}</p>
                  )}
                  
                  <div className="mt-2 text-sm text-gray-500">
                    Current roles: {user.roles.join(', ')}
                  </div>
                </div>
              )}

              {/* Confirmation field for dangerous actions */}
              {config.requiresConfirmation && (
                <div className="mb-4">
                  <label htmlFor="confirmation" className="block text-sm font-medium text-gray-700 mb-2">
                    Type the user&apos;s email address to confirm *
                  </label>
                  <input
                    id="confirmation"
                    type="text"
                    value={confirmationText}
                    onChange={(e) => setConfirmationText(e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.confirmation ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder={user.email}
                    disabled={loading}
                  />
                  {errors.confirmation && (
                    <p className="mt-1 text-sm text-red-600">{errors.confirmation}</p>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className={`px-4 py-2 text-sm font-medium text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 transition-colors ${styles.button}`}
              >
                {loading ? (
                  <div className="flex items-center">
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </div>
                ) : (
                  config.buttonText
                )}
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  )
}