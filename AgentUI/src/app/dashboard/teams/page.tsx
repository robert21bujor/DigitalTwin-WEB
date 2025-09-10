'use client'

import { SettingsModal } from '@/components/dashboard/SettingsModal'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRealTimeMetrics } from '@/hooks/useRealTimeMetrics'
import { useAuthStore } from '@/stores/auth'
import { ArrowLeft, Bot, Crown, Edit, Loader2, LogOut, MessageSquare, MoreVertical, RefreshCw, Settings, Shield, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function TeamsPage() {
  const router = useRouter()
  const { user, isAuthenticated, logout, isLoading: authLoading } = useAuthStore()
  const { metrics, agentActivities, loading, error, refetch } = useRealTimeMetrics()
  const [showSettings, setShowSettings] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/')
    } else if (user && user.role !== 'cmo') {
      // Only CMO can access team management
      router.push('/chat')
    }
  }, [isAuthenticated, user, router])

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true)
      toast.loading('Signing out...', { id: 'logout' })
      await logout()
      await new Promise(resolve => setTimeout(resolve, 100))
      toast.success('Successfully signed out!', { id: 'logout' })
      router.replace('/')
    } catch (error) {
      console.error('Logout error:', error)
      toast.error('Failed to sign out. Please try again.', { id: 'logout' })
    } finally {
      setIsLoggingOut(false)
    }
  }

  const handleBackToDashboard = () => {
    // All users go to manager dashboard
    router.push('/dashboard/manager')
  }

  const handleManageDepartment = (department: string) => {
    router.push(`/dashboard/${department}`)
    toast.success(`Opening ${department} department management...`)
  }

  const handleEditTeam = (team: string) => {
    toast.success(`Team ${team} configuration opened!`)
  }

  const handleMessageTeam = (team: string) => {
    router.push(`/chat?team=${team}`)
    toast.success(`Starting team chat with ${team}...`)
  }

  const departments = [
    {
      id: 'business_dev',
      name: 'Business Development',
      description: 'Investment portfolio management, business development, and presales engineering',
      agents: agentActivities.filter(a => 
        ['ipm', 'bdm', 'presales_engineer', 'sales_engineer'].some(type => 
          a.agent_id.includes(type) || a.agent_name.toLowerCase().includes(type)
        ) || a.department === 'sales'
      ),
      color: 'bg-blue-500',
      manager: 'Business Development Manager'
    },
    {
      id: 'operations',
      name: 'Operations',
      description: 'Operations management, customer success, delivery, legal, and reporting',
      agents: agentActivities.filter(a => 
        ['head_of_operations', 'senior_csm', 'delivery_consultant', 'legal', 'reporting_manager', 'reporting_specialist'].some(type => 
          a.agent_id.includes(type) || a.agent_name.toLowerCase().includes(type)
        ) || a.department === 'legal' || a.department === 'operations'
      ),
      color: 'bg-green-500',
      manager: 'Operations Manager'
    }
  ]

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-lg">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Button variant="ghost" size="sm" onClick={handleBackToDashboard}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Users className="h-8 w-8 text-blue-500" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Team Management
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Manage departments and team performance
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" onClick={refetch} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowSettings(true)}>
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
              <Button variant="ghost" size="sm" onClick={handleLogout} disabled={isLoggingOut}>
                {isLoggingOut ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <LogOut className="h-4 w-4 mr-2" />
                )}
                {isLoggingOut ? 'Signing out...' : 'Logout'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Total Departments
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {departments.length}
                  </p>
                </div>
                <Users className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Active Agents
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.activeAgents}
                  </p>
                </div>
                <Bot className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Team Messages
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.totalMessages}
                  </p>
                </div>
                <MessageSquare className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    System Health
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {metrics.systemHealth}%
                  </p>
                </div>
                <Shield className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Department Teams */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Department Teams
            </h2>
            <Button onClick={() => toast.success('Create new team feature coming soon!')}>
              Create New Team
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {departments.map((dept) => (
              <Card key={dept.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`w-4 h-4 rounded-full ${dept.color}`}></div>
                      <div>
                        <CardTitle className="text-lg">{dept.name}</CardTitle>
                        <CardDescription>{dept.description}</CardDescription>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Team Stats */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                          {dept.agents.length}
                        </p>
                        <p className="text-sm text-gray-500">Active Agents</p>
                      </div>
                      <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                          {dept.agents.filter(a => a.status === 'online').length}
                        </p>
                        <p className="text-sm text-gray-500">Online Now</p>
                      </div>
                    </div>

                    {/* Manager Info */}
                    <div className="flex items-center space-x-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <Crown className="h-5 w-5 text-blue-500" />
                      <div>
                        <p className="font-medium text-blue-900 dark:text-blue-100">
                          {dept.manager}
                        </p>
                        <p className="text-sm text-blue-600 dark:text-blue-300">
                          Department Manager
                        </p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex space-x-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleManageDepartment(dept.id)}
                      >
                        <Edit className="h-3 w-3 mr-1" />
                        Manage
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex-1"
                        onClick={() => handleMessageTeam(dept.id)}
                      >
                        <MessageSquare className="h-3 w-3 mr-1" />
                        Message
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Recent Team Activity */}
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Recent Team Activity</CardTitle>
              <CardDescription>
                Latest actions across all departments
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : agentActivities.slice(0, 5).map((activity, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Bot className="h-5 w-5 text-blue-500" />
                      <div>
                        <p className="font-medium">{activity.agent_name}</p>
                        <p className="text-sm text-gray-500">
                          {activity.department} • {activity.activity}
                        </p>
                        <p className="text-xs text-gray-400">
                          {new Date(activity.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className={`w-2 h-2 rounded-full ${
                        activity.status === 'online' ? 'bg-green-500' : 
                        activity.status === 'busy' ? 'bg-yellow-500' : 'bg-gray-400'
                      }`}></div>
                      <span className="text-sm text-gray-500 capitalize">
                        {activity.status}
                      </span>
                    </div>
                  </div>
                ))}
                
                {agentActivities.length === 0 && !loading && (
                  <p className="text-gray-500 text-center py-8">
                    No recent team activity
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Settings Modal */}
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
    </div>
  )
} 