'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAgentMetrics, useRealTimeMetrics } from '@/hooks/useRealTimeMetrics';
import { useAuthStore } from '@/stores/auth';
import {
    Activity,
    AlertCircle,
    BarChart,
    FileText,
    MessageSquare,
    RefreshCw,
    Settings,
    Target,
    TrendingUp,
    Users
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Real-time agent data interface
interface DigitalAgent {
    id: string;
    name: string;
    role: string;
    status: 'online' | 'busy' | 'offline';
    department: string;
    capabilities: string[];
    lastSeen: string;
    isActive: boolean;
    activity?: string;
}

interface AgentTask {
    id: string;
    title: string;
    agent: string;
    priority: 'high' | 'medium' | 'low';
    status: 'pending' | 'in_progress' | 'completed';
    dueDate: string;
}

export default function DigitalMarketingDashboard() {
    const { user } = useAuthStore();
    const router = useRouter();
    const { metrics, agentActivities, loading, error, refetch } = useRealTimeMetrics();
    const { activities: digitalActivities } = useAgentMetrics('digital');
    const [tasks, setTasks] = useState<AgentTask[]>([]);
    const [newTaskTitle, setNewTaskTitle] = useState('');
    const [selectedAgent, setSelectedAgent] = useState('');

    // Load real agent data from registry
    const [digitalAgents, setDigitalAgents] = useState<DigitalAgent[]>([]);

    useEffect(() => {
        // Transform real-time activities into digital agents data
        const digitalAgentTypes = ['seo', 'sem', 'analytics', 'funnel', 'landing'];

        const agentsFromActivities = agentActivities
            .filter(activity =>
                digitalAgentTypes.some(type =>
                    activity.agent_id.toLowerCase().includes(type) ||
                    activity.agent_name.toLowerCase().includes(type)
                ) || activity.department.toLowerCase().includes('digital') ||
                activity.department.toLowerCase().includes('marketing')
            )
            .map(activity => ({
                id: activity.agent_id,
                name: activity.agent_name,
                role: activity.agent_name.includes('SEO') ? 'SEO Optimization Specialist' :
                    activity.agent_name.includes('SEM') ? 'Search Engine Marketing Specialist' :
                        activity.agent_name.includes('Analytics') ? 'Marketing Analytics Specialist' :
                            activity.agent_name.includes('Funnel') ? 'Funnel Optimization Specialist' :
                                activity.agent_name.includes('Landing') ? 'Landing Page Specialist' :
                                    'Digital Marketing Specialist',
                status: activity.status,
                department: activity.department,
                capabilities: activity.agent_name.includes('SEO') ? ['keyword research', 'technical SEO', 'content optimization'] :
                    activity.agent_name.includes('SEM') ? ['paid search', 'PPC campaigns', 'ad optimization'] :
                        activity.agent_name.includes('Analytics') ? ['data analysis', 'performance measurement', 'reporting'] :
                            activity.agent_name.includes('Funnel') ? ['funnel analysis', 'conversion optimization'] :
                                activity.agent_name.includes('Landing') ? ['landing pages', 'A/B testing', 'UX optimization'] :
                                    ['digital marketing'],
                lastSeen: activity.timestamp,
                isActive: activity.status === 'online' || activity.status === 'busy',
                activity: activity.activity
            }));

        setDigitalAgents(agentsFromActivities);
    }, [agentActivities]);

    // All authenticated users can access this dashboard

    const addTask = () => {
        if (newTaskTitle && selectedAgent) {
            const newTask: AgentTask = {
                id: Date.now().toString(),
                title: newTaskTitle,
                agent: selectedAgent,
                priority: 'medium',
                status: 'pending',
                dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
            };
            setTasks([...tasks, newTask]);
            setNewTaskTitle('');
            setSelectedAgent('');
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'online': return 'bg-green-500';
            case 'busy': return 'bg-yellow-500';
            case 'offline': return 'bg-gray-500';
            default: return 'bg-gray-500';
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'high': return 'bg-red-100 text-red-800';
            case 'medium': return 'bg-yellow-100 text-yellow-800';
            case 'low': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const formatTimestamp = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / (1000 * 60));

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minutes ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
        return date.toLocaleDateString();
    };

    if (loading) {
        return (
            <div className="container mx-auto px-4 py-8">
                <div className="flex items-center justify-center min-h-[400px]">
                    <div className="flex items-center space-x-2">
                        <RefreshCw className="h-6 w-6 animate-spin" />
                        <span>Loading real-time metrics...</span>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container mx-auto px-4 py-8">
                <Card>
                    <CardContent className="pt-6">
                        <div className="flex items-center space-x-2 text-red-600 mb-4">
                            <AlertCircle className="h-5 w-5" />
                            <span>Error loading metrics: {error}</span>
                        </div>
                        <Button onClick={refetch} variant="outline">
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Retry
                        </Button>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Digital Marketing Dashboard</h1>
                        <p className="text-gray-600 mt-2">Real-time digital marketing metrics and agent management</p>
                    </div>
                    <Button onClick={refetch} variant="outline" size="sm">
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Refresh
                    </Button>
                </div>
            </div>

            {/* Real-time System Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Active Digital Agents</p>
                                <p className="text-2xl font-bold">{digitalAgents.filter(a => a.isActive).length}</p>
                            </div>
                            <Users className="h-5 w-5 text-muted-foreground" />
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Total Messages</p>
                                <p className="text-2xl font-bold">{metrics.totalMessages}</p>
                            </div>
                            <MessageSquare className="h-5 w-5 text-muted-foreground" />
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">Messages/Hour</p>
                                <p className="text-2xl font-bold">{metrics.messagesThisHour}</p>
                            </div>
                            <TrendingUp className="h-5 w-5 text-muted-foreground" />
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-muted-foreground">System Health</p>
                                <p className="text-2xl font-bold">{metrics.systemHealth}%</p>
                            </div>
                            <Activity className="h-5 w-5 text-muted-foreground" />
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="agents" className="space-y-6">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="agents">Digital Agents</TabsTrigger>
                    <TabsTrigger value="tasks">Task Management</TabsTrigger>
                    <TabsTrigger value="metrics">Real-time Metrics</TabsTrigger>
                </TabsList>

                <TabsContent value="agents" className="space-y-6">
                    {digitalAgents.length === 0 ? (
                        <Card>
                            <CardContent className="pt-6">
                                <div className="text-center text-muted-foreground">
                                    <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No digital marketing agents are currently active.</p>
                                    <p className="text-sm mt-2">Agents will appear here when they come online.</p>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {digitalAgents.map((agent) => (
                                <Card key={agent.id} className="hover:shadow-lg transition-shadow">
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-3">
                                                <Avatar>
                                                    <AvatarFallback>{agent.name.charAt(0)}</AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <CardTitle className="text-lg">{agent.name}</CardTitle>
                                                    <CardDescription className="text-sm">{agent.role}</CardDescription>
                                                </div>
                                            </div>
                                            <div className={`w-3 h-3 rounded-full ${getStatusColor(agent.status)}`} />
                                        </div>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="text-sm">
                                            <p className="text-muted-foreground">Department</p>
                                            <p className="font-medium">{agent.department}</p>
                                        </div>

                                        {agent.activity && (
                                            <div className="text-sm">
                                                <p className="text-muted-foreground">Current Activity</p>
                                                <p className="font-medium">{agent.activity}</p>
                                            </div>
                                        )}

                                        <div>
                                            <p className="text-sm text-muted-foreground mb-2">Capabilities</p>
                                            <div className="flex flex-wrap gap-1">
                                                {agent.capabilities.map((skill, index) => (
                                                    <Badge key={index} variant="secondary" className="text-xs">
                                                        {skill}
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="pt-2 border-t">
                                            <p className="text-xs text-muted-foreground">
                                                Last seen: {formatTimestamp(agent.lastSeen)}
                                            </p>
                                        </div>

                                        <div className="flex gap-2">
                                            <Button size="sm" className="flex-1" disabled={!agent.isActive}>
                                                <MessageSquare className="h-4 w-4 mr-1" />
                                                Chat
                                            </Button>
                                            <Button size="sm" variant="outline">
                                                <Settings className="h-4 w-4" />
                                            </Button>
                                        </div>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                <TabsContent value="tasks" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Assign New Task</CardTitle>
                            <CardDescription>Create and assign tasks to your digital marketing agents</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="flex gap-4">
                                <Input
                                    placeholder="Enter task description..."
                                    value={newTaskTitle}
                                    onChange={(e) => setNewTaskTitle(e.target.value)}
                                    className="flex-1"
                                />
                                <select
                                    value={selectedAgent}
                                    onChange={(e) => setSelectedAgent(e.target.value)}
                                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    disabled={digitalAgents.length === 0}
                                >
                                    <option value="">Select Agent</option>
                                    {digitalAgents.filter(agent => agent.isActive).map((agent) => (
                                        <option key={agent.id} value={agent.name}>
                                            {agent.name}
                                        </option>
                                    ))}
                                </select>
                                <Button
                                    onClick={addTask}
                                    disabled={!newTaskTitle || !selectedAgent || digitalAgents.length === 0}
                                >
                                    Assign Task
                                </Button>
                            </div>
                            {digitalAgents.length === 0 && (
                                <p className="text-sm text-muted-foreground mt-2">
                                    No active agents available for task assignment.
                                </p>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Active Tasks</CardTitle>
                            <CardDescription>Monitor and manage digital marketing tasks</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {tasks.length === 0 ? (
                                <div className="text-center text-muted-foreground py-8">
                                    <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No tasks assigned yet.</p>
                                    <p className="text-sm mt-2">Create a task above to get started.</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {tasks.map((task) => (
                                        <div key={task.id} className="flex items-center justify-between p-4 border rounded-lg">
                                            <div className="flex-1">
                                                <h4 className="font-medium">{task.title}</h4>
                                                <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                                                    <span>Assigned to: {task.agent}</span>
                                                    <span>Due: {task.dueDate}</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Badge className={getPriorityColor(task.priority)}>
                                                    {task.priority}
                                                </Badge>
                                                <Badge variant={task.status === 'completed' ? 'default' : 'secondary'}>
                                                    {task.status.replace('_', ' ')}
                                                </Badge>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="metrics" className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Activity className="h-5 w-5" />
                                    System Performance
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Active Agents</p>
                                        <p className="text-2xl font-bold">{metrics.activeAgents}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Departments</p>
                                        <p className="text-2xl font-bold">{metrics.departments}</p>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">System Health</p>
                                    <p className="text-2xl font-bold">{metrics.systemHealth}%</p>
                                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                                        <div
                                            className="bg-green-600 h-2 rounded-full"
                                            style={{ width: `${metrics.systemHealth}%` }}
                                        ></div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <MessageSquare className="h-5 w-5" />
                                    Communication Activity
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Total Messages</p>
                                        <p className="text-2xl font-bold">{metrics.totalMessages}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">This Hour</p>
                                        <p className="text-2xl font-bold">{metrics.messagesThisHour}</p>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Average Response Time</p>
                                    <p className="text-2xl font-bold">{metrics.avgResponseTime}s</p>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Target className="h-5 w-5" />
                                    Task Management
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-muted-foreground">Completed</p>
                                        <p className="text-2xl font-bold">{metrics.tasksCompleted}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Pending</p>
                                        <p className="text-2xl font-bold">{metrics.pendingTasks}</p>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-sm text-muted-foreground">Active Users</p>
                                    <p className="text-2xl font-bold">{metrics.activeUsers}</p>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <BarChart className="h-5 w-5" />
                                    Recent Activity
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {digitalActivities.length === 0 ? (
                                    <div className="text-center text-muted-foreground py-4">
                                        <p>No recent digital marketing activity</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {digitalActivities.slice(0, 5).map((activity) => (
                                            <div key={activity.id} className="flex items-center space-x-3 text-sm">
                                                <div className={`w-2 h-2 rounded-full ${getStatusColor(activity.status)}`} />
                                                <div className="flex-1">
                                                    <p className="font-medium">{activity.agent_name}</p>
                                                    <p className="text-muted-foreground">{activity.activity}</p>
                                                </div>
                                                <span className="text-xs text-muted-foreground">
                                                    {formatTimestamp(activity.timestamp)}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
} 
