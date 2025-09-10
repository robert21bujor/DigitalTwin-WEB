'use client'

import { CheckCircle, Loader2, XCircle } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'

export default function GmailCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent multiple callback executions (authorization code can only be used ONCE)
      if (isProcessing) {
        console.log('OAuth callback already processing, ignoring duplicate request')
        return
      }
      setIsProcessing(true)
      
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        if (error) {
          setStatus('error')
          setMessage(`OAuth error: ${error}`)
          return
        }

        if (!code || !state) {
          setStatus('error')
          setMessage('Missing authorization code or state parameter')
          return
        }

        // Extract user_id from state parameter
        // Updated regex to handle complex user IDs with dashes, etc.
        // Captures everything between "user_" and the last "_" (which starts the random token)
        const stateMatch = state.match(/^user_(.+)_[a-f0-9]{32}$/)
        if (!stateMatch) {
          setStatus('error')
          setMessage('Invalid state parameter format')
          return
        }

        const userId = stateMatch[1]

        // Complete OAuth flow
        const response = await fetch('http://localhost:8000/api/gmail/callback', {
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
          setMessage(`Gmail connected successfully for ${result.gmail_email}`)
          
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
          setMessage(result.error || 'Failed to complete OAuth flow')
        }

      } catch (error) {
        setStatus('error')
        setMessage(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
      // Note: Don't reset isProcessing to ensure only one execution per page load
    }

    handleCallback()
  }, [searchParams, router]) // Removed isProcessing from dependencies to prevent re-runs

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="max-w-md w-full mx-auto p-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8 text-center">
          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-4" />
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Connecting Gmail...
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Please wait while we complete the authorization process.
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h1 className="text-xl font-semibold text-green-900 dark:text-green-100 mb-2">
                Gmail Connected!
              </h1>
              <p className="text-green-600 dark:text-green-400 mb-4">
                {message}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Redirecting you back to the application...
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h1 className="text-xl font-semibold text-red-900 dark:text-red-100 mb-2">
                Connection Failed
              </h1>
              <p className="text-red-600 dark:text-red-400 mb-4">
                {message}
              </p>
              <button
                onClick={() => {
                  if (window.opener) {
                    window.close()
                  } else {
                    router.push('/dashboard/manager')
                  }
                }}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
              >
                Close
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
} 