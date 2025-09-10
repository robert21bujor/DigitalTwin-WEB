'use client'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useState, useEffect } from 'react'

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

interface ChangeRoleModalProps {
  user: UserProfile | null
  isOpen: boolean
  onClose: () => void
  onConfirm: (userId: string, role: string, adminRights: string) => Promise<void>
  loading: boolean
}

export default function ChangeRoleModal({ user, isOpen, onClose, onConfirm, loading }: ChangeRoleModalProps) {
  const [selectedRole, setSelectedRole] = useState('')
  const [selectedAdminRights, setSelectedAdminRights] = useState('')

  // Reset form when user changes or modal opens
  useEffect(() => {
    if (user && isOpen) {
      setSelectedRole(user.role)
      setSelectedAdminRights(user.admin_rights)
    }
  }, [user, isOpen])

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
    { value: 'gtm_agent', label: 'GTM Agent' },
    { value: 'competitor_agent', label: 'Competitor Agent' },
    { value: 'launch_agent', label: 'Launch Agent' },
    { value: 'seo_agent', label: 'SEO Agent' },
    { value: 'sem_agent', label: 'SEM Agent' },
    { value: 'landing_agent', label: 'Landing Agent' },
    { value: 'analytics_agent', label: 'Analytics Agent' },
    { value: 'funnel_agent', label: 'Funnel Agent' },
    { value: 'content_agent', label: 'Content Agent' },
    { value: 'brand_agent', label: 'Brand Agent' },
    { value: 'social_agent', label: 'Social Agent' },
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

  const handleSubmit = async () => {
    if (!user || !selectedRole || !selectedAdminRights) return
    
    await onConfirm(user.id, selectedRole, selectedAdminRights)
    onClose()
  }

  const handleClose = () => {
    onClose()
    // Reset form
    if (user) {
      setSelectedRole(user.role)
      setSelectedAdminRights(user.admin_rights)
    }
  }

  if (!user) return null

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle>Change User Role</DialogTitle>
          <DialogDescription>
            Update the role and admin rights for {user.username} ({user.email})
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="space-y-2">
            <label htmlFor="role" className="text-sm font-medium">
              Role
            </label>
            <Select value={selectedRole} onValueChange={setSelectedRole}>
              <SelectTrigger>
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent className="max-h-[300px]">
                {roles.map((role) => (
                  <SelectItem key={role.value} value={role.value}>
                    {role.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label htmlFor="admin_rights" className="text-sm font-medium">
              Admin Rights
            </label>
            <Select value={selectedAdminRights} onValueChange={setSelectedAdminRights}>
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
          </div>

          <div className="mt-4 p-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">
              <strong>Current:</strong> {user.role} with {user.admin_rights} rights
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              <strong>New:</strong> {selectedRole} with {selectedAdminRights} rights
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={loading || !selectedRole || !selectedAdminRights || 
              (selectedRole === user.role && selectedAdminRights === user.admin_rights)}
          >
            {loading ? 'Updating...' : 'Update Role'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}