'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Users,
  Shield,
  Activity,
  FileText,
  Settings,
  LogOut,
  ChevronRight
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { AdminUserManagement } from '@/components/admin/AdminUserManagement'
import { AdminAnalyticsDashboard } from '@/components/admin/AdminAnalyticsDashboard'
import { AuditLogViewer } from '@/components/admin/AuditLogViewer'

type TabType = 'dashboard' | 'users' | 'audit' | 'settings'

export default function AdminPage() {
  const router = useRouter()
  const { user, signOut } = useAuthStore()
  const [activeTab, setActiveTab] = useState<TabType>('dashboard')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is admin
    if (!user) {
      router.push('/login')
    } else if (user.role !== 'admin' && user.role !== 'super_admin') {
      router.push('/')
    } else {
      setLoading(false)
    }
  }, [user, router])

  const handleSignOut = async () => {
    await signOut()
    router.push('/login')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500" />
      </div>
    )
  }

  const tabs = [
    { id: 'dashboard' as const, label: 'Analytics', icon: Activity },
    { id: 'users' as const, label: 'Users', icon: Users },
    { id: 'audit' as const, label: 'Audit Logs', icon: FileText },
    { id: 'settings' as const, label: 'Settings', icon: Settings }
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Admin Panel
          </h1>
        </div>

        <nav className="px-4 pb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                activeTab === tab.id
                  ? 'bg-green-50 text-green-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <tab.icon className="h-5 w-5" />
              {tab.label}
              {activeTab === tab.id && (
                <ChevronRight className="h-4 w-4 ml-auto" />
              )}
            </button>
          ))}
        </nav>

        <div className="mt-auto p-4 border-t border-gray-200">
          <div className="px-4 py-2 text-sm text-gray-600">
            <p className="font-medium">{user?.email}</p>
            <p className="text-xs text-gray-500 uppercase">{user?.role}</p>
          </div>
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors mt-2"
          >
            <LogOut className="h-5 w-5" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-auto">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="p-8"
        >
          {activeTab === 'dashboard' && <AdminAnalyticsDashboard />}
          {activeTab === 'users' && <AdminUserManagement />}
          {activeTab === 'audit' && <AuditLogViewer />}
          {activeTab === 'settings' && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Settings</h2>
              <p className="text-gray-600">Admin settings coming soon...</p>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}