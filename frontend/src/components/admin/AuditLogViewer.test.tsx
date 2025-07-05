import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuditLogViewer } from './AuditLogViewer'

// Mock useAuth hook
const mockUseAuth = vi.fn()
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth()
}))

// Mock fetch
global.fetch = vi.fn()

const mockAuditLogs = [
  {
    id: '1',
    event_type: 'login',
    user_id: 'user1',
    user_email: 'user1@example.com',
    success: true,
    ip_address: '192.168.1.1',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    details: { login_method: 'email', remember_me: false },
    created_at: '2024-01-01T10:00:00Z'
  },
  {
    id: '2',
    event_type: 'login',
    user_id: 'user2',
    user_email: 'user2@example.com',
    success: false,
    ip_address: '192.168.1.2',
    user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    details: { error: 'Invalid credentials', attempts: 3 },
    created_at: '2024-01-01T11:00:00Z'
  },
  {
    id: '3',
    event_type: 'admin_user_suspend',
    user_id: 'admin1',
    user_email: 'admin@example.com',
    success: true,
    ip_address: '10.0.0.1',
    user_agent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    details: { target_user: 'user2@example.com', reason: 'Policy violation' },
    created_at: '2024-01-01T12:00:00Z'
  }
]

const mockApiResponse = {
  logs: mockAuditLogs,
  total_count: 3,
  page: 1,
  page_size: 50,
  total_pages: 1,
  has_next: false,
  has_previous: false
}

describe('AuditLogViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock successful fetch response
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockApiResponse
    })

    // Mock URL.createObjectURL and related functions for export tests
    global.URL.createObjectURL = vi.fn(() => 'mock-url')
    global.URL.revokeObjectURL = vi.fn()
    
    // Mock createElement and appendChild for download tests
    const mockAnchor = {
      href: '',
      download: '',
      click: vi.fn()
    }
    document.createElement = vi.fn().mockReturnValue(mockAnchor)
    document.body.appendChild = vi.fn()
    document.body.removeChild = vi.fn()
  })

  describe('Permission-based rendering', () => {
    it('should show access denied when user lacks audit permissions', () => {
      mockUseAuth.mockReturnValue({
        user: { id: 'user1', email: 'user@example.com' },
        hasPermission: vi.fn().mockReturnValue(false)
      })

      render(<AuditLogViewer />)

      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.getByText("You don't have permission to view audit logs.")).toBeInTheDocument()
    })

    it('should render audit log viewer when user has permissions', async () => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })

      render(<AuditLogViewer />)

      await waitFor(() => {
        expect(screen.getByText('Audit Logs')).toBeInTheDocument()
      })
    })
  })

  describe('Audit log display', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should display audit logs correctly', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        expect(screen.getByText('user1@example.com')).toBeInTheDocument()
        expect(screen.getByText('user2@example.com')).toBeInTheDocument()
        expect(screen.getByText('admin@example.com')).toBeInTheDocument()
      })
    })

    it('should show correct event types', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const loginEvents = screen.getAllByText('login')
        expect(loginEvents).toHaveLength(2)
        
        const adminEvent = screen.getByText('admin_user_suspend')
        expect(adminEvent).toBeInTheDocument()
      })
    })

    it('should display success and failed status correctly', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const successBadges = screen.getAllByText('Success')
        expect(successBadges).toHaveLength(2)
        
        const failedBadge = screen.getByText('Failed')
        expect(failedBadge).toBeInTheDocument()
      })
    })

    it('should show IP addresses and timestamps', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        expect(screen.getByText('192.168.1.1')).toBeInTheDocument()
        expect(screen.getByText('192.168.1.2')).toBeInTheDocument()
        expect(screen.getByText('10.0.0.1')).toBeInTheDocument()
      })
    })
  })

  describe('Filtering functionality', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should show filters when filter button is clicked', async () => {
      render(<AuditLogViewer />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        expect(screen.getByText('Event Type')).toBeInTheDocument()
        expect(screen.getByText('Success Status')).toBeInTheDocument()
        expect(screen.getByText('IP Address')).toBeInTheDocument()
        expect(screen.getByText('After')).toBeInTheDocument()
        expect(screen.getByText('Before')).toBeInTheDocument()
      })
    })

    it('should handle event type filter changes', async () => {
      render(<AuditLogViewer />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        const eventTypeSelect = screen.getByDisplayValue('All Events')
        fireEvent.change(eventTypeSelect, { target: { value: 'login' } })
        
        expect(eventTypeSelect).toHaveValue('login')
      })
    })

    it('should handle success status filter', async () => {
      render(<AuditLogViewer />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        const successSelect = screen.getByDisplayValue('All')
        fireEvent.change(successSelect, { target: { value: 'true' } })
        
        expect(successSelect).toHaveValue('true')
      })
    })

    it('should handle IP address filter', async () => {
      render(<AuditLogViewer />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        const ipInput = screen.getByPlaceholderText('192.168.1.1')
        fireEvent.change(ipInput, { target: { value: '192.168.1.1' } })
        
        expect(ipInput).toHaveValue('192.168.1.1')
      })
    })

    it('should handle date range filters', async () => {
      render(<AuditLogViewer />)

      const filterButton = screen.getByText('Filters')
      fireEvent.click(filterButton)

      await waitFor(() => {
        const afterInput = screen.getByLabelText('After')
        const beforeInput = screen.getByLabelText('Before')
        
        fireEvent.change(afterInput, { target: { value: '2024-01-01T00:00' } })
        fireEvent.change(beforeInput, { target: { value: '2024-01-02T00:00' } })
        
        expect(afterInput).toHaveValue('2024-01-01T00:00')
        expect(beforeInput).toHaveValue('2024-01-02T00:00')
      })
    })
  })

  describe('Log details modal', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should open details modal when View Details is clicked', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const viewDetailsButtons = screen.getAllByText('View Details')
        fireEvent.click(viewDetailsButtons[0])
      })

      await waitFor(() => {
        expect(screen.getByText('Audit Log Details')).toBeInTheDocument()
        expect(screen.getByText('Event Type')).toBeInTheDocument()
        expect(screen.getByText('Status')).toBeInTheDocument()
        expect(screen.getByText('User')).toBeInTheDocument()
        expect(screen.getByText('Timestamp')).toBeInTheDocument()
      })
    })

    it('should show detailed information in modal', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const viewDetailsButtons = screen.getAllByText('View Details')
        fireEvent.click(viewDetailsButtons[0])
      })

      await waitFor(() => {
        expect(screen.getByText('user1@example.com')).toBeInTheDocument()
        expect(screen.getByText('192.168.1.1')).toBeInTheDocument()
        expect(screen.getByText('ID: user1')).toBeInTheDocument()
      })
    })

    it('should close modal when X button is clicked', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const viewDetailsButtons = screen.getAllByText('View Details')
        fireEvent.click(viewDetailsButtons[0])
      })

      await waitFor(() => {
        const closeButton = screen.getByText('×')
        fireEvent.click(closeButton)
      })

      await waitFor(() => {
        expect(screen.queryByText('Audit Log Details')).not.toBeInTheDocument()
      })
    })

    it('should show details JSON when available', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const viewDetailsButtons = screen.getAllByText('View Details')
        fireEvent.click(viewDetailsButtons[0])
      })

      await waitFor(() => {
        expect(screen.getByText('Details')).toBeInTheDocument()
        expect(screen.getByText(/"login_method": "email"/)).toBeInTheDocument()
        expect(screen.getByText(/"remember_me": false/)).toBeInTheDocument()
      })
    })
  })

  describe('Export functionality', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should handle JSON export', async () => {
      // Mock blob response for export
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiResponse
        })
        .mockResolvedValueOnce({
          ok: true,
          blob: async () => new Blob(['mock json data'], { type: 'application/json' })
        })

      render(<AuditLogViewer />)

      await waitFor(() => {
        const exportButton = screen.getByText('Export JSON')
        fireEvent.click(exportButton)
      })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/admin/audit-logs/export',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json'
            }),
            body: expect.stringContaining('json')
          })
        )
      })
    })

    it('should handle CSV export', async () => {
      // Mock blob response for export
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiResponse
        })
        .mockResolvedValueOnce({
          ok: true,
          blob: async () => new Blob(['mock csv data'], { type: 'text/csv' })
        })

      render(<AuditLogViewer />)

      await waitFor(() => {
        const exportButton = screen.getByText('Export CSV')
        fireEvent.click(exportButton)
      })

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          '/api/admin/audit-logs/export',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json'
            }),
            body: expect.stringContaining('csv')
          })
        )
      })
    })

    it('should handle export errors', async () => {
      global.fetch = vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockApiResponse
        })
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ detail: 'Export failed' })
        })

      render(<AuditLogViewer />)

      await waitFor(() => {
        const exportButton = screen.getByText('Export JSON')
        fireEvent.click(exportButton)
      })

      await waitFor(() => {
        expect(screen.getByText('Failed to export audit logs')).toBeInTheDocument()
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

      render(<AuditLogViewer />)

      expect(screen.getByText('Loading audit logs...')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('user1@example.com')).toBeInTheDocument()
      }, { timeout: 200 })
    })

    it('should handle API errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      render(<AuditLogViewer />)

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })

    it('should handle empty results', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...mockApiResponse,
          logs: [],
          total_count: 0
        })
      })

      render(<AuditLogViewer />)

      await waitFor(() => {
        expect(screen.getByText('No audit logs found matching your criteria.')).toBeInTheDocument()
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

      render(<AuditLogViewer />)

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

      render(<AuditLogViewer />)

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
      render(<AuditLogViewer />)

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

      render(<AuditLogViewer />)

      const refreshButton = screen.getByText('Refresh')
      fireEvent.click(refreshButton)

      expect(refreshButton).toBeDisabled()

      await waitFor(() => {
        expect(refreshButton).not.toBeDisabled()
      }, { timeout: 200 })
    })
  })

  describe('Event icons and styling', () => {
    beforeEach(() => {
      mockUseAuth.mockReturnValue({
        user: { id: 'admin1', email: 'admin@example.com' },
        hasPermission: vi.fn().mockReturnValue(true)
      })
    })

    it('should display appropriate icons for different event types', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        // Should have icons for different event types
        const eventIcons = document.querySelectorAll('svg')
        expect(eventIcons.length).toBeGreaterThan(0)
      })
    })

    it('should apply correct styling for success vs failed events', async () => {
      render(<AuditLogViewer />)

      await waitFor(() => {
        const successBadges = screen.getAllByText('Success')
        const failedBadges = screen.getAllByText('Failed')
        
        expect(successBadges.length).toBeGreaterThan(0)
        expect(failedBadges.length).toBeGreaterThan(0)
      })
    })
  })
})