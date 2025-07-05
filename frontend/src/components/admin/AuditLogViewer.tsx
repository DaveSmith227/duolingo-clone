'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Filter, 
  Download, 
  Calendar,
  Shield,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
  Monitor,
  User,
  Clock,
  MapPin
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { 
  sanitizeSearchQuery, 
  sanitizeUrlParams, 
  escapeHtml,
  RateLimiter,
  getSecurityHeaders,
  sanitizePaginationParams 
} from '@/lib/security'

interface AuditLogEntry {
  id: string
  event_type: string
  user_id: string | null
  user_email: string | null
  success: boolean
  ip_address: string | null
  user_agent: string | null
  details: Record<string, any> | null
  created_at: string
}

interface AuditLogResponse {
  logs: AuditLogEntry[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface AuditLogFilters {
  user_id: string
  event_type: string
  success: string
  ip_address: string
  created_after: string
  created_before: string
}

interface AuditLogViewerProps {
  className?: string
}

const EVENT_TYPE_OPTIONS = [
  { value: '', label: 'All Events' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'registration', label: 'Registration' },
  { value: 'password_reset', label: 'Password Reset' },
  { value: 'password_change', label: 'Password Change' },
  { value: 'profile_update', label: 'Profile Update' },
  { value: 'admin_user_suspend', label: 'Admin: User Suspend' },
  { value: 'admin_user_unsuspend', label: 'Admin: User Unsuspend' },
  { value: 'admin_user_delete', label: 'Admin: User Delete' },
  { value: 'admin_bulk_suspend', label: 'Admin: Bulk Suspend' },
  { value: 'admin_bulk_unsuspend', label: 'Admin: Bulk Unsuspend' },
  { value: 'failed_login_attempt', label: 'Failed Login' },
  { value: 'account_locked', label: 'Account Locked' },
  { value: 'suspicious_activity', label: 'Suspicious Activity' }
]

// Rate limiter instance (10 requests per minute)
const rateLimiter = new RateLimiter(10, 60000)

export function AuditLogViewer({ className = '' }: AuditLogViewerProps) {
  const { user: currentUser, hasPermission } = useAuth()
  
  // State management
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(50)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)
  
  // Filter state
  const [filters, setFilters] = useState<AuditLogFilters>({
    user_id: '',
    event_type: '',
    success: '',
    ip_address: '',
    created_after: '',
    created_before: ''
  })
  
  // UI state
  const [showFilters, setShowFilters] = useState(false)
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null)
  
  // Check admin permissions
  const canViewAuditLogs = hasPermission('admin.audit.view') || hasPermission('admin.all')
  
  // Fetch audit logs
  const fetchLogs = useCallback(async () => {
    if (!canViewAuditLogs) return
    
    setLoading(true)
    setError(null)
    
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString()
      })
      
      // Add filters
      Object.entries(filters).forEach(([key, value]) => {
        if (value.trim()) {
          params.append(key, value.trim())
        }
      })
      
      const response = await fetch(`/api/admin/audit-logs?${params}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch audit logs')
      }
      
      const data: AuditLogResponse = await response.json()
      setLogs(data.logs)
      setTotalCount(data.total_count)
      setTotalPages(data.total_pages)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch audit logs')
    } finally {
      setLoading(false)
    }
  }, [currentPage, pageSize, filters, canViewAuditLogs])
  
  // Fetch logs on mount and filter changes
  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])
  
  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<AuditLogFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setCurrentPage(1)
  }, [])
  
  // Handle pagination
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page)
  }, [])
  
  // Export logs
  const exportLogs = useCallback(async (format: 'json' | 'csv') => {
    if (!canViewAuditLogs) return
    
    setExporting(true)
    
    try {
      const response = await fetch('/api/admin/audit-logs/export', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          format,
          filters: Object.fromEntries(
            Object.entries(filters).filter(([_, value]) => value.trim())
          ),
          include_details: true
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to export audit logs')
      }
      
      // Download file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export audit logs')
    } finally {
      setExporting(false)
    }
  }, [filters, canViewAuditLogs])
  
  // Format date helper
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }
  
  // Get event type icon
  const getEventIcon = (eventType: string, success: boolean) => {
    if (!success) {
      return <XCircle className="w-4 h-4 text-red-500" />
    }
    
    switch (eventType) {
      case 'login':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'logout':
        return <XCircle className="w-4 h-4 text-gray-500" />
      case 'registration':
        return <User className="w-4 h-4 text-blue-500" />
      case 'password_reset':
      case 'password_change':
        return <Shield className="w-4 h-4 text-orange-500" />
      default:
        if (eventType.startsWith('admin_')) {
          return <Shield className="w-4 h-4 text-purple-500" />
        }
        return <FileText className="w-4 h-4 text-gray-500" />
    }
  }
  
  // Get event type badge color
  const getEventBadgeColor = (eventType: string, success: boolean) => {
    if (!success) {
      return 'bg-red-100 text-red-800'
    }
    
    switch (eventType) {
      case 'login':
        return 'bg-green-100 text-green-800'
      case 'logout':
        return 'bg-gray-100 text-gray-800'
      case 'registration':
        return 'bg-blue-100 text-blue-800'
      case 'password_reset':
      case 'password_change':
        return 'bg-orange-100 text-orange-800'
      default:
        if (eventType.startsWith('admin_')) {
          return 'bg-purple-100 text-purple-800'
        }
        return 'bg-gray-100 text-gray-800'
    }
  }
  
  // Log details modal
  const LogDetailsModal = ({ log }: { log: AuditLogEntry }) => (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={() => setSelectedLog(null)}
        />
        
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="inline-block transform overflow-hidden rounded-lg bg-white text-left align-bottom shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:align-middle"
        >
          <div className="bg-white px-6 py-4">
            <div className="flex items-center justify-between border-b border-gray-200 pb-3">
              <h3 className="text-lg font-medium text-gray-900">
                Audit Log Details
              </h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Event Type</label>
                  <div className="flex items-center mt-1">
                    {getEventIcon(log.event_type, log.success)}
                    <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${getEventBadgeColor(log.event_type, log.success)}`}>
                      {log.event_type}
                    </span>
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-500">Status</label>
                  <div className="mt-1">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {log.success ? 'Success' : 'Failed'}
                    </span>
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-500">User</label>
                  <div className="mt-1 text-sm text-gray-900">
                    {log.user_email || 'Anonymous'}
                    {log.user_id && (
                      <div className="text-xs text-gray-500">ID: {log.user_id}</div>
                    )}
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-500">Timestamp</label>
                  <div className="mt-1 text-sm text-gray-900">
                    {formatDate(log.created_at)}
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-500">IP Address</label>
                  <div className="mt-1 text-sm text-gray-900">
                    {log.ip_address || 'N/A'}
                  </div>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-gray-500">User Agent</label>
                  <div className="mt-1 text-sm text-gray-900 truncate" title={log.user_agent || ''}>
                    {log.user_agent || 'N/A'}
                  </div>
                </div>
              </div>
              
              {log.details && Object.keys(log.details).length > 0 && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Details</label>
                  <div className="mt-1">
                    <pre className="text-xs bg-gray-50 rounded p-3 overflow-auto max-h-40">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
  
  if (!canViewAuditLogs) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-500">You don&apos;t have permission to view audit logs.</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Audit Logs</h2>
            <p className="text-sm text-gray-500 mt-1">
              View authentication events and security audit trail
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium transition-colors ${
                showFilters 
                  ? 'bg-blue-50 text-blue-700 border-blue-300' 
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </button>
            
            <div className="relative">
              <button 
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                onClick={() => exportLogs('json')}
                disabled={exporting}
              >
                <Download className="w-4 h-4 mr-2" />
                Export JSON
              </button>
            </div>
            
            <button 
              className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              onClick={() => exportLogs('csv')}
              disabled={exporting}
            >
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </button>
            
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="inline-flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-6 py-4 bg-gray-50 border-b border-gray-200"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Event Type
                </label>
                <select
                  value={filters.event_type}
                  onChange={(e) => handleFilterChange({ event_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  {EVENT_TYPE_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Success Status
                </label>
                <select
                  value={filters.success}
                  onChange={(e) => handleFilterChange({ success: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All</option>
                  <option value="true">Success</option>
                  <option value="false">Failed</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  IP Address
                </label>
                <input
                  type="text"
                  value={filters.ip_address}
                  onChange={(e) => handleFilterChange({ ip_address: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="192.168.1.1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  After
                </label>
                <input
                  type="datetime-local"
                  value={filters.created_after}
                  onChange={(e) => handleFilterChange({ created_after: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Before
                </label>
                <input
                  type="datetime-local"
                  value={filters.created_before}
                  onChange={(e) => handleFilterChange({ created_before: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Error Display */}
      {error && (
        <div className="px-6 py-4 bg-red-50 border-b border-red-200">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
            <span className="text-sm text-red-700">{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-600"
            >
              ×
            </button>
          </div>
        </div>
      )}
      
      {/* Logs Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Event
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                IP Address
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center">
                  <div className="flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 animate-spin text-gray-400 mr-2" />
                    <span className="text-gray-500">Loading audit logs...</span>
                  </div>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center">
                  <div className="text-gray-500">
                    <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>No audit logs found matching your criteria.</p>
                  </div>
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center">
                      {getEventIcon(log.event_type, log.success)}
                      <div className="ml-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEventBadgeColor(log.event_type, log.success)}`}>
                          {log.event_type}
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {log.user_email || 'Anonymous'}
                    </div>
                    {log.user_id && (
                      <div className="text-xs text-gray-500">ID: {log.user_id}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {log.success ? 'Success' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <div className="flex items-center">
                      <MapPin className="w-3 h-3 mr-1" />
                      {log.ip_address || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <div className="flex items-center">
                      <Clock className="w-3 h-3 mr-1" />
                      {formatDate(log.created_at)}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="text-blue-600 hover:text-blue-900 text-sm font-medium"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} entries
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Previous
              </button>
              
              <div className="flex items-center space-x-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const page = i + 1
                  return (
                    <button
                      key={page}
                      onClick={() => handlePageChange(page)}
                      className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                        currentPage === page
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  )
                })}
              </div>
              
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Log Details Modal */}
      <AnimatePresence>
        {selectedLog && <LogDetailsModal log={selectedLog} />}
      </AnimatePresence>
    </div>
  )
}