'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { Bell, Check, CheckCircle, ChevronRight, Mail, RefreshCw, Trash2, UserCheck, UserPlus, UserX, X, XCircle } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'

interface Notification {
  id: string
  type: string
  title: string
  body: string
  severity: 'info' | 'warn' | 'critical'
  delivery_state: 'pending' | 'sent' | 'read' | 'archived'
  created_at: string
  metadata?: Record<string, any>
  resource_type?: string
  resource_id?: string
}

interface NotificationsPanelProps {
  userId: string
  onNotificationClick?: () => void
  onUnreadCountChange?: (newCount: number) => void
  onPanelOpen?: boolean
}

export function NotificationsPanel({ userId, onNotificationClick, onUnreadCountChange, onPanelOpen }: NotificationsPanelProps) {
  const router = useRouter()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [error, setError] = useState<string | null>(null)
  const hasMarkedAsViewedRef = useRef(false)

  const fetchNotifications = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params = new URLSearchParams({
        limit: '20',
        unread_only: filter === 'unread' ? 'true' : 'false'
      })
      
      const response = await fetch(`http://localhost:8000/api/notifications/?${params}`, {
        headers: {
          'X-User-ID': userId
        }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch notifications')
      }

      const data = await response.json()
      setNotifications(data.notifications || [])
    } catch (err) {
      console.error('Error fetching notifications:', err)
      setError('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) {
      fetchNotifications()
    }
  }, [userId, filter])

  // Auto-mark all unread notifications as read when panel opens
  useEffect(() => {
    if (onPanelOpen && notifications.length > 0 && !hasMarkedAsViewedRef.current) {
      const unreadIds = notifications
        .filter(n => n.delivery_state === 'pending' || n.delivery_state === 'sent')
        .map(n => n.id)
      
      if (unreadIds.length > 0) {
        hasMarkedAsViewedRef.current = true
        markAsRead(unreadIds)
      }
    } else if (!onPanelOpen) {
      // Reset when panel closes so it can mark as read again on next open
      hasMarkedAsViewedRef.current = false
    }
  }, [onPanelOpen, notifications])

  const markAsRead = async (notificationIds: string[]) => {
    try {
      console.log('Marking notifications as read:', notificationIds)
      
      const response = await fetch('http://localhost:8000/api/notifications/read', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': userId
        },
        body: JSON.stringify(notificationIds)
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Mark as read successful:', result)
        
        // Update local state
        setNotifications(prev => 
          prev.map(notif => 
            notificationIds.includes(notif.id) 
              ? { ...notif, delivery_state: 'read' as const }
              : notif
          )
        )
        
        // Update unread count
        const unreadToMarkCount = notifications.filter(n => 
          notificationIds.includes(n.id) && 
          (n.delivery_state === 'pending' || n.delivery_state === 'sent')
        ).length
        
        if (unreadToMarkCount > 0 && onUnreadCountChange) {
          // Get current unread count from notifications
          const currentUnread = notifications.filter(n => 
            n.delivery_state === 'pending' || n.delivery_state === 'sent'
          ).length
          onUnreadCountChange(Math.max(0, currentUnread - unreadToMarkCount))
        }
      } else {
        const errorText = await response.text()
        console.error('Failed to mark as read:', response.status, errorText)
        setError('Failed to mark notifications as read')
      }
    } catch (err) {
      console.error('Error marking notifications as read:', err)
      setError('Failed to mark notifications as read')
    }
  }

  const getNavigationPath = (notification: Notification): string => {
    const { type, metadata, resource_type, resource_id } = notification
    
    // Chat-related notifications
    if (type.startsWith('chat.')) {
      if (metadata?.conversation_id) {
        return `/chat?conversation_id=${encodeURIComponent(metadata.conversation_id)}`
      }
      if (metadata?.agent_name) {
        // Convert agent name to agent ID format if needed
        const agentId = metadata.agent_id || `agent.${metadata.agent_name.toLowerCase().replace(/\s+/g, '_')}`
        return `/chat?agent=${encodeURIComponent(agentId)}`
      }
      return '/chat'
    }
    
    // Gmail/Email notifications
    if (type.startsWith('system.gmail.') || type.includes('email')) {
      return '/dashboard/emails'
    }
    
    // Email permission notifications
    if (type === 'email_permission_request' || type === 'email_permission_response') {
      return '/dashboard/team-organigram'
    }
    
    // Task notifications
    if (type.startsWith('task.')) {
      if (resource_type === 'task' && resource_id) {
        return `/dashboard/manager?task=${encodeURIComponent(resource_id)}`
      }
      return '/dashboard/manager'
    }
    
    // Agent-related notifications
    if (type.startsWith('agent.')) {
      if (metadata?.agent_id) {
        return `/chat?agent=${encodeURIComponent(metadata.agent_id)}`
      }
      return '/dashboard/manager'
    }
    
    // System notifications
    if (type.startsWith('system.')) {
      return '/dashboard/manager'
    }
    
    // Default fallback
    return '/dashboard/manager'
  }

  const handleNotificationClick = async (notification: Notification) => {
    // Mark as read if unread
    const isUnread = notification.delivery_state === 'pending' || notification.delivery_state === 'sent'
    if (isUnread) {
      await markAsRead([notification.id])
    }
    
    // Navigate to relevant page
    const path = getNavigationPath(notification)
    router.push(path)
    
    // Close notification panel
    onNotificationClick?.()
  }

  const removeNotification = async (notificationId: string, event?: React.MouseEvent) => {
    // Prevent event bubbling to avoid triggering notification click
    if (event) {
      event.preventDefault()
      event.stopPropagation()
    }
    
    try {
      const removedNotification = notifications.find(n => n.id === notificationId)
      const isUnread = removedNotification && 
        (removedNotification.delivery_state === 'pending' || removedNotification.delivery_state === 'sent')
      
      // Archive the notification via the backend
      const response = await fetch(`http://localhost:8000/api/notifications/${notificationId}/archive`, {
        method: 'POST',
        headers: {
          'X-User-ID': userId
        }
      })
      
      if (!response.ok) {
        throw new Error(`Failed to archive notification: ${response.statusText}`)
      }
      
      // Remove from local state (optimistic update)
      setNotifications(prev => prev.filter(notif => notif.id !== notificationId))
      
      // Update unread count if the removed notification was unread
      if (isUnread && onUnreadCountChange) {
        const currentUnread = notifications.filter(n => 
          n.delivery_state === 'pending' || n.delivery_state === 'sent'
        ).length
        onUnreadCountChange(Math.max(0, currentUnread - 1))
      }
      
    } catch (err) {
      console.error('Failed to remove notification:', err)
      setError('Failed to remove notification')
    }
  }

  const markAllAsRead = async () => {
    const unreadIds = notifications
      .filter(n => n.delivery_state === 'pending' || n.delivery_state === 'sent')
      .map(n => n.id)
    
    if (unreadIds.length > 0) {
      await markAsRead(unreadIds)
    }
  }

  const handleEmailPermissionResponse = async (notificationId: string, action: 'approve' | 'deny', permissionId: string, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation()
      event.preventDefault()
    }

    try {
      const response = await fetch('http://localhost:8000/api/email-permissions/respond', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          permission_id: permissionId,
          action: action,
          responding_user_id: userId
        })
      })

      if (response.ok) {
        // Mark notification as read and update locally
        await markAsRead([notificationId])
        
        // Remove the notification from view
        setNotifications(prev => prev.filter(n => n.id !== notificationId))
        
        toast.success(`Email permission ${action}d successfully`)
        
        // Refresh notifications to get updated list
        await fetchNotifications()
      } else {
        throw new Error(`Failed to ${action} email permission`)
      }
    } catch (err) {
      console.error(`Error ${action}ing email permission:`, err)
      toast.error(`Failed to ${action} email permission`)
    }
  }

  const removeAllNotifications = async () => {
    if (notifications.length === 0) return
    
    try {
      const unreadNotifications = notifications.filter(n => 
        n.delivery_state === 'pending' || n.delivery_state === 'sent'
      )
      
      // Archive all notifications via the backend
      const archivePromises = notifications.map(async (notification) => {
        try {
          const response = await fetch(`http://localhost:8000/api/notifications/${notification.id}/archive`, {
            method: 'POST',
            headers: {
              'X-User-ID': userId
            }
          })
          
          if (!response.ok) {
            console.warn(`Failed to archive notification ${notification.id}: ${response.statusText}`)
          }
        } catch (err) {
          console.warn(`Error archiving notification ${notification.id}:`, err)
        }
      })
      
      // Wait for all archive requests to complete (but don't fail if some fail)
      await Promise.allSettled(archivePromises)
      
      // Clear local state (optimistic update)
      setNotifications([])
      
      // Reset unread count
      if (onUnreadCountChange) {
        onUnreadCountChange(0)
      }
      
    } catch (err) {
      console.error('Error removing all notifications:', err)
      setError('Failed to remove all notifications')
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200'
      case 'warn': return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default: return 'text-blue-600 bg-blue-50 border-blue-200'
    }
  }

  const getTypeIcon = (type: string) => {
    if (type.startsWith('chat.')) return '💬'
    if (type.startsWith('task.')) return '📋'
    if (type.startsWith('agent.')) return '🤖'
    if (type.startsWith('system.')) return '⚙️'
    if (type.startsWith('auth.')) return '🔐'
    return '🔔'
  }

  const formatTime = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return 'Unknown time'
    }
  }

  if (loading) {
    return (
      <div className="p-4 space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex space-x-3">
              <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-600 mb-3">{error}</p>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchNotifications}
          className="text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="max-h-96 overflow-hidden flex flex-col">
      {/* Filter and Actions */}
      <div className="flex items-center justify-between p-3 border-b bg-gray-50">
        <div className="flex gap-2">
          <Button
            variant={filter === 'all' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilter('all')}
            className="text-xs h-7"
          >
            All
          </Button>
          <Button
            variant={filter === 'unread' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setFilter('unread')}
            className="text-xs h-7"
          >
            Unread
          </Button>
        </div>
        
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={markAllAsRead}
            className="text-xs h-7"
            title="Mark all as read"
            disabled={notifications.filter(n => n.delivery_state === 'pending' || n.delivery_state === 'sent').length === 0}
          >
            <Check className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={removeAllNotifications}
            className="text-xs h-7 hover:bg-red-100 hover:text-red-600"
            title="Remove all notifications"
            disabled={notifications.length === 0}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchNotifications}
            className="text-xs h-7"
            title="Refresh"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              {filter === 'unread' ? 'No unread notifications' : 'No notifications yet'}
            </p>
          </div>
        ) : (
          <div className="divide-y">
            {notifications.map((notification) => {
              const isUnread = notification.delivery_state === 'pending' || notification.delivery_state === 'sent'
              
              return (
                <div
                  key={notification.id}
                  className={cn(
                    "p-3 hover:bg-gray-50 cursor-pointer transition-colors border-l-2 border-transparent hover:border-blue-300",
                    isUnread && "bg-blue-50/50 border-l-blue-400"
                  )}
                  onClick={() => handleNotificationClick(notification)}
                  title={`Click to view ${notification.type.includes('chat') ? 'conversation' : 'details'}`}
                >
                  <div className="flex items-start space-x-3">
                    {/* Icon/Avatar */}
                    <div className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center text-sm border",
                      getSeverityColor(notification.severity)
                    )}>
                      {getTypeIcon(notification.type)}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <h4 className={cn(
                          "text-sm font-medium truncate",
                          isUnread ? "font-semibold" : "font-normal"
                        )}>
                          {notification.title}
                        </h4>
                        <div className="flex items-center ml-2 flex-shrink-0">
                          {isUnread && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" />
                          )}
                          <span className="text-xs text-gray-500 mr-2">
                            {formatTime(notification.created_at)}
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 hover:bg-red-100 hover:text-red-600 opacity-60 hover:opacity-100"
                            onClick={(e) => removeNotification(notification.id, e)}
                            title="Remove notification"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                          <ChevronRight className="h-3 w-3 text-gray-400 opacity-60 ml-1" />
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {notification.body}
                      </p>
                      
                      {/* Email Permission Request Actions */}
                      {notification.type === 'email_permission_request' && notification.metadata?.permission_id && (
                        <div className="flex space-x-2 mt-3" onClick={(e) => e.stopPropagation()}>
                          <Button
                            size="sm"
                            variant="default"
                            className="bg-green-600 hover:bg-green-700 text-white h-7 px-3"
                            onClick={(e) => handleEmailPermissionResponse(
                              notification.id, 
                              'approve', 
                              notification.metadata?.permission_id || '', 
                              e
                            )}
                          >
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-300 text-red-600 hover:bg-red-50 h-7 px-3"
                            onClick={(e) => handleEmailPermissionResponse(
                              notification.id, 
                              'deny', 
                              notification.metadata?.permission_id || '', 
                              e
                            )}
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            Deny
                          </Button>
                        </div>
                      )}
                      
                      {/* Email Permission Response */}
                      {notification.type === 'email_permission_response' && (
                        <div className="flex items-center mt-2">
                          {notification.metadata?.action === 'approve' ? (
                            <Badge variant="default" className="bg-green-100 text-green-800">
                              <UserCheck className="h-3 w-3 mr-1" />
                              Access Granted
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="bg-red-100 text-red-800">
                              <UserX className="h-3 w-3 mr-1" />
                              Access Denied
                            </Badge>
                          )}
                        </div>
                      )}
                      
                      {notification.severity !== 'info' && (
                        <Badge 
                          variant={notification.severity === 'critical' ? 'destructive' : 'secondary'}
                          className="mt-2 text-xs"
                        >
                          {notification.severity}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      {notifications.length > 0 && (
        <div className="p-3 border-t bg-gray-50">
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-500">
              {notifications.length} notification{notifications.length !== 1 ? 's' : ''}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-7"
              onClick={() => {
                // TODO: Navigate to full notifications page
                onNotificationClick?.()
              }}
            >
              View all
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// Helper functions for notification display
const getTypeIcon = (type: string) => {
  if (type.startsWith('chat.')) return '💬'
  if (type.startsWith('task.')) return '📋'
  if (type.startsWith('agent.')) return '🤖'
  if (type.startsWith('system.gmail.') || type.includes('email')) return <Mail className="h-4 w-4" />
  if (type === 'email_permission_request') return <UserPlus className="h-4 w-4" />
  if (type === 'email_permission_response') return <UserCheck className="h-4 w-4" />
  return <Bell className="h-4 w-4" />
}

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-700 border-red-300'
    case 'warn': return 'bg-yellow-100 text-yellow-700 border-yellow-300'
    default: return 'bg-blue-100 text-blue-700 border-blue-300'
  }
}

const formatTime = (dateString: string) => {
  try {
    return formatDistanceToNow(new Date(dateString), { addSuffix: true })
  } catch {
    return 'Unknown'
  }
}
