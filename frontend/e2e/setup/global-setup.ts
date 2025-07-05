/**
 * Global E2E Test Setup
 * 
 * Sets up test environment, creates test users, and prepares
 * authentication states for E2E testing.
 */

import { chromium, FullConfig } from '@playwright/test'
import { TestUserFactory } from './test-user-factory'
import { AuthenticationHelper } from './auth-helper'

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test setup...')
  
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()
  
  try {
    // Initialize test environment
    await setupTestEnvironment()
    
    // Create test users
    const testUsers = await createTestUsers()
    
    // Setup authentication states
    await setupAuthenticationStates(page, testUsers)
    
    console.log('✅ E2E test setup completed successfully')
  } catch (error) {
    console.error('❌ E2E test setup failed:', error)
    throw error
  } finally {
    await browser.close()
  }
}

async function setupTestEnvironment() {
  console.log('🔧 Setting up test environment...')
  
  // Verify backend is running
  const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
  
  try {
    const response = await fetch(`${baseURL}/api/health`)
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`)
    }
    console.log('✅ Backend health check passed')
  } catch (error) {
    console.error('❌ Backend health check failed:', error)
    throw error
  }
  
  // Setup test database state if needed
  await resetTestDatabase()
}

async function createTestUsers() {
  console.log('👥 Creating test users...')
  
  const userFactory = new TestUserFactory()
  
  const testUsers = {
    regularUser: await userFactory.createUser({
      email: 'test.user@example.com',
      password: 'TestPassword123!',
      firstName: 'Test',
      lastName: 'User',
      role: 'user'
    }),
    
    adminUser: await userFactory.createUser({
      email: 'admin.user@example.com',
      password: 'AdminPassword123!',
      firstName: 'Admin',
      lastName: 'User',
      role: 'admin'
    }),
    
    moderatorUser: await userFactory.createUser({
      email: 'moderator.user@example.com',
      password: 'ModeratorPassword123!',
      firstName: 'Moderator',
      lastName: 'User',
      role: 'moderator'
    }),
    
    unverifiedUser: await userFactory.createUser({
      email: 'unverified.user@example.com',
      password: 'UnverifiedPassword123!',
      firstName: 'Unverified',
      lastName: 'User',
      role: 'user',
      emailVerified: false
    }),
    
    lockedUser: await userFactory.createUser({
      email: 'locked.user@example.com',
      password: 'LockedPassword123!',
      firstName: 'Locked',
      lastName: 'User',
      role: 'user',
      accountLocked: true
    })
  }
  
  console.log('✅ Test users created successfully')
  return testUsers
}

async function setupAuthenticationStates(page: any, testUsers: any) {
  console.log('🔐 Setting up authentication states...')
  
  const authHelper = new AuthenticationHelper(page)
  
  // Setup regular user authentication
  await authHelper.loginAndSaveState(
    testUsers.regularUser.email,
    testUsers.regularUser.password,
    './e2e/auth/authenticated-user.json'
  )
  
  // Setup admin user authentication
  await authHelper.loginAndSaveState(
    testUsers.adminUser.email,
    testUsers.adminUser.password,
    './e2e/auth/admin-user.json'
  )
  
  // Setup moderator user authentication
  await authHelper.loginAndSaveState(
    testUsers.moderatorUser.email,
    testUsers.moderatorUser.password,
    './e2e/auth/moderator-user.json'
  )
  
  console.log('✅ Authentication states saved')
}

async function resetTestDatabase() {
  console.log('🗄️ Resetting test database...')
  
  // Call backend endpoint to reset test data
  const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
  
  try {
    const response = await fetch(`${baseURL}/api/test/reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.TEST_API_KEY}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`Database reset failed: ${response.status}`)
    }
    
    console.log('✅ Test database reset successfully')
  } catch (error) {
    console.warn('⚠️ Database reset failed (continuing anyway):', error)
  }
}

export default globalSetup