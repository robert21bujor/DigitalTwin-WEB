'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth'
import { ArrowLeft, Bot, CheckCircle, Clock, MessageSquare, Plus, Settings, Users, XCircle } from 'lucide-react'
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
  assigned_user?: string | string[]
  user_has_email_access?: boolean
}

interface EmailPermissionRequest {
  id: string
  requesting_user_id: string
  granting_user_id: string
  requesting_user_name: string
  granting_user_name: string
  agent_name: string
  status: 'pending' | 'approved' | 'denied'
  created_at: string
}

export default function TeamOrganigramPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [requestingAccess, setRequestingAccess] = useState<string[]>([])
  const [pendingRequests, setPendingRequests] = useState<EmailPermissionRequest[]>([])
  const [selectedUsers, setSelectedUsers] = useState<{[agentId: string]: string}>({}) // Track selected user for each agent

  useEffect(() => {
    if (user?.id) {
      fetchAgents()
      fetchPendingRequests()
    }
  }, [user?.id])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:8000/api/agents')
      
      if (!response.ok) {
        throw new Error('Failed to fetch agents')
      }

      const agents: Agent[] = await response.json()
      setAgents(agents)
    } catch (error) {
      console.error('Error fetching agents:', error)
      toast.error('Failed to load team data')
    } finally {
      setLoading(false)
    }
  }

  const fetchPendingRequests = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/email-permissions/requests?user_id=${user?.id}`)
      if (response.ok) {
        const data = await response.json()
        setPendingRequests(data.requests || [])
      }
    } catch (error) {
      console.error('Error fetching pending requests:', error)
    }
  }

  const requestEmailAccess = async (agentId: string, agentName: string, targetUserEmail: string) => {
    if (!user?.id) return

    setRequestingAccess(prev => [...prev, agentId])
    
    try {
      const response = await fetch('http://localhost:8000/api/email-permissions/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          requesting_user_id: user.id,
          agent_id: agentId,
          agent_name: agentName,
          target_user_email: targetUserEmail,
          message: `Request email access for ${agentName} agent context`
        })
      })

      const result = await response.json()
      
      if (result.success) {
        toast.success(`Email access request sent to ${targetUserEmail}!`)
        fetchPendingRequests()
      } else {
        toast.error(`Failed to send request: ${result.error}`)
      }
    } catch (error) {
      console.error('Error requesting email access:', error)
      toast.error('Failed to send email access request')
    } finally {
      setRequestingAccess(prev => prev.filter(id => id !== agentId))
    }
  }

  const handleAgentChat = (agentRole: string) => {
    const formattedRole = agentRole.toLowerCase().replace(/\s+/g, '_')
    router.push(`/chat?agent=agent.${formattedRole}`)
  }

  const handleAgentConfig = (agentId: string) => {
    router.push(`/dashboard/agent-config?agent=${agentId}`)
  }

  // Group agents by department
  const groupAgentsByDepartment = (agents: Agent[]) => {
    const grouped: { [key: string]: Agent[] } = {}
    
    agents.forEach(agent => {
      const dept = agent.department || 'Other'
      if (!grouped[dept]) {
        grouped[dept] = []
      }
      grouped[dept].push(agent)
    })
    
    // Sort departments
    const departmentOrder = ['Executive', 'BusinessDev', 'Operations', 'Marketing', 'Other']
    const sortedDepartments: { [key: string]: Agent[] } = {}
    
    departmentOrder.forEach(dept => {
      if (grouped[dept]) {
        sortedDepartments[dept] = grouped[dept].sort((a, b) => a.name.localeCompare(b.name))
      }
    })
    
    // Add any remaining departments
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

  // Helper function to get assigned users as array
  const getAssignedUsers = (agent: Agent): string[] => {
    if (!agent.assigned_user) return []
    if (Array.isArray(agent.assigned_user)) return agent.assigned_user
    return [agent.assigned_user]
  }

  // Helper function to check if current user is assigned to agent
  const isCurrentUserAssigned = (agent: Agent): boolean => {
    if (!user?.email) return false
    const assignedUsers = getAssignedUsers(agent)
    return assignedUsers.includes(user.email)
  }

  // Helper function to check if user should see request button
  const shouldShowRequestButton = (agent: Agent): boolean => {
    const assignedUsers = getAssignedUsers(agent)
    
    // Don't show if no users assigned to agent
    if (assignedUsers.length === 0) return false
    
    // Don't show if current user is assigned to this agent
    if (isCurrentUserAssigned(agent)) return false
    
    // Don't show if user already has access or pending request
    const emailStatus = getEmailAccessStatus(agent)
    if (emailStatus !== 'none') return false
    
    return true
  }

  const getEmailAccessStatus = (agent: Agent) => {
    const pendingRequest = pendingRequests.find(req => 
      req.agent_name === agent.name && req.requesting_user_id === user?.id
    )
    
    if (pendingRequest) {
      return pendingRequest.status
    }
    
    return agent.user_has_email_access ? 'approved' : 'none'
  }

  const groupedAgents = groupAgentsByDepartment(agents)

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-500">Loading team organigram...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => router.back()}
            className="flex items-center"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Team Organigram
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-1">
              Manage team structure and email permissions
            </p>
          </div>
        </div>
        <Badge variant="outline" className="flex items-center space-x-2">
          <Users className="h-4 w-4" />
          <span>{agents.length} Agents</span>
        </Badge>
      </div>

      {/* Team Structure */}
      <div className="space-y-8">
        {Object.entries(groupedAgents).map(([department, departmentAgents]) => (
          <Card key={department} className="overflow-hidden">
            <CardHeader className={`text-white ${getDepartmentColor(department)}`}>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl">
                    {getDepartmentDisplayName(department)}
                  </CardTitle>
                  <CardDescription className="text-white/80">
                    {departmentAgents.length} agent{departmentAgents.length !== 1 ? 's' : ''}
                  </CardDescription>
                </div>
                <Bot className="h-8 w-8 text-white/80" />
              </div>
            </CardHeader>
            
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {departmentAgents.map((agent) => {
                  const emailStatus = getEmailAccessStatus(agent)
                  const isRequesting = requestingAccess.includes(agent.id)
                  
                  return (
                    <div key={agent.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                      {/* Agent Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h4 className="font-semibold text-lg">{agent.name}</h4>
                          <p className="text-sm text-gray-500">{agent.specialization}</p>
                          {getAssignedUsers(agent).length > 0 && (
                            <div className="mt-1">
                              {getAssignedUsers(agent).map((email, index) => (
                                <Badge key={index} variant="secondary" className="mr-1 mb-1">
                                  Assigned to {email}
                                  {isCurrentUserAssigned(agent) && email === user?.email && (
                                    <span className="ml-1 text-blue-600">(You)</span>
                                  )}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className={`w-3 h-3 rounded-full ${
                          agent.status === 'online' ? 'bg-green-500' : 'bg-gray-400'
                        }`} title={`Status: ${agent.status}`}></div>
                      </div>

                      {/* Email Access Status */}
                      <div className="mb-4">
                        {emailStatus === 'approved' && (
                          <div className="flex items-center text-green-600 text-sm">
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Email access granted
                          </div>
                        )}
                        {emailStatus === 'pending' && (
                          <div className="flex items-center text-yellow-600 text-sm">
                            <Clock className="h-4 w-4 mr-2" />
                            Email access pending
                          </div>
                        )}
                        {emailStatus === 'denied' && (
                          <div className="flex items-center text-red-600 text-sm">
                            <XCircle className="h-4 w-4 mr-2" />
                            Email access denied
                          </div>
                        )}
                        {shouldShowRequestButton(agent) && (
                          <div className="space-y-2">
                            {getAssignedUsers(agent).length === 1 ? (
                              // Single user - direct request button
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => requestEmailAccess(agent.id, agent.name, getAssignedUsers(agent)[0])}
                                disabled={isRequesting}
                                className="w-full"
                              >
                                {isRequesting ? (
                                  <>
                                    <Clock className="h-4 w-4 mr-2 animate-spin" />
                                    Requesting...
                                  </>
                                ) : (
                                  <>
                                    <Plus className="h-4 w-4 mr-2" />
                                    Request Access from {getAssignedUsers(agent)[0]}
                                  </>
                                )}
                              </Button>
                            ) : (
                              // Multiple users - show selection dropdown
                              <div className="space-y-2">
                                <select
                                  value={selectedUsers[agent.id] || ''}
                                  onChange={(e) => setSelectedUsers(prev => ({...prev, [agent.id]: e.target.value}))}
                                  className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value="" disabled>Select user to request from</option>
                                  {getAssignedUsers(agent).map((email) => (
                                    <option key={email} value={email}>
                                      {email}
                                    </option>
                                  ))}
                                </select>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    const targetEmail = selectedUsers[agent.id]
                                    if (targetEmail) {
                                      requestEmailAccess(agent.id, agent.name, targetEmail)
                                    } else {
                                      toast.error('Please select a user first')
                                    }
                                  }}
                                  disabled={isRequesting || !selectedUsers[agent.id]}
                                  className="w-full"
                                >
                                  {isRequesting ? (
                                    <>
                                      <Clock className="h-4 w-4 mr-2 animate-spin" />
                                      Requesting...
                                    </>
                                  ) : (
                                    <>
                                      <Plus className="h-4 w-4 mr-2" />
                                      Request Email Access
                                    </>
                                  )}
                                </Button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="flex space-x-2">
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleAgentChat(agent.role)}
                          className="flex-1"
                        >
                          <MessageSquare className="h-4 w-4 mr-2" />
                          Chat
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleAgentConfig(agent.id)}
                          className="flex-1"
                        >
                          <Settings className="h-4 w-4 mr-2" />
                          Config
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Legend */}
      <Card className="mt-8">
        <CardHeader>
          <CardTitle className="text-lg">Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span>Online Agent</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
              <span>Offline Agent</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span>Email Access Granted</span>
            </div>
            <div className="flex items-center space-x-2">
              <Clock className="h-4 w-4 text-yellow-600" />
              <span>Email Access Pending</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
