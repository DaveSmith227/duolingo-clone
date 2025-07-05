import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { RegisterForm } from './RegisterForm'

// Mock the auth module
vi.mock('@/lib/supabase', () => ({
  auth: {
    signUp: vi.fn(),
    signInWithOAuth: vi.fn()
  }
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>
  },
  AnimatePresence: ({ children }: any) => <>{children}</>
}))

import { auth } from '@/lib/supabase'

const mockAuth = auth as any

describe('RegisterForm', () => {
  const mockOnSuccess = vi.fn()
  const mockOnError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  const renderRegisterForm = (props = {}) => {
    return render(
      <RegisterForm
        onSuccess={mockOnSuccess}
        onError={mockOnError}
        {...props}
      />
    )
  }

  const fillValidForm = async () => {
    const user = userEvent.setup()
    
    await user.type(screen.getByLabelText(/email address/i), 'test@example.com')
    await user.type(screen.getByLabelText(/first name/i), 'John')
    await user.type(screen.getByLabelText(/^password$/i), 'Password123!')
    await user.type(screen.getByLabelText(/confirm password/i), 'Password123!')
    await user.click(screen.getByLabelText(/agree to.*terms of service/i))
    await user.click(screen.getByLabelText(/agree to.*privacy policy/i))

    return user
  }

  describe('Rendering', () => {
    it('renders registration form with all elements', () => {
      renderRegisterForm()

      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/first name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/agree to.*terms of service/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/agree to.*privacy policy/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    })

    it('renders social registration buttons by default', () => {
      renderRegisterForm()

      expect(screen.getByText(/or sign up with/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /apple/i })).toBeInTheDocument()
    })

    it('hides social registration buttons when showSocialButtons is false', () => {
      renderRegisterForm({ showSocialButtons: false })

      expect(screen.queryByText(/or sign up with/i)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /google/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument()
    })

    it('shows password toggle buttons', () => {
      renderRegisterForm()

      const passwordToggles = screen.getAllByRole('button', { name: '' }) // Eye icon buttons
      expect(passwordToggles).toHaveLength(2) // One for password, one for confirm password
    })

    it('displays privacy notice section', () => {
      renderRegisterForm()

      expect(screen.getByText(/privacy & terms/i)).toBeInTheDocument()
      expect(screen.getByText(/by creating an account/i)).toBeInTheDocument()
      expect(screen.getByText(/never sell your personal information/i)).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    describe('Email Validation', () => {
      it('validates email field on submit', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/email is required/i)).toBeInTheDocument()
        })
      })

      it('validates email format', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const emailInput = screen.getByLabelText(/email address/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(emailInput, 'invalid-email')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
        })
      })
    })

    describe('First Name Validation', () => {
      it('validates first name field on submit', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/first name is required/i)).toBeInTheDocument()
        })
      })

      it('validates first name length', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const firstNameInput = screen.getByLabelText(/first name/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(firstNameInput, 'A')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/first name must be at least 2 characters/i)).toBeInTheDocument()
        })
      })

      it('validates first name format', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const firstNameInput = screen.getByLabelText(/first name/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(firstNameInput, 'John123')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/first name can only contain letters/i)).toBeInTheDocument()
        })
      })
    })

    describe('Password Validation', () => {
      it('validates password field on submit', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/password is required/i)).toBeInTheDocument()
        })
      })

      it('validates password strength', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const passwordInput = screen.getByLabelText(/^password$/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(passwordInput, 'weak')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/password must be at least 8 characters long/i)).toBeInTheDocument()
        })
      })

      it('shows password strength indicator', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const passwordInput = screen.getByLabelText(/^password$/i)
        
        // Type a weak password
        await user.type(passwordInput, 'password')
        expect(screen.getByText(/weak/i)).toBeInTheDocument()

        // Clear and type a strong password
        await user.clear(passwordInput)
        await user.type(passwordInput, 'StrongPass123!')
        expect(screen.getByText(/strong/i)).toBeInTheDocument()
      })
    })

    describe('Confirm Password Validation', () => {
      it('validates confirm password field on submit', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const passwordInput = screen.getByLabelText(/^password$/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(passwordInput, 'Password123!')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/please confirm your password/i)).toBeInTheDocument()
        })
      })

      it('validates password match', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        const passwordInput = screen.getByLabelText(/^password$/i)
        const confirmPasswordInput = screen.getByLabelText(/confirm password/i)
        const submitButton = screen.getByRole('button', { name: /create account/i })

        await user.type(passwordInput, 'Password123!')
        await user.type(confirmPasswordInput, 'DifferentPassword123!')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
        })
      })
    })

    describe('Terms and Privacy Validation', () => {
      it('validates terms of service agreement', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        await user.type(screen.getByLabelText(/email address/i), 'test@example.com')
        await user.type(screen.getByLabelText(/first name/i), 'John')
        await user.type(screen.getByLabelText(/^password$/i), 'Password123!')
        await user.type(screen.getByLabelText(/confirm password/i), 'Password123!')
        // Don't check terms and privacy

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/you must agree to the terms of service/i)).toBeInTheDocument()
        })
      })

      it('validates privacy policy agreement', async () => {
        renderRegisterForm()
        const user = userEvent.setup()

        await user.type(screen.getByLabelText(/email address/i), 'test@example.com')
        await user.type(screen.getByLabelText(/first name/i), 'John')
        await user.type(screen.getByLabelText(/^password$/i), 'Password123!')
        await user.type(screen.getByLabelText(/confirm password/i), 'Password123!')
        await user.click(screen.getByLabelText(/agree to.*terms of service/i))
        // Don't check privacy policy

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(/you must agree to the privacy policy/i)).toBeInTheDocument()
        })
      })
    })

    it('clears field errors when user starts typing', async () => {
      renderRegisterForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /create account/i })

      // Trigger validation error
      await user.click(submitButton)
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })

      // Start typing to clear error
      await user.type(emailInput, 'test@example.com')
      await waitFor(() => {
        expect(screen.queryByText(/email is required/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Password Visibility Toggle', () => {
    it('toggles password visibility when eye icon is clicked', async () => {
      renderRegisterForm()
      const user = userEvent.setup()

      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      const toggleButtons = screen.getAllByRole('button', { name: '' }) // Eye icon buttons
      const passwordToggle = toggleButtons[0] // First toggle for password field

      // Initially password field should be type="password"
      expect(passwordInput.type).toBe('password')

      // Click to show password
      await user.click(passwordToggle)
      expect(passwordInput.type).toBe('text')

      // Click to hide password
      await user.click(passwordToggle)
      expect(passwordInput.type).toBe('password')
    })

    it('toggles confirm password visibility when eye icon is clicked', async () => {
      renderRegisterForm()
      const user = userEvent.setup()

      const confirmPasswordInput = screen.getByLabelText(/confirm password/i) as HTMLInputElement
      const toggleButtons = screen.getAllByRole('button', { name: '' }) // Eye icon buttons
      const confirmPasswordToggle = toggleButtons[1] // Second toggle for confirm password field

      // Initially confirm password field should be type="password"
      expect(confirmPasswordInput.type).toBe('password')

      // Click to show password
      await user.click(confirmPasswordToggle)
      expect(confirmPasswordInput.type).toBe('text')

      // Click to hide password
      await user.click(confirmPasswordToggle)
      expect(confirmPasswordInput.type).toBe('password')
    })
  })

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      mockAuth.signUp.mockResolvedValue({
        user: { id: '123', email: 'test@example.com' },
        session: null,
        error: null
      })

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockAuth.signUp).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'Password123!',
          firstName: 'John',
          metadata: {
            agreed_to_terms: true,
            agreed_to_privacy: true,
            terms_version: '1.0',
            privacy_version: '1.0'
          }
        })
      })

      expect(mockOnSuccess).toHaveBeenCalledWith({
        id: '123',
        email: 'test@example.com'
      })
    })

    it('shows loading state during submission', async () => {
      mockAuth.signUp.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      await user.click(submitButton)

      expect(screen.getByText(/creating account.../i)).toBeInTheDocument()
      expect(submitButton).toBeDisabled()

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText(/creating account.../i)).not.toBeInTheDocument()
      })
    })

    it('handles registration errors', async () => {
      mockAuth.signUp.mockResolvedValue({
        user: null,
        session: null,
        error: 'User already registered'
      })

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/an account with this email address already exists/i)).toBeInTheDocument()
      })

      expect(mockOnError).toHaveBeenCalledWith('An account with this email address already exists. Please try signing in instead.')
    })

    it('handles unexpected errors', async () => {
      mockAuth.signUp.mockRejectedValue(new Error('Network error'))

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/an unexpected error occurred/i)).toBeInTheDocument()
      })

      expect(mockOnError).toHaveBeenCalledWith('An unexpected error occurred. Please try again.')
    })

    it('disables form during submission', async () => {
      mockAuth.signUp.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      await user.click(submitButton)

      expect(screen.getByLabelText(/email address/i)).toBeDisabled()
      expect(screen.getByLabelText(/first name/i)).toBeDisabled()
      expect(screen.getByLabelText(/^password$/i)).toBeDisabled()
      expect(screen.getByLabelText(/confirm password/i)).toBeDisabled()
      expect(submitButton).toBeDisabled()

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByLabelText(/email address/i)).not.toBeDisabled()
      })
    })
  })

  describe('Social Authentication', () => {
    it('handles Google OAuth registration', async () => {
      mockAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null })

      renderRegisterForm()
      const user = userEvent.setup()

      const googleButton = screen.getByRole('button', { name: /google/i })
      await user.click(googleButton)

      expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'google'
      })
    })

    it('handles Apple OAuth registration', async () => {
      mockAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null })

      renderRegisterForm()
      const user = userEvent.setup()

      const appleButton = screen.getByRole('button', { name: /apple/i })
      await user.click(appleButton)

      expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'apple'
      })
    })

    it('disables social buttons during form submission', async () => {
      mockAuth.signUp.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderRegisterForm()
      const user = await fillValidForm()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      const googleButton = screen.getByRole('button', { name: /google/i })
      const appleButton = screen.getByRole('button', { name: /apple/i })

      await user.click(submitButton)

      expect(googleButton).toBeDisabled()
      expect(appleButton).toBeDisabled()

      // Wait for loading to complete
      await waitFor(() => {
        expect(googleButton).not.toBeDisabled()
      })
    })
  })

  describe('Error Message Mapping', () => {
    const errorTestCases = [
      { supabaseError: 'Password is too weak', expectedMessage: 'Please choose a stronger password.' },
      { supabaseError: 'Invalid email', expectedMessage: 'Please enter a valid email address.' },
      { supabaseError: 'Signup is disabled', expectedMessage: 'New registrations are temporarily disabled. Please try again later.' },
      { supabaseError: 'Unknown error', expectedMessage: 'Registration failed. Please check your information and try again.' }
    ]

    errorTestCases.forEach(({ supabaseError, expectedMessage }) => {
      it(`maps "${supabaseError}" to user-friendly message`, async () => {
        mockAuth.signUp.mockResolvedValue({
          user: null,
          session: null,
          error: supabaseError
        })

        renderRegisterForm()
        const user = await fillValidForm()

        const submitButton = screen.getByRole('button', { name: /create account/i })
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(expectedMessage)).toBeInTheDocument()
        })
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      renderRegisterForm()

      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/first name/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/agree to.*terms of service/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/agree to.*privacy policy/i)).toBeInTheDocument()
    })

    it('has proper form attributes', () => {
      renderRegisterForm()

      const emailInput = screen.getByLabelText(/email address/i)
      const firstNameInput = screen.getByLabelText(/first name/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmPasswordInput = screen.getByLabelText(/confirm password/i)

      expect(emailInput).toHaveAttribute('type', 'email')
      expect(emailInput).toHaveAttribute('autoComplete', 'email')
      expect(emailInput).toBeRequired()

      expect(firstNameInput).toHaveAttribute('type', 'text')
      expect(firstNameInput).toHaveAttribute('autoComplete', 'given-name')
      expect(firstNameInput).toBeRequired()

      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(passwordInput).toHaveAttribute('autoComplete', 'new-password')
      expect(passwordInput).toBeRequired()

      expect(confirmPasswordInput).toHaveAttribute('type', 'password')
      expect(confirmPasswordInput).toHaveAttribute('autoComplete', 'new-password')
      expect(confirmPasswordInput).toBeRequired()
    })

    it('has proper link attributes for external links', () => {
      renderRegisterForm()

      const termsLink = screen.getByRole('link', { name: /terms of service/i })
      const privacyLink = screen.getByRole('link', { name: /privacy policy/i })

      expect(termsLink).toHaveAttribute('target', '_blank')
      expect(termsLink).toHaveAttribute('rel', 'noopener noreferrer')
      expect(privacyLink).toHaveAttribute('target', '_blank')
      expect(privacyLink).toHaveAttribute('rel', 'noopener noreferrer')
    })
  })
})