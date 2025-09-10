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
      // Prevent multiple callback executions
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

        // Get user ID from localStorage (stored before OAuth popup opened)
        let userId = localStorage.getItem('clickup-oauth-user-id')
        
        // If not in localStorage, try to get from parent window (fallback)
        if (!userId && window.opener) {
          try {
            const parentAuth = window.opener.useAuthStore?.getState?.()
            if (parentAuth?.user?.id) {
              userId = parentAuth.user.id
            }
          } catch (e) {
            // Ignore errors accessing parent window
          }
        }
        
        if (!userId) {
          setStatus('error')
          setMessage('Could not determine user ID for OAuth callback')
          return
        }

        // Complete OAuth flow by calling backend
        const response = await fetch('http://localhost:8000/api/clickup/callback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            user_id: userId,
            code: code
          })
        })

        const result = await response.json()

        if (result.success) {
          setStatus('success')
          setMessage(`ClickUp connected successfully!`)
          
          // Notify parent window if this is a popup
          if (window.opener) {
            window.opener.postMessage({
              type: 'clickup-oauth-success',
              data: result
            }, '*')
          }
          
          // Redirect back to the application after 2 seconds
          setTimeout(() => {
            if (window.opener) {
              window.close()
            } else {
              router.push('/dashboard/manager')
            }
          }, 2000)
        } else {
          setStatus('error')
          setMessage(`Connection failed: ${result.error || 'Unknown error'}`)
          
          // Notify parent window of error
          if (window.opener) {
            window.opener.postMessage({
              type: 'clickup-oauth-error',
              error: result.error || 'Unknown error'
            }, '*')
          }
        }
        
      } catch (error) {
        setStatus('error')
        setMessage(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
        
        // Notify parent window of error
        if (window.opener) {
          window.opener.postMessage({
            type: 'clickup-oauth-error',
            error: error instanceof Error ? error.message : 'Network error'
          }, '*')
        }
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
              <div>
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                <h2 className="mt-4 text-lg font-medium text-gray-900">Connecting ClickUp...</h2>
                <p className="mt-2 text-sm text-gray-600">Please wait while we complete the connection.</p>
              </div>
            )}
            
            {status === 'success' && (
              <div>
                <div className="rounded-full bg-green-100 p-3 mx-auto w-16 h-16 flex items-center justify-center">
                  <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                  </svg>
                </div>
                <h2 className="mt-4 text-lg font-medium text-gray-900">✅ Success!</h2>
                <p className="mt-2 text-sm text-gray-600">{message}</p>
                <p className="mt-1 text-xs text-gray-500">This window will close automatically...</p>
              </div>
            )}
            
            {status === 'error' && (
              <div>
                <div className="rounded-full bg-red-100 p-3 mx-auto w-16 h-16 flex items-center justify-center">
                  <svg className="h-8 w-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
                  </svg>
                </div>
                <h2 className="mt-4 text-lg font-medium text-gray-900">❌ Connection Failed</h2>
                <p className="mt-2 text-sm text-gray-600">{message}</p>
                <button
                  onClick={() => window.close()}
                  className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded"
                >
                  Close Window
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
