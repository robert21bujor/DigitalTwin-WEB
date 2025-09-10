'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { updatePasswordAndCompleteSetup } from '@/lib/supabase'
import { Eye, EyeOff, Lock, Shield } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface ForcedPasswordResetProps {
  username: string
  email: string
  onPasswordResetComplete: () => void
}

export default function ForcedPasswordReset({ 
  username, 
  email, 
  onPasswordResetComplete 
}: ForcedPasswordResetProps) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  const passwordRequirements = [
    { text: 'At least 8 characters', valid: newPassword.length >= 8 },
    { text: 'Contains uppercase letter', valid: /[A-Z]/.test(newPassword) },
    { text: 'Contains lowercase letter', valid: /[a-z]/.test(newPassword) },
    { text: 'Contains number', valid: /\d/.test(newPassword) },
    { text: 'Contains special character', valid: /[!@#$%^&*(),.?":{}|<>]/.test(newPassword) },
  ]

  const isPasswordValid = passwordRequirements.every(req => req.valid)
  const passwordsMatch = newPassword === confirmPassword && confirmPassword.length > 0

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isPasswordValid) {
      toast.error('Please meet all password requirements')
      return
    }

    if (!passwordsMatch) {
      toast.error('Passwords do not match')
      return
    }

    setIsResetting(true)

    try {
      const { error } = await updatePasswordAndCompleteSetup(newPassword)

      if (error) {
        const errorMessage = (error as any)?.message || 'Unknown error'
        toast.error(`Password reset failed: ${errorMessage}`)
        return
      }

      toast.success('Password updated successfully! Welcome to the platform.')
      onPasswordResetComplete()
    } catch (error) {
      toast.error('Password reset failed. Please try again.')
    } finally {
      setIsResetting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md mx-auto shadow-lg">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center">
            <Shield className="w-8 h-8 text-orange-600" />
          </div>
          <CardTitle className="text-2xl">Password Reset Required</CardTitle>
          <CardDescription className="text-center">
            Welcome <strong>{username}</strong>! For security reasons, you must set a new password before accessing the platform.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handlePasswordReset} className="space-y-6">
            {/* Account Info */}
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-blue-800">
                <p><strong>Account:</strong> {email}</p>
                <p><strong>Username:</strong> {username}</p>
              </div>
            </div>

            {/* New Password */}
            <div className="space-y-2">
              <label htmlFor="newPassword" className="text-sm font-medium flex items-center gap-2">
                <Lock className="w-4 h-4" />
                New Password
              </label>
              <div className="relative">
                <Input
                  id="newPassword"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your new password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  disabled={isResetting}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Password Requirements */}
            {newPassword && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-700">Password Requirements:</p>
                <div className="space-y-1">
                  {passwordRequirements.map((req, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <div className={`w-2 h-2 rounded-full ${req.valid ? 'bg-green-500' : 'bg-gray-300'}`} />
                      <span className={req.valid ? 'text-green-700' : 'text-gray-500'}>
                        {req.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Confirm Password */}
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium">
                Confirm New Password
              </label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm your new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={isResetting}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {confirmPassword && !passwordsMatch && (
                <p className="text-sm text-red-600">Passwords do not match</p>
              )}
            </div>

            <Button 
              type="submit" 
              className="w-full"
              disabled={!isPasswordValid || !passwordsMatch || isResetting}
            >
              {isResetting ? 'Updating Password...' : 'Set New Password & Continue'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Having trouble? Contact your system administrator for assistance.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}