import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AdminAnalyticsDashboard } from './AdminAnalyticsDashboard'
import { useAuthStore } from '@/stores/authStore'
import { adminApi } from '@/lib/api/admin'

// Mock dependencies
vi.mock('@/stores/authStore')
vi.mock('@/lib/api/admin')
vi.mock('./AuthTrendsChart', () => ({
  AuthTrendsChart: () => <div>Auth Trends Chart</div>
}))

const mockUser = {
  id: 'admin123',
  email: 'admin@example.com',
  role: 'admin'
}

const mockMetrics = {
  totalUsers: 12543,
  activeUsers: 8934,
  successfulLogins: 45672,
  failedLogins: 1234,
  loginSuccessRate: 97.4,
  averageSessionDuration: 1800,
  newUsersToday: 156,
  newUsersThisWeek: 892,
  suspendedUsers: 45,
  deletedUsers: 12
}

const mockAlerts = [
  {
    id: '1',
    type: 'failed_login' as const,
    severity: 'medium' as const,
    message: 'Multiple failed login attempts detected',
    userId: 'user123',
    userEmail: 'suspicious@example.com',
    timestamp: new Date().toISOString(),
    ipAddress: '192.168.1.100'
  }
]

const mockTrends = {
  loginTrends: [
    { timestamp: new Date().toISOString(), value: 1000 },
    { timestamp: new Date(Date.now() - 86400000).toISOString(), value: 950 }
  ],
  registrationTrends: [
    { timestamp: new Date().toISOString(), value: 50 },
    { timestamp: new Date(Date.now() - 86400000).toISOString(), value: 45 }
  ],
  failureTrends: [
    { timestamp: new Date().toISOString(), value: 20 },
    { timestamp: new Date(Date.now() - 86400000).toISOString(), value: 25 }
  ]
}

describe('AdminAnalyticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuthStore).mockReturnValue({ user: mockUser } as any)
    vi.mocked(adminApi.getAuthMetrics).mockResolvedValue({ data: mockMetrics })
    vi.mocked(adminApi.getSecurityAlerts).mockResolvedValue({ data: mockAlerts })
    vi.mocked(adminApi.getAuthTrends).mockResolvedValue({ data: mockTrends })
    vi.mocked(adminApi.exportAnalytics).mockResolvedValue({ data: 'csv,data' })
  })

  it('renders dashboard with loading state initially', () => {
    render(<AdminAnalyticsDashboard />)
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('displays authentication metrics after loading', async () => {
    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Analytics')).toBeInTheDocument()
    })

    // Check metrics display
    expect(screen.getByText('12,543')).toBeInTheDocument() // Total users
    expect(screen.getByText('97.4%')).toBeInTheDocument() // Success rate
    expect(screen.getByText('1,234')).toBeInTheDocument() // Failed logins
    expect(screen.getByText('30m')).toBeInTheDocument() // Avg session duration
  })

  it('displays security alerts', async () => {
    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Security Alerts')).toBeInTheDocument()
    })

    expect(screen.getByText('Multiple failed login attempts detected')).toBeInTheDocument()
    expect(screen.getByText('User: suspicious@example.com')).toBeInTheDocument()
    expect(screen.getByText('IP: 192.168.1.100')).toBeInTheDocument()
  })

  it('handles date range selection', async () => {
    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Analytics')).toBeInTheDocument()
    })

    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: '30d' } })

    await waitFor(() => {
      expect(adminApi.getAuthMetrics).toHaveBeenCalledWith('30d')
    })
  })

  it('handles refresh button click', async () => {
    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Analytics')).toBeInTheDocument()
    })

    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    fireEvent.click(refreshButton)

    expect(adminApi.getAuthMetrics).toHaveBeenCalledTimes(2)
  })

  it('handles export functionality', async () => {
    // Mock URL methods
    const mockCreateObjectURL = vi.fn()
    const mockRevokeObjectURL = vi.fn()
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL

    // Mock createElement and click
    const mockClick = vi.fn()
    const mockAnchor = { href: '', download: '', click: mockClick }
    vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as any)

    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Analytics')).toBeInTheDocument()
    })

    const exportButton = screen.getByRole('button', { name: /export/i })
    fireEvent.click(exportButton)

    await waitFor(() => {
      expect(adminApi.exportAnalytics).toHaveBeenCalledWith('7d')
    })

    expect(mockCreateObjectURL).toHaveBeenCalled()
    expect(mockClick).toHaveBeenCalled()
    expect(mockRevokeObjectURL).toHaveBeenCalled()
  })

  it('displays error message on API failure', async () => {
    vi.mocked(adminApi.getAuthMetrics).mockRejectedValue(new Error('API Error'))

    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load analytics data')).toBeInTheDocument()
    })
  })

  it('renders empty state for no security alerts', async () => {
    vi.mocked(adminApi.getSecurityAlerts).mockResolvedValue({ data: [] })

    render(<AdminAnalyticsDashboard />)
    
    await waitFor(() => {
      expect(screen.getByText('No security alerts in the selected time period')).toBeInTheDocument()
    })
  })
})