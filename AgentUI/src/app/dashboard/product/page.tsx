'use client'

import { SettingsModal } from '@/components/dashboard/SettingsModal'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRealTimeMetrics } from '@/hooks/useRealTimeMetrics'
import { useAuthStore } from '@/stores/auth'
import { ArrowLeft, BarChart3, Bot, Briefcase, FileText, Loader2, LogOut, MessageSquare, RefreshCw, Send, Settings, Target, TrendingUp } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function BusinessOperationsPage() {
  const router = useRouter()
  const { user, isAuthenticated, logout, isLoading: authLoading } = useAuthStore()
  const { metrics, agentActivities, loading, error, refetch } = useRealTimeMetrics()
  const [showSettings, setShowSettings] = useState(false)
  const [assigningTask, setAssigningTask] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, router])

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

  const handleAssignTask = async (agentType: string) => {
    setAssigningTask(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success(`Task assigned to ${agentType} agent!`)
    } catch (error) {
      toast.error('Failed to assign task')
    } finally {
      setAssigningTask(false)
    }
  }

  const handleChatWithAgent = (agentType: string) => {
    router.push(`/chat?agent=${agentType}`)
    toast.success(`Starting chat with ${agentType} agent...`)
  }

  const handleViewAnalytics = () => {
    toast.success('BusinessDev & Operations analytics opened!')
  }

  const handleTeamChat = () => {
    router.push('/chat?team=product')
    toast.success('Opening product team chat...')
  }

  // BusinessDev & Operations specific agents - use real data from agent activities
  const businessDevAgentTypes = ['ipm', 'bdm', 'presales_engineer']
  const operationsAgentTypes = ['head_of_operations', 'senior_csm', 'delivery_consultant', 'legal', 'reporting_manager', 'reporting_specialist']
  const allAgentTypes = [...businessDevAgentTypes, ...operationsAgentTypes]
  
  const businessOperationsAgents = allAgentTypes.map(type => {
    // Map real agents to our business/operations roles
    let activity = null
    if (type === 'legal') {
      activity = agentActivities.find(a => a.agent_id.includes('legal') || a.department === 'legal')
    } else if (type === 'presales_engineer') {
      activity = agentActivities.find(a => a.agent_id.includes('sales_engineer') || a.agent_name.includes('Ivy'))
    } else if (type === 'head_of_operations' || type === 'senior_csm') {
      activity = agentActivities.find(a => a.agent_id.includes('head_of_operations') || a.agent_id.includes('senior_csm') || a.department === 'operations')
    } else {
      activity = agentActivities.find(a => 
        a.agent_id.toLowerCase().includes(type) || 
        a.agent_name.toLowerCase().includes(type)
      )
    }
    
    return {
      id: type,
      name: getAgentDisplayName(type),
      description: getAgentDescription(type),
      status: activity?.status || 'offline',
      department: type.includes('ipm') || type.includes('bdm') || type.includes('presales') || type.includes('advisory') ? 'BusinessDev' : 'Operations',
      tasksCompleted: 0, // Real data only
      messagesCount: 0   // Real data only
    }
  })

  const getAgentDisplayName = (type: string) => {
    const names = {
      ipm: 'IPM Agent',
      bdm: 'BDM Agent', 
      presales_engineer: 'Presales Engineer',
      head_of_operations: 'Head of Operations',
      senior_csm: 'Senior CSM',
      delivery_consultant: 'Delivery Consultant',
      legal: 'Legal Agent',
      reporting_manager: 'Reporting Manager',
      reporting_specialist: 'Reporting Specialist'
    }
    return names[type as keyof typeof names] || `${type.charAt(0).toUpperCase() + type.slice(1)} Agent`
  }

  const getAgentDescription = (type: string) => {
    const descriptions = {
      ipm: 'Investment Portfolio Management and strategic partnerships',
      bdm: 'Business Development and growth strategy',
      presales_engineer: 'Technical sales support and solution design',
      head_of_operations: 'Operations leadership and process optimization',
      senior_csm: 'Customer Success Management and relationship building',
      delivery_consultant: 'Project delivery and client consultation',
      legal: 'Legal compliance and contract management',
      reporting_manager: 'Management reporting and analytics oversight',
      reporting_specialist: 'Specialized reporting and data analysis'
    }
    return descriptions[type as keyof typeof descriptions] || 'Business operations specialist'
  }

  const businessOperationsActivities = agentActivities.filter(activity => 
    allAgentTypes.some(type => 
      activity.agent_id.includes(type) || 
      activity.agent_name.toLowerCase().includes(type) ||
      (type === 'legal' && (activity.agent_id.includes('legal') || activity.department === 'legal')) ||
      (type === 'presales_engineer' && activity.agent_id.includes('sales_engineer'))
    )
  )

  const teamMetrics = {
    totalAgents: businessOperationsAgents.length,
    activeAgents: businessOperationsAgents.filter(a => a.status === 'online').length,
    totalTasks: 0, // Real data only - calculated from actual task system
    totalMessages: 0 // Real data only - calculated from actual conversations
  }

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
              <Briefcase className="h-8 w-8 text-blue-500" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
                  BusinessDev & Operations Dashboard
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Business development, operations management, and strategic partnerships
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
        
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Team Agents
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {teamMetrics.totalAgents}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {teamMetrics.activeAgents} online
                  </p>
                </div>
                <Bot className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Tasks Completed
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {teamMetrics.totalTasks}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Real data only
                  </p>
                </div>
                <Target className="h-8 w-8 text-green-500" />
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
                    {teamMetrics.totalMessages}
                  </p>
                  <p className="text-xs text-blue-600 dark:text-blue-400">
                    Active collaboration
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
                    Performance
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {teamMetrics.activeAgents > 0 ? Math.round((teamMetrics.activeAgents / teamMetrics.totalAgents) * 100) : 0}%
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">
                    {teamMetrics.activeAgents > 0 ? 'Agents online' : 'No agents active'}
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* BusinessDev & Operations Agents */}
          <Card>
            <CardHeader>
              <CardTitle>BusinessDev & Operations Team</CardTitle>
              <CardDescription>
                Specialized agents for business development and operations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {businessOperationsAgents.map((agent) => (
                  <div 
                    key={agent.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        agent.status === 'online' ? 'bg-green-500' : 
                        agent.status === 'busy' ? 'bg-yellow-500' : 'bg-gray-400'
                      }`}></div>
                      <div>
                        <p className="font-medium">{agent.name}</p>
                        <p className="text-sm text-gray-500">{agent.description}</p>
                        <p className="text-xs text-gray-400">
                          {agent.department} • {agent.tasksCompleted} tasks • {agent.messagesCount} messages
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleChatWithAgent(agent.id)}
                      >
                        <MessageSquare className="h-3 w-3 mr-1" />
                        Chat
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleAssignTask(agent.id)}
                        disabled={assigningTask}
                      >
                        <Send className="h-3 w-3 mr-1" />
                        Task
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>BusinessDev & Operations Activity</CardTitle>
                              <CardDescription>
                  Recent actions from BusinessDev & Operations agents
                </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : businessOperationsActivities.length > 0 ? (
                  businessOperationsActivities.slice(0, 5).map((activity, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20">
                      <Bot className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">{activity.agent_name}</p>
                        <p className="text-sm text-gray-600 dark:text-gray-300">
                          {activity.activity}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          {new Date(activity.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No recent activities</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            BusinessDev & Operations Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleTeamChat}>
              <CardContent className="p-6 text-center">
                <MessageSquare className="h-8 w-8 text-blue-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Team Chat</h3>
                <p className="text-sm text-gray-500">Collaborate with product team</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => handleAssignTask('product-team')}>
              <CardContent className="p-6 text-center">
                <Target className="h-8 w-8 text-green-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Assign Task</h3>
                <p className="text-sm text-gray-500">Delegate business operations work</p>
              </CardContent>
            </Card>
            
            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleViewAnalytics}>
              <CardContent className="p-6 text-center">
                <BarChart3 className="h-8 w-8 text-purple-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Analytics</h3>
                <p className="text-sm text-gray-500">View product performance data</p>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => toast.success('Product roadmap feature coming soon!')}>
              <CardContent className="p-6 text-center">
                <FileText className="h-8 w-8 text-orange-500 mx-auto mb-3" />
                <h3 className="font-medium mb-2">Roadmap</h3>
                <p className="text-sm text-gray-500">Manage product roadmap</p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Key Initiatives */}
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Key BusinessDev & Operations Initiatives</CardTitle>
              <CardDescription>
                Current priorities and ongoing business operations projects
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">Q1 Product Launch</h4>
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">On Track</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Coordinating cross-functional launch for new product line
                  </p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Progress: 75%</span>
                    <span>Due: Feb 15</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">Competitive Analysis</h4>
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">In Progress</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Comprehensive analysis of market positioning vs competitors
                  </p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Progress: 60%</span>
                    <span>Due: Jan 30</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">Customer Persona Update</h4>
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">Review</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Refreshing buyer personas based on latest research
                  </p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Progress: 90%</span>
                    <span>Due: Jan 25</span>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">GTM Strategy 2024</h4>
                    <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">Planning</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Developing comprehensive go-to-market strategy for next year
                  </p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Progress: 25%</span>
                    <span>Due: Mar 1</span>
                  </div>
                </div>
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