import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginForm } from '../LoginForm';
import { useAuth } from '@/lib/hooks/useAuth';
import { useRouter } from 'next/navigation';

// Mock dependencies
jest.mock('@/lib/hooks/useAuth');
jest.mock('next/navigation');

const mockLogin = jest.fn();
const mockPush = jest.fn();

describe('LoginForm Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useAuth as jest.Mock).mockReturnValue({
      login: mockLogin,
      isLoading: false,
      error: null
    });
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush
    });
  });

  describe('Rendering', () => {
    it('should render all form elements', () => {
      render(<LoginForm />);
      
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument();
      expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/remember me/i)).toBeInTheDocument();
    });

    it('should render social login buttons', () => {
      render(<LoginForm />);
      
      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /apple/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /facebook/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /tiktok/i })).toBeInTheDocument();
    });

    it('should show loading state when isLoading is true', () => {
      (useAuth as jest.Mock).mockReturnValue({
        login: mockLogin,
        isLoading: true,
        error: null
      });
      
      render(<LoginForm />);
      
      const submitButton = screen.getByRole('button', { name: /logging in/i });
      expect(submitButton).toBeDisabled();
    });

    it('should display error message when error exists', () => {
      const errorMessage = 'Invalid credentials';
      (useAuth as jest.Mock).mockReturnValue({
        login: mockLogin,
        isLoading: false,
        error: errorMessage
      });
      
      render(<LoginForm />);
      
      expect(screen.getByRole('alert')).toHaveTextContent(errorMessage);
    });
  });

  describe('Form Validation', () => {
    it('should show validation error for empty email', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show validation error for invalid email format', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'invalid-email');
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      expect(await screen.findByText(/valid email/i)).toBeInTheDocument();
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show validation error for empty password', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      await user.type(emailInput, 'test@example.com');
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
      expect(mockLogin).not.toHaveBeenCalled();
    });

    it('should show validation error for short password', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'short');
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      expect(await screen.findByText(/at least 8 characters/i)).toBeInTheDocument();
      expect(mockLogin).not.toHaveBeenCalled();
    });
  });

  describe('Form Submission', () => {
    it('should call login with correct data on valid submission', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValueOnce({ success: true });
      
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const rememberCheckbox = screen.getByLabelText(/remember me/i);
      
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPassword123!');
      await user.click(rememberCheckbox);
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'ValidPassword123!',
          rememberMe: true
        });
      });
    });

    it('should redirect to dashboard on successful login', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValueOnce({ success: true });
      
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPassword123!');
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard');
      });
    });

    it('should handle login failure gracefully', async () => {
      const user = userEvent.setup();
      const errorMessage = 'Invalid credentials';
      mockLogin.mockRejectedValueOnce(new Error(errorMessage));
      
      render(<LoginForm />);
      
      const emailInput = screen.getByLabelText(/email/i);
      const passwordInput = screen.getByLabelText(/password/i);
      
      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'ValidPassword123!');
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(mockPush).not.toHaveBeenCalled();
      });
    });
  });

  describe('Password Visibility Toggle', () => {
    it('should toggle password visibility', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const passwordInput = screen.getByLabelText(/password/i);
      const toggleButton = screen.getByRole('button', { name: /toggle password/i });
      
      // Initially password should be hidden
      expect(passwordInput).toHaveAttribute('type', 'password');
      
      // Click toggle to show password
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');
      
      // Click again to hide password
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Social Login', () => {
    it('should handle Google login', async () => {
      const user = userEvent.setup();
      const mockSocialLogin = jest.fn();
      
      (useAuth as jest.Mock).mockReturnValue({
        login: mockLogin,
        socialLogin: mockSocialLogin,
        isLoading: false,
        error: null
      });
      
      render(<LoginForm />);
      
      const googleButton = screen.getByRole('button', { name: /google/i });
      await user.click(googleButton);
      
      expect(mockSocialLogin).toHaveBeenCalledWith('google');
    });

    it('should disable social buttons during loading', () => {
      (useAuth as jest.Mock).mockReturnValue({
        login: mockLogin,
        isLoading: true,
        error: null
      });
      
      render(<LoginForm />);
      
      const socialButtons = screen.getAllByRole('button', { name: /sign in with/i });
      socialButtons.forEach(button => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper aria labels', () => {
      render(<LoginForm />);
      
      const form = screen.getByRole('form');
      expect(form).toHaveAttribute('aria-label', 'Login form');
      
      const emailInput = screen.getByLabelText(/email/i);
      expect(emailInput).toHaveAttribute('aria-required', 'true');
      
      const passwordInput = screen.getByLabelText(/password/i);
      expect(passwordInput).toHaveAttribute('aria-required', 'true');
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      // Tab through form elements
      await user.tab();
      expect(screen.getByLabelText(/email/i)).toHaveFocus();
      
      await user.tab();
      expect(screen.getByLabelText(/password/i)).toHaveFocus();
      
      await user.tab();
      expect(screen.getByLabelText(/remember me/i)).toHaveFocus();
      
      await user.tab();
      expect(screen.getByRole('button', { name: /log in/i })).toHaveFocus();
    });

    it('should announce errors to screen readers', async () => {
      const user = userEvent.setup();
      render(<LoginForm />);
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      const errorAlert = await screen.findByRole('alert');
      expect(errorAlert).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Rate Limiting', () => {
    it('should show rate limit error after multiple failed attempts', async () => {
      const user = userEvent.setup();
      const rateLimitError = 'Too many login attempts. Please try again later.';
      
      render(<LoginForm />);
      
      // Simulate multiple failed attempts
      for (let i = 0; i < 5; i++) {
        mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
        
        const emailInput = screen.getByLabelText(/email/i);
        const passwordInput = screen.getByLabelText(/password/i);
        
        await user.clear(emailInput);
        await user.clear(passwordInput);
        await user.type(emailInput, 'test@example.com');
        await user.type(passwordInput, 'wrongpassword');
        
        const submitButton = screen.getByRole('button', { name: /log in/i });
        await user.click(submitButton);
      }
      
      // On the 6th attempt, should show rate limit error
      mockLogin.mockRejectedValueOnce(new Error(rateLimitError));
      
      const submitButton = screen.getByRole('button', { name: /log in/i });
      await user.click(submitButton);
      
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(rateLimitError);
      });
    });
  });
});