import { useAuthStore } from '@/stores/auth'
import { useEffect, useState } from 'react'

export interface Metrics {
  activeAgents: number
  totalMessages: number
  messagesThisHour: number
  avgResponseTime: number
  departments: number
  activeUsers: number
  systemHealth: number
  tasksCompleted: number
  pendingTasks: number
}

export interface AgentActivity {
  id: string
  agent_id: string
  agent_name: string
  department: string
  activity: string
  timestamp: string
  status: 'online' | 'busy' | 'offline'
}

export function useRealTimeMetrics() {
  const { user } = useAuthStore()
  const [metrics, setMetrics] = useState<Metrics>({
    activeAgents: 0,
    totalMessages: 0,
    messagesThisHour: 0,
    avgResponseTime: 0,
    departments: 0,
    activeUsers: 0,
    systemHealth: 95,
    tasksCompleted: 0,
    pendingTasks: 0
  })
  const [agentActivities, setAgentActivities] = useState<AgentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch initial metrics from local FastAPI backend
  const fetchMetrics = async () => {
    try {
      setLoading(true)
      
      // Fetch agents from local backend
      const agentsResponse = await fetch('http://localhost:8000/api/agents')
      if (!agentsResponse.ok) {
        throw new Error(`Backend API error: ${agentsResponse.status} ${agentsResponse.statusText}`)
      }
      
      const agentsData = await agentsResponse.json()
      const agents = agentsData.agents || []
      
      // Calculate metrics from agent data
      const activeAgents = agents.filter((agent: any) => agent.status === 'online').length
      const departments = new Set(agents.map((agent: any) => agent.department)).size
      
      // Create agent activities from agent data
      const activities: AgentActivity[] = agents.map((agent: any) => ({
        id: agent.agent_id,
        agent_id: agent.agent_id,
        agent_name: agent.user_name,
        department: agent.department,
        activity: agent.status === 'online' ? 'Active' : 'Idle',
        timestamp: agent.last_seen || new Date().toISOString(),
        status: agent.status as 'online' | 'busy' | 'offline'
      }))

      // Fetch real metrics from the new metrics endpoint
      let realMetrics = {
        activeAgents,
        totalMessages: 0,
        messagesThisHour: 0,
        avgResponseTime: 0,
        departments,
        activeUsers: 1,
        systemHealth: 95,
        tasksCompleted: 0,
        pendingTasks: 0
      }

      try {
        const metricsResponse = await fetch('http://localhost:8000/api/metrics')
        if (metricsResponse.ok) {
          const metricsData = await metricsResponse.json()
          realMetrics = {
            activeAgents: metricsData.activeAgents || activeAgents,
            totalMessages: metricsData.totalMessages || 0,
            messagesThisHour: metricsData.messagesThisHour || 0,
            avgResponseTime: metricsData.avgResponseTime || 0,
            departments: metricsData.departments || departments,
            activeUsers: metricsData.activeUsers || 1,
            systemHealth: metricsData.systemHealth || 95,
            tasksCompleted: metricsData.tasksCompleted || 0,
            pendingTasks: metricsData.pendingTasks || 0
          }
          console.log('✅ Real metrics loaded:', realMetrics)
        } else {
          console.warn('Failed to fetch real metrics, using agent-based data')
        }
      } catch (metricsError) {
        console.warn('Metrics endpoint error:', metricsError)
      }

      setMetrics(realMetrics)
      
      setAgentActivities(activities)
      setError(null)
      
    } catch (err) {
      console.error('Error fetching metrics:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics')
      
      // Set metrics based on available data
      setMetrics({
        activeAgents: 0,
        totalMessages: 0,
        messagesThisHour: 0,
        avgResponseTime: 0,
        departments: 2,
        activeUsers: 1,
        systemHealth: 0,
        tasksCompleted: 0,
        pendingTasks: 0
      })
      
      setAgentActivities([
        {
          id: 'agent.ipm_agent',
          agent_id: 'agent.ipm_agent',
          agent_name: 'IPM Agent',
          department: 'BusinessDev',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        },
        {
          id: 'agent.bdm_agent',
          agent_id: 'agent.bdm_agent',
          agent_name: 'BDM Agent',
          department: 'BusinessDev',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        },
        {
          id: 'agent.presales_engineer',
          agent_id: 'agent.presales_engineer',
          agent_name: 'Presales Engineer',
          department: 'BusinessDev',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        },
        {
          id: 'agent.head_of_operations',
          agent_id: 'agent.head_of_operations',
          agent_name: 'Head of Operations',
          department: 'Operations',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        },
        {
          id: 'agent.legal_agent',
          agent_id: 'agent.legal_agent',
          agent_name: 'Legal Agent',
          department: 'Operations',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        },
        {
          id: 'agent.senior_csm',
          agent_id: 'agent.senior_csm',
          agent_name: 'Senior CSM',
          department: 'Operations',
          activity: 'Active',
          timestamp: new Date().toISOString(),
          status: 'online'
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
    
    // Set up periodic refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000)
    
    return () => clearInterval(interval)
  }, [])

  return {
    metrics,
    agentActivities,
    loading,
    error,
    refetch: fetchMetrics
  }
}

export function useAgentMetrics(agentType?: string) {
  const { agentActivities, loading, error } = useRealTimeMetrics()
  
  const filteredActivities = agentType 
    ? agentActivities.filter(activity => 
        activity.agent_id.includes(agentType) || 
        activity.department.toLowerCase().includes(agentType.toLowerCase())
      )
    : agentActivities

  return {
    activities: filteredActivities,
    loading,
    error
  }
} 