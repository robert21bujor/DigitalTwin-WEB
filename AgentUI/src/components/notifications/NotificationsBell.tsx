'use client'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    Popover,
    PopoverContent,
    PopoverTrigger
} from '@/components/ui/popover'
import { useNotifications } from '@/hooks/useNotifications'
import { Bell, X } from 'lucide-react'
import { useState } from 'react'
import { NotificationsPanel } from './NotificationsPanel'

interface NotificationsBellProps {
  userId: string
  className?: string
}

export function NotificationsBell({ userId, className = '' }: NotificationsBellProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { unreadCount, isConnected, error, updateUnreadCount } = useNotifications(userId)

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`relative p-2 hover:bg-gray-100 ${className}`}
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
          {!isConnected && (
            <div className="absolute -bottom-1 -right-1 h-2 w-2 bg-yellow-500 rounded-full" 
                 title="Notification connection issue" />
          )}
        </Button>
      </PopoverTrigger>
      
      <PopoverContent 
        className="w-96 p-0 mr-4" 
        align="end"
        sideOffset={8}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold text-lg">Notifications</h3>
          <div className="flex items-center gap-2">
            {!isConnected && (
              <span className="text-xs text-yellow-600">Reconnecting...</span>
            )}
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => setIsOpen(false)}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <NotificationsPanel 
          userId={userId} 
          onNotificationClick={() => setIsOpen(false)}
          onUnreadCountChange={updateUnreadCount}
          onPanelOpen={isOpen}
        />
      </PopoverContent>
    </Popover>
  )
}
