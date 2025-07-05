'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  AlertTriangle,
  Shield,
  TrendingUp,
  TrendingDown,
  Users,
  UserCheck,
  UserX,
  Clock,
  Download,
  RefreshCw,
  Calendar,
  AlertCircle
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { adminApi } from '@/lib/api/admin'
import { sanitizeDateRange } from '@/lib/security'
import { rateLimiter } from '@/lib/security'
import { AuthTrendsChart } from './AuthTrendsChart'

interface AuthMetrics {
  totalUsers: number
  activeUsers: number
  successfulLogins: number
  failedLogins: number
  loginSuccessRate: number
  averageSessionDuration: number
  newUsersToday: number
  newUsersThisWeek: number
  suspendedUsers: number
  deletedUsers: number
}

interface SecurityAlert {
  id: string
  type: 'failed_login' | 'suspicious_activity' | 'brute_force' | 'account_locked'
  severity: 'low' | 'medium' | 'high' | 'critical'
  message: string
  userId?: string
  userEmail?: string
  timestamp: string
  ipAddress?: string
  metadata?: Record<string, any>
}

interface TimeSeriesData {
  timestamp: string
  value: number
}

interface AuthTrends {
  loginTrends: TimeSeriesData[]
  registrationTrends: TimeSeriesData[]
  failureTrends: TimeSeriesData[]
}

export function AdminAnalyticsDashboard() {
  const { user } = useAuthStore()
  const [metrics, setMetrics] = useState<AuthMetrics | null>(null)
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [trends, setTrends] = useState<AuthTrends | null>(null)
  const [dateRange, setDateRange] = useState('7d')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchAnalytics = useCallback(async () => {
    if (!rateLimiter.isAllowed(`analytics-fetch-${user?.id}`)) {
      setError('Too many requests. Please wait a moment.')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const sanitizedRange = sanitizeDateRange(dateRange)
      
      // Fetch all analytics data in parallel
      const [metricsRes, alertsRes, trendsRes] = await Promise.all([
        adminApi.getAuthMetrics(sanitizedRange),
        adminApi.getSecurityAlerts(sanitizedRange),
        adminApi.getAuthTrends(sanitizedRange)
      ])

      setMetrics(metricsRes.data)
      setAlerts(alertsRes.data)
      setTrends(trendsRes.data)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
      setError('Failed to load analytics data')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [user?.id, dateRange])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  const handleRefresh = () => {
    setRefreshing(true)
    fetchAnalytics()
  }

  const handleExport = async () => {
    if (!rateLimiter.isAllowed(`analytics-export-${user?.id}`)) {
      setError('Too many export requests. Please wait a moment.')
      return
    }

    try {
      const response = await adminApi.exportAnalytics(dateRange)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `auth-analytics-${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Failed to export analytics:', err)
      setError('Failed to export analytics data')
    }
  }

  const getSeverityColor = (severity: SecurityAlert['severity']) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100'
      case 'high': return 'text-orange-600 bg-orange-100'
      case 'medium': return 'text-yellow-600 bg-yellow-100'
      case 'low': return 'text-blue-600 bg-blue-100'
    }
  }

  const getSeverityIcon = (severity: SecurityAlert['severity']) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  if (loading && !refreshing) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Authentication Analytics</h2>
          <p className="text-gray-600 mt-1">Monitor authentication metrics and security alerts</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
          </select>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
        >
          {error}
        </motion.div>
      )}

      {/* Key Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white p-6 rounded-xl shadow-sm border border-gray-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Total Users</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.totalUsers.toLocaleString()}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <Users className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-500">
                    {metrics.activeUsers.toLocaleString()} active
                  </span>
                </div>
              </div>
              <div className="p-3 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white p-6 rounded-xl shadow-sm border border-gray-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Login Success Rate</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.loginSuccessRate.toFixed(1)}%
                </p>
                <div className="flex items-center gap-1 mt-2">
                  {metrics.loginSuccessRate >= 95 ? (
                    <TrendingUp className="h-4 w-4 text-green-500" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-sm text-gray-500">
                    {metrics.successfulLogins.toLocaleString()} successful
                  </span>
                </div>
              </div>
              <div className="p-3 bg-green-100 rounded-lg">
                <UserCheck className="h-6 w-6 text-green-600" />
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white p-6 rounded-xl shadow-sm border border-gray-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Failed Logins</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {metrics.failedLogins.toLocaleString()}
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <UserX className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-500">
                    {metrics.suspendedUsers} suspended
                  </span>
                </div>
              </div>
              <div className="p-3 bg-red-100 rounded-lg">
                <UserX className="h-6 w-6 text-red-600" />
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white p-6 rounded-xl shadow-sm border border-gray-200"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Avg Session Duration</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {Math.floor(metrics.averageSessionDuration / 60)}m
                </p>
                <div className="flex items-center gap-1 mt-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <span className="text-sm text-gray-500">
                    {metrics.newUsersToday} new today
                  </span>
                </div>
              </div>
              <div className="p-3 bg-purple-100 rounded-lg">
                <Activity className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Authentication Trends Chart */}
      {trends && (
        <AuthTrendsChart
          loginTrends={trends.loginTrends}
          registrationTrends={trends.registrationTrends}
          failureTrends={trends.failureTrends}
        />
      )}

      {/* Security Alerts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="bg-white rounded-xl shadow-sm border border-gray-200"
      >
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Shield className="h-5 w-5 text-gray-700" />
              Security Alerts
            </h3>
            <span className="text-sm text-gray-500">
              {alerts.length} active alerts
            </span>
          </div>
        </div>
        <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No security alerts in the selected time period
            </div>
          ) : (
            alerts.map((alert) => (
              <div key={alert.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${getSeverityColor(alert.severity)}`}>
                    {getSeverityIcon(alert.severity)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-gray-900">{alert.message}</p>
                      <span className="text-xs text-gray-500">
                        {new Date(alert.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {alert.userEmail && (
                      <p className="text-sm text-gray-600 mt-1">
                        User: {alert.userEmail}
                      </p>
                    )}
                    {alert.ipAddress && (
                      <p className="text-sm text-gray-600">
                        IP: {alert.ipAddress}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </div>
  )
}