/**
 * User Registration E2E Tests
 * 
 * Comprehensive tests for user registration flows including
 * email/password signup, social authentication, and error scenarios.
 */

import { test, expect } from '@playwright/test'
import { AuthHelper } from '../helpers/auth-helper'
import { FormHelper } from '../helpers/form-helper'
import { EmailHelper } from '../helpers/email-helper'

test.describe('User Registration', () => {
  let authHelper: AuthHelper
  let formHelper: FormHelper
  let emailHelper: EmailHelper
  
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page)
    formHelper = new FormHelper(page)
    emailHelper = new EmailHelper()
    
    await page.goto('/auth/register')
  })
  
  test.describe('Email/Password Registration', () => {
    test('should register new user successfully', async ({ page }) => {
      const userData = {
        email: `test.${Date.now()}@example.com`,
        password: 'TestPassword123!',
        firstName: 'Test',
        lastName: 'User'
      }
      
      // Fill registration form
      await formHelper.fillRegistrationForm(userData)
      
      // Submit form
      await page.click('[data-testid="register-submit"]')
      
      // Verify loading state
      await expect(page.locator('[data-testid="register-submit"]')).toContainText('Creating account...')
      
      // Verify successful registration
      await expect(page).toHaveURL('/auth/verify-email')
      await expect(page.locator('[data-testid="success-message"]')).toContainText('Account created successfully')
      
      // Verify verification email was sent
      const verificationEmail = await emailHelper.waitForEmail(userData.email, 'verify')
      expect(verificationEmail).toBeTruthy()
    })
    
    test('should show validation errors for invalid data', async ({ page }) => {
      // Test empty form submission
      await page.click('[data-testid="register-submit"]')
      
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Email is required')
      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password is required')
      await expect(page.locator('[data-testid="firstName-error"]')).toContainText('First name is required')
      
      // Test invalid email
      await formHelper.fillField('email', 'invalid-email')
      await page.click('[data-testid="register-submit"]')
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Please enter a valid email')
      
      // Test weak password
      await formHelper.fillField('password', '123')
      await page.click('[data-testid="register-submit"]')
      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password must be at least 8 characters')
    })
    
    test('should prevent registration with existing email', async ({ page }) => {
      const existingEmail = 'existing.user@example.com'
      
      // Try to register with existing email
      await formHelper.fillRegistrationForm({
        email: existingEmail,
        password: 'TestPassword123!',
        firstName: 'Test',
        lastName: 'User'
      })
      
      await page.click('[data-testid="register-submit"]')
      
      // Verify error message
      await expect(page.locator('[data-testid="general-error"]')).toContainText('Email already registered')
      
      // Verify form is still visible
      await expect(page.locator('[data-testid="registration-form"]')).toBeVisible()
    })
    
    test('should enforce password strength requirements', async ({ page }) => {
      const weakPasswords = [
        'password',      // No uppercase, numbers, symbols
        'PASSWORD',      // No lowercase, numbers, symbols
        'Password',      // No numbers, symbols
        'Password1',     // No symbols
        'Pass1!',       // Too short
      ]
      
      for (const password of weakPasswords) {
        await formHelper.fillField('password', password)
        await page.click('[data-testid="register-submit"]')
        
        // Verify password strength feedback
        const strengthIndicator = page.locator('[data-testid="password-strength"]')
        await expect(strengthIndicator).toHaveClass(/weak|medium/)
        
        // Clear field for next test
        await formHelper.clearField('password')
      }
      
      // Test strong password
      await formHelper.fillField('password', 'StrongPassword123!')
      const strengthIndicator = page.locator('[data-testid="password-strength"]')
      await expect(strengthIndicator).toHaveClass(/strong/)
    })
    
    test('should handle terms and privacy agreement', async ({ page }) => {
      const userData = {
        email: `test.${Date.now()}@example.com`,
        password: 'TestPassword123!',
        firstName: 'Test',
        lastName: 'User'
      }
      
      await formHelper.fillRegistrationForm(userData)
      
      // Try to submit without agreeing to terms
      await page.click('[data-testid="register-submit"]')
      await expect(page.locator('[data-testid="terms-error"]')).toContainText('You must agree to the terms')
      
      // Agree to terms and privacy
      await page.check('[data-testid="agree-terms"]')
      await page.check('[data-testid="agree-privacy"]')
      
      // Submit form
      await page.click('[data-testid="register-submit"]')
      
      // Verify successful registration
      await expect(page).toHaveURL('/auth/verify-email')
    })
  })
  
  test.describe('Social Authentication Registration', () => {
    test('should register with Google', async ({ page }) => {
      // Mock Google OAuth response
      await page.route('**/auth/google', route => {
        route.fulfill({
          status: 302,
          headers: {
            'Location': '/auth/callback?provider=google&code=mock_code'
          }
        })
      })
      
      // Click Google registration button
      await page.click('[data-testid="google-register"]')
      
      // Verify OAuth flow initiated
      await expect(page).toHaveURL(/google/)
      
      // Complete profile if needed
      if (await page.locator('[data-testid="complete-profile"]').isVisible()) {
        await formHelper.fillField('firstName', 'Google')
        await formHelper.fillField('lastName', 'User')
        await page.click('[data-testid="complete-profile-submit"]')
      }
      
      // Verify successful registration
      await expect(page).toHaveURL('/dashboard')
    })
    
    test('should register with Apple', async ({ page }) => {
      // Mock Apple OAuth response
      await page.route('**/auth/apple', route => {
        route.fulfill({
          status: 302,
          headers: {
            'Location': '/auth/callback?provider=apple&code=mock_code'
          }
        })
      })
      
      await page.click('[data-testid="apple-register"]')
      await expect(page).toHaveURL(/appleid.apple.com/)
    })
    
    test('should handle OAuth errors gracefully', async ({ page }) => {
      // Mock OAuth error
      await page.route('**/auth/google', route => {
        route.fulfill({
          status: 400,
          body: JSON.stringify({ error: 'oauth_error', message: 'OAuth authentication failed' })
        })
      })
      
      await page.click('[data-testid="google-register"]')
      
      // Verify error handling
      await expect(page.locator('[data-testid="oauth-error"]')).toContainText('OAuth authentication failed')
      await expect(page.locator('[data-testid="registration-form"]')).toBeVisible()
    })
  })
  
  test.describe('Email Verification Flow', () => {
    test('should complete email verification', async ({ page }) => {
      // Register user
      const userData = {
        email: `verify.${Date.now()}@example.com`,
        password: 'TestPassword123!',
        firstName: 'Verify',
        lastName: 'User'
      }
      
      await authHelper.registerUser(userData)
      await expect(page).toHaveURL('/auth/verify-email')
      
      // Get verification email
      const verificationEmail = await emailHelper.waitForEmail(userData.email, 'verify')
      const verificationLink = emailHelper.extractVerificationLink(verificationEmail)
      
      // Click verification link
      await page.goto(verificationLink)
      
      // Verify successful verification
      await expect(page).toHaveURL('/dashboard')
      await expect(page.locator('[data-testid="welcome-message"]')).toContainText('Welcome to Duolingo!')
    })
    
    test('should resend verification email', async ({ page }) => {
      const email = 'resend.test@example.com'
      
      // Go to verification page
      await page.goto('/auth/verify-email')
      
      // Click resend button
      await page.click('[data-testid="resend-verification"]')
      
      // Verify success message
      await expect(page.locator('[data-testid="resend-success"]')).toContainText('Verification email sent')
      
      // Verify email was sent
      const verificationEmail = await emailHelper.waitForEmail(email, 'verify')
      expect(verificationEmail).toBeTruthy()
    })
    
    test('should handle expired verification tokens', async ({ page }) => {
      const expiredToken = 'expired_token_123'
      
      await page.goto(`/auth/verify-email?token=${expiredToken}`)
      
      // Verify error message
      await expect(page.locator('[data-testid="verification-error"]')).toContainText('Verification link has expired')
      
      // Verify resend option is available
      await expect(page.locator('[data-testid="resend-verification"]')).toBeVisible()
    })
  })
  
  test.describe('Rate Limiting', () => {
    test('should enforce registration rate limits', async ({ page }) => {
      const baseEmail = `ratelimit.${Date.now()}`
      
      // Attempt multiple registrations quickly
      for (let i = 0; i < 6; i++) {
        await formHelper.fillRegistrationForm({
          email: `${baseEmail}.${i}@example.com`,
          password: 'TestPassword123!',
          firstName: 'Rate',
          lastName: 'Test'
        })
        
        await page.click('[data-testid="register-submit"]')
        
        if (i >= 5) {
          // Should hit rate limit
          await expect(page.locator('[data-testid="rate-limit-error"]')).toContainText('Too many registration attempts')
        }
        
        // Reset form
        await page.reload()
      }
    })
  })
  
  test.describe('Accessibility', () => {
    test('should be accessible with keyboard navigation', async ({ page }) => {
      // Test tab navigation
      await page.keyboard.press('Tab') // Email field
      await expect(page.locator('[data-testid="email-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Password field
      await expect(page.locator('[data-testid="password-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // First name field
      await expect(page.locator('[data-testid="firstName-input"]')).toBeFocused()
      
      // Test form submission with Enter
      await formHelper.fillRegistrationForm({
        email: `keyboard.${Date.now()}@example.com`,
        password: 'TestPassword123!',
        firstName: 'Keyboard',
        lastName: 'User'
      })
      
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL('/auth/verify-email')
    })
    
    test('should have proper ARIA labels', async ({ page }) => {
      // Verify form has proper labels
      await expect(page.locator('[data-testid="email-input"]')).toHaveAttribute('aria-label', 'Email address')
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('aria-label', 'Password')
      await expect(page.locator('[data-testid="firstName-input"]')).toHaveAttribute('aria-label', 'First name')
      
      // Verify error regions
      await expect(page.locator('[data-testid="form-errors"]')).toHaveAttribute('role', 'alert')
    })
  })
})