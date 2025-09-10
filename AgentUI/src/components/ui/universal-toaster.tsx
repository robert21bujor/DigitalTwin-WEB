'use client'

import { X } from 'lucide-react'
import React, { useState } from 'react'
import toast, { Toaster } from 'react-hot-toast'

// Universal Toast Component with Close Button
const UniversalToast = ({ t, message, type }: { t: any, message: string, type: 'success' | 'error' | 'loading' | 'default' }) => {
  const [isVisible, setIsVisible] = useState(true)

  const handleClose = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    // Immediately hide the toast
    setIsVisible(false)
    
    // Also dismiss from toast library
    setTimeout(() => {
      toast.dismiss(t.id)
    }, 0)
  }

  const handleNotificationClick = () => {
    setIsVisible(false)
    setTimeout(() => {
      toast.dismiss(t.id)
    }, 0)
  }

  // Don't render if not visible
  if (!isVisible) {
    return null
  }

  const getStyles = () => {
    const baseStyles = {
      background: '#10b981',
      color: 'white',
      borderRadius: '8px',
      boxShadow: '0 4px 12px rgba(16, 185, 129, 0.25)',
      padding: '12px 40px 12px 16px',
      fontWeight: '500',
      position: 'relative' as const,
      minWidth: '300px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      cursor: 'pointer',
    }

    switch (type) {
      case 'success':
        return { ...baseStyles, background: '#10b981', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.25)' }
      case 'error':
        return { ...baseStyles, background: '#ef4444', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.25)' }
      case 'loading':
        return { ...baseStyles, background: '#3b82f6', boxShadow: '0 4px 12px rgba(59, 130, 246, 0.25)' }
      default:
        return {
          ...baseStyles,
          background: 'hsl(var(--background))',
          color: 'hsl(var(--foreground))',
          border: '1px solid hsl(var(--border))',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        }
    }
  }

  return (
    <div style={getStyles()} onClick={handleNotificationClick}>
      <span>{message}</span>
      <button
        onClick={handleClose}
        type="button"
        aria-label="Close notification"
        style={{
          position: 'absolute',
          top: '4px',
          right: '4px',
          width: '32px',
          height: '32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(0, 0, 0, 0.15)',
          border: '2px solid rgba(255, 255, 255, 0.3)',
          borderRadius: '50%',
          cursor: 'pointer',
          color: 'white',
          opacity: 0.9,
          transition: 'all 0.1s ease',
          zIndex: 1000,
          fontSize: '18px',
          fontWeight: 'bold',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.opacity = '1'
          e.currentTarget.style.background = 'rgba(0, 0, 0, 0.3)'
          e.currentTarget.style.transform = 'scale(1.15)'
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.6)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.opacity = '0.9'
          e.currentTarget.style.background = 'rgba(0, 0, 0, 0.15)'
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.3)'
        }}
      >
        <X size={18} strokeWidth={3} />
      </button>
    </div>
  )
}

// Universal Toaster Component
export const UniversalToaster = () => {
  return (
    <Toaster 
      position="top-right"
      toastOptions={{
        duration: 4000,
      }}
    >
      {(t) => {
        // Determine the toast type and message
        let type: 'success' | 'error' | 'loading' | 'default' = 'default'
        let message = ''
        
        if (t.type === 'success') {
          type = 'success'
          message = typeof t.message === 'string' ? t.message : 'Success!'
        } else if (t.type === 'error') {
          type = 'error'
          message = typeof t.message === 'string' ? t.message : 'Error!'
        } else if (t.type === 'loading') {
          type = 'loading'
          message = typeof t.message === 'string' ? t.message : 'Loading...'
        } else {
          message = typeof t.message === 'string' ? t.message : 'Notification'
        }
        
        return <UniversalToast t={t} message={message} type={type} />
      }}
    </Toaster>
  )
}
