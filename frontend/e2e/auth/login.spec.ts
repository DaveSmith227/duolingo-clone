/**
 * User Login E2E Tests
 * 
 * Comprehensive tests for user login flows including email/password,
 * social authentication, remember me, and security scenarios.
 */

import { test, expect } from '@playwright/test'
import { AuthHelper } from '../helpers/auth-helper'
import { FormHelper } from '../helpers/form-helper'

test.describe('User Login', () => {
  let authHelper: AuthHelper
  let formHelper: FormHelper
  
  test.beforeEach(async ({ page }) => {
    authHelper = new AuthHelper(page)
    formHelper = new FormHelper(page)
    
    await page.goto('/auth/login')
  })
  
  test.describe('Email/Password Login', () => {
    test('should login successfully with valid credentials', async ({ page }) => {
      const credentials = {
        email: 'test.user@example.com',
        password: 'TestPassword123!'
      }
      
      // Fill login form
      await formHelper.fillField('email', credentials.email)
      await formHelper.fillField('password', credentials.password)
      
      // Submit form
      await page.click('[data-testid="login-submit"]')
      
      // Verify loading state
      await expect(page.locator('[data-testid="login-submit"]')).toContainText('Signing in...')
      
      // Verify successful login
      await expect(page).toHaveURL('/dashboard')
      await expect(page.locator('[data-testid="user-menu"]')).toContainText('Test User')
      
      // Verify authentication state
      const userProfile = page.locator('[data-testid="user-profile"]')
      await expect(userProfile).toContainText(credentials.email)
    })
    
    test('should show error for invalid credentials', async ({ page }) => {
      await formHelper.fillField('email', 'invalid@example.com')
      await formHelper.fillField('password', 'wrongpassword')
      
      await page.click('[data-testid="login-submit"]')
      
      // Verify error message
      await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid email or password')
      
      // Verify form is still visible
      await expect(page.locator('[data-testid="login-form"]')).toBeVisible()
      
      // Verify fields are cleared or maintained appropriately
      await expect(page.locator('[data-testid="email-input"]')).toHaveValue('invalid@example.com')
      await expect(page.locator('[data-testid="password-input"]')).toHaveValue('')
    })
    
    test('should validate required fields', async ({ page }) => {
      // Submit empty form
      await page.click('[data-testid="login-submit"]')
      
      // Verify validation errors
      await expect(page.locator('[data-testid="email-error"]')).toContainText('Email is required')
      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password is required')
      
      // Fill email only
      await formHelper.fillField('email', 'test@example.com')
      await page.click('[data-testid="login-submit"]')
      
      await expect(page.locator('[data-testid="email-error"]')).not.toBeVisible()
      await expect(page.locator('[data-testid="password-error"]')).toContainText('Password is required')
    })
    
    test('should handle remember me functionality', async ({ page }) => {
      const credentials = {
        email: 'test.user@example.com',
        password: 'TestPassword123!'
      }
      
      // Fill credentials and check remember me
      await formHelper.fillField('email', credentials.email)
      await formHelper.fillField('password', credentials.password)
      await page.check('[data-testid="remember-me"]')
      
      // Verify remember me explanation
      await expect(page.locator('[data-testid="remember-me-text"]')).toContainText('Keep me signed in for 30 days')
      
      await page.click('[data-testid="login-submit"]')
      
      // Verify successful login
      await expect(page).toHaveURL('/dashboard')
      
      // Verify session is extended (check localStorage or cookies)
      const rememberMeState = await page.evaluate(() => {
        return localStorage.getItem('auth-remember-me')
      })
      expect(rememberMeState).toBe('true')
    })
    
    test('should toggle password visibility', async ({ page }) => {
      const password = 'TestPassword123!'
      
      await formHelper.fillField('password', password)
      
      // Password should be hidden initially
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('type', 'password')
      
      // Click toggle button
      await page.click('[data-testid="password-toggle"]')
      
      // Password should be visible
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('type', 'text')
      await expect(page.locator('[data-testid="password-input"]')).toHaveValue(password)
      
      // Click toggle again
      await page.click('[data-testid="password-toggle"]')
      
      // Password should be hidden again
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('type', 'password')
    })
  })
  
  test.describe('Social Authentication', () => {
    test('should login with Google', async ({ page }) => {
      // Mock Google OAuth flow
      await page.route('**/auth/google**', route => {
        route.fulfill({
          status: 302,
          headers: {
            'Location': '/auth/callback?provider=google&code=success'
          }
        })
      })
      
      await page.click('[data-testid="google-login"]')
      
      // Verify OAuth flow initiated
      await expect(page).toHaveURL(/google/)
      
      // Mock successful callback
      await page.goto('/auth/callback?provider=google&code=success')
      
      // Verify successful login
      await expect(page).toHaveURL('/dashboard')
    })
    
    test('should login with Apple', async ({ page }) => {
      await page.route('**/auth/apple**', route => {
        route.fulfill({
          status: 302,
          headers: {
            'Location': '/auth/callback?provider=apple&code=success'
          }
        })
      })
      
      await page.click('[data-testid="apple-login"]')
      await expect(page).toHaveURL(/appleid.apple.com/)
    })
    
    test('should handle OAuth errors', async ({ page }) => {
      await page.route('**/auth/google**', route => {
        route.fulfill({
          status: 400,
          body: JSON.stringify({ error: 'access_denied', message: 'User denied access' })
        })
      })
      
      await page.click('[data-testid="google-login"]')
      
      // Verify error handling
      await expect(page.locator('[data-testid="oauth-error"]')).toContainText('User denied access')
    })
  })
  
  test.describe('Account Security', () => {
    test('should handle locked account', async ({ page }) => {
      const credentials = {
        email: 'locked.user@example.com',
        password: 'LockedPassword123!'
      }
      
      await formHelper.fillField('email', credentials.email)
      await formHelper.fillField('password', credentials.password)
      await page.click('[data-testid="login-submit"]')
      
      // Verify locked account message
      await expect(page.locator('[data-testid="account-locked"]')).toContainText('Account is temporarily locked')
      
      // Verify contact support link
      await expect(page.locator('[data-testid="contact-support"]')).toBeVisible()
    })
    
    test('should handle unverified email', async ({ page }) => {
      const credentials = {
        email: 'unverified.user@example.com',
        password: 'UnverifiedPassword123!'
      }
      
      await formHelper.fillField('email', credentials.email)
      await formHelper.fillField('password', credentials.password)
      await page.click('[data-testid="login-submit"]')
      
      // Verify email verification prompt
      await expect(page.locator('[data-testid="email-verification"]')).toContainText('Please verify your email')
      
      // Verify resend verification option
      await expect(page.locator('[data-testid="resend-verification"]')).toBeVisible()
    })
    
    test('should enforce rate limiting after failed attempts', async ({ page }) => {
      const credentials = {
        email: 'test.user@example.com',
        password: 'wrongpassword'
      }
      
      // Attempt multiple failed logins
      for (let i = 0; i < 6; i++) {
        await formHelper.fillField('email', credentials.email)
        await formHelper.fillField('password', credentials.password)
        await page.click('[data-testid="login-submit"]')
        
        if (i < 5) {
          await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid email or password')
        } else {
          // Should hit rate limit
          await expect(page.locator('[data-testid="rate-limit-error"]')).toContainText('Too many failed attempts')
        }
        
        // Clear form for next attempt
        await page.reload()
      }
    })
  })
  
  test.describe('Multi-Factor Authentication', () => {
    test('should prompt for MFA when enabled', async ({ page }) => {
      const credentials = {
        email: 'mfa.user@example.com',
        password: 'MFAPassword123!'
      }
      
      await formHelper.fillField('email', credentials.email)
      await formHelper.fillField('password', credentials.password)
      await page.click('[data-testid="login-submit"]')
      
      // Verify MFA prompt
      await expect(page).toHaveURL('/auth/mfa')
      await expect(page.locator('[data-testid="mfa-prompt"]')).toContainText('Enter your 2FA code')
      
      // Test TOTP code entry
      await formHelper.fillField('mfa-code', '123456')
      await page.click('[data-testid="verify-mfa"]')
      
      // Verify successful login after MFA
      await expect(page).toHaveURL('/dashboard')
    })
    
    test('should handle backup codes', async ({ page }) => {
      // Navigate to MFA page
      await page.goto('/auth/mfa?challenge=test_challenge')
      
      // Switch to backup codes
      await page.click('[data-testid="use-backup-code"]')
      
      await expect(page.locator('[data-testid="backup-code-input"]')).toBeVisible()
      
      // Enter backup code
      await formHelper.fillField('backup-code', 'backup123')
      await page.click('[data-testid="verify-backup"]')
      
      // Verify successful verification
      await expect(page).toHaveURL('/dashboard')
    })
  })
  
  test.describe('Navigation and Links', () => {
    test('should navigate to password reset', async ({ page }) => {
      await page.click('[data-testid="forgot-password"]')
      await expect(page).toHaveURL('/auth/forgot-password')
    })
    
    test('should navigate to registration', async ({ page }) => {
      await page.click('[data-testid="create-account"]')
      await expect(page).toHaveURL('/auth/register')
    })
    
    test('should redirect authenticated users', async ({ page }) => {
      // Login first
      await authHelper.login('test.user@example.com', 'TestPassword123!')
      
      // Try to access login page
      await page.goto('/auth/login')
      
      // Should redirect to dashboard
      await expect(page).toHaveURL('/dashboard')
    })
  })
  
  test.describe('Responsive Design', () => {
    test('should work on mobile devices', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })
      
      await page.goto('/auth/login')
      
      // Verify mobile layout
      await expect(page.locator('[data-testid="login-form"]')).toBeVisible()
      await expect(page.locator('[data-testid="social-buttons"]')).toBeVisible()
      
      // Test mobile form interaction
      await formHelper.fillField('email', 'mobile@example.com')
      await formHelper.fillField('password', 'MobilePassword123!')
      await page.click('[data-testid="login-submit"]')
      
      await expect(page).toHaveURL('/dashboard')
    })
  })
  
  test.describe('Accessibility', () => {
    test('should support keyboard navigation', async ({ page }) => {
      // Test tab navigation
      await page.keyboard.press('Tab') // Email field
      await expect(page.locator('[data-testid="email-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Password field
      await expect(page.locator('[data-testid="password-input"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Remember me checkbox
      await expect(page.locator('[data-testid="remember-me"]')).toBeFocused()
      
      await page.keyboard.press('Tab') // Submit button
      await expect(page.locator('[data-testid="login-submit"]')).toBeFocused()
      
      // Test form submission with Enter
      await formHelper.fillField('email', 'keyboard@example.com')
      await formHelper.fillField('password', 'KeyboardPassword123!')
      await page.keyboard.press('Enter')
      
      await expect(page).toHaveURL('/dashboard')
    })
    
    test('should have proper ARIA attributes', async ({ page }) => {
      // Verify form accessibility
      await expect(page.locator('[data-testid="login-form"]')).toHaveAttribute('role', 'form')
      await expect(page.locator('[data-testid="email-input"]')).toHaveAttribute('aria-label', 'Email address')
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('aria-label', 'Password')
      
      // Verify error announcements
      await page.click('[data-testid="login-submit"]')
      await expect(page.locator('[data-testid="form-errors"]')).toHaveAttribute('role', 'alert')
    })
  })
})