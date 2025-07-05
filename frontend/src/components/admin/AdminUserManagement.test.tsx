import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AdminUserManagement } from './AdminUserManagement'

// Mock useAuth hook
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}))

// Mock fetch
global.fetch = vi.fn()

const mockUsers = [
  {
    id: '1',
    email: 'user1@example.com',
    name: 'John Doe',
    is_active: true,
    is_suspended: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    last_login_at: '2024-01-03T00:00:00Z',
    login_count: 10,
    failed_login_count: 2,
    roles: ['user'],
    supabase_id: 'supabase-1'
  },
  {
    id: '2',
    email: 'admin@example.com',
    name: 'Jane Admin',
    is_active: true,
    is_suspended: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    last_login_at: '2024-01-03T00:00:00Z',
    login_count: 50,
    failed_login_count: 0,
    roles: ['admin', 'user'],
    supabase_id: 'supabase-2'
  },
  {
    id: '3',
    email: 'suspended@example.com',
    name: 'Suspended User',
    is_active: false,
    is_suspended: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    last_login_at: null,
    login_count: 5,
    failed_login_count: 10,
    roles: ['user'],
    supabase_id: 'supabase-3'
  }
]

const mockApiResponse = {
  users: mockUsers,
  total_count: 3,
  page: 1,
  page_size: 20,
  total_pages: 1,
  has_next: false,
  has_previous: false
}

describe('AdminUserManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful fetch response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockApiResponse
    })
  })

  describe('Permission-based rendering', () => {
    it('should show access denied when user lacks admin permissions', () => {
      mockUseAuth.mockReturnValue({
        user: { id: 'user1', email: 'user@example.com' },
        hasPermission: vi.fn().mockReturnValue(false)
      })

      render(<AdminUserManagement />)

      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.getByText("You don't have permission to manage users.")).toBeInTheDocument()
    })

    it('should render user management interface when user has admin permissions', async () => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })

      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('User Management')).toBeInTheDocument()
      })
    })
  })

  describe('User list display', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should display users correctly', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
        expect(screen.getByText('user1@example.com')).toBeInTheDocument()
        expect(screen.getByText('Jane Admin')).toBeInTheDocument()
        expect(screen.getByText('admin@example.com')).toBeInTheDocument()
        expect(screen.getByText('Suspended User')).toBeInTheDocument()
        expect(screen.getByText('suspended@example.com')).toBeInTheDocument()
      })
    })

    it('should show correct status badges', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const activeBadges = screen.getAllByText('Active')
        expect(activeBadges).toHaveLength(2)
        
        const suspendedBadge = screen.getByText('Suspended')
        expect(suspendedBadge).toBeInTheDocument()
      })
    })

    it('should display user roles correctly', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        // Check that roles are displayed
        const userRoles = screen.getAllByText('user')
        expect(userRoles.length).toBeGreaterThan(0)
        
        const adminRole = screen.getByText('admin')
        expect(adminRole).toBeInTheDocument()
      })
    })

    it('should show login statistics', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('10 successful')).toBeInTheDocument()
        expect(screen.getByText('2 failed')).toBeInTheDocument()
        expect(screen.getByText('50 successful')).toBeInTheDocument()
        expect(screen.getByText('0 failed')).toBeInTheDocument()
      })
    })
  })

  describe('Search functionality', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should handle search input', async () => {
      render(<AdminUserManagement />)

      const searchInput = screen.getByPlaceholderText('Search users by email or name...')
      fireEvent.change(searchInput, { target: { value: 'john' } })

      // Verify search input value changes
      expect(searchInput).toHaveValue('john')
    })

    it('should trigger search API call when typing', async () => {
      render(<AdminUserManagement />)

      const searchInput = screen.getByPlaceholderText('Search users by email or name...')
      fireEvent.change(searchInput, { target: { value: 'john' } })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('query=john'),
          expect.any(Object)
        )
      })
    })
  })

  describe('Filtering', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should have status filter dropdown', async () => {
      render(<AdminUserManagement />)

      const statusFilter = screen.getByDisplayValue('All Users')
      expect(statusFilter).toBeInTheDocument()

      // Change status filter
      fireEvent.change(statusFilter, { target: { value: 'active' } })
      expect(statusFilter).toHaveValue('active')
    })

    it('should show advanced filters when filter button is clicked', async () => {
      render(<AdminUserManagement />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        expect(screen.getByText('Created After')).toBeInTheDocument()
        expect(screen.getByText('Created Before')).toBeInTheDocument()
        expect(screen.getByText('Sort By')).toBeInTheDocument()
        expect(screen.getByText('Sort Order')).toBeInTheDocument()
      })
    })

    it('should handle date filters', async () => {
      render(<AdminUserManagement />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        const createdAfterInput = screen.getByLabelText('Created After')
        fireEvent.change(createdAfterInput, { target: { value: '2024-01-01' } })
        expect(createdAfterInput).toHaveValue('2024-01-01')
      })
    })
  })

  describe('User selection', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should allow individual user selection', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox')
        const userCheckbox = checkboxes[1] // First checkbox is select all
        
        fireEvent.click(userCheckbox)
        expect(userCheckbox).toBeChecked()
      })
    })

    it('should handle select all functionality', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const selectAllCheckbox = screen.getAllByRole('checkbox')[0]
        
        fireEvent.click(selectAllCheckbox)
        expect(selectAllCheckbox).toBeChecked()
        
        // All user checkboxes should be checked
        const userCheckboxes = screen.getAllByRole('checkbox').slice(1)
        userCheckboxes.forEach(checkbox => {
          expect(checkbox).toBeChecked()
        })
      })
    })

    it('should show bulk actions when users are selected', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const userCheckbox = screen.getAllByRole('checkbox')[1]
        fireEvent.click(userCheckbox)
      })

      await waitFor(() => {
        expect(screen.getByText('1 user selected')).toBeInTheDocument()
        expect(screen.getByText('Suspend')).toBeInTheDocument()
        expect(screen.getByText('Activate')).toBeInTheDocument()
        expect(screen.getByText('Delete')).toBeInTheDocument()
      })
    })
  })

  describe('User actions', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should show actions menu when more button is clicked', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const moreButtons = screen.getAllByRole('button')
        const moreButton = moreButtons.find(button => 
          button.querySelector('svg') // Looking for MoreVertical icon
        )
        
        if (moreButton) {
          fireEvent.click(moreButton)
        }
      })

      await waitFor(() => {
        expect(screen.getByText('View Details')).toBeInTheDocument()
        expect(screen.getByText('Suspend User')).toBeInTheDocument()
        expect(screen.getByText('Delete User')).toBeInTheDocument()
      })
    })

    it('should handle user action API calls', async () => {
      // Mock the user action API call
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiResponse
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiResponse
        })

      render(<AdminUserManagement />)

      await waitFor(() => {
        const moreButtons = screen.getAllByRole('button')
        const moreButton = moreButtons.find(button => 
          button.querySelector('svg')
        )
        
        if (moreButton) {
          fireEvent.click(moreButton)
        }
      })

      await waitFor(() => {
        const suspendButton = screen.getByText('Suspend User')
        fireEvent.click(suspendButton)
      })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/users/1/actions'),
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json'
            }),
            body: expect.stringContaining('suspend')
          })
        )
      })
    })
  })

  describe('Loading and error states', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should show loading state', async () => {
      // Mock a delayed response
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: async () => mockApiResponse
        }), 100))
      )

      render(<AdminUserManagement />)

      expect(screen.getByText('Loading users...')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument()
      }, { timeout: 200 })
    })

    it('should handle API errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })

    it('should handle empty results', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...mockApiResponse,
          users: [],
          total_count: 0
        })
      })

      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('No users found matching your criteria.')).toBeInTheDocument()
      })
    })
  })

  describe('Pagination', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should show pagination when there are multiple pages', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...mockApiResponse,
          total_pages: 3,
          has_next: true
        })
      })

      render(<AdminUserManagement />)

      await waitFor(() => {
        expect(screen.getByText('Previous')).toBeInTheDocument()
        expect(screen.getByText('Next')).toBeInTheDocument()
        expect(screen.getByText('1')).toBeInTheDocument()
      })
    })

    it('should handle page navigation', async () => {
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            ...mockApiResponse,
            total_pages: 3,
            has_next: true
          })
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            ...mockApiResponse,
            page: 2,
            total_pages: 3,
            has_next: true,
            has_previous: true
          })
        })

      render(<AdminUserManagement />)

      await waitFor(() => {
        const nextButton = screen.getByText('Next')
        fireEvent.click(nextButton)
      })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('page=2'),
          expect.any(Object)
        )
      })
    })
  })

  describe('Refresh functionality', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should refresh data when refresh button is clicked', async () => {
      render(<AdminUserManagement />)

      await waitFor(() => {
        const refreshButton = screen.getByText('Refresh')
        fireEvent.click(refreshButton)
      })

      expect(global.fetch).toHaveBeenCalledTimes(2) // Initial load + refresh
    })

    it('should disable refresh button while loading', async () => {
      // Mock a delayed response
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({
          ok: true,
          json: async () => mockApiResponse
        }), 100))
      )

      render(<AdminUserManagement />)

      const refreshButton = screen.getByText('Refresh')
      fireEvent.click(refreshButton)

      expect(refreshButton).toBeDisabled()

      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled()
      }, { timeout: 200 })
    })
  })
})