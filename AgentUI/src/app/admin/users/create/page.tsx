'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NavigationHeader } from '@/components/ui/navigation-header'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/stores/auth'
import { Loader2, UserPlus } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function CreateUserPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    email: '',
    role: '',
    adminRights: 'none'
  })

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
  }, [user, router])

  // Centralized role definitions - keep in sync with Authentication/role_constants.py
  const roles = [
    { value: 'none', label: 'No Specific Role' },
    { value: 'cmo', label: 'Chief Marketing Officer' },
    { value: 'ceo', label: 'Chief Executive Officer' },
    { value: 'cto', label: 'Chief Technology Officer' },
    { value: 'cfo', label: 'Chief Financial Officer' },
    { value: 'product_manager', label: 'Product Manager' },
    { value: 'digital_manager', label: 'Digital Manager' },
    { value: 'content_manager', label: 'Content Manager' },
    { value: 'business_dev_manager', label: 'Business Development Manager' },
    { value: 'operations_manager', label: 'Operations Manager' },
    { value: 'positioning_agent', label: 'Positioning Agent' },
    { value: 'persona_agent', label: 'Persona Agent' },
    { value: 'gtm_agent', label: 'Go-to-Market Agent' },
    { value: 'competitor_agent', label: 'Competitor Agent' },
    { value: 'launch_agent', label: 'Launch Agent' },
    { value: 'seo_agent', label: 'SEO Agent' },
    { value: 'sem_agent', label: 'SEM Agent' },
    { value: 'landing_agent', label: 'Landing Page Agent' },
    { value: 'analytics_agent', label: 'Analytics Agent' },
    { value: 'funnel_agent', label: 'Funnel Agent' },
    { value: 'content_agent', label: 'Content Agent' },
    { value: 'brand_agent', label: 'Brand Agent' },
    { value: 'social_agent', label: 'Social Media Agent' },
    { value: 'community_agent', label: 'Community Agent' },
    { value: 'ipm_agent', label: 'IPM Agent' },
    { value: 'bdm_agent', label: 'BDM Agent' },
    { value: 'presales_engineer_agent', label: 'Presales Engineer Agent' },
    { value: 'advisory_board_manager_agent', label: 'Advisory Board Manager Agent' },
    { value: 'head_of_operations_agent', label: 'Head of Operations Agent' },
    { value: 'senior_csm_agent', label: 'Senior CSM Agent' },
    { value: 'senior_delivery_consultant_agent', label: 'Senior Delivery Consultant Agent' },
    { value: 'delivery_consultant_bg_agent', label: 'Delivery Consultant (BG) Agent' },
    { value: 'delivery_consultant_hu_agent', label: 'Delivery Consultant (HU) Agent' },
    { value: 'delivery_consultant_en_agent', label: 'Delivery Consultant (EN) Agent' },
    { value: 'reporting_manager_agent', label: 'Reporting Manager Agent' },
    { value: 'reporting_specialist_agent', label: 'Reporting Specialist Agent' },
    { value: 'legal_agent', label: 'Legal Agent' },
    { value: 'employee', label: 'Employee' },
    { value: 'contractor', label: 'Contractor' },
    { value: 'intern', label: 'Intern' }
  ]

  const adminRights = [
    { value: 'none', label: 'No Admin Rights' },
    { value: 'admin', label: 'Basic Admin' },
    { value: 'super_admin', label: 'Super Admin' },
    { value: 'system_admin', label: 'System Admin' }
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.email || !formData.role) {
      toast.error('Please fill in all required fields')
      return
    }

    if (!formData.email.includes('@')) {
      toast.error('Please enter a valid email address')
      return
    }

    setLoading(true)

    try {
      // Generate temporary password
      const tempPassword = `Temp${Math.random().toString(36).slice(-8)}!`
      
      // Get the current session token to pass to the API
      const { data: { session } } = await supabase.auth.getSession()
      
      // Use Python registration service (same as admin_register.py)
      const response = await fetch('/api/admin/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': session?.access_token ? `Bearer ${session.access_token}` : '',
        },
        body: JSON.stringify({
          email: formData.email,
          password: tempPassword,
          role: formData.role,
          adminRights: formData.adminRights
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const result = await response.json()
      
      if (!result.success) {
        throw new Error(result.error || 'Registration failed')
      }

      // Copy password to clipboard
      await navigator.clipboard.writeText(tempPassword)

      toast.success(`User created successfully via Python service! Temporary password copied to clipboard: ${tempPassword}`)
      
      // Show additional info if available
      if (result.user) {
        console.log('Created user:', result.user)
      }
      
      // Redirect back to users list
      router.push('/admin/users')

    } catch (error: any) {
      console.error('Create user error:', error)
      toast.error(`Failed to create user: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (!user || (user.admin_rights !== 'system_admin' && user.admin_rights !== 'super_admin')) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationHeader 
        title="Create New User" 
        showBackButton={true} 
        backUrl="/admin/users" 
      />
      
      <div className="container mx-auto p-6 max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <UserPlus className="w-8 h-8 text-blue-600" />
              Create New User
            </h1>
            <p className="text-gray-600 mt-1">Add a new user to the system</p>
          </div>
        </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>User Information</CardTitle>
          <CardDescription>
            Enter the details for the new user. A temporary password will be generated and the user will be required to change it on first login.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email Address <span className="text-red-500">*</span>
              </label>
              <Input
                id="email"
                type="email"
                placeholder="user@company.com"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                required
                disabled={loading}
              />
            </div>

            {/* Username auto-generated from email */}
            {formData.email && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-600">
                  Username (auto-generated)
                </label>
                <div className="p-3 bg-gray-50 rounded-md border">
                  <code className="text-sm text-gray-700">
                    {formData.email.split('@')[0]}
                  </code>
                </div>
                <p className="text-xs text-gray-500">
                  Username is automatically generated from email prefix and used for system identification
                </p>
              </div>
            )}

            {/* Role */}
            <div className="space-y-2">
              <label htmlFor="role" className="text-sm font-medium">
                Role <span className="text-red-500">*</span>
              </label>
              <Select value={formData.role} onValueChange={(value) => handleInputChange('role', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Admin Rights */}
            <div className="space-y-2">
              <label htmlFor="adminRights" className="text-sm font-medium">
                Admin Rights
              </label>
              <Select value={formData.adminRights} onValueChange={(value) => handleInputChange('adminRights', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select admin rights" />
                </SelectTrigger>
                <SelectContent>
                  {adminRights.map((right) => (
                    <SelectItem key={right.value} value={right.value}>
                      {right.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500">
                Admin rights are separate from company roles and grant system-level permissions
              </p>
            </div>

            {/* Security Notice */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-orange-100 flex items-center justify-center mt-0.5">
                  <span className="text-orange-600 text-xs font-bold">!</span>
                </div>
                <div className="text-sm">
                  <p className="font-medium text-orange-800">Security Notice</p>
                  <p className="text-orange-700 mt-1">
                    A temporary password will be generated and copied to your clipboard. 
                    The user will be required to change this password on their first login.
                  </p>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div className="flex gap-4">
              <Button type="submit" disabled={loading} className="flex-1">
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating User...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4 mr-2" />
                    Create User
                  </>
                )}
              </Button>
              
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => router.push('/admin/users')}
                disabled={loading}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
      </div>
    </div>
  )
}