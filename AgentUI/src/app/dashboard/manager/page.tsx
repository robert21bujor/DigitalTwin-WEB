'use client'

import AdminButton from '@/components/admin/AdminButton'
import { SettingsModal } from '@/components/dashboard/SettingsModal'
import { NotificationsBell } from '@/components/notifications/NotificationsBell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRealTimeMetrics } from '@/hooks/useRealTimeMetrics'
import { useAuthStore } from '@/stores/auth'
import { AlertCircle, BarChart3, Bot, Briefcase, Loader2, LogOut, Mail, MessageSquare, RefreshCw, Send, Settings, Target, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'


// Agent interface for API data
interface Agent {
  id: string
  name: string
  role: string
  department: string
  status: string
  capabilities: string[]
  specialization: string
}

export default function ManagerDashboard() {
  const router = useRouter()
  const { user, isAuthenticated, logout, isLoading: authLoading } = useAuthStore()
  const { metrics, agentActivities, loading, error, refetch } = useRealTimeMetrics()
  const [showSettings, setShowSettings] = useState(false)
  const [assigningTask, setAssigningTask] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [allAgents, setAllAgents] = useState<Agent[]>([])
  const [loadingAgents, setLoadingAgents] = useState(true)
  const [pendingEmailsCount, setPendingEmailsCount] = useState(0)
  const [loadingPendingEmails, setLoadingPendingEmails] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/')
    }
    // Allow all authenticated users to access this dashboard
  }, [isAuthenticated, router])

  // Fetch all agents from API
  const fetchAllAgents = async () => {
    try {
      setLoadingAgents(true)
      const response = await fetch('http://localhost:8000/api/agents')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const agents: Agent[] = await response.json()
      setAllAgents(agents)
      console.log('Fetched all agents:', agents)
    } catch (error) {
      console.error('Error fetching agents:', error)
      toast.error('Failed to load agents')
    } finally {
      setLoadingAgents(false)
    }
  }

  // Fetch pending emails count from review queue
  const fetchPendingEmailsCount = async () => {
    try {
      setLoadingPendingEmails(true)
      const response = await fetch('/api/gmail/review-queue')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      
      const reviewQueue = await response.json()
      setPendingEmailsCount(reviewQueue.length)
    } catch (error) {
      console.error('Error fetching pending emails count:', error)
      setPendingEmailsCount(0) // Default to 0 on error
    } finally {
      setLoadingPendingEmails(false)
    }
  }

  // Refresh all data
  const refreshDashboardData = () => {
    fetchAllAgents()
    fetchPendingEmailsCount()
  }

  // Fetch agents and pending emails on component mount
  useEffect(() => {
    if (isAuthenticated) {
      refreshDashboardData()
    }
  }, [isAuthenticated])

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

  const handleRefresh = () => {
    refetch()
    fetchAllAgents()
    toast.success('Team metrics refreshed!')
  }

  // Check if agent is assigned to current user
  const isAgentAssignedToUser = (agent: Agent) => {
    return user?.agent_assignments?.some(assignment => 
      assignment.agent_type.toLowerCase() === agent.role.toLowerCase() ||
      assignment.agent_type.toLowerCase().includes(agent.name.toLowerCase().replace(/\s+/g, '_'))
    ) || false
  }

  // Group agents by department with user assignments prioritized
  const groupAgentsByDepartment = (agents: Agent[]) => {
    const grouped: { [key: string]: Agent[] } = {}
    
    agents.forEach(agent => {
      const dept = agent.department || 'Other'
      if (!grouped[dept]) {
        grouped[dept] = []
      }
      grouped[dept].push(agent)
    })
    
    // Sort departments and agents within each department (assigned agents first)
    const sortedDepartments: { [key: string]: Agent[] } = {}
    const departmentOrder = ['Executive', 'BusinessDev', 'Operations', 'Marketing', 'Other']
    
    departmentOrder.forEach(dept => {
      if (grouped[dept]) {
        const assignedAgents = grouped[dept].filter(agent => isAgentAssignedToUser(agent))
        const unassignedAgents = grouped[dept].filter(agent => !isAgentAssignedToUser(agent))
        
        // Sort both groups alphabetically, then combine with assigned first
        assignedAgents.sort((a, b) => a.name.localeCompare(b.name))
        unassignedAgents.sort((a, b) => a.name.localeCompare(b.name))
        
        sortedDepartments[dept] = [...assignedAgents, ...unassignedAgents]
      }
    })
    
    // Add any remaining departments not in the order
    Object.keys(grouped).forEach(dept => {
      if (!departmentOrder.includes(dept)) {
        sortedDepartments[dept] = grouped[dept].sort((a, b) => a.name.localeCompare(b.name))
      }
    })
    
    return sortedDepartments
  }

  const getDepartmentColor = (department: string) => {
    switch (department) {
      case 'Executive': return 'bg-red-500'
      case 'BusinessDev': return 'bg-blue-500'
      case 'Operations': return 'bg-green-500'
      case 'Marketing': return 'bg-orange-500'
      default: return 'bg-gray-500'
    }
  }

  const getDepartmentDisplayName = (department: string) => {
    switch (department) {
      case 'BusinessDev': return 'Business Development'
      default: return department
    }
  }

  const handleTeamChat = () => {
    router.push('/chat?mode=team')
    toast.success('Opening team chat...')
  }

  const handleAssignTask = async (agentType: string) => {
    setAssigningTask(true)
    try {
      // Simulate task assignment
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success(`Task assigned to ${agentType} agent!`)
    } catch (error) {
      toast.error('Failed to assign task')
    } finally {
      setAssigningTask(false)
    }
  }

  const handleViewTeamMetrics = () => {
    router.push(`/dashboard/analytics?team=${user?.role}`)
    toast.success('Loading team analytics...')
  }

  const handleTeamConfig = () => {
    router.push(`/dashboard/config?team=${user?.role}`)
    toast.success('Opening team configuration...')
  }

  const handleChatWithAgent = (agentType: string) => {
    router.push(`/chat?agent=${agentType}`)
    toast.success(`Starting chat with ${agentType} agent...`)
  }

  const handleConfigAgent = (agentType: string) => {
    router.push(`/dashboard/agent-config?agent=${agentType}`)
    toast.success(`Opening ${agentType} agent configuration...`)
  }



  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num)
  }

  const calculateTeamMetrics = () => {
    if (!allAgents.length) return { teamAgents: 0, activeTeamAgents: 0, teamMessages: 0, teamTasks: 0 }
    
    const onlineAgents = allAgents.filter(agent => agent.status === 'online')
    
    return {
      teamAgents: allAgents.length,
      activeTeamAgents: onlineAgents.length,
      teamMessages: 0, // Real data only
      teamTasks: 0 // Real data only
    }
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

  const teamMetrics = calculateTeamMetrics()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Navigation Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4">
          {/* Left side - Title */}
          <div className="flex items-center space-x-3">
            <Briefcase className="h-8 w-8 text-blue-500" />
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                Agent Communication Dashboard
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Welcome, {user.username} - {user.role?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </p>
            </div>
          </div>
          
          {/* Right side - Action buttons */}
          <div className="flex items-center space-x-3">
            {/* User info */}
            <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
              <Users className="h-4 w-4" />
              <span>{user.username}</span>
              {user.admin_rights && user.admin_rights !== 'none' && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full text-xs font-medium">
                  {user.admin_rights}
                </span>
              )}
            </div>

            <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button variant="ghost" size="sm" onClick={() => router.push('/dashboard/emails')}>
              <Mail className="h-4 w-4 mr-2" />
              Emails
            </Button>
            <AdminButton />
            {user?.id && <NotificationsBell userId={user.id} />}
            <Button variant="ghost" size="sm" onClick={() => setShowSettings(true)}>
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </Button>
            <Button variant="ghost" size="sm" onClick={handleLogout} disabled={isLoggingOut} 
                    className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950">
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <p className="text-red-800 font-medium">Error loading team metrics</p>
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
                    Total Agents
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loadingAgents ? '...' : formatNumber(teamMetrics.teamAgents)}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {teamMetrics.activeTeamAgents} online
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
                    Tasks Completed
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : formatNumber(teamMetrics.teamTasks)}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Real task data
                  </p>
                </div>
                <Target className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Team Messages
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {loading ? '...' : formatNumber(teamMetrics.teamMessages)}
                  </p>
                  <p className="text-xs text-purple-600 dark:text-purple-400">
                    Active collaboration
                  </p>
                </div>
                <MessageSquare className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card className={loading ? 'opacity-50' : ''}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Performance
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {teamMetrics.activeTeamAgents > 0 ? Math.round((teamMetrics.activeTeamAgents / teamMetrics.teamAgents) * 100) : 0}%
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {teamMetrics.activeTeamAgents > 0 ? 'Agents online' : 'No agents active'}
                  </p>
                </div>
                <BarChart3 className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* All Agents by Department */}
          <Card>
            <CardHeader>
              <CardTitle>Your Agents & All Available Agents</CardTitle>
              <CardDescription>
                Your assigned agents appear first, followed by all other agents ({allAgents.length} total)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {loadingAgents ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : Object.entries(groupAgentsByDepartment(allAgents)).map(([department, agents]) => (
                  <div key={department} className="space-y-2">
                    {/* Department Header */}
                    <div className="flex items-center space-x-2 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                      <div className={`w-3 h-3 rounded-full ${getDepartmentColor(department)}`} />
                      <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                        {getDepartmentDisplayName(department)}
                        <span className="text-xs text-gray-500 ml-2">({agents.length} agents)</span>
                      </h4>
                    </div>
                    
                    {/* Agents in this department */}
                    <div className="space-y-2 ml-4">
                      {agents.map((agent) => {
                        const activity = agentActivities.find(a => 
                          a.agent_id === agent.id || 
                          a.agent_name.toLowerCase() === agent.name.toLowerCase()
                        )
                        const isAssigned = isAgentAssignedToUser(agent)
                  return (
                    <div 
                            key={agent.id}
                            className={`flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 border-l-4 ${
                              isAssigned 
                                ? 'border-l-blue-500 bg-blue-50 dark:bg-blue-950/20' 
                                : 'border-l-gray-200 hover:border-l-blue-400'
                            }`}
                    >
                      <div className="flex items-center space-x-3">
                              <div className={`w-2 h-2 rounded-full ${
                                agent.status === 'online' ? 'bg-green-500' : 
                                agent.status === 'busy' ? 'bg-yellow-500' : 'bg-gray-400'
                              }`}></div>
                        <div>
                                <div className="flex items-center space-x-2">
                                  <p className="font-medium text-sm">{agent.name}</p>
                                  {isAssigned && (
                                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
                                      Assigned
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-gray-500">
                                  {agent.specialization || agent.role} • {agent.status}
                          </p>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm" 
                                onClick={() => handleChatWithAgent(agent.role)}
                        >
                          <MessageSquare className="h-3 w-3 mr-1" />
                          Chat
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                                onClick={() => handleConfigAgent(agent.role)}
                        >
                          <Settings className="h-3 w-3 mr-1" />
                          Config
                        </Button>
                      </div>
                    </div>
                  )
                })}
                    </div>
                  </div>
                ))}
                
                {allAgents.length === 0 && !loadingAgents && (
                  <div className="text-center py-8 text-gray-500">
                    <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No agents available</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Agent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Activity</CardTitle>
              <CardDescription>
                Recent actions from all agents across departments
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
                      <p className="text-sm font-medium">
                        {activity.agent_name}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {activity.activity}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Status: {activity.status} • {new Date(activity.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={() => handleAssignTask(activity.agent_id)}
                      disabled={assigningTask}
                    >
                      <Send className="h-3 w-3 mr-1" />
                      {assigningTask ? 'Assigning...' : 'Assign Task'}
                    </Button>
                  </div>
                ))}
                
                {agentActivities.length === 0 && !loading && (
                  <p className="text-gray-500 text-center py-4">
                    No recent agent activity
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Manager Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleTeamChat}>
              <CardContent className="p-6 text-center">
                <MessageSquare className="h-8 w-8 text-blue-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Team Chat</h3>
                <p className="text-sm text-gray-500">Communicate with your agents</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => handleAssignTask('team')}>
              <CardContent className="p-6 text-center">
                <Target className="h-8 w-8 text-green-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Assign Tasks</h3>
                <p className="text-sm text-gray-500">Delegate work to team agents</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleViewTeamMetrics}>
              <CardContent className="p-6 text-center">
                <BarChart3 className="h-8 w-8 text-purple-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Team Metrics</h3>
                <p className="text-sm text-gray-500">View team performance data</p>
              </CardContent>
            </Card>
            
            <Card className={`cursor-pointer hover:shadow-md transition-shadow ${
              pendingEmailsCount > 1 
                ? 'border-orange-200 bg-orange-50' 
                : ''
            }`} onClick={() => router.push('/dashboard/emails')}>
              <CardContent className="p-6 text-center">
                <Mail className={`h-8 w-8 mx-auto mb-3 ${
                  pendingEmailsCount > 1 ? 'text-orange-500' : 'text-gray-400'
                }`} />
                <h3 className="font-medium mb-2">Email Queue</h3>
                <p className="text-sm text-gray-500">Review pending emails</p>
                <div className="mt-2">
                  {loadingPendingEmails ? (
                    <span className="inline-block bg-gray-100 text-gray-500 text-xs px-2 py-1 rounded-full">
                      Loading...
                    </span>
                  ) : (
                    <span className={`inline-block text-xs px-2 py-1 rounded-full ${
                      pendingEmailsCount > 1 
                        ? 'bg-orange-100 text-orange-800' 
                        : pendingEmailsCount === 1
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-500'
                    }`}>
                      {pendingEmailsCount} pending
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => router.push('/dashboard/team-organigram')}>
              <CardContent className="p-6 text-center">
                <Users className="h-8 w-8 text-blue-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">View Team</h3>
                <p className="text-sm text-gray-500">Team organigram and email permissions</p>
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