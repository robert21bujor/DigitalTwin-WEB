'use client'

import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'
import { Home, LogOut, User } from 'lucide-react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'

interface NavigationHeaderProps {
  title?: string
  showBackButton?: boolean
  backUrl?: string
}

export function NavigationHeader({ title, showBackButton = false, backUrl = '/dashboard/manager' }: NavigationHeaderProps) {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    try {
      await logout()
      toast.success('Logged out successfully')
      router.push('/')
    } catch (error) {
      toast.error('Logout failed')
    }
  }

  const handleHome = () => {
    router.push('/dashboard/manager')
  }

  const handleBack = () => {
    if (showBackButton) {
      router.push(backUrl)
    }
  }

  return (
    <div className="flex items-center justify-between p-4 border-b bg-white sticky top-0 z-50">
      {/* Left side - Title and optional back button */}
      <div className="flex items-center space-x-4">
        {showBackButton && (
          <Button variant="outline" size="sm" onClick={handleBack}>
            ← Back
          </Button>
        )}
        {title && (
          <h1 className="text-xl font-semibold text-gray-800">{title}</h1>
        )}
      </div>

      {/* Right side - User info and action buttons */}
      <div className="flex items-center space-x-3">
        {/* User info */}
        {user && (
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <User className="h-4 w-4" />
            <span>{user.username}</span>
            {user.admin_rights && user.admin_rights !== 'none' && (
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                {user.admin_rights}
              </span>
            )}
          </div>
        )}

        {/* Home button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleHome}
          className="flex items-center space-x-1"
        >
          <Home className="h-4 w-4" />
          <span>Dashboard</span>
        </Button>

        {/* Logout button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleLogout}
          className="flex items-center space-x-1 text-red-600 hover:text-red-700 hover:bg-red-50"
        >
          <LogOut className="h-4 w-4" />
          <span>Logout</span>
        </Button>
      </div>
    </div>
  )
}