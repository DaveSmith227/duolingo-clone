import puppeteer, { Browser, Page } from 'puppeteer';

describe('Authentication E2E Tests', () => {
  let browser: Browser;
  let page: Page;
  const baseUrl = process.env.BASE_URL || 'http://localhost:3000';

  beforeAll(async () => {
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  });

  afterAll(async () => {
    await browser.close();
  });

  beforeEach(async () => {
    page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
  });

  afterEach(async () => {
    await page.close();
  });

  describe('Login Flow', () => {
    it('should display login form with all required elements', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Check for email input
      const emailInput = await page.$('input[type="email"]');
      expect(emailInput).toBeTruthy();
      
      // Check for password input
      const passwordInput = await page.$('input[type="password"]');
      expect(passwordInput).toBeTruthy();
      
      // Check for submit button
      const submitButton = await page.$('button[type="submit"]');
      expect(submitButton).toBeTruthy();
      
      // Check for social login buttons
      const googleButton = await page.$('button[aria-label*="Google"]');
      const appleButton = await page.$('button[aria-label*="Apple"]');
      const facebookButton = await page.$('button[aria-label*="Facebook"]');
      
      expect(googleButton).toBeTruthy();
      expect(appleButton).toBeTruthy();
      expect(facebookButton).toBeTruthy();
      
      // Check for forgot password link
      const forgotPasswordLink = await page.$('a[href*="forgot-password"]');
      expect(forgotPasswordLink).toBeTruthy();
    });

    it('should show validation errors for invalid inputs', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Submit empty form
      await page.click('button[type="submit"]');
      
      // Wait for validation messages
      await page.waitForSelector('[role="alert"]', { timeout: 5000 });
      
      // Check for email validation error
      const emailError = await page.$eval('[role="alert"]', el => el.textContent);
      expect(emailError).toContain('email');
      
      // Type invalid email
      await page.type('input[type="email"]', 'invalid-email');
      await page.click('button[type="submit"]');
      
      // Check for email format error
      await page.waitForSelector('[role="alert"]', { timeout: 5000 });
      const formatError = await page.$eval('[role="alert"]', el => el.textContent);
      expect(formatError).toContain('valid email');
    });

    it('should handle login rate limiting', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Attempt multiple failed logins
      for (let i = 0; i < 6; i++) {
        await page.type('input[type="email"]', 'test@example.com');
        await page.type('input[type="password"]', 'wrongpassword');
        await page.click('button[type="submit"]');
        
        // Clear inputs for next attempt
        await page.evaluate(() => {
          (document.querySelector('input[type="email"]') as HTMLInputElement).value = '';
          (document.querySelector('input[type="password"]') as HTMLInputElement).value = '';
        });
      }
      
      // Check for rate limit error
      const rateLimitError = await page.waitForSelector('[role="alert"]', { timeout: 5000 });
      const errorText = await rateLimitError?.evaluate(el => el.textContent);
      expect(errorText).toContain('too many attempts');
    });
  });

  describe('Registration Flow', () => {
    it('should display registration form with all required elements', async () => {
      await page.goto(`${baseUrl}/register`);
      
      // Check for required inputs
      const firstNameInput = await page.$('input[name="firstName"]');
      const emailInput = await page.$('input[type="email"]');
      const passwordInput = await page.$('input[type="password"]');
      const confirmPasswordInput = await page.$('input[name="confirmPassword"]');
      
      expect(firstNameInput).toBeTruthy();
      expect(emailInput).toBeTruthy();
      expect(passwordInput).toBeTruthy();
      expect(confirmPasswordInput).toBeTruthy();
      
      // Check for password strength indicator
      const strengthIndicator = await page.$('[data-testid="password-strength"]');
      expect(strengthIndicator).toBeTruthy();
      
      // Check for privacy consent checkbox
      const consentCheckbox = await page.$('input[type="checkbox"][name="consent"]');
      expect(consentCheckbox).toBeTruthy();
    });

    it('should validate password strength requirements', async () => {
      await page.goto(`${baseUrl}/register`);
      
      // Type weak password
      await page.type('input[type="password"]', 'weak');
      
      // Check strength indicator
      await page.waitForSelector('[data-testid="password-strength"]');
      const strengthText = await page.$eval('[data-testid="password-strength"]', el => el.textContent);
      expect(strengthText?.toLowerCase()).toContain('weak');
      
      // Type strong password
      await page.evaluate(() => {
        (document.querySelector('input[type="password"]') as HTMLInputElement).value = '';
      });
      await page.type('input[type="password"]', 'StrongP@ssw0rd123!');
      
      // Check updated strength
      const updatedStrength = await page.$eval('[data-testid="password-strength"]', el => el.textContent);
      expect(updatedStrength?.toLowerCase()).toContain('strong');
    });

    it('should validate password confirmation match', async () => {
      await page.goto(`${baseUrl}/register`);
      
      await page.type('input[name="firstName"]', 'Test');
      await page.type('input[type="email"]', 'test@example.com');
      await page.type('input[type="password"]', 'Password123!');
      await page.type('input[name="confirmPassword"]', 'DifferentPassword123!');
      
      await page.click('button[type="submit"]');
      
      // Check for mismatch error
      const mismatchError = await page.waitForSelector('[role="alert"]', { timeout: 5000 });
      const errorText = await mismatchError?.evaluate(el => el.textContent);
      expect(errorText).toContain('match');
    });
  });

  describe('Password Reset Flow', () => {
    it('should navigate to password reset from login', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Click forgot password link
      await page.click('a[href*="forgot-password"]');
      
      // Wait for navigation
      await page.waitForNavigation();
      
      // Check we're on reset page
      expect(page.url()).toContain('forgot-password');
      
      // Check for email input
      const emailInput = await page.$('input[type="email"]');
      expect(emailInput).toBeTruthy();
      
      // Check for submit button
      const submitButton = await page.$('button[type="submit"]');
      const buttonText = await submitButton?.evaluate(el => el.textContent);
      expect(buttonText).toContain('Reset');
    });

    it('should show success message after reset request', async () => {
      await page.goto(`${baseUrl}/forgot-password`);
      
      await page.type('input[type="email"]', 'test@example.com');
      await page.click('button[type="submit"]');
      
      // Wait for success message
      const successMessage = await page.waitForSelector('[role="status"]', { timeout: 5000 });
      const messageText = await successMessage?.evaluate(el => el.textContent);
      expect(messageText).toContain('email sent');
    });
  });

  describe('Protected Route Access', () => {
    it('should redirect to login when accessing protected route', async () => {
      // Try to access protected route
      await page.goto(`${baseUrl}/dashboard`);
      
      // Wait for redirect
      await page.waitForNavigation();
      
      // Should be redirected to login
      expect(page.url()).toContain('login');
      
      // Check for redirect message
      const redirectMessage = await page.$('[data-testid="redirect-message"]');
      expect(redirectMessage).toBeTruthy();
    });
  });

  describe('Session Management', () => {
    it('should handle remember me functionality', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Check remember me checkbox
      const rememberCheckbox = await page.$('input[type="checkbox"][name="rememberMe"]');
      expect(rememberCheckbox).toBeTruthy();
      
      // Check the checkbox
      await page.click('input[type="checkbox"][name="rememberMe"]');
      
      // Verify it's checked
      const isChecked = await page.$eval('input[type="checkbox"][name="rememberMe"]', 
        (el: HTMLInputElement) => el.checked
      );
      expect(isChecked).toBe(true);
    });
  });

  describe('Social Authentication', () => {
    it('should initiate Google OAuth flow', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Set up request interception
      await page.setRequestInterception(true);
      
      let oauthRequested = false;
      page.on('request', (request) => {
        if (request.url().includes('google') && request.url().includes('oauth')) {
          oauthRequested = true;
        }
        request.continue();
      });
      
      // Click Google button
      await page.click('button[aria-label*="Google"]');
      
      // Wait a bit for the request
      await page.waitForTimeout(1000);
      
      // OAuth should have been initiated
      expect(oauthRequested).toBe(true);
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels and keyboard navigation', async () => {
      await page.goto(`${baseUrl}/login`);
      
      // Check for form role
      const form = await page.$('form[role="form"]');
      expect(form).toBeTruthy();
      
      // Tab through form elements
      await page.keyboard.press('Tab'); // Focus email
      const focusedEmail = await page.evaluate(() => 
        document.activeElement?.getAttribute('type')
      );
      expect(focusedEmail).toBe('email');
      
      await page.keyboard.press('Tab'); // Focus password
      const focusedPassword = await page.evaluate(() => 
        document.activeElement?.getAttribute('type')
      );
      expect(focusedPassword).toBe('password');
      
      // Check for aria-labels
      const emailLabel = await page.$eval('input[type="email"]', 
        el => el.getAttribute('aria-label')
      );
      expect(emailLabel).toBeTruthy();
    });
  });

  describe('Mobile Responsiveness', () => {
    it('should render properly on mobile viewport', async () => {
      // Set mobile viewport
      await page.setViewport({ width: 375, height: 667 });
      
      await page.goto(`${baseUrl}/login`);
      
      // Check that form is visible
      const form = await page.$('form');
      const isVisible = await form?.isIntersectingViewport();
      expect(isVisible).toBe(true);
      
      // Check social buttons stack vertically
      const socialButtons = await page.$$('button[aria-label*="Sign in with"]');
      expect(socialButtons.length).toBeGreaterThan(0);
      
      // Get positions to verify vertical stacking
      const positions = await Promise.all(
        socialButtons.map(button => 
          button.boundingBox()
        )
      );
      
      // Check if buttons are stacked (same x position, different y)
      if (positions.length > 1 && positions[0] && positions[1]) {
        expect(positions[0].x).toBe(positions[1].x);
        expect(positions[0].y).not.toBe(positions[1].y);
      }
    });
  });
});