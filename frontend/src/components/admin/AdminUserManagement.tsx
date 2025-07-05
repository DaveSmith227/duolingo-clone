'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Search, 
  Filter, 
  Download, 
  UserCheck, 
  UserX, 
  Trash2, 
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Shield,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Eye,
  Settings,
  Key,
  LogOut,
  ShieldCheck
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { UserActionDialog, UserActionType } from './UserActionDialog'
import { BulkUserActionDialog, BulkUserActionType } from './BulkUserActionDialog'
import { 
  sanitizeSearchQuery, 
  sanitizeUrlParams, 
  escapeHtml,
  RateLimiter,
  getSecurityHeaders,
  sanitizeSortParams,
  sanitizePaginationParams 
} from '@/lib/security'

interface User {
  id: string
  email: string
  name: string
  is_active: boolean
  is_suspended: boolean
  created_at: string
  updated_at: string | null
  last_login_at: string | null
  login_count: number
  failed_login_count: number
  roles: string[]
  supabase_id: string | null
}

interface UserSearchResponse {
  users: User[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

interface SearchFilters {
  query: string
  status: 'all' | 'active' | 'suspended' | 'deleted'
  created_after: string
  created_before: string
  sort_by: 'created_at' | 'email' | 'name' | 'updated_at'
  sort_order: 'asc' | 'desc'
}

interface AdminUserManagementProps {
  className?: string
}

// Rate limiter instance (10 requests per minute)
const rateLimiter = new RateLimiter(10, 60000)

export function AdminUserManagement({ className = '' }: AdminUserManagementProps) {
  const { user: currentUser, hasPermission } = useAuth()
  
  // State management
  const [users, setUsers] = useState<User[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Filter state
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    status: 'all',
    created_after: '',
    created_before: '',
    sort_by: 'created_at',
    sort_order: 'desc'
  })
  
  // UI state
  const [showFilters, setShowFilters] = useState(false)
  const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set())
  const [actionMenuUser, setActionMenuUser] = useState<string | null>(null)
  const [actionDialog, setActionDialog] = useState<{
    isOpen: boolean
    user: User | null
    action: UserActionType | null
    loading: boolean
  }>({
    isOpen: false,
    user: null,
    action: null,
    loading: false
  })
  const [bulkActionDialog, setBulkActionDialog] = useState<{
    isOpen: boolean
    action: BulkUserActionType | null
    loading: boolean
  }>({
    isOpen: false,
    action: null,
    loading: false
  })
  
  // Check admin permissions
  const canManageUsers = hasPermission('admin.users.manage') || hasPermission('admin.all')
  
  // Fetch users
  const fetchUsers = useCallback(async () => {
    if (!canManageUsers) return
    
    // Rate limiting check
    if (!rateLimiter.isAllowed(`user-search-${currentUser?.id}`)) {
      setError('Too many requests. Please wait a moment.')
      return
    }
    
    setLoading(true)
    setError(null)
    
    try {
      // Sanitize and validate parameters
      const { sortBy, sortOrder } = sanitizeSortParams(filters.sort_by, filters.sort_order)
      const { page, pageSize: validPageSize } = sanitizePaginationParams(currentPage, pageSize)
      
      const sanitizedParams = {
        page: page.toString(),
        page_size: validPageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
        status: filters.status
      }
      
      // Sanitize search query
      if (filters.query.trim()) {
        const sanitizedQuery = sanitizeSearchQuery(filters.query.trim())
        if (sanitizedQuery) {
          sanitizedParams.query = sanitizedQuery
        }
      }
      
      // Validate dates
      if (filters.created_after && !isNaN(Date.parse(filters.created_after))) {
        sanitizedParams.created_after = filters.created_after
      }
      if (filters.created_before && !isNaN(Date.parse(filters.created_before))) {
        sanitizedParams.created_before = filters.created_before
      }
      
      const params = sanitizeUrlParams(sanitizedParams)
      
      const response = await fetch(`/api/admin/users/search?${params}`, {
        credentials: 'include',
        headers: getSecurityHeaders()
      })
      
      if (!response.ok) {
        // Don't expose detailed error messages
        throw new Error('Failed to fetch users')
      }
      
      const data: UserSearchResponse = await response.json()
      setUsers(data.users)
      setTotalCount(data.total_count)
      setTotalPages(data.total_pages)
      
    } catch (err) {
      // Log error details server-side, show generic message to user
      console.error('User fetch error:', err)
      setError('Failed to fetch users. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [currentPage, pageSize, filters, canManageUsers, currentUser?.id])
  
  // Fetch users on mount and filter changes
  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])
  
  // Handle search
  const handleSearch = useCallback((query: string) => {
    setFilters(prev => ({ ...prev, query }))
    setCurrentPage(1)
  }, [])
  
  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<SearchFilters>) => {
    setFilters(prev => ({ ...prev, ...newFilters }))
    setCurrentPage(1)
  }, [])
  
  // Handle user selection
  const toggleUserSelection = useCallback((userId: string) => {
    setSelectedUsers(prev => {
      const newSelection = new Set(prev)
      if (newSelection.has(userId)) {
        newSelection.delete(userId)
      } else {
        newSelection.add(userId)
      }
      return newSelection
    })
  }, [])
  
  // Handle select all
  const toggleSelectAll = useCallback(() => {
    if (selectedUsers.size === users.length) {
      setSelectedUsers(new Set())
    } else {
      setSelectedUsers(new Set(users.map(user => user.id)))
    }
  }, [users, selectedUsers.size])
  
  // Handle pagination
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page)
    setSelectedUsers(new Set())
  }, [])
  
  // Open action dialog
  const openActionDialog = useCallback((user: User, action: UserActionType) => {
    setActionDialog({
      isOpen: true,
      user,
      action,
      loading: false
    })
    setActionMenuUser(null)
  }, [])

  // Close action dialog
  const closeActionDialog = useCallback(() => {
    setActionDialog({
      isOpen: false,
      user: null,
      action: null,
      loading: false
    })
  }, [])

  // Perform user action
  const performUserAction = useCallback(async (action: UserActionType, reason: string, additionalData: any = {}) => {
    if (!actionDialog.user) return

    setActionDialog(prev => ({ ...prev, loading: true }))

    try {
      const response = await fetch(`/api/admin/users/${actionDialog.user.id}/actions`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          action, 
          reason,
          additional_data: additionalData
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to ${action} user`)
      }
      
      // Refresh users list
      await fetchUsers()
      closeActionDialog()
      
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} user`)
      setActionDialog(prev => ({ ...prev, loading: false }))
    }
  }, [actionDialog.user, fetchUsers, closeActionDialog])

  // Open bulk action dialog
  const openBulkActionDialog = useCallback((action: BulkUserActionType) => {
    setBulkActionDialog({
      isOpen: true,
      action,
      loading: false
    })
  }, [])

  // Close bulk action dialog
  const closeBulkActionDialog = useCallback(() => {
    setBulkActionDialog({
      isOpen: false,
      action: null,
      loading: false
    })
  }, [])

  // Perform bulk user action
  const performBulkUserAction = useCallback(async (action: BulkUserActionType, reason: string, userIds: string[]) => {
    setBulkActionDialog(prev => ({ ...prev, loading: true }))

    try {
      const response = await fetch('/api/admin/users/bulk-actions', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          action, 
          reason,
          user_ids: userIds
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to ${action} users`)
      }
      
      // Refresh users list and clear selection
      await fetchUsers()
      setSelectedUsers(new Set())
      closeBulkActionDialog()
      
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} users`)
      setBulkActionDialog(prev => ({ ...prev, loading: false }))
    }
  }, [fetchUsers, closeBulkActionDialog])

  // Get selected users
  const selectedUsersData = useMemo(() => {
    return users.filter(user => selectedUsers.has(user.id))
  }, [users, selectedUsers])
  
  // Status badge component
  const StatusBadge = ({ user }: { user: User }) => {
    if (!user.is_active && user.is_suspended) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <UserX className="w-3 h-3 mr-1" />
          Suspended
        </span>
      )
    }
    if (user.is_active) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <UserCheck className="w-3 h-3 mr-1" />
          Active
        </span>
      )
    }
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        <Clock className="w-3 h-3 mr-1" />
        Inactive
      </span>
    )
  }
  
  // Format date helper
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  
  // Render user actions menu
  const UserActionsMenu = ({ user }: { user: User }) => (
    <div className="absolute right-0 top-8 z-10 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
      <button
        onClick={() => {/* Handle view details */}}
        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center"
      >
        <Eye className="w-4 h-4 mr-2" />
        View Details
      </button>
      
      {user.is_active ? (
        <button
          onClick={() => openActionDialog(user, 'suspend')}
          className="w-full px-4 py-2 text-left text-sm text-orange-600 hover:bg-orange-50 flex items-center"
        >
          <UserX className="w-4 h-4 mr-2" />
          Suspend User
        </button>
      ) : (
        <button
          onClick={() => openActionDialog(user, 'unsuspend')}
          className="w-full px-4 py-2 text-left text-sm text-green-600 hover:bg-green-50 flex items-center"
        >
          <UserCheck className="w-4 h-4 mr-2" />
          Unsuspend User
        </button>
      )}
      
      <button
        onClick={() => openActionDialog(user, 'force_logout')}
        className="w-full px-4 py-2 text-left text-sm text-yellow-600 hover:bg-yellow-50 flex items-center"
      >
        <LogOut className="w-4 h-4 mr-2" />
        Force Logout
      </button>
      
      <button
        onClick={() => openActionDialog(user, 'reset_password')}
        className="w-full px-4 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 flex items-center"
      >
        <Key className="w-4 h-4 mr-2" />
        Reset Password
      </button>
      
      <button
        onClick={() => openActionDialog(user, 'change_role')}
        className="w-full px-4 py-2 text-left text-sm text-purple-600 hover:bg-purple-50 flex items-center"
      >
        <ShieldCheck className="w-4 h-4 mr-2" />
        Change Role
      </button>
      
      <div className="border-t border-gray-100 my-1" />
      
      <button
        onClick={() => openActionDialog(user, 'delete')}
        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center"
      >
        <Trash2 className="w-4 h-4 mr-2" />
        Delete User
      </button>
    </div>
  )
  
  if (!canManageUsers) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-500">You don&apos;t have permission to manage users.</p>
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
            <h2 className="text-xl font-semibold text-gray-900">User Management</h2>
            <p className="text-sm text-gray-500 mt-1">
              Manage user accounts, permissions, and access
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
            <button className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
              <Download className="w-4 h-4 mr-2" />
              Export
            </button>
            <button
              onClick={fetchUsers}
              disabled={loading}
              className="inline-flex items-center px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>
      </div>
      
      {/* Search and Filters */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Search users by email or name..."
              value={filters.query}
              onChange={(e) => handleSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <select
            value={filters.status}
            onChange={(e) => handleFilterChange({ status: e.target.value as any })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Users</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
            <option value="deleted">Deleted</option>
          </select>
        </div>
        
        {/* Advanced Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 p-4 bg-gray-50 rounded-lg"
            >
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Created After
                  </label>
                  <input
                    type="date"
                    value={filters.created_after}
                    onChange={(e) => handleFilterChange({ created_after: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Created Before
                  </label>
                  <input
                    type="date"
                    value={filters.created_before}
                    onChange={(e) => handleFilterChange({ created_before: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sort By
                  </label>
                  <select
                    value={filters.sort_by}
                    onChange={(e) => handleFilterChange({ sort_by: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="created_at">Created Date</option>
                    <option value="updated_at">Updated Date</option>
                    <option value="email">Email</option>
                    <option value="name">Name</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sort Order
                  </label>
                  <select
                    value={filters.sort_order}
                    onChange={(e) => handleFilterChange({ sort_order: e.target.value as any })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="desc">Newest First</option>
                    <option value="asc">Oldest First</option>
                  </select>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
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
      
      {/* Users Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedUsers.size === users.length && users.length > 0}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Roles
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Login Stats
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Login
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center">
                  <div className="flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 animate-spin text-gray-400 mr-2" />
                    <span className="text-gray-500">Loading users...</span>
                  </div>
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-12 text-center">
                  <div className="text-gray-500">
                    <Search className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>No users found matching your criteria.</p>
                  </div>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedUsers.has(user.id)}
                      onChange={() => toggleUserSelection(user.id)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {escapeHtml(user.name || 'Unknown')}
                      </div>
                      <div className="text-sm text-gray-500">{escapeHtml(user.email)}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge user={user} />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((role) => (
                        <span
                          key={role}
                          className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
                        >
                          {escapeHtml(role)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {user.login_count} successful
                    </div>
                    <div className="text-sm text-gray-500">
                      {user.failed_login_count} failed
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(user.last_login_at)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="px-6 py-4 relative">
                    <button
                      onClick={() => setActionMenuUser(actionMenuUser === user.id ? null : user.id)}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <MoreVertical className="w-5 h-5" />
                    </button>
                    {actionMenuUser === user.id && (
                      <UserActionsMenu user={user} />
                    )}
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
              Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} users
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
      
      {/* Bulk Actions */}
      {selectedUsers.size > 0 && (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-3">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              {selectedUsers.size} user{selectedUsers.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex items-center space-x-2">
              <button 
                onClick={() => openBulkActionDialog('suspend')}
                className="px-3 py-1 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 transition-colors"
              >
                Suspend
              </button>
              <button 
                onClick={() => openBulkActionDialog('unsuspend')}
                className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
              >
                Unsuspend
              </button>
            </div>
            <button
              onClick={() => setSelectedUsers(new Set())}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* User Action Dialog */}
      <UserActionDialog
        isOpen={actionDialog.isOpen}
        onClose={closeActionDialog}
        onConfirm={performUserAction}
        user={actionDialog.user}
        action={actionDialog.action}
        loading={actionDialog.loading}
      />

      {/* Bulk User Action Dialog */}
      <BulkUserActionDialog
        isOpen={bulkActionDialog.isOpen}
        onClose={closeBulkActionDialog}
        onConfirm={performBulkUserAction}
        users={selectedUsersData}
        action={bulkActionDialog.action}
        loading={bulkActionDialog.loading}
      />
    </div>
  )
}