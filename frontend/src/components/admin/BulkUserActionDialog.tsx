'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  AlertTriangle, 
  UserX, 
  UserCheck, 
  X,
  Loader2,
  Users
} from 'lucide-react'

export type BulkUserActionType = 'suspend' | 'unsuspend'

interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  is_suspended: boolean
}

interface BulkUserActionDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (action: BulkUserActionType, reason: string, userIds: string[]) => Promise<void>
  users: User[]
  action: BulkUserActionType | null
  loading?: boolean
}

const BULK_ACTION_CONFIG = {
  suspend: {
    title: 'Suspend Multiple Users',
    description: 'This will prevent all selected users from logging in and terminate their active sessions.',
    icon: UserX,
    color: 'orange',
    buttonText: 'Suspend Users',
    severity: 'warning' as const
  },
  unsuspend: {
    title: 'Unsuspend Multiple Users',
    description: 'This will restore access for all selected users and allow them to log in.',
    icon: UserCheck,
    color: 'green',
    buttonText: 'Unsuspend Users',
    severity: 'info' as const
  }
}

export function BulkUserActionDialog({
  isOpen,
  onClose,
  onConfirm,
  users,
  action,
  loading = false
}: BulkUserActionDialogProps) {
  const [reason, setReason] = useState('')
  const [errors, setErrors] = useState<{ reason?: string }>({})

  if (!isOpen || !action || users.length === 0) return null

  const config = BULK_ACTION_CONFIG[action]
  const Icon = config.icon

  const validateForm = (): boolean => {
    const newErrors: typeof errors = {}

    if (!reason.trim()) {
      newErrors.reason = 'Reason is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async () => {
    if (!validateForm()) return

    try {
      const userIds = users.map(user => user.id)
      await onConfirm(action, reason.trim(), userIds)
      handleClose()
    } catch (error) {
      // Error handling is done by parent component
    }
  }

  const handleClose = () => {
    setReason('')
    setErrors({})
    onClose()
  }

  const getSeverityStyles = (severity: 'info' | 'warning') => {
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
                      {users.length} user{users.length !== 1 ? 's' : ''} selected
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

                {config.severity === 'warning' && (
                  <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                    <div className="flex">
                      <AlertTriangle className="w-5 h-5 text-orange-400 mr-2 mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="text-sm font-medium text-orange-800 mb-1">
                          Warning: Bulk Action
                        </h4>
                        <p className="text-sm text-orange-600">
                          This action will affect {users.length} user{users.length !== 1 ? 's' : ''} simultaneously.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Selected users preview */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Selected Users ({users.length})
                </h4>
                <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3">
                  {users.slice(0, 10).map((user) => (
                    <div key={user.id} className="flex items-center justify-between py-1">
                      <span className="text-sm text-gray-900">{user.name}</span>
                      <span className="text-xs text-gray-500">{user.email}</span>
                    </div>
                  ))}
                  {users.length > 10 && (
                    <div className="text-xs text-gray-500 text-center py-2">
                      ... and {users.length - 10} more user{users.length - 10 !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>

              {/* Reason field */}
              <div className="mb-4">
                <label htmlFor="bulk-reason" className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for this bulk action *
                </label>
                <textarea
                  id="bulk-reason"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none ${
                    errors.reason ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Please provide a detailed reason for this bulk action..."
                  disabled={loading}
                />
                {errors.reason && (
                  <p className="mt-1 text-sm text-red-600">{errors.reason}</p>
                )}
              </div>
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