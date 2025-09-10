'use client'

import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/stores/auth'
import { Shield, Settings } from 'lucide-react'
import { useRouter } from 'next/navigation'

export default function AdminButton() {
  const router = useRouter()
  const { user } = useAuthStore()

  // Only show to system admins and super admins
  if (!user || (user.admin_rights !== 'system_admin' && user.admin_rights !== 'super_admin')) {
    return null
  }

  return (
    <Button
      onClick={() => router.push('/admin/users')}
      variant="outline"
      className="border-red-200 hover:border-red-300 hover:bg-red-50 text-red-700"
    >
      <Shield className="w-4 h-4 mr-2" />
      Admin Panel
    </Button>
  )
}