/**
 * Test User Factory
 * 
 * Creates and manages test users for E2E testing scenarios.
 * Handles user creation, cleanup, and state management.
 */

interface TestUserData {
  email: string
  password: string
  firstName: string
  lastName: string
  role: 'user' | 'admin' | 'moderator'
  emailVerified?: boolean
  accountLocked?: boolean
}

interface CreatedTestUser extends TestUserData {
  id: string
  createdAt: string
}

export class TestUserFactory {
  private baseURL: string
  private apiKey: string
  private createdUsers: CreatedTestUser[] = []
  
  constructor() {
    this.baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
    this.apiKey = process.env.TEST_API_KEY || 'test-api-key'
  }
  
  /**
   * Create a test user with specified properties
   */
  async createUser(userData: TestUserData): Promise<CreatedTestUser> {
    console.log(`👤 Creating test user: ${userData.email}`)
    
    try {
      const response = await fetch(`${this.baseURL}/api/test/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          ...userData,
          emailVerified: userData.emailVerified ?? true,
          accountLocked: userData.accountLocked ?? false
        })
      })
      
      if (!response.ok) {
        const error = await response.text()
        throw new Error(`Failed to create user ${userData.email}: ${error}`)
      }
      
      const createdUser = await response.json()
      this.createdUsers.push(createdUser)
      
      console.log(`✅ Test user created: ${userData.email} (ID: ${createdUser.id})`)
      return createdUser
      
    } catch (error) {
      console.error(`❌ Failed to create user ${userData.email}:`, error)
      throw error
    }
  }
  
  /**
   * Create multiple test users
   */
  async createUsers(usersData: TestUserData[]): Promise<CreatedTestUser[]> {
    const users = []
    
    for (const userData of usersData) {
      const user = await this.createUser(userData)
      users.push(user)
    }
    
    return users
  }
  
  /**
   * Get a test user by email
   */
  getUserByEmail(email: string): CreatedTestUser | undefined {
    return this.createdUsers.find(user => user.email === email)
  }
  
  /**
   * Get all created test users
   */
  getAllUsers(): CreatedTestUser[] {
    return [...this.createdUsers]
  }
  
  /**
   * Clean up all created test users
   */
  async cleanup(): Promise<void> {
    console.log('🧹 Cleaning up test users...')
    
    for (const user of this.createdUsers) {
      try {
        await this.deleteUser(user.id)
      } catch (error) {
        console.warn(`⚠️ Failed to delete user ${user.email}:`, error)
      }
    }
    
    this.createdUsers = []
    console.log('✅ Test user cleanup completed')
  }
  
  /**
   * Delete a specific test user
   */
  private async deleteUser(userId: string): Promise<void> {
    const response = await fetch(`${this.baseURL}/api/test/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`Failed to delete user ${userId}: ${response.status}`)
    }
  }
  
  /**
   * Create standard test user set
   */
  static createStandardTestUsers(): TestUserData[] {
    return [
      {
        email: 'user1@test.com',
        password: 'TestPassword123!',
        firstName: 'User',
        lastName: 'One',
        role: 'user'
      },
      {
        email: 'user2@test.com',
        password: 'TestPassword123!',
        firstName: 'User',
        lastName: 'Two',
        role: 'user'
      },
      {
        email: 'admin@test.com',
        password: 'AdminPassword123!',
        firstName: 'Admin',
        lastName: 'User',
        role: 'admin'
      },
      {
        email: 'moderator@test.com',
        password: 'ModeratorPassword123!',
        firstName: 'Moderator',
        lastName: 'User',
        role: 'moderator'
      }
    ]
  }
  
  /**
   * Create test users for specific scenarios
   */
  static createScenarioUsers() {
    return {
      // Authentication flow testing
      authFlow: [
        {
          email: 'auth.new@test.com',
          password: 'NewUserPassword123!',
          firstName: 'New',
          lastName: 'AuthUser',
          role: 'user' as const
        },
        {
          email: 'auth.existing@test.com',
          password: 'ExistingPassword123!',
          firstName: 'Existing',
          lastName: 'AuthUser',
          role: 'user' as const
        }
      ],
      
      // Security testing
      security: [
        {
          email: 'security.locked@test.com',
          password: 'LockedPassword123!',
          firstName: 'Locked',
          lastName: 'User',
          role: 'user' as const,
          accountLocked: true
        },
        {
          email: 'security.unverified@test.com',
          password: 'UnverifiedPassword123!',
          firstName: 'Unverified',
          lastName: 'User',
          role: 'user' as const,
          emailVerified: false
        }
      ],
      
      // Admin testing
      admin: [
        {
          email: 'admin.super@test.com',
          password: 'SuperAdminPassword123!',
          firstName: 'Super',
          lastName: 'Admin',
          role: 'admin' as const
        },
        {
          email: 'admin.regular@test.com',
          password: 'RegularAdminPassword123!',
          firstName: 'Regular',
          lastName: 'Admin',
          role: 'admin' as const
        }
      ]
    }
  }
}