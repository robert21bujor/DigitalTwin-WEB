'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'

interface UseNotificationsReturn {
  unreadCount: number
  isConnected: boolean
  error: string | null
  sendMessage: (message: any) => void
  reconnect: () => void
  updateUnreadCount: (newCount: number) => void
}

interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
}

export function useNotifications(userId: string): UseNotificationsReturn {
  const [unreadCount, setUnreadCount] = useState(0)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5

  const connectWebSocket = useCallback(() => {
    if (!userId) return

    try {
      // Close existing connection if any
      if (wsRef.current) {
        wsRef.current.close()
      }

      const wsUrl = `ws://localhost:8000/ws/notifications?user_id=${encodeURIComponent(userId)}`
      console.log('Connecting to WebSocket:', wsUrl)
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('Notification WebSocket connected')
        setIsConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          console.log('WebSocket message received:', message)
          
          switch (message.type) {
            case 'connection_ack':
              console.log('WebSocket connection acknowledged')
              break
              
            case 'unread_count':
              setUnreadCount(message.data.unread_count || 0)
              break
              
            case 'notification':
              const notification = message.data.notification
              if (notification) {
                // Show toast for new notification
                toast.success(notification.title, {
                  duration: 4000,
                })
                
                // Update unread count
                setUnreadCount(prev => prev + (message.data.unread_count_delta || 1))
              }
              break
              
            case 'initial_notifications':
              setUnreadCount(message.data.unread_count || 0)
              console.log('Initial notifications loaded:', message.data.notifications?.length || 0)
              break
              
            case 'ping':
              // Respond to ping with pong
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ 
                  type: 'pong', 
                  data: { timestamp: new Date().toISOString() } 
                }))
              }
              break
              
            default:
              console.log('Unknown WebSocket message type:', message.type)
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setIsConnected(false)
        
        // Only attempt reconnection if it wasn't a manual close
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          console.log(`Attempting reconnection in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connectWebSocket()
          }, delay)
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Connection lost. Please refresh the page.')
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('Connection error')
        setIsConnected(false)
      }

    } catch (err) {
      console.error('Error creating WebSocket connection:', err)
      setError('Failed to connect to notifications')
    }
  }, [userId])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0
    setError(null)
    connectWebSocket()
  }, [connectWebSocket])

  // Fetch initial unread count via HTTP (fallback)
  const fetchUnreadCount = useCallback(async () => {
    if (!userId) return

    try {
      const response = await fetch(`http://localhost:8000/api/notifications/unread-count?user_id=${encodeURIComponent(userId)}`)
      if (response.ok) {
        const data = await response.json()
        setUnreadCount(data.unread_count || 0)
      }
    } catch (err) {
      console.error('Error fetching unread count:', err)
    }
  }, [userId])

  // Initialize WebSocket connection
  useEffect(() => {
    if (userId) {
      connectWebSocket()
      fetchUnreadCount()
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, [userId, connectWebSocket, fetchUnreadCount])

  // Mark notifications as read via WebSocket
  const markAsRead = useCallback((notificationIds: string[]) => {
    sendMessage({
      type: 'mark_read',
      data: { notification_ids: notificationIds }
    })
  }, [sendMessage])

  // Update unread count manually
  const updateUnreadCount = useCallback((newCount: number) => {
    setUnreadCount(newCount)
  }, [])

  return {
    unreadCount,
    isConnected,
    error,
    sendMessage,
    reconnect,
    updateUnreadCount
  }
}
