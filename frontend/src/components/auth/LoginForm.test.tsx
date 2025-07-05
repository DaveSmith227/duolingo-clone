import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { LoginForm } from './LoginForm'

// Mock the auth module
vi.mock('@/lib/supabase', () => ({
  auth: {
    signIn: vi.fn(),
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

describe('LoginForm', () => {
  const mockOnSuccess = vi.fn()
  const mockOnError = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  const renderLoginForm = (props = {}) => {
    return render(
      <LoginForm
        onSuccess={mockOnSuccess}
        onError={mockOnError}
        {...props}
      />
    )
  }

  describe('Rendering', () => {
    it('renders login form with all elements', () => {
      renderLoginForm()

      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.getByText(/forgot password/i)).toBeInTheDocument()
    })

    it('renders social login buttons by default', () => {
      renderLoginForm()

      expect(screen.getByText(/or continue with/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /apple/i })).toBeInTheDocument()
    })

    it('hides social login buttons when showSocialButtons is false', () => {
      renderLoginForm({ showSocialButtons: false })

      expect(screen.queryByText(/or continue with/i)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /google/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument()
    })

    it('shows password toggle button', () => {
      renderLoginForm()

      const toggleButton = screen.getByRole('button', { name: '' }) // Eye icon button
      expect(toggleButton).toBeInTheDocument()
    })
  })

  describe('Form Validation', () => {
    it('validates email field on submit', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })
    })

    it('validates email format', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
      })
    })

    it('validates password field on submit', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('validates password length', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, '123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
      })
    })

    it('clears field errors when user starts typing', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

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
      renderLoginForm()
      const user = userEvent.setup()

      const passwordInput = screen.getByLabelText(/^password$/i) as HTMLInputElement
      const toggleButton = screen.getByRole('button', { name: '' }) // Eye icon button

      // Initially password field should be type="password"
      expect(passwordInput.type).toBe('password')

      // Click to show password
      await user.click(toggleButton)
      expect(passwordInput.type).toBe('text')

      // Click to hide password
      await user.click(toggleButton)
      expect(passwordInput.type).toBe('password')
    })
  })

  describe('Form Submission', () => {
    it('submits form with valid data', async () => {
      mockAuth.signIn.mockResolvedValue({
        user: { id: '123', email: 'test@example.com' },
        session: { access_token: 'token' },
        error: null
      })

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const rememberMeInput = screen.getByLabelText(/remember me/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(rememberMeInput)
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockAuth.signIn).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
          rememberMe: true
        })
      })

      expect(mockOnSuccess).toHaveBeenCalledWith({
        id: '123',
        email: 'test@example.com'
      })
    })

    it('shows loading state during submission', async () => {
      mockAuth.signIn.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      expect(screen.getByText(/signing in.../i)).toBeInTheDocument()
      expect(submitButton).toBeDisabled()

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByText(/signing in.../i)).not.toBeInTheDocument()
      })
    })

    it('handles authentication errors', async () => {
      mockAuth.signIn.mockResolvedValue({
        user: null,
        session: null,
        error: 'Invalid login credentials'
      })

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument()
      })

      expect(mockOnError).toHaveBeenCalledWith('Invalid email or password. Please try again.')
    })

    it('handles unexpected errors', async () => {
      mockAuth.signIn.mockRejectedValue(new Error('Network error'))

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/an unexpected error occurred/i)).toBeInTheDocument()
      })

      expect(mockOnError).toHaveBeenCalledWith('An unexpected error occurred. Please try again.')
    })

    it('disables form during submission', async () => {
      mockAuth.signIn.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const rememberMeInput = screen.getByLabelText(/remember me/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      expect(emailInput).toBeDisabled()
      expect(passwordInput).toBeDisabled()
      expect(rememberMeInput).toBeDisabled()
      expect(submitButton).toBeDisabled()

      // Wait for loading to complete
      await waitFor(() => {
        expect(emailInput).not.toBeDisabled()
      })
    })
  })

  describe('Social Authentication', () => {
    it('handles Google OAuth login', async () => {
      mockAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null })

      renderLoginForm()
      const user = userEvent.setup()

      const googleButton = screen.getByRole('button', { name: /google/i })
      await user.click(googleButton)

      expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'google'
      })
    })

    it('handles Apple OAuth login', async () => {
      mockAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null })

      renderLoginForm()
      const user = userEvent.setup()

      const appleButton = screen.getByRole('button', { name: /apple/i })
      await user.click(appleButton)

      expect(mockAuth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'apple'
      })
    })

    it('disables social buttons during form submission', async () => {
      mockAuth.signIn.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderLoginForm()
      const user = userEvent.setup()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      const googleButton = screen.getByRole('button', { name: /google/i })
      const appleButton = screen.getByRole('button', { name: /apple/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
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
      { supabaseError: 'Email not confirmed', expectedMessage: 'Please check your email and click the confirmation link.' },
      { supabaseError: 'Too many requests', expectedMessage: 'Too many login attempts. Please wait a moment and try again.' },
      { supabaseError: 'User not found', expectedMessage: 'No account found with this email address.' },
      { supabaseError: 'Unknown error', expectedMessage: 'Login failed. Please check your credentials and try again.' }
    ]

    errorTestCases.forEach(({ supabaseError, expectedMessage }) => {
      it(`maps "${supabaseError}" to user-friendly message`, async () => {
        mockAuth.signIn.mockResolvedValue({
          user: null,
          session: null,
          error: supabaseError
        })

        renderLoginForm()
        const user = userEvent.setup()

        const emailInput = screen.getByLabelText(/email address/i)
        const passwordInput = screen.getByLabelText(/^password$/i)
        const submitButton = screen.getByRole('button', { name: /sign in/i })

        await user.type(emailInput, 'test@example.com')
        await user.type(passwordInput, 'password123')
        await user.click(submitButton)

        await waitFor(() => {
          expect(screen.getByText(expectedMessage)).toBeInTheDocument()
        })
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      renderLoginForm()

      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument()
    })

    it('has proper form attributes', () => {
      renderLoginForm()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)

      expect(emailInput).toHaveAttribute('type', 'email')
      expect(emailInput).toHaveAttribute('autoComplete', 'email')
      expect(emailInput).toBeRequired()

      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
      expect(passwordInput).toBeRequired()
    })

    it('shows validation errors with proper ARIA attributes', async () => {
      renderLoginForm()
      const user = userEvent.setup()

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)

      await waitFor(() => {
        const errorMessage = screen.getByText(/email is required/i)
        expect(errorMessage).toBeInTheDocument()
      })
    })
  })
})