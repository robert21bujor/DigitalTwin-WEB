'use client'

import ChangeRoleModal from '@/components/admin/ChangeRoleModal'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NavigationHeader } from '@/components/ui/navigation-header'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/stores/auth'
import {
    CheckCircle,
    Key,
    RefreshCw,
    Search,
    Settings,
    Shield,
    Trash2,
    UserCheck,
    UserPlus,
    Users,
    UserX,
    XCircle
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface UserProfile {
  id: string
  auth_user_id: string
  email: string
  username: string
  role: string
  admin_rights: string
  is_active: boolean
  created_at: string
  updated_at: string
  metadata: any
}

interface AuthUser {
  id: string
  email: string
  email_confirmed_at: string | null
  last_sign_in_at: string | null
  created_at: string
}

export default function AdminUsersPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [users, setUsers] = useState<UserProfile[]>([]) // Filtered users for display
  const [allUsers, setAllUsers] = useState<UserProfile[]>([]) // All users for statistics
  const [authUsers, setAuthUsers] = useState<AuthUser[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [changeRoleUser, setChangeRoleUser] = useState<UserProfile | null>(null)
  const [isChangeRoleModalOpen, setIsChangeRoleModalOpen] = useState(false)

  // Check admin permissions
  useEffect(() => {
    if (!user) {
      router.push('/')
      return
    }
    
    if (user.admin_rights !== 'system_admin' && user.admin_rights !== 'super_admin') {
      toast.error('Access denied. System admin privileges required.')
      router.push('/dashboard/manager')
      return
    }
    
    loadUsers()
  }, [user, router])

  const loadUsers = async () => {
    try {
      setLoading(true)
      
      // Use Python service for user listing (more reliable)
      // Get the current session token to pass to the API
      const { data: { session } } = await supabase.auth.getSession()
      
      console.log('🔍 Admin panel: Loading users...')
      console.log('  Session token present:', !!session?.access_token)
      
      const response = await fetch('/api/admin/users-list', {
        headers: {
          'Authorization': session?.access_token ? `Bearer ${session.access_token}` : '',
        },
      })
      
      console.log('📡 API Response:', { 
        status: response.status, 
        statusText: response.statusText,
        ok: response.ok 
      })
      
      const data = await response.json()
      console.log('📄 Response data:', data)
      
      if (!response.ok) {
        const errorMsg = data.error || `HTTP ${response.status}: ${response.statusText}`
        const debugInfo = data.debug ? `\n\nDebug: ${JSON.stringify(data.debug, null, 2)}` : ''
        throw new Error(errorMsg + debugInfo)
      }
      
      if (data.error) {
        const debugInfo = data.debug ? `\n\nDebug: ${JSON.stringify(data.debug, null, 2)}` : ''
        throw new Error(data.error + debugInfo)
      }
      
      // Store all users for statistics and display
      const allProfiles = data.profiles || []
      setAllUsers(allProfiles)
      
      // Show all users including the current user
      setUsers(allProfiles)
      setAuthUsers(data.authUsers || [])
      
    } catch (error: any) {
      console.error('Load users error:', error)
      toast.error(`Failed to load users: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteUser = async (userId: string, authUserId: string) => {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return
    }
    
    try {
      setActionLoading(`delete-${userId}`)
      
      // Delete from auth first
      const { error: authError } = await supabase.auth.admin.deleteUser(authUserId)
      if (authError) throw authError
      
      // Profile should be deleted automatically due to foreign key cascade
      // But let's verify and clean up if needed
      const { error: profileError } = await supabase
        .from('user_profiles')
        .delete()
        .eq('id', userId)
      
      if (profileError && !profileError.message.includes('no rows')) {
        throw profileError
      }
      
      toast.success('User deleted successfully')
      loadUsers()
    } catch (error: any) {
      toast.error(`Failed to delete user: ${error.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleForcePasswordReset = async (authUserId: string, userEmail: string) => {
    try {
      setActionLoading(`password-${authUserId}`)
      
      // Generate temporary password
      const tempPassword = `Temp${Math.random().toString(36).slice(-8)}!`
      
      // Update auth password
      const { error: authError } = await supabase.auth.admin.updateUserById(authUserId, {
        password: tempPassword
      })
      
      if (authError) throw authError
      
      // Update profile metadata
      const { error: profileError } = await supabase
        .from('user_profiles')
        .update({
          metadata: {
            requires_password_reset: true,
            temp_password_generated: true,
            temp_password_created_at: new Date().toISOString(),
            created_via: 'admin_force_reset'
          }
        })
        .eq('auth_user_id', authUserId)
      
      if (profileError) throw profileError
      
      // Show password to admin
      navigator.clipboard.writeText(tempPassword)
      toast.success(`Temporary password set and copied to clipboard: ${tempPassword}`)
      
      loadUsers()
    } catch (error: any) {
      toast.error(`Failed to reset password: ${error.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleToggleActive = async (userId: string, currentStatus: boolean) => {
    try {
      setActionLoading(`toggle-${userId}`)
      
      const { error } = await supabase
        .from('user_profiles')
        .update({ is_active: !currentStatus })
        .eq('id', userId)
      
      if (error) throw error
      
      toast.success(`User ${!currentStatus ? 'activated' : 'deactivated'} successfully`)
      loadUsers()
    } catch (error: any) {
      toast.error(`Failed to update user status: ${error.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleChangeRole = (userProfile: UserProfile) => {
    setChangeRoleUser(userProfile)
    setIsChangeRoleModalOpen(true)
  }

  const handleChangeRoleSubmit = async (userId: string, role: string, adminRights: string) => {
    try {
      setActionLoading(`role-${userId}`)
      
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role, adminRights }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to update user role')
      }

      toast.success('User role updated successfully')
      loadUsers()
    } catch (error: any) {
      toast.error(`Failed to update user role: ${error.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  const filteredUsers = users.filter(user =>
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.role.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getAuthUser = (authUserId: string) => {
    return authUsers.find(au => au.id === authUserId)
  }

  const getRoleBadgeColor = (role: string) => {
    if (role.includes('cmo') || role.includes('ceo')) return 'bg-purple-100 text-purple-800'
    if (role.includes('manager')) return 'bg-blue-100 text-blue-800'
    if (role.includes('agent')) return 'bg-green-100 text-green-800'
    return 'bg-gray-100 text-gray-800'
  }

  const getAdminBadgeColor = (adminRights: string) => {
    switch (adminRights) {
      case 'system_admin': return 'bg-red-100 text-red-800'
      case 'super_admin': return 'bg-orange-100 text-orange-800'
      case 'admin': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-600'
    }
  }

  if (!user || (user.admin_rights !== 'system_admin' && user.admin_rights !== 'super_admin')) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationHeader title="User Management" />
      
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Users className="w-8 h-8 text-blue-600" />
              User Management
            </h1>
            <p className="text-gray-600 mt-1">Manage system users, roles, and permissions</p>
          </div>
        
        <div className="flex gap-2">
          <Button
            onClick={loadUsers}
            variant="outline"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button onClick={() => router.push('/admin/users/create')}>
            <UserPlus className="w-4 h-4 mr-2" />
            Add User
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Users</p>
                <p className="text-2xl font-bold">{allUsers.length}</p>
              </div>
              <Users className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active Users</p>
                <p className="text-2xl font-bold text-green-600">
                  {allUsers.filter(u => u.is_active).length}
                </p>
              </div>
              <UserCheck className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Inactive Users</p>
                <p className="text-2xl font-bold text-red-600">
                  {allUsers.filter(u => !u.is_active).length}
                </p>
              </div>
              <UserX className="w-8 h-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Admins</p>
                <p className="text-2xl font-bold text-purple-600">
                  {allUsers.filter(u => u.admin_rights !== 'none').length}
                </p>
              </div>
              <Shield className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search users by email, username, or role..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <CardTitle>Users ({filteredUsers.length})</CardTitle>
          <CardDescription>
            Manage user accounts, roles, and permissions. Your own account ({user?.username}) is excluded from this list.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
              <span className="ml-2">Loading users...</span>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No users found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">User</th>
                    <th className="text-left p-2">Role</th>
                    <th className="text-left p-2">Admin Rights</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">Last Sign In</th>
                    <th className="text-left p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((userProfile) => {
                    const authUser = getAuthUser(userProfile.auth_user_id)
                    return (
                      <tr key={userProfile.id} className="border-b hover:bg-gray-50">
                        <td className="p-2">
                          <div>
                            <div className="font-medium">
                              {userProfile.username}
                              {userProfile.email === user?.email && (
                                <span className="ml-2 text-sm text-blue-600 font-normal">(You)</span>
                              )}
                            </div>
                            <div className="text-sm text-gray-600">{userProfile.email}</div>
                          </div>
                        </td>
                        <td className="p-2">
                          <Badge className={getRoleBadgeColor(userProfile.role)}>
                            {userProfile.role.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="p-2">
                          <Badge className={getAdminBadgeColor(userProfile.admin_rights)}>
                            {userProfile.admin_rights.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="p-2">
                          <div className="flex items-center gap-2">
                            {userProfile.is_active ? (
                              <CheckCircle className="w-4 h-4 text-green-500" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-500" />
                            )}
                            <span className={userProfile.is_active ? 'text-green-700' : 'text-red-700'}>
                              {userProfile.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </td>
                        <td className="p-2">
                          <div className="text-sm">
                            {authUser?.last_sign_in_at 
                              ? new Date(authUser.last_sign_in_at).toLocaleDateString()
                              : 'Never'
                            }
                          </div>
                        </td>
                        <td className="p-2">
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleToggleActive(userProfile.id, userProfile.is_active)}
                              disabled={actionLoading === `toggle-${userProfile.id}`}
                            >
                              {userProfile.is_active ? 'Deactivate' : 'Activate'}
                            </Button>
                            
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleChangeRole(userProfile)}
                              disabled={actionLoading === `role-${userProfile.id}`}
                            >
                              <Settings className="w-4 h-4 mr-1" />
                              Change Role
                            </Button>

                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleForcePasswordReset(userProfile.auth_user_id, userProfile.email)}
                              disabled={actionLoading === `password-${userProfile.auth_user_id}`}
                            >
                              <Key className="w-4 h-4 mr-1" />
                              Reset Password
                            </Button>
                            
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDeleteUser(userProfile.id, userProfile.auth_user_id)}
                              disabled={actionLoading === `delete-${userProfile.id}` || userProfile.id === user?.id}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      </div>

      <ChangeRoleModal
        user={changeRoleUser}
        isOpen={isChangeRoleModalOpen}
        onClose={() => {
          setIsChangeRoleModalOpen(false)
          setChangeRoleUser(null)
        }}
        onConfirm={handleChangeRoleSubmit}
        loading={actionLoading?.startsWith('role-') || false}
      />
    </div>
  )
}