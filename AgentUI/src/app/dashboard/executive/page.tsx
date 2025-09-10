'use client'

import { SettingsModal } from '@/components/dashboard/SettingsModal'
import { NotificationsBell } from '@/components/notifications/NotificationsBell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import { useRealTimeMetrics } from '@/hooks/useRealTimeMetrics'
import { useAuthStore } from '@/stores/auth'
import { AlertCircle, BarChart3, Bot, Crown, Loader2, LogOut, MessageSquare, RefreshCw, Settings, TrendingUp, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function ExecutiveDashboard() {
  const router = useRouter()
  const { user, isAuthenticated, logout, isLoading: authLoading } = useAuthStore()
  const { metrics, agentActivities, loading, error, refetch } = useRealTimeMetrics()
  const [showSettings, setShowSettings] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/')
    }
    // Allow all authenticated users to access this dashboard
  }, [isAuthenticated, router])

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true)
      toast.loading('Signing out...', { id: 'logout' })
      
      // Execute logout and wait for completion
      await logout()
      
      // Small delay to ensure state is cleared
      await new Promise(resolve => setTimeout(resolve, 100))
      
      toast.success('Successfully signed out!', { id: 'logout' })
      
      // Navigate after successful logout
      router.replace('/')
    } catch (error) {
      console.error('Logout error:', error)
      toast.error('Failed to sign out. Please try again.', { id: 'logout' })
    } finally {
      setIsLoggingOut(false)
    }
  }

  const handleRefresh = () => {
    refetch()
    toast.success('Metrics refreshed!')
  }

  const handleViewAnalytics = () => {
    setShowAnalytics(true)
    toast.success('Analytics view activated!')
  }

  const handleManageTeams = () => {
    router.push('/dashboard/teams')
    toast.success('Navigating to team management...')
  }

  const handleStrategicChat = () => {
    router.push('/chat?mode=strategic')
    toast.success('Opening strategic chat...')
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num)
  }

  const formatResponseTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    return `${Math.round(seconds / 60)}m`
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-lg">Redirecting to login...</p>
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
              <Crown className="h-8 w-8 text-yellow-500" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Executive Dashboard
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Welcome, {user.username} - Chief Executive Officer
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              {user?.id && <NotificationsBell userId={user.id} />}
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
        
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <p className="text-red-800 font-medium">Error loading metrics</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              Retry
            </Button>
          </div>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Active Agents
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : formatNumber(metrics.activeAgents)}
                  </p>
                  <p className="text-xs text-blue-600 dark:text-blue-400">
                    {metrics.activeAgents} of {metrics.activeAgents + Math.max(0, 7 - metrics.activeAgents)} total
                  </p>
                </div>
                <Bot className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Messages Today
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : formatNumber(metrics.messagesThisHour * 24)}
                  </p>
                  <p className="text-xs text-blue-600 dark:text-blue-400">
                    {formatNumber(metrics.messagesThisHour)} this hour
                  </p>
                </div>
                <MessageSquare className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Response Time
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : formatResponseTime(metrics.avgResponseTime)}
                  </p>
                  <p className="text-xs text-purple-600 dark:text-purple-400">
                    {metrics.avgResponseTime < 60 ? 'Fast response' : 
                     metrics.avgResponseTime < 300 ? 'Good response' : 'Needs attention'}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    System Health
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : metrics.systemHealth}%
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {loading ? '...' : 
                     metrics.systemHealth >= 90 ? 'All systems operational' :
                     metrics.systemHealth >= 70 ? 'Systems mostly healthy' :
                     metrics.systemHealth >= 50 ? 'Some systems degraded' :
                     'Critical systems attention needed'
                    }
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Department Overview */}
          <Card>
            <CardHeader>
              <CardTitle>Department Overview</CardTitle>
              <CardDescription>
                BusinessDev & Operations department status and performance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    <div>
                      <p className="font-medium">Business Development</p>
                      <p className="text-sm text-gray-500">
                        {agentActivities.filter(a => 
                          ['ipm', 'bdm', 'presales_engineer', 'sales_engineer'].some(type => 
                            a.agent_id.includes(type) || a.agent_name.toLowerCase().includes(type)
                          ) || a.department === 'sales'
                        ).length} agents active
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/product')}>
                    View Details
                  </Button>
                </div>

                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <div>
                      <p className="font-medium">Operations</p>
                      <p className="text-sm text-gray-500">
                        {agentActivities.filter(a => 
                          ['head_of_operations', 'senior_csm', 'delivery_consultant', 'legal', 'reporting_manager', 'reporting_specialist'].some(type => 
                            a.agent_id.includes(type) || a.agent_name.toLowerCase().includes(type)
                          ) || a.department === 'legal' || a.department === 'operations'
                        ).length} agents active
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => router.push('/dashboard/operations')}>
                    View Details
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
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
                  <div key={index} className="flex items-start space-x-3 p-3 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20">
                    <Bot className="h-5 w-5 text-blue-500 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium">{activity.agent_name}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {activity.activity}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {activity.department} • {new Date(activity.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <div className={`w-2 h-2 rounded-full mt-2 ${
                      activity.status === 'online' ? 'bg-green-500' : 
                      activity.status === 'busy' ? 'bg-yellow-500' : 'bg-gray-400'
                    }`}></div>
                  </div>
                ))}
                
                {agentActivities.length === 0 && !loading && (
                  <p className="text-gray-500 text-center py-4">
                    No recent activity
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Executive Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Executive Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleViewAnalytics}>
              <CardContent className="p-6 text-center">
                <BarChart3 className="h-8 w-8 text-blue-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">View Analytics</h3>
                <p className="text-sm text-gray-500">Comprehensive performance metrics</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleManageTeams}>
              <CardContent className="p-6 text-center">
                <Users className="h-8 w-8 text-green-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Manage Teams</h3>
                <p className="text-sm text-gray-500">Oversee departments and agents</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleStrategicChat}>
              <CardContent className="p-6 text-center">
                <MessageSquare className="h-8 w-8 text-purple-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Strategic Chat</h3>
                <p className="text-sm text-gray-500">Communicate with all agents</p>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => setShowSettings(true)}>
              <CardContent className="p-6 text-center">
                <Settings className="h-8 w-8 text-orange-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">System Config</h3>
                <p className="text-sm text-gray-500">Configure system settings</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
    </div>
  )
} 