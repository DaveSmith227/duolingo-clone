/**
 * Tests for RegisterForm component
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RegisterForm } from '../index'
import { auth } from '@/lib/supabase'

// Mock Supabase
jest.mock('@/lib/supabase', () => ({
  auth: {
    signUp: jest.fn()
  }
}))

// Mock Framer Motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
    p: ({ children, ...props }: any) => <p {...props}>{children}</p>
  }
}))

describe('RegisterForm', () => {
  const mockOnSuccess = jest.fn()
  const mockOnError = jest.fn()
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders all form fields', () => {
    render(<RegisterForm />)
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
    expect(screen.getByText(/terms of service/i)).toBeInTheDocument()
    expect(screen.getByText(/privacy policy/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('validates email format', async () => {
    render(<RegisterForm />)
    
    const emailInput = screen.getByLabelText(/email/i)
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    // Invalid email
    await user.type(emailInput, 'invalid-email')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/valid email address/i)).toBeInTheDocument()
    })
  })

  it('validates password strength', async () => {
    render(<RegisterForm />)
    
    const passwordInput = screen.getByLabelText('Password')
    
    // Type weak password
    await user.type(passwordInput, 'weak')
    
    // Should show password strength indicator
    await waitFor(() => {
      expect(screen.getByText(/password strength/i)).toBeInTheDocument()
      expect(screen.getByText(/very weak/i)).toBeInTheDocument()
    })
  })

  it('validates password confirmation', async () => {
    render(<RegisterForm />)
    
    const passwordInput = screen.getByLabelText('Password')
    const confirmInput = screen.getByLabelText(/confirm password/i)
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    await user.type(passwordInput, 'StrongP@ss123')
    await user.type(confirmInput, 'DifferentP@ss123')
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
  })

  it('requires consent checkboxes', async () => {
    render(<RegisterForm />)
    
    const submitButton = screen.getByRole('button', { name: /create account/i })
    
    // Fill valid data but don't check boxes
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/first name/i), 'Test')
    await user.type(screen.getByLabelText('Password'), 'StrongP@ss123')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongP@ss123')
    
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/agree to the terms of service/i)).toBeInTheDocument()
      expect(screen.getByText(/agree to the privacy policy/i)).toBeInTheDocument()
    })
  })

  it('successfully submits form with valid data', async () => {
    const mockUser = { id: '123', email: 'test@example.com' }
    ;(auth.signUp as jest.Mock).mockResolvedValue({
      user: mockUser,
      session: {},
      error: null
    })
    
    render(<RegisterForm onSuccess={mockOnSuccess} />)
    
    // Fill form
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/first name/i), 'Test')
    await user.type(screen.getByLabelText('Password'), 'StrongP@ss123')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongP@ss123')
    
    // Check consent boxes
    await user.click(screen.getByRole('checkbox', { name: /terms of service/i }))
    await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    
    // Submit
    await user.click(screen.getByRole('button', { name: /create account/i }))
    
    await waitFor(() => {
      expect(auth.signUp).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'StrongP@ss123',
        firstName: 'Test',
        metadata: expect.any(Object)
      })
      expect(mockOnSuccess).toHaveBeenCalledWith(mockUser)
    })
  })

  it('handles registration errors', async () => {
    const errorMessage = 'Email already exists'
    ;(auth.signUp as jest.Mock).mockResolvedValue({
      user: null,
      session: null,
      error: { message: errorMessage }
    })
    
    render(<RegisterForm onError={mockOnError} />)
    
    // Fill and submit form
    await user.type(screen.getByLabelText(/email/i), 'existing@example.com')
    await user.type(screen.getByLabelText(/first name/i), 'Test')
    await user.type(screen.getByLabelText('Password'), 'StrongP@ss123')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongP@ss123')
    await user.click(screen.getByRole('checkbox', { name: /terms of service/i }))
    await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    await user.click(screen.getByRole('button', { name: /create account/i }))
    
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
      expect(mockOnError).toHaveBeenCalledWith(errorMessage)
    })
  })

  it('shows loading state during submission', async () => {
    ;(auth.signUp as jest.Mock).mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 1000))
    )
    
    render(<RegisterForm />)
    
    // Fill minimum required fields
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/first name/i), 'Test')
    await user.type(screen.getByLabelText('Password'), 'StrongP@ss123')
    await user.type(screen.getByLabelText(/confirm password/i), 'StrongP@ss123')
    await user.click(screen.getByRole('checkbox', { name: /terms of service/i }))
    await user.click(screen.getByRole('checkbox', { name: /privacy policy/i }))
    
    // Submit
    await user.click(screen.getByRole('button', { name: /create account/i }))
    
    // Should show loading state
    expect(screen.getByText(/creating account/i)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('toggles password visibility', async () => {
    render(<RegisterForm />)
    
    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement
    const toggleButton = screen.getAllByRole('button', { name: /password/i })[0]
    
    // Initially password type
    expect(passwordInput.type).toBe('password')
    
    // Click toggle
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('text')
    
    // Click again
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('password')
  })

  it('renders social login buttons when enabled', () => {
    render(<RegisterForm showSocialButtons={true} />)
    
    expect(screen.getByText(/continue with google/i)).toBeInTheDocument()
    expect(screen.getByText(/continue with apple/i)).toBeInTheDocument()
    expect(screen.getByText(/continue with facebook/i)).toBeInTheDocument()
  })

  it('hides social login buttons when disabled', () => {
    render(<RegisterForm showSocialButtons={false} />)
    
    expect(screen.queryByText(/continue with google/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/continue with apple/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/continue with facebook/i)).not.toBeInTheDocument()
  })
})