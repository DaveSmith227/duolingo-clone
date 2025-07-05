import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { UserActionDialog, UserActionType } from './UserActionDialog'

const mockUser = {
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  is_active: true,
  is_suspended: false,
  roles: ['user']
}

const mockOnClose = vi.fn()
const mockOnConfirm = vi.fn()

describe('UserActionDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockOnConfirm.mockResolvedValue(undefined)
  })

  describe('Rendering and basic functionality', () => {
    it('should not render when isOpen is false', () => {
      render(
        <UserActionDialog
          isOpen={false}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      expect(screen.queryByText('Suspend User')).not.toBeInTheDocument()
    })

    it('should render when isOpen is true', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      expect(screen.getByText('Suspend User')).toBeInTheDocument()
      expect(screen.getByText('Test User (test@example.com)')).toBeInTheDocument()
    })

    it('should call onClose when cancel button is clicked', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('should call onClose when X button is clicked', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const closeButton = screen.getByRole('button', { name: '' })
      fireEvent.click(closeButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('should call onClose when background overlay is clicked', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const overlay = document.querySelector('.bg-gray-500')
      if (overlay) {
        fireEvent.click(overlay)
      }

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Action types and configurations', () => {
    const actionTypes: UserActionType[] = ['suspend', 'unsuspend', 'delete', 'reset_password', 'force_logout', 'change_role']

    actionTypes.forEach(action => {
      it(`should render correct content for ${action} action`, () => {
        render(
          <UserActionDialog
            isOpen={true}
            onClose={mockOnClose}
            onConfirm={mockOnConfirm}
            user={mockUser}
            action={action}
          />
        )

        // Check that action-specific content is rendered
        switch (action) {
          case 'suspend':
            expect(screen.getByText('Suspend User')).toBeInTheDocument()
            expect(screen.getByText(/prevent the user from logging in/)).toBeInTheDocument()
            break
          case 'unsuspend':
            expect(screen.getByText('Unsuspend User')).toBeInTheDocument()
            expect(screen.getByText(/restore the user\'s access/)).toBeInTheDocument()
            break
          case 'delete':
            expect(screen.getByText('Delete User Account')).toBeInTheDocument()
            expect(screen.getByText(/permanently delete the user account/)).toBeInTheDocument()
            expect(screen.getByText(/This action is irreversible/)).toBeInTheDocument()
            break
          case 'reset_password':
            expect(screen.getByText('Reset Password')).toBeInTheDocument()
            expect(screen.getByText(/send a password reset email/)).toBeInTheDocument()
            break
          case 'force_logout':
            expect(screen.getByText('Force Logout')).toBeInTheDocument()
            expect(screen.getByText(/terminate all active sessions/)).toBeInTheDocument()
            break
          case 'change_role':
            expect(screen.getByText('Change User Role')).toBeInTheDocument()
            expect(screen.getByText(/update the user\'s role/)).toBeInTheDocument()
            expect(screen.getByText('New Role *')).toBeInTheDocument()
            break
        }
      })
    })

    it('should show confirmation field for delete action', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="delete"
        />
      )

      expect(screen.getByText('Type the user\'s email address to confirm *')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('test@example.com')).toBeInTheDocument()
    })

    it('should show role selection for change_role action', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="change_role"
        />
      )

      expect(screen.getByText('New Role *')).toBeInTheDocument()
      expect(screen.getByText('Select a role...')).toBeInTheDocument()
      expect(screen.getByText('Current roles: user')).toBeInTheDocument()
    })
  })

  describe('Form validation', () => {
    it('should validate required reason field', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const submitButton = screen.getByText('Suspend User')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Reason is required')).toBeInTheDocument()
      })

      expect(mockOnConfirm).not.toHaveBeenCalled()
    })

    it('should validate confirmation email for delete action', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="delete"
        />
      )

      // Fill in reason but not confirmation
      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Test reason' } })

      const submitButton = screen.getByText('Delete Account')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Please type the user\'s email address to confirm')).toBeInTheDocument()
      })

      expect(mockOnConfirm).not.toHaveBeenCalled()
    })

    it('should validate role selection for change_role action', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="change_role"
        />
      )

      // Fill in reason but not role
      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Test reason' } })

      const submitButton = screen.getByText('Change Role')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Please select a role')).toBeInTheDocument()
      })

      expect(mockOnConfirm).not.toHaveBeenCalled()
    })

    it('should allow valid form submission for suspend action', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Valid suspension reason' } })

      const submitButton = screen.getByText('Suspend User')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalledWith('suspend', 'Valid suspension reason', {})
      })
    })

    it('should allow valid form submission for delete action', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="delete"
        />
      )

      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Valid deletion reason' } })

      const confirmationInput = screen.getByPlaceholderText('test@example.com')
      fireEvent.change(confirmationInput, { target: { value: 'test@example.com' } })

      const submitButton = screen.getByText('Delete Account')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalledWith('delete', 'Valid deletion reason', {})
      })
    })

    it('should allow valid form submission for change_role action', async () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="change_role"
        />
      )

      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Valid role change reason' } })

      const roleSelect = screen.getByDisplayValue('Select a role...')
      fireEvent.change(roleSelect, { target: { value: 'admin' } })

      const submitButton = screen.getByText('Change Role')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalledWith('change_role', 'Valid role change reason', { new_role: 'admin' })
      })
    })
  })

  describe('Loading states', () => {
    it('should show loading state on submit button when loading is true', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
          loading={true}
        />
      )

      expect(screen.getByText('Processing...')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Processing/ })).toBeDisabled()
    })

    it('should disable form inputs when loading is true', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="delete"
          loading={true}
        />
      )

      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      const confirmationInput = screen.getByPlaceholderText('test@example.com')
      const cancelButton = screen.getByText('Cancel')
      const closeButton = screen.getByRole('button', { name: '' })

      expect(reasonTextarea).toBeDisabled()
      expect(confirmationInput).toBeDisabled()
      expect(cancelButton).toBeDisabled()
      expect(closeButton).toBeDisabled()
    })
  })

  describe('Role selection functionality', () => {
    it('should filter out current user roles from available roles', () => {
      const userWithMultipleRoles = {
        ...mockUser,
        roles: ['user', 'instructor']
      }

      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={userWithMultipleRoles}
          action="change_role"
        />
      )

      const roleSelect = screen.getByDisplayValue('Select a role...')
      
      // Check that current roles are not in the options
      expect(screen.queryByText('User')).not.toBeInTheDocument()
      expect(screen.queryByText('Instructor')).not.toBeInTheDocument()
      
      // Check that other roles are available
      fireEvent.click(roleSelect)
      expect(screen.getByText('Moderator')).toBeInTheDocument()
      expect(screen.getByText('Admin')).toBeInTheDocument()
    })

    it('should display current roles correctly', () => {
      const userWithMultipleRoles = {
        ...mockUser,
        roles: ['user', 'instructor', 'moderator']
      }

      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={userWithMultipleRoles}
          action="change_role"
        />
      )

      expect(screen.getByText('Current roles: user, instructor, moderator')).toBeInTheDocument()
    })
  })

  describe('Form reset on close', () => {
    it('should reset form fields when dialog is closed and reopened', async () => {
      const { rerender } = render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      // Fill in form
      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Test reason' } })
      expect(reasonTextarea).toHaveValue('Test reason')

      // Close dialog
      const cancelButton = screen.getByText('Cancel')
      fireEvent.click(cancelButton)

      // Reopen dialog
      rerender(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      // Form should be reset
      const newReasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      expect(newReasonTextarea).toHaveValue('')
    })
  })

  describe('Error handling', () => {
    it('should handle onConfirm errors gracefully', async () => {
      const errorMessage = 'Action failed'
      mockOnConfirm.mockRejectedValue(new Error(errorMessage))

      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      const reasonTextarea = screen.getByPlaceholderText('Please provide a detailed reason for this action...')
      fireEvent.change(reasonTextarea, { target: { value: 'Valid reason' } })

      const submitButton = screen.getByText('Suspend User')
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockOnConfirm).toHaveBeenCalled()
      })

      // Dialog should not close on error
      expect(mockOnClose).not.toHaveBeenCalled()
    })
  })

  describe('Accessibility', () => {
    it('should have proper form labels', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="delete"
        />
      )

      expect(screen.getByLabelText('Reason for this action *')).toBeInTheDocument()
      expect(screen.getByLabelText('Type the user\'s email address to confirm *')).toBeInTheDocument()
    })

    it('should have proper button roles', () => {
      render(
        <UserActionDialog
          isOpen={true}
          onClose={mockOnClose}
          onConfirm={mockOnConfirm}
          user={mockUser}
          action="suspend"
        />
      )

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Suspend User' })).toBeInTheDocument()
    })
  })
})