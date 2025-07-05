import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { ProfileManagement } from './ProfileManagement'

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({
    push: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn()
  }))
}))

// Mock the auth hook
vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn()
}))

// Mock Supabase auth
vi.mock('@/lib/supabase', () => ({
  auth: {
    updateUser: vi.fn(),
    deleteUser: vi.fn()
  }
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

import { useAuth } from '@/hooks/useAuth'
import { auth } from '@/lib/supabase'

const mockUseAuth = useAuth as any
const mockAuth = auth as any

describe('ProfileManagement', () => {
  const mockUser = {
    id: '123',
    email: 'test@example.com',
    firstName: 'John',
    lastName: 'Doe',
    role: 'user',
    isEmailVerified: true,
    createdAt: '2023-01-01T00:00:00.000Z'
  }

  const mockAuthHook = {
    user: mockUser,
    session: null,
    isLoading: false,
    isInitialized: true,
    error: null,
    isAuthenticated: true,
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    clearError: vi.fn(),
    updateUserProfile: vi.fn(),
    hasRole: vi.fn(),
    hasPermission: vi.fn(),
    isEmailVerified: vi.fn(() => true),
    getUserInitials: vi.fn(() => 'JD'),
    getUserDisplayName: vi.fn(() => 'John Doe'),
    needsOnboarding: vi.fn(() => false)
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue(mockAuthHook)
    mockAuth.updateUser.mockResolvedValue({ error: null })
    mockAuth.deleteUser.mockResolvedValue({ error: null })
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('Tab Navigation', () => {
    it('renders all tabs', () => {
      render(<ProfileManagement />)

      expect(screen.getByText('Profile')).toBeInTheDocument()
      expect(screen.getByText('Password')).toBeInTheDocument()
      expect(screen.getByText('Account')).toBeInTheDocument()
      expect(screen.getByText('Data')).toBeInTheDocument()
    })

    it('switches between tabs correctly', () => {
      render(<ProfileManagement />)

      // Default tab is Profile
      expect(screen.getByText('Profile Information')).toBeInTheDocument()

      // Switch to Password tab
      fireEvent.click(screen.getByText('Password'))
      expect(screen.getByText('Change Password')).toBeInTheDocument()

      // Switch to Account tab
      fireEvent.click(screen.getByText('Account'))
      expect(screen.getByText('Account Settings')).toBeInTheDocument()

      // Switch to Data tab
      fireEvent.click(screen.getByText('Data'))
      expect(screen.getByText('Data Export')).toBeInTheDocument()
    })
  })

  describe('Profile Tab', () => {
    it('displays user information correctly', () => {
      render(<ProfileManagement />)

      expect(screen.getByDisplayValue('John')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Doe')).toBeInTheDocument()
      expect(screen.getByDisplayValue('test@example.com')).toBeInTheDocument()
      expect(screen.getByText('JD')).toBeInTheDocument()
      expect(screen.getByText('Email verified')).toBeInTheDocument()
    })

    it('validates required fields', async () => {
      render(<ProfileManagement />)

      // Clear first name
      const firstNameInput = screen.getByDisplayValue('John')
      fireEvent.change(firstNameInput, { target: { value: '' } })

      // Try to save
      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(screen.getByText('First name is required')).toBeInTheDocument()
      })
    })

    it('validates email format', async () => {
      render(<ProfileManagement />)

      // Enter invalid email
      const emailInput = screen.getByDisplayValue('test@example.com')
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })

      // Try to save
      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
      })
    })

    it('updates profile successfully', async () => {
      const onSuccess = vi.fn()
      render(<ProfileManagement onSuccess={onSuccess} />)

      // Change first name
      const firstNameInput = screen.getByDisplayValue('John')
      fireEvent.change(firstNameInput, { target: { value: 'Johnny' } })

      // Save changes
      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(mockAuthHook.updateUserProfile).toHaveBeenCalledWith({
          firstName: 'Johnny',
          lastName: 'Doe',
          email: 'test@example.com'
        })
        expect(onSuccess).toHaveBeenCalledWith('Profile updated successfully')
      })
    })

    it('handles profile update errors', async () => {
      const onError = vi.fn()
      mockAuthHook.updateUserProfile.mockRejectedValue(new Error('Update failed'))

      render(<ProfileManagement onError={onError} />)

      // Save changes
      fireEvent.click(screen.getByText('Save Changes'))

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Update failed')
      })
    })
  })

  describe('Password Tab', () => {
    beforeEach(() => {
      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Password'))
    })

    it('renders password form fields', () => {
      expect(screen.getByLabelText('Current Password')).toBeInTheDocument()
      expect(screen.getByLabelText('New Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm New Password')).toBeInTheDocument()
    })

    it('toggles password visibility', () => {
      const currentPasswordInput = screen.getByLabelText('Current Password')
      const toggleButtons = screen.getAllByRole('button', { name: '' })

      // Initially password type
      expect(currentPasswordInput).toHaveAttribute('type', 'password')

      // Click toggle button
      fireEvent.click(toggleButtons[0])
      expect(currentPasswordInput).toHaveAttribute('type', 'text')

      // Click again to hide
      fireEvent.click(toggleButtons[0])
      expect(currentPasswordInput).toHaveAttribute('type', 'password')
    })

    it('validates password requirements', async () => {
      const currentPasswordInput = screen.getByLabelText('Current Password')
      const newPasswordInput = screen.getByLabelText('New Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm New Password')

      fireEvent.change(currentPasswordInput, { target: { value: 'currentpass' } })
      fireEvent.change(newPasswordInput, { target: { value: 'short' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'different' } })

      fireEvent.click(screen.getByText('Update Password'))

      await waitFor(() => {
        expect(screen.getByText('New password must be at least 8 characters')).toBeInTheDocument()
        expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
      })
    })

    it('updates password successfully', async () => {
      const onSuccess = vi.fn()
      render(<ProfileManagement onSuccess={onSuccess} />)
      fireEvent.click(screen.getByText('Password'))

      const currentPasswordInput = screen.getByLabelText('Current Password')
      const newPasswordInput = screen.getByLabelText('New Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm New Password')

      fireEvent.change(currentPasswordInput, { target: { value: 'currentpass' } })
      fireEvent.change(newPasswordInput, { target: { value: 'newpassword123' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'newpassword123' } })

      fireEvent.click(screen.getByText('Update Password'))

      await waitFor(() => {
        expect(mockAuth.updateUser).toHaveBeenCalledWith({
          password: 'newpassword123'
        })
        expect(onSuccess).toHaveBeenCalledWith('Password updated successfully')
      })
    })

    it('handles password update errors', async () => {
      const onError = vi.fn()
      mockAuth.updateUser.mockResolvedValue({ error: { message: 'Password update failed' } })

      render(<ProfileManagement onError={onError} />)
      fireEvent.click(screen.getByText('Password'))

      const currentPasswordInput = screen.getByLabelText('Current Password')
      const newPasswordInput = screen.getByLabelText('New Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm New Password')

      fireEvent.change(currentPasswordInput, { target: { value: 'currentpass' } })
      fireEvent.change(newPasswordInput, { target: { value: 'newpassword123' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'newpassword123' } })

      fireEvent.click(screen.getByText('Update Password'))

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Password update failed')
      })
    })
  })

  describe('Account Tab', () => {
    beforeEach(() => {
      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Account'))
    })

    it('displays account information', () => {
      expect(screen.getByText('Active')).toBeInTheDocument()
      expect(screen.getByText('User')).toBeInTheDocument()
      expect(screen.getByText('Verified')).toBeInTheDocument()
    })

    it('shows delete account section', () => {
      expect(screen.getByText('Delete Account')).toBeInTheDocument()
      expect(screen.getByText('Permanently delete your account and all associated data. This action cannot be undone.')).toBeInTheDocument()
    })

    it('opens delete confirmation modal', () => {
      const deleteButton = screen.getByRole('button', { name: 'Delete Account' })
      fireEvent.click(deleteButton)

      expect(screen.getByText('Are you sure you want to delete your account?')).toBeInTheDocument()
    })

    it('cancels account deletion', () => {
      const deleteButton = screen.getByRole('button', { name: 'Delete Account' })
      fireEvent.click(deleteButton)

      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      fireEvent.click(cancelButton)

      expect(screen.queryByText('Are you sure you want to delete your account?')).not.toBeInTheDocument()
    })

    it('deletes account successfully', async () => {
      const onSuccess = vi.fn()
      render(<ProfileManagement onSuccess={onSuccess} />)
      fireEvent.click(screen.getByText('Account'))

      const deleteButton = screen.getByRole('button', { name: 'Delete Account' })
      fireEvent.click(deleteButton)

      const confirmDeleteButton = screen.getAllByText('Delete Account')[1]
      fireEvent.click(confirmDeleteButton)

      await waitFor(() => {
        expect(mockAuth.deleteUser).toHaveBeenCalled()
        expect(mockAuthHook.signOut).toHaveBeenCalled()
        expect(onSuccess).toHaveBeenCalledWith('Account deleted successfully')
      })
    })

    it('handles account deletion errors', async () => {
      const onError = vi.fn()
      mockAuth.deleteUser.mockResolvedValue({ error: { message: 'Deletion failed' } })

      render(<ProfileManagement onError={onError} />)
      fireEvent.click(screen.getByText('Account'))

      const deleteButton = screen.getByRole('button', { name: 'Delete Account' })
      fireEvent.click(deleteButton)

      const confirmDeleteButton = screen.getAllByText('Delete Account')[1]
      fireEvent.click(confirmDeleteButton)

      await waitFor(() => {
        expect(onError).toHaveBeenCalledWith('Deletion failed')
      })
    })
  })

  describe('Data Tab', () => {
    beforeEach(() => {
      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Data'))
    })

    it('displays data export section', () => {
      expect(screen.getByText('Data Export')).toBeInTheDocument()
      expect(screen.getByText('Export Your Data')).toBeInTheDocument()
      expect(screen.getByText('Download a copy of your personal data')).toBeInTheDocument()
    })

    it('shows what is included in export', () => {
      expect(screen.getByText('Profile information (name, email, preferences)')).toBeInTheDocument()
      expect(screen.getByText('Account settings and configuration')).toBeInTheDocument()
      expect(screen.getByText('Learning progress and achievements')).toBeInTheDocument()
    })

    it('exports data successfully', async () => {
      const onSuccess = vi.fn()
      
      // Mock document.createElement and click
      const mockLink = {
        setAttribute: vi.fn(),
        click: vi.fn()
      }
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink as any)

      render(<ProfileManagement onSuccess={onSuccess} />)
      fireEvent.click(screen.getByText('Data'))

      const exportButton = screen.getByRole('button', { name: 'Export Data' })
      fireEvent.click(exportButton)

      await waitFor(() => {
        expect(mockLink.setAttribute).toHaveBeenCalledWith('href', expect.stringContaining('data:application/json'))
        expect(mockLink.setAttribute).toHaveBeenCalledWith('download', expect.stringContaining('duolingo-user-data-'))
        expect(mockLink.click).toHaveBeenCalled()
        expect(onSuccess).toHaveBeenCalledWith('Data exported successfully')
      })
    })
  })

  describe('Error Handling', () => {
    it('displays general errors', () => {
      render(<ProfileManagement />)

      // Simulate error state
      mockAuthHook.updateUserProfile.mockRejectedValue(new Error('Network error'))

      fireEvent.click(screen.getByText('Save Changes'))

      waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })

    it('clears field errors when user types', () => {
      render(<ProfileManagement />)

      const firstNameInput = screen.getByDisplayValue('John')
      
      // Clear field to trigger error
      fireEvent.change(firstNameInput, { target: { value: '' } })
      fireEvent.click(screen.getByText('Save Changes'))

      waitFor(() => {
        expect(screen.getByText('First name is required')).toBeInTheDocument()
      })

      // Type to clear error
      fireEvent.change(firstNameInput, { target: { value: 'J' } })

      waitFor(() => {
        expect(screen.queryByText('First name is required')).not.toBeInTheDocument()
      })
    })
  })

  describe('Loading States', () => {
    it('shows loading state during profile update', async () => {
      mockAuthHook.updateUserProfile.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      render(<ProfileManagement />)

      fireEvent.click(screen.getByText('Save Changes'))

      expect(screen.getByText('Saving...')).toBeInTheDocument()
    })

    it('shows loading state during password update', async () => {
      mockAuth.updateUser.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Password'))

      const currentPasswordInput = screen.getByLabelText('Current Password')
      const newPasswordInput = screen.getByLabelText('New Password')
      const confirmPasswordInput = screen.getByLabelText('Confirm New Password')

      fireEvent.change(currentPasswordInput, { target: { value: 'currentpass' } })
      fireEvent.change(newPasswordInput, { target: { value: 'newpassword123' } })
      fireEvent.change(confirmPasswordInput, { target: { value: 'newpassword123' } })

      fireEvent.click(screen.getByText('Update Password'))

      expect(screen.getByText('Updating...')).toBeInTheDocument()
    })

    it('shows loading state during account deletion', async () => {
      mockAuth.deleteUser.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Account'))

      const deleteButton = screen.getByRole('button', { name: 'Delete Account' })
      fireEvent.click(deleteButton)

      const confirmDeleteButton = screen.getAllByText('Delete Account')[1]
      fireEvent.click(confirmDeleteButton)

      expect(screen.getByText('Deleting...')).toBeInTheDocument()
    })

    it('shows loading state during data export', async () => {
      render(<ProfileManagement />)
      fireEvent.click(screen.getByText('Data'))

      const exportButton = screen.getByRole('button', { name: 'Export Data' })
      fireEvent.click(exportButton)

      expect(screen.getByText('Exporting...')).toBeInTheDocument()
    })
  })
})