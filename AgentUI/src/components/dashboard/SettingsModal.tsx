'use client'

import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/stores/auth'
import { Calendar, CheckCircle, ExternalLink, Loader2, LogOut, Mail, Moon, RefreshCw, Shield, Unlink, User, XCircle } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface SettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface UserSettings {
  appearance: {
    theme: 'light' | 'dark'
  }
  privacy: {
    showOnlineStatus: boolean
    allowDirectMessages: boolean
  }
  profile: {
    displayName: string
    bio: string
  }
}

interface GmailStatus {
  connected: boolean
  gmail_email?: string
  gmail_name?: string
  connected_at?: string
  is_expired?: boolean
  error?: string
}

interface AutoSyncStatus {
  auto_sync_enabled: boolean
  thread_running: boolean
  active_users_count: number
  sync_interval_minutes: number
}

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const { user, updateUserTheme, logout } = useAuthStore()
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus>({ connected: false })
  const [gmailLoading, setGmailLoading] = useState(false)
  const [syncLoading, setSyncLoading] = useState(false)
  const [syncProgress, setSyncProgress] = useState<string>("")
  const [syncDays, setSyncDays] = useState<string>("30")
  const [autoSyncStatus, setAutoSyncStatus] = useState<AutoSyncStatus>({
    auto_sync_enabled: false,
    thread_running: false,
    active_users_count: 0,
    sync_interval_minutes: 20
  })
  const [autoSyncLoading, setAutoSyncLoading] = useState(false)
  
  // Google (Gmail + Calendar) state
  const [calendarStatus, setCalendarStatus] = useState<{connected: boolean, available?: boolean, error?: string}>({ connected: false })
  const [calendarLoading, setCalendarLoading] = useState(false)
  
  // ClickUp state
  const [clickupStatus, setClickUpStatus] = useState<{connected: boolean, clickup_email?: string, clickup_username?: string, error?: string}>({ connected: false })
  const [clickupLoading, setClickUpLoading] = useState(false)
  const [showTokenInput, setShowTokenInput] = useState(false)
  const [personalToken, setPersonalToken] = useState('')
  
  const [settings, setSettings] = useState<UserSettings>({
    appearance: {
      theme: 'light'
    },
    privacy: {
      showOnlineStatus: true,
      allowDirectMessages: true
    },
    profile: {
      displayName: user?.username || '',
      bio: ''
    }
  })

  // Load user's theme preference on mount
  useEffect(() => {
    if (user?.theme) {
      setSettings(prev => ({
        ...prev,
        appearance: {
          theme: user.theme as 'light' | 'dark'
        }
      }))
    }
  }, [user?.theme])

  // Load Google connection status (Gmail + Calendar), ClickUp, and auto-sync status on open
  useEffect(() => {
    if (open && user?.id) {
      fetchGmailStatus()
      fetchAutoSyncStatus()
      fetchCalendarStatus()
      fetchClickUpStatus()
    }
  }, [open, user?.id])

  const fetchGmailStatus = async () => {
    if (!user?.id) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/gmail/status?user_id=${user.id}`)
      const status = await response.json()
      setGmailStatus(status)
    } catch (error) {
      console.error('Error fetching Gmail status:', error)
      setGmailStatus({ connected: false, error: 'Failed to fetch status' })
    }
  }

  const fetchAutoSyncStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/gmail/auto-sync/status')
      const status = await response.json()
      setAutoSyncStatus(status)
    } catch (error) {
      console.error('Error fetching auto-sync status:', error)
    }
  }

  const handleConnectGoogle = async () => {
    if (!user?.id) return
    
    try {
      setGmailLoading(true)
      
      // Get authorization URL
      const response = await fetch(`http://localhost:8000/api/gmail/auth-url?user_id=${user.id}`)
      const data = await response.json()
      
      if (data.success && data.auth_url) {
        // Open Google OAuth in new window
        window.open(data.auth_url, 'google-oauth', 'width=500,height=600')
        
        // Listen for OAuth completion
        const checkAuth = setInterval(async () => {
          try {
            const statusResponse = await fetch(`http://localhost:8000/api/gmail/status?user_id=${user.id}`)
            const status = await statusResponse.json()
            
            if (status.connected) {
              setGmailStatus(status)
              // Also refresh calendar status since Google connection now enables both
              await fetchCalendarStatus()
              clearInterval(checkAuth)
              setGmailLoading(false)
              toast.success('Google connected successfully! Gmail and Calendar are now available.')
            }
          } catch (error) {
            // Continue checking
          }
        }, 2000)
        
        // Stop checking after 5 minutes
        setTimeout(() => {
          clearInterval(checkAuth)
          setGmailLoading(false)
        }, 300000)
        
      } else {
        throw new Error(data.error || 'Failed to get authorization URL')
      }
    } catch (error) {
      console.error('Error connecting Google:', error)
      toast.error('Failed to connect Google')
      setGmailLoading(false)
    }
  }

  const handleDisconnectGoogle = async () => {
    if (!user?.id) return
    
    try {
      setGmailLoading(true)
      
      const response = await fetch('http://localhost:8000/api/gmail/disconnect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: user.id })
      })
      
      const result = await response.json()
      
      if (result.success) {
        setGmailStatus({ connected: false })
        setCalendarStatus({ connected: false })
        toast.success('Google disconnected successfully! Gmail and Calendar access removed.')
      } else {
        throw new Error(result.error || 'Failed to disconnect Google')
      }
    } catch (error) {
      console.error('Error disconnecting Google:', error)
      toast.error('Failed to disconnect Google')
    } finally {
      setGmailLoading(false)
    }
  }

  const handleSyncEmails = async () => {
    if (!user?.id) return
    
    try {
      setSyncLoading(true)
      
      // Start the sync
      const syncPromise = fetch('http://localhost:8000/api/gmail/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          user_id: user.id,
          days_back: syncDays === "ALL" ? 3650 : parseInt(syncDays), // 3650 days ≈ 10 years for "ALL"
          max_results: syncDays === "ALL" ? 1000 : 100  // Higher limit for ALL
        })
      })
      
      // Poll for progress updates
      const progressInterval = setInterval(async () => {
        try {
          const progressResponse = await fetch('http://localhost:8000/api/gmail/sync/progress')
          const progress = await progressResponse.json()
          
          if (progress.active) {
            // Update progress in UI
            let progressMsg = `${progress.stage}: ${progress.message}`
            if (progress.progress && progress.total) {
              progressMsg += ` (${progress.progress}/${progress.total})`
            }
            setSyncProgress(progressMsg)
          } else {
            // Sync completed or failed
            clearInterval(progressInterval)
            setSyncProgress("")
          }
        } catch (error) {
          // Continue polling even if progress check fails
        }
      }, 1000) // Check every second
      
      // Wait for sync to complete
      const response = await syncPromise
      const result = await response.json()
      
      // Clear progress polling
      clearInterval(progressInterval)
      
      if (result.success) {
        const period = syncDays === "ALL" ? "all emails" : `last ${syncDays} days`
        toast.success(`Synced ${result.total_processed} emails from ${period}!`)
        if (result.skipped_duplicates && result.skipped_duplicates > 0) {
          toast(`Skipped ${result.skipped_duplicates} duplicate emails`, {
            icon: 'ℹ️'
          })
        }
        if (result.new_documents && result.new_documents > 0) {
          toast.success(`Created ${result.new_documents} new documents`)
        }
      } else {
        throw new Error(result.error || 'Failed to sync emails')
      }
    } catch (error) {
      console.error('Error syncing emails:', error)
      toast.error('Failed to sync emails')
    } finally {
      setSyncLoading(false)
    }
  }

  const handleToggleAutoSync = async () => {
    try {
      setAutoSyncLoading(true)
      
      const endpoint = autoSyncStatus.auto_sync_enabled ? 'stop' : 'start'
      const response = await fetch(`http://localhost:8000/api/gmail/auto-sync/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      })
      
      const result = await response.json()
      
      if (result.success) {
        await fetchAutoSyncStatus() // Refresh status
        toast.success(result.message)
      } else {
        throw new Error(result.error || 'Failed to toggle auto-sync')
      }
    } catch (error) {
      console.error('Error toggling auto-sync:', error)
      toast.error('Failed to toggle auto-sync')
    } finally {
      setAutoSyncLoading(false)
    }
  }

  // Calendar functions
  const fetchCalendarStatus = async () => {
    if (!user?.id) return
    
    try {
      setCalendarLoading(true)
      
      // Check if Gmail is connected first (required for Calendar)
      const gmailResponse = await fetch(`http://localhost:8000/api/gmail/status?user_id=${user.id}`)
      const gmailData = await gmailResponse.json()
      
      if (!gmailData.connected) {
        setCalendarStatus({ 
          connected: false, 
          available: false, 
          error: 'Gmail connection required for Calendar access' 
        })
        return
      }
      
      // Check Calendar availability using Gmail tokens
      const calendarResponse = await fetch(`http://localhost:8000/api/calendar/status?user_id=${user.id}`)
      const calendarData = await calendarResponse.json()
      
      setCalendarStatus({
        connected: gmailData.connected,
        available: calendarData.available || false,
        error: calendarData.error
      })
      
    } catch (error) {
      console.error('Error fetching calendar status:', error)
      setCalendarStatus({ 
        connected: false, 
        available: false, 
        error: 'Failed to check calendar status' 
      })
    } finally {
      setCalendarLoading(false)
    }
  }

  const fetchClickUpStatus = async () => {
    if (!user?.id) return
    
    try {
      const response = await fetch(`http://localhost:8000/api/clickup/status?user_id=${user.id}`)
      const status = await response.json()
      setClickUpStatus(status)
    } catch (error) {
      console.error('Error fetching ClickUp status:', error)
      setClickUpStatus({ connected: false, error: 'Failed to fetch status' })
    }
  }

  const handleConnectClickUp = async () => {
    if (!user?.id) return
    
    try {
      setClickUpLoading(true)
      
      // Get OAuth URL from backend API (working version approach)
      const authUrlResponse = await fetch(`http://localhost:8000/api/clickup/auth-url?user_id=${user.id}`)
      const authUrlResult = await authUrlResponse.json()
      
      if (!authUrlResult.success) {
        throw new Error(authUrlResult.error || 'Failed to get ClickUp authorization URL')
      }
      
      // Store user ID for callback before opening OAuth popup
      localStorage.setItem('clickup-oauth-user-id', user.id)
      
      // Open ClickUp OAuth in new window
      const popup = window.open(authUrlResult.auth_url, 'clickup-oauth', 'width=500,height=600')
      
      // Listen for messages from the OAuth callback (working version approach)
      const handleOAuthMessage = (event: MessageEvent) => {
        if (event.data?.type === 'clickup-oauth-success') {
          setClickUpLoading(false)
          toast.success('ClickUp connected successfully!')
          fetchClickUpStatus() // Refresh status
          window.removeEventListener('message', handleOAuthMessage)
          if (popup && !popup.closed) {
            popup.close()
          }
        } else if (event.data?.type === 'clickup-oauth-error') {
          setClickUpLoading(false)
          toast.error(`ClickUp connection failed: ${event.data.error}`)
          window.removeEventListener('message', handleOAuthMessage)
          if (popup && !popup.closed) {
            popup.close()
          }
        }
      }
      
      window.addEventListener('message', handleOAuthMessage)
      
      // Fallback: Stop listening after 5 minutes
      setTimeout(() => {
        setClickUpLoading(false)
        window.removeEventListener('message', handleOAuthMessage)
        if (popup && !popup.closed) {
          popup.close()
        }
      }, 300000)
      
    } catch (error) {
      console.error('Error connecting ClickUp:', error)
      toast.error('Failed to connect ClickUp')
      setClickUpLoading(false)
    }
  }

  const handleDisconnectClickUp = async () => {
    if (!user?.id) return
    
    try {
      setClickUpLoading(true)
      
      const response = await fetch('http://localhost:8000/api/clickup/disconnect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: user.id })
      })
      
      const result = await response.json()
      
      if (result.success) {
        setClickUpStatus({ connected: false })
        toast.success('ClickUp disconnected successfully!')
      } else {
        throw new Error(result.error || 'Failed to disconnect ClickUp')
      }
    } catch (error) {
      console.error('Error disconnecting ClickUp:', error)
      toast.error('Failed to disconnect ClickUp')
    } finally {
      setClickUpLoading(false)
    }
  }

  const handleVerifyClickUp = async () => {
    if (!user?.id) return
    
    try {
      setClickUpLoading(true)
      
      const response = await fetch(`http://localhost:8000/api/clickup/verify?user_id=${user.id}`, {
        method: 'POST'
      })
      
      const result = await response.json()
      
      if (result.success) {
        toast.success('ClickUp connection verified successfully!')
        // Refresh status
        await fetchClickUpStatus()
      } else {
        toast.error(result.error || 'ClickUp verification failed')
      }
    } catch (error) {
      console.error('Error verifying ClickUp:', error)
      toast.error('Failed to verify ClickUp connection')
    } finally {
      setClickUpLoading(false)
    }
  }

  const handleConnectWithToken = async () => {
    if (!user?.id || !personalToken.trim()) return
    
    try {
      setClickUpLoading(true)
      
      const response = await fetch('http://localhost:8000/api/clickup/connect-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          personal_token: personalToken.trim()
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        setClickUpStatus({ connected: true, ...result.user_info })
        setPersonalToken('')
        setShowTokenInput(false)
        toast.success('ClickUp connected successfully with personal token!')
      } else {
        toast.error(result.error || 'Failed to connect with personal token')
      }
    } catch (error) {
      console.error('Error connecting with token:', error)
      toast.error('Failed to connect ClickUp with personal token')
    } finally {
      setClickUpLoading(false)
    }
  }

  const handleTestCalendar = async () => {
    if (!user?.id) return
    
    try {
      setCalendarLoading(true)
      
      // Test calendar access with today's events
      const response = await fetch(`http://localhost:8000/api/calendar/test?user_id=${user.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: "What's on my calendar today?",
          user_id: user.id 
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        toast.success(`Calendar test successful! ${result.events_count || 0} events found for today.`)
        setCalendarStatus(prev => ({ ...prev, available: true, error: undefined }))
      } else {
        toast.error(result.error || 'Calendar test failed')
        setCalendarStatus(prev => ({ ...prev, available: false, error: result.error }))
      }
      
    } catch (error) {
      console.error('Error testing calendar:', error)
      toast.error('Failed to test calendar access')
    } finally {
      setCalendarLoading(false)
    }
  }

  const handleLogout = async () => {
    try {
      setLoading(true)
      await logout()
      toast.success('Logged out successfully')
      onOpenChange(false)
      router.push('/')
    } catch (error) {
      toast.error('Logout failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setLoading(true)
      
      // Save theme preference
      updateUserTheme(settings.appearance.theme)
      
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      toast.success('Settings saved successfully!')
      onOpenChange(false)
    } catch (error) {
      toast.error('Failed to save settings')
    } finally {
      setLoading(false)
    }
  }

  const updateSetting = (section: keyof UserSettings, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Manage your account settings and preferences
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Profile Settings */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <User className="h-5 w-5" />
              <h3 className="text-lg font-medium">Profile</h3>
            </div>
            <div className="space-y-3 pl-7">
              <div>
                <label className="text-sm font-medium">Display Name</label>
                <Input
                  value={settings.profile.displayName}
                  onChange={(e) => updateSetting('profile', 'displayName', e.target.value)}
                  placeholder="Your display name"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Account Role</label>
                <Input
                  value={user?.role?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'}
                  disabled
                  className="bg-gray-100 dark:bg-gray-800 cursor-not-allowed"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Bio</label>
                <Input
                  value={settings.profile.bio}
                  onChange={(e) => updateSetting('profile', 'bio', e.target.value)}
                  placeholder="Tell us about yourself"
                />
              </div>
            </div>
          </div>

          {/* Google Integration */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Mail className="h-5 w-5" />
              <h3 className="text-lg font-medium">Google Integration</h3>
            </div>
            <div className="space-y-4 pl-7">
              <div className="p-4 border rounded-lg bg-gray-50 dark:bg-gray-900">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    {gmailStatus.connected && !gmailStatus.is_expired ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : gmailStatus.connected && gmailStatus.is_expired ? (
                      <XCircle className="h-5 w-5 text-orange-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-gray-400" />
                    )}
                    <span className="font-medium">
                      {gmailStatus.connected && !gmailStatus.is_expired ? 'Connected' : 
                       gmailStatus.connected && gmailStatus.is_expired ? 'Logged Off (Token Expired)' : 
                       'Not Connected'}
                    </span>
                    {gmailStatus.connected && !gmailStatus.is_expired && (
                      <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                        (Gmail + Calendar)
                      </span>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchGmailStatus}
                    disabled={gmailLoading}
                  >
                    <RefreshCw className={`h-4 w-4 ${gmailLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>

                {gmailStatus.connected ? (
                  <div className="space-y-3">
                    <div className="text-sm space-y-1">
                      <p><strong>Email:</strong> {gmailStatus.gmail_email}</p>
                      <p><strong>Name:</strong> {gmailStatus.gmail_name}</p>
                      <p><strong>Connected:</strong> {gmailStatus.connected_at ? new Date(gmailStatus.connected_at).toLocaleDateString() : 'Unknown'}</p>
                      <p><strong>Calendar Status:</strong> 
                        <span className={`ml-1 ${calendarStatus.connected && calendarStatus.available ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'}`}>
                          {calendarStatus.connected && calendarStatus.available ? 'Available' : 'Checking...'}
                        </span>
                      </p>
                      {gmailStatus.is_expired && (
                        <p className="text-red-600 dark:text-red-400">
                          <strong>Status:</strong> Authentication expired - Please reconnect to access Google services
                        </p>
                      )}
                    </div>
                    
                    {/* Days Selection */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Sync Period
                      </label>
                      <Select value={syncDays} onValueChange={setSyncDays}>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select sync period" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="30">Last 30 days</SelectItem>
                          <SelectItem value="60">Last 60 days</SelectItem>
                          <SelectItem value="90">Last 90 days</SelectItem>
                          <SelectItem value="ALL">All emails</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div className="flex space-x-2 flex-wrap">
                      <Button
                        size="sm"
                        onClick={handleSyncEmails}
                        disabled={syncLoading || gmailLoading}
                      >
                        {syncLoading ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4 mr-2" />
                        )}
                        Sync Emails
                      </Button>
                      
                      {calendarStatus.connected && calendarStatus.available && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleTestCalendar}
                          disabled={calendarLoading}
                        >
                          {calendarLoading ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <Calendar className="h-4 w-4 mr-2" />
                          )}
                          Test Calendar
                        </Button>
                      )}
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDisconnectGoogle}
                        disabled={gmailLoading || syncLoading}
                      >
                        {gmailLoading ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Unlink className="h-4 w-4 mr-2" />
                        )}
                        Disconnect Google
                      </Button>
                    </div>
                    
                    {/* Sync Progress Indicator */}
                    {syncProgress && (
                      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <div className="flex items-center space-x-2">
                          <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                          <span className="text-sm text-blue-800 dark:text-blue-200 font-medium">
                            Gmail Sync Progress
                          </span>
                        </div>
                        <p className="text-xs text-blue-600 dark:text-blue-300 mt-1">
                          {syncProgress}
                        </p>
                      </div>
                    )}
                    
                    {/* Auto-Sync Controls */}
                    <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <div className={`h-2 w-2 rounded-full ${autoSyncStatus.thread_running ? 'bg-green-500' : 'bg-gray-400'}`} />
                          <span className="font-medium text-sm">Auto-Sync</span>
                          <span className="text-xs text-gray-500">
                            ({autoSyncStatus.sync_interval_minutes} min intervals)
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant={autoSyncStatus.auto_sync_enabled ? "destructive" : "default"}
                          onClick={handleToggleAutoSync}
                          disabled={autoSyncLoading}
                        >
                          {autoSyncLoading ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          ) : null}
                          {autoSyncStatus.auto_sync_enabled ? 'Stop' : 'Start'}
                        </Button>
                      </div>
                      
                      <div className="text-xs text-gray-600 dark:text-gray-400">
                        <p>
                          <strong>Status:</strong> {autoSyncStatus.thread_running ? 'Running' : 'Stopped'} • 
                          <strong> Active Users:</strong> {autoSyncStatus.active_users_count}
                        </p>
                        <p className="mt-1">
                          Automatically syncs emails every {autoSyncStatus.sync_interval_minutes} minutes for all connected Gmail accounts.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Connect your Google account to access Gmail and Calendar features. This enables email synchronization and calendar access for your companion agents.
                    </p>
                    
                    <Button
                      onClick={handleConnectGoogle}
                      disabled={gmailLoading}
                      className="w-full"
                    >
                      {gmailLoading ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Mail className="h-4 w-4 mr-2" />
                      )}
                      Connect Google
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </Button>
                    
                    {gmailStatus.error && (
                      <p className="text-sm text-red-600 dark:text-red-400">
                        Error: {gmailStatus.error}
                      </p>
                    )}
                  </div>
                )}
              </div>
              
              <div className="text-xs text-gray-500 dark:text-gray-400">
                <p><strong>What this does:</strong></p>
                <ul className="mt-1 ml-4 list-disc space-y-1">
                  <li><strong>Gmail:</strong> Syncs emails from your inbox with smart categorization (Colleagues → Internal/, Clients → Clients/)</li>
                  <li><strong>Calendar:</strong> Enables companion agents (CMO, Operations Manager, BDM, Senior CSM) to access your calendar</li>
                  <li>Converts emails to Word documents organized by detected category</li>
                  <li>Auto-sync runs every 20 minutes to keep everything up-to-date</li>
                  <li>Single OAuth connection provides access to both Gmail and Calendar services</li>
                </ul>
              </div>
            </div>
          </div>



          {/* ClickUp Integration */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 18h20v2H2v-2zM13.84 4.91l1.48 1.48L8.66 12.84 7.18 11.36l6.66-6.45zM19.07 2.5c-.34 0-.68.13-.93.39L16.8 4.24l2.96 2.96 1.34-1.34c.51-.51.51-1.35 0-1.86L19.99 2.89c-.25-.25-.58-.39-.92-.39z"/>
              </svg>
              <h3 className="text-lg font-medium">ClickUp Integration</h3>
            </div>
            <div className="space-y-4 pl-7">
              <div className="p-4 border rounded-lg bg-gray-50 dark:bg-gray-900">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    {clickupStatus.connected ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-gray-400" />
                    )}
                    <span className="font-medium">
                      {clickupStatus.connected ? 'Connected' : 'Not Connected'}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={fetchClickUpStatus}
                    disabled={clickupLoading}
                  >
                    <RefreshCw className={`h-4 w-4 ${clickupLoading ? 'animate-spin' : ''}`} />
                  </Button>
                </div>

                {clickupStatus.connected ? (
                  <div className="space-y-3">
                    <div className="text-sm space-y-1">
                      {clickupStatus.clickup_email && (
                        <p><strong>Email:</strong> {clickupStatus.clickup_email}</p>
                      )}
                      {clickupStatus.clickup_username && (
                        <p><strong>Username:</strong> {clickupStatus.clickup_username}</p>
                      )}
                      <p><strong>Status:</strong> Ready for future integrations</p>
                    </div>
                    
                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        onClick={handleVerifyClickUp}
                        disabled={clickupLoading}
                      >
                        {clickupLoading ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <CheckCircle className="h-4 w-4 mr-2" />
                        )}
                        Verify Connection
                      </Button>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDisconnectClickUp}
                        disabled={clickupLoading}
                      >
                        {clickupLoading ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Unlink className="h-4 w-4 mr-2" />
                        )}
                        Disconnect
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Connect your ClickUp account to enable future project management integrations. Choose your preferred connection method:
                    </p>
                    
                    {!showTokenInput ? (
                      <div className="space-y-2">
                        <Button
                          onClick={handleConnectClickUp}
                          disabled={clickupLoading}
                          className="w-full"
                        >
                          {clickupLoading ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          ) : (
                            <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M2 18h20v2H2v-2zM13.84 4.91l1.48 1.48L8.66 12.84 7.18 11.36l6.66-6.45zM19.07 2.5c-.34 0-.68.13-.93.39L16.8 4.24l2.96 2.96 1.34-1.34c.51-.51.51-1.35 0-1.86L19.99 2.89c-.25-.25-.58-.39-.92-.39z"/>
                            </svg>
                          )}
                          Connect with OAuth
                          <ExternalLink className="h-4 w-4 ml-2" />
                        </Button>
                        
                        <Button
                          variant="outline"
                          onClick={() => setShowTokenInput(true)}
                          className="w-full"
                        >
                          <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
                          </svg>
                          Use Personal API Token
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div>
                          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            ClickUp Personal API Token
                          </label>
                          <input
                            type="password"
                            value={personalToken}
                            onChange={(e) => setPersonalToken(e.target.value)}
                            placeholder="Enter your ClickUp personal API token"
                            className="w-full mt-1 p-2 border rounded-md dark:bg-gray-800 dark:border-gray-600"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Get your token from ClickUp → Settings → Apps → API Token
                          </p>
                        </div>
                        
                        <div className="flex space-x-2">
                          <Button
                            onClick={handleConnectWithToken}
                            disabled={clickupLoading || !personalToken.trim()}
                            className="flex-1"
                          >
                            {clickupLoading ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <CheckCircle className="h-4 w-4 mr-2" />
                            )}
                            Connect
                          </Button>
                          
                          <Button
                            variant="outline"
                            onClick={() => {
                              setShowTokenInput(false)
                              setPersonalToken('')
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    )}
                    
                    {clickupStatus.error && (
                      <p className="text-sm text-red-600 dark:text-red-400">
                        Error: {clickupStatus.error}
                      </p>
                    )}
                  </div>
                )}
              </div>
              
              <div className="text-xs text-gray-500 dark:text-gray-400">
                <p><strong>What this does:</strong></p>
                <ul className="mt-1 ml-4 list-disc space-y-1">
                  <li>Establishes a secure OAuth connection with your ClickUp account</li>
                  <li>Stores encrypted credentials for future feature development</li>
                  <li>Currently provides connection status only - no active functionality</li>
                  <li>Prepares your account for upcoming project management integrations</li>
                  <li>Can be disconnected at any time to revoke access</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Theme Settings */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Moon className="h-5 w-5" />
              <h3 className="text-lg font-medium">Theme</h3>
            </div>
            <div className="space-y-3 pl-7">
              <div>
                <label className="text-sm font-medium">Appearance</label>
                <select
                  value={settings.appearance.theme}
                  onChange={(e) => updateSetting('appearance', 'theme', e.target.value as 'light' | 'dark')}
                  className="w-full mt-1 p-2 border rounded-md dark:bg-gray-800 dark:border-gray-600"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
            </div>
          </div>

          {/* Privacy Settings */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <h3 className="text-lg font-medium">Privacy</h3>
            </div>
            <div className="space-y-3 pl-7">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Show Online Status</p>
                  <p className="text-sm text-gray-500">Let others see when you're online</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.privacy.showOnlineStatus}
                  onChange={(e) => updateSetting('privacy', 'showOnlineStatus', e.target.checked)}
                  className="h-4 w-4"
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Allow Direct Messages</p>
                  <p className="text-sm text-gray-500">Allow other users to message you directly</p>
                </div>
                <input
                  type="checkbox"
                  checked={settings.privacy.allowDirectMessages}
                  onChange={(e) => updateSetting('privacy', 'allowDirectMessages', e.target.checked)}
                  className="h-4 w-4"
                />
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleLogout}
            disabled={loading}
            className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200 hover:border-red-300"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
          
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={loading}>
              {loading ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 