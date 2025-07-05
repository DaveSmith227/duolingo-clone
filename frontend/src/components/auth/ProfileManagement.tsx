'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  User, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  Save, 
  Download, 
  Trash2, 
  AlertCircle, 
  CheckCircle, 
  Camera,
  Shield,
  Loader2
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { auth } from '@/lib/supabase'

interface ProfileManagementProps {
  onSuccess?: (message: string) => void
  onError?: (error: string) => void
  className?: string
}

interface ProfileFormData {
  firstName: string
  lastName: string
  email: string
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

interface FormErrors {
  firstName?: string
  lastName?: string
  email?: string
  currentPassword?: string
  newPassword?: string
  confirmPassword?: string
  general?: string
}

type TabType = 'profile' | 'password' | 'account' | 'data'

export function ProfileManagement({
  onSuccess,
  onError,
  className = ''
}: ProfileManagementProps) {
  const authHook = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('profile')
  const [formData, setFormData] = useState<ProfileFormData>({
    firstName: authHook.user?.firstName || '',
    lastName: authHook.user?.lastName || '',
    email: authHook.user?.email || '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [isLoading, setIsLoading] = useState(false)
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [showDeleteConfirmation, setShowDeleteConfirmation] = useState(false)
  const [isExporting, setIsExporting] = useState(false)

  // Update form data when user changes
  useEffect(() => {
    if (authHook.user) {
      setFormData(prev => ({
        ...prev,
        firstName: authHook.user?.firstName || '',
        lastName: authHook.user?.lastName || '',
        email: authHook.user?.email || ''
      }))
    }
  }, [authHook.user])

  const handleInputChange = useCallback((field: keyof ProfileFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Clear specific field error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }, [errors])

  const validateProfileForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required'
    } else if (formData.firstName.length < 2) {
      newErrors.firstName = 'First name must be at least 2 characters'
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required'
    } else if (formData.lastName.length < 2) {
      newErrors.lastName = 'Last name must be at least 2 characters'
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validatePasswordForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.currentPassword) {
      newErrors.currentPassword = 'Current password is required'
    }

    if (!formData.newPassword) {
      newErrors.newPassword = 'New password is required'
    } else if (formData.newPassword.length < 8) {
      newErrors.newPassword = 'New password must be at least 8 characters'
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your new password'
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleUpdateProfile = async () => {
    if (!validateProfileForm()) return

    setIsLoading(true)
    setErrors({})

    try {
      // Update profile using auth store
      await authHook.updateUserProfile({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email
      })

      onSuccess?.('Profile updated successfully')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update profile'
      setErrors({ general: errorMessage })
      onError?.(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpdatePassword = async () => {
    if (!validatePasswordForm()) return

    setIsLoading(true)
    setErrors({})

    try {
      // Update password using Supabase auth
      const { error } = await auth.updateUser({
        password: formData.newPassword
      })

      if (error) {
        throw new Error(error.message)
      }

      // Clear password fields
      setFormData(prev => ({
        ...prev,
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      }))

      onSuccess?.('Password updated successfully')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update password'
      setErrors({ general: errorMessage })
      onError?.(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  const handleExportData = async () => {
    setIsExporting(true)

    try {
      // Create user data export
      const userData = {
        profile: {
          firstName: authHook.user?.firstName,
          lastName: authHook.user?.lastName,
          email: authHook.user?.email,
          role: authHook.user?.role,
          createdAt: authHook.user?.createdAt,
          isEmailVerified: authHook.user?.isEmailVerified
        },
        exportedAt: new Date().toISOString()
      }

      // Create downloadable file
      const dataStr = JSON.stringify(userData, null, 2)
      const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)
      
      const exportFileDefaultName = `duolingo-user-data-${new Date().toISOString().split('T')[0]}.json`

      const linkElement = document.createElement('a')
      linkElement.setAttribute('href', dataUri)
      linkElement.setAttribute('download', exportFileDefaultName)
      linkElement.click()

      onSuccess?.('Data exported successfully')
    } catch {
      const errorMessage = 'Failed to export data'
      onError?.(errorMessage)
    } finally {
      setIsExporting(false)
    }
  }

  const handleDeleteAccount = async () => {
    setIsLoading(true)
    setErrors({})

    try {
      // Delete account using Supabase auth
      const { error } = await auth.deleteUser()

      if (error) {
        throw new Error(error.message)
      }

      // Sign out after account deletion
      await authHook.signOut()
      
      onSuccess?.('Account deleted successfully')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete account'
      setErrors({ general: errorMessage })
      onError?.(errorMessage)
    } finally {
      setIsLoading(false)
      setShowDeleteConfirmation(false)
    }
  }

  const tabs = [
    { id: 'profile' as TabType, label: 'Profile', icon: User },
    { id: 'password' as TabType, label: 'Password', icon: Lock },
    { id: 'account' as TabType, label: 'Account', icon: Shield },
    { id: 'data' as TabType, label: 'Data', icon: Download }
  ]

  return (
    <div className={`max-w-4xl mx-auto ${className}`}>
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Account Settings</h1>
        <p className="text-gray-600">Manage your profile and account preferences</p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="flex space-x-8">
          {tabs.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* General Error */}
      <AnimatePresence>
        {errors.general && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3 mb-6"
          >
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{errors.general}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'profile' && (
          <motion.div
            key="profile"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-6">
                <User className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">Profile Information</h2>
              </div>

              <div className="space-y-4">
                {/* Avatar Section */}
                <div className="flex items-center gap-4 mb-6">
                  <div className="relative">
                    <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center">
                      <span className="text-xl font-semibold text-blue-600">
                        {authHook.getUserInitials()}
                      </span>
                    </div>
                    <button className="absolute -bottom-1 -right-1 h-6 w-6 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center hover:bg-gray-50 transition-colors">
                      <Camera className="h-3 w-3 text-gray-600" />
                    </button>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{authHook.getUserDisplayName()}</h3>
                    <p className="text-sm text-gray-500">{authHook.user?.email}</p>
                  </div>
                </div>

                {/* First Name */}
                <div className="space-y-2">
                  <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                    First Name
                  </label>
                  <input
                    id="firstName"
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => handleInputChange('firstName', e.target.value)}
                    className={`
                      w-full px-4 py-3 border rounded-xl transition-colors duration-200
                      focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${errors.firstName 
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                      }
                      placeholder-gray-400 text-gray-900
                    `}
                    placeholder="Enter your first name"
                    disabled={isLoading}
                  />
                  <AnimatePresence>
                    {errors.firstName && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.firstName}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Last Name */}
                <div className="space-y-2">
                  <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                    Last Name
                  </label>
                  <input
                    id="lastName"
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => handleInputChange('lastName', e.target.value)}
                    className={`
                      w-full px-4 py-3 border rounded-xl transition-colors duration-200
                      focus:outline-none focus:ring-2 focus:ring-offset-2
                      ${errors.lastName 
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                      }
                      placeholder-gray-400 text-gray-900
                    `}
                    placeholder="Enter your last name"
                    disabled={isLoading}
                  />
                  <AnimatePresence>
                    {errors.lastName && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.lastName}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email Address
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Mail className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={formData.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      className={`
                        w-full pl-10 pr-4 py-3 border rounded-xl transition-colors duration-200
                        focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${errors.email 
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                        }
                        placeholder-gray-400 text-gray-900
                      `}
                      placeholder="Enter your email"
                      disabled={isLoading}
                    />
                  </div>
                  <AnimatePresence>
                    {errors.email && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.email}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Email Verification Status */}
                <div className={`flex items-center gap-2 text-sm ${
                  authHook.isEmailVerified() ? 'text-green-600' : 'text-yellow-600'
                }`}>
                  <CheckCircle className="h-4 w-4" />
                  {authHook.isEmailVerified() ? 'Email verified' : 'Email not verified'}
                </div>

                {/* Save Button */}
                <div className="pt-4">
                  <motion.button
                    onClick={handleUpdateProfile}
                    disabled={isLoading}
                    whileHover={{ scale: isLoading ? 1 : 1.02 }}
                    whileTap={{ scale: isLoading ? 1 : 0.98 }}
                    className={`
                      flex items-center gap-2 px-6 py-3 border border-transparent rounded-xl
                      text-sm font-medium text-white transition-all duration-200
                      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                      ${isLoading 
                        ? 'bg-blue-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
                      }
                    `}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="h-4 w-4" />
                        Save Changes
                      </>
                    )}
                  </motion.button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'password' && (
          <motion.div
            key="password"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-6">
                <Lock className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">Change Password</h2>
              </div>

              <div className="space-y-4">
                {/* Current Password */}
                <div className="space-y-2">
                  <label htmlFor="currentPassword" className="block text-sm font-medium text-gray-700">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      id="currentPassword"
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={formData.currentPassword}
                      onChange={(e) => handleInputChange('currentPassword', e.target.value)}
                      className={`
                        w-full px-4 py-3 pr-10 border rounded-xl transition-colors duration-200
                        focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${errors.currentPassword 
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                        }
                        placeholder-gray-400 text-gray-900
                      `}
                      placeholder="Enter current password"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {showCurrentPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                  <AnimatePresence>
                    {errors.currentPassword && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.currentPassword}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* New Password */}
                <div className="space-y-2">
                  <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      id="newPassword"
                      type={showNewPassword ? 'text' : 'password'}
                      value={formData.newPassword}
                      onChange={(e) => handleInputChange('newPassword', e.target.value)}
                      className={`
                        w-full px-4 py-3 pr-10 border rounded-xl transition-colors duration-200
                        focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${errors.newPassword 
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                        }
                        placeholder-gray-400 text-gray-900
                      `}
                      placeholder="Enter new password"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {showNewPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                  <AnimatePresence>
                    {errors.newPassword && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.newPassword}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Confirm New Password */}
                <div className="space-y-2">
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      id="confirmPassword"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={formData.confirmPassword}
                      onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                      className={`
                        w-full px-4 py-3 pr-10 border rounded-xl transition-colors duration-200
                        focus:outline-none focus:ring-2 focus:ring-offset-2
                        ${errors.confirmPassword 
                          ? 'border-red-300 focus:border-red-500 focus:ring-red-500' 
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                        }
                        placeholder-gray-400 text-gray-900
                      `}
                      placeholder="Confirm new password"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                  <AnimatePresence>
                    {errors.confirmPassword && (
                      <motion.p
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-sm text-red-600 flex items-center gap-1"
                      >
                        <AlertCircle className="h-4 w-4" />
                        {errors.confirmPassword}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Password Requirements */}
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-2">Password Requirements</h4>
                  <ul className="text-xs text-blue-700 space-y-1">
                    <li>• At least 8 characters long</li>
                    <li>• Include uppercase and lowercase letters</li>
                    <li>• Include at least one number</li>
                    <li>• Include at least one special character</li>
                  </ul>
                </div>

                {/* Update Password Button */}
                <div className="pt-4">
                  <motion.button
                    onClick={handleUpdatePassword}
                    disabled={isLoading}
                    whileHover={{ scale: isLoading ? 1 : 1.02 }}
                    whileTap={{ scale: isLoading ? 1 : 0.98 }}
                    className={`
                      flex items-center gap-2 px-6 py-3 border border-transparent rounded-xl
                      text-sm font-medium text-white transition-all duration-200
                      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                      ${isLoading 
                        ? 'bg-blue-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
                      }
                    `}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Updating...
                      </>
                    ) : (
                      <>
                        <Lock className="h-4 w-4" />
                        Update Password
                      </>
                    )}
                  </motion.button>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'account' && (
          <motion.div
            key="account"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-6">
                <Shield className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">Account Settings</h2>
              </div>

              <div className="space-y-6">
                {/* Account Information */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Account Status</label>
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                      <span className="text-sm text-gray-600">Active</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Account Type</label>
                    <span className="text-sm text-gray-600 capitalize">{authHook.user?.role || 'User'}</span>
                  </div>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Member Since</label>
                    <span className="text-sm text-gray-600">
                      {authHook.user?.createdAt 
                        ? new Date(authHook.user.createdAt).toLocaleDateString()
                        : 'N/A'
                      }
                    </span>
                  </div>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Email Status</label>
                    <div className="flex items-center gap-2">
                      <div className={`h-2 w-2 rounded-full ${authHook.isEmailVerified() ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                      <span className="text-sm text-gray-600">
                        {authHook.isEmailVerified() ? 'Verified' : 'Pending verification'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Delete Account */}
                <div className="border-t border-gray-200 pt-6">
                  <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <h3 className="text-sm font-medium text-red-900 mb-1">Delete Account</h3>
                        <p className="text-sm text-red-700 mb-4">
                          Permanently delete your account and all associated data. This action cannot be undone.
                        </p>
                        <motion.button
                          onClick={() => setShowDeleteConfirmation(true)}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                          Delete Account
                        </motion.button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'data' && (
          <motion.div
            key="data"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-6">
                <Download className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-semibold text-gray-900">Data Export</h2>
              </div>

              <div className="space-y-6">
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <Download className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-blue-900 mb-1">Export Your Data</h3>
                      <p className="text-sm text-blue-700 mb-4">
                        Download a copy of your personal data including profile information, learning progress, and account settings.
                      </p>
                      <motion.button
                        onClick={handleExportData}
                        disabled={isExporting}
                        whileHover={{ scale: isExporting ? 1 : 1.02 }}
                        whileTap={{ scale: isExporting ? 1 : 0.98 }}
                        className={`
                          flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors
                          ${isExporting 
                            ? 'bg-blue-400 text-white cursor-not-allowed' 
                            : 'bg-blue-600 text-white hover:bg-blue-700'
                          }
                        `}
                      >
                        {isExporting ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Exporting...
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4" />
                            Export Data
                          </>
                        )}
                      </motion.button>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                  <h3 className="text-sm font-medium text-gray-900 mb-2">What&apos;s included in your export:</h3>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• Profile information (name, email, preferences)</li>
                    <li>• Account settings and configuration</li>
                    <li>• Learning progress and achievements</li>
                    <li>• Activity history and statistics</li>
                    <li>• Account creation date and metadata</li>
                  </ul>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteConfirmation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-xl p-6 max-w-md w-full"
            >
              <div className="flex items-center gap-3 mb-4">
                <AlertCircle className="h-6 w-6 text-red-500" />
                <h3 className="text-lg font-semibold text-gray-900">Delete Account</h3>
              </div>
              
              <p className="text-sm text-gray-600 mb-6">
                Are you sure you want to delete your account? This action cannot be undone and all your data will be permanently removed.
              </p>
              
              <div className="flex gap-3">
                <motion.button
                  onClick={() => setShowDeleteConfirmation(false)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </motion.button>
                <motion.button
                  onClick={handleDeleteAccount}
                  disabled={isLoading}
                  whileHover={{ scale: isLoading ? 1 : 1.02 }}
                  whileTap={{ scale: isLoading ? 1 : 0.98 }}
                  className={`
                    flex-1 px-4 py-2 text-white rounded-lg transition-colors
                    ${isLoading 
                      ? 'bg-red-400 cursor-not-allowed' 
                      : 'bg-red-600 hover:bg-red-700'
                    }
                  `}
                >
                  {isLoading ? (
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Deleting...
                    </div>
                  ) : (
                    'Delete Account'
                  )}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}