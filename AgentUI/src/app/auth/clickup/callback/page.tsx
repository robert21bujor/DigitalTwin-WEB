'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function ClickUpCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState<string>('')
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent multiple callback executions (authorization code can only be used ONCE)
      if (isProcessing) {
        return
      }
      setIsProcessing(true)
      
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        if (error) {
          setStatus('error')
          setMessage(`ClickUp OAuth error: ${error}`)
          return
        }

        if (!code) {
          setStatus('error')
          setMessage('Missing authorization code')
          return
        }

        let userId = null

        // Get user ID quickly from OAuth-specific storage
        userId = localStorage.getItem('clickup-oauth-user-id')
        
        // Clean up the temporary storage for security
        if (userId) {
          localStorage.removeItem('clickup-oauth-user-id')
        }
        
        // Fallback: try to get user ID from main auth store
        if (!userId) {
          try {
            const authData = localStorage.getItem('auth-store')
            if (authData) {
              const parsed = JSON.parse(authData)
              if (parsed?.state?.user?.id) {
                userId = parsed.state.user.id
              }
            }
          } catch (e) {
            // Invalid JSON or missing data
          }
        }

        if (!userId) {
          setStatus('error')
          setMessage('Could not determine user ID for OAuth callback')
          return
        }

        // Complete OAuth flow
        const response = await fetch('http://localhost:8000/api/clickup/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            code: code,
            state: state
          })
        })

        const result = await response.json()

        if (result.success) {
          setStatus('success')
          setMessage(`ClickUp connected successfully for ${result.clickup_username || result.clickup_email || 'your account'}`)
          
          // Redirect back to the application after 2 seconds
          setTimeout(() => {
            window.close() // Close OAuth popup
            // If not in popup, redirect to dashboard
            if (window.opener) {
              window.close()
            } else {
              router.push('/dashboard/manager')
            }
          }, 2000)
        } else {
          setStatus('error')
          setMessage(result.error || 'Failed to complete ClickUp OAuth flow')
        }

      } catch (error) {
        setStatus('error')
        setMessage(`Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    }

    handleCallback()
  }, [searchParams, router, isProcessing])

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="text-center">
            {status === 'loading' && (
              <>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                <h2 className="text-lg font-medium text-gray-900 mb-2">
                  Connecting ClickUp...
                </h2>
                <p className="text-sm text-gray-600">
                  Please wait while we complete the authentication process.
                </p>
              </>
            )}
            
            {status === 'success' && (
              <>
                <div className="rounded-full bg-green-100 p-3 w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                  <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className="text-lg font-medium text-green-900 mb-2">
                  ClickUp Connected!
                </h2>
                <p className="text-sm text-green-700">
                  {message}
                </p>
                <p className="text-xs text-gray-500 mt-2">
                  This window will close automatically...
                </p>
              </>
            )}
            
            {status === 'error' && (
              <>
                <div className="rounded-full bg-red-100 p-3 w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                  <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <h2 className="text-lg font-medium text-red-900 mb-2">
                  Connection Failed
                </h2>
                <p className="text-sm text-red-700 mb-4">
                  {message}
                </p>
                <button
                  onClick={() => window.close()}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  Close Window
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
