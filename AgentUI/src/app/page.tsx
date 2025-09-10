'use client'

import ForcedPasswordReset from '@/components/auth/ForcedPasswordReset'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/auth'
import { BarChart3, Bot, Loader2, MessageSquare, Shield, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'

export default function HomePage() {
  const router = useRouter()
  const { user, isLoading, isAuthenticated, login, initialize, refreshUser } = useAuthStore()
  const [showLogin, setShowLogin] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [showPasswordReset, setShowPasswordReset] = useState(false)
  const initializeRef = useRef(false)

  useEffect(() => {
    // Only initialize once to prevent infinite loops
    if (!initializeRef.current) {
      initializeRef.current = true
      initialize()
    }
  }, []) // Remove initialize dependency to prevent loop

  useEffect(() => {
    if (isAuthenticated && user) {
      // Check if user needs to reset password (exception for username "admin")
      if ((user.requires_password_reset || user.is_first_login) && user.username !== 'admin') {
        setShowPasswordReset(true)
        return
      }
      
      // All authenticated users go to manager dashboard
      router.push('/dashboard/manager')
    }
  }, [isAuthenticated, user, router])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!email || !password) {
      toast.error('Please enter both email and password')
      return
    }

    setIsLoggingIn(true)
    
    try {
      const result = await login(email, password)
      
      if (result.success) {
        if (result.requiresPasswordReset) {
          toast.success('Login successful! Please set a new password.')
          setShowPasswordReset(true)
        } else {
          toast.success('Login successful!')
          // Redirect happens in useEffect above
        }
      } else {
        toast.error('Invalid credentials')
      }
    } catch (error) {
      toast.error('Login failed. Please try again.')
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handlePasswordResetComplete = async () => {
    // Refresh user data and redirect to dashboard
    await refreshUser()
    setShowPasswordReset(false)
    toast.success('Welcome to the platform!')
    router.push('/dashboard/manager')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // Show password reset screen if user needs to reset password
  if (showPasswordReset && user) {
    return (
      <ForcedPasswordReset
        username={user.username}
        email={user.email}
        onPasswordResetComplete={handlePasswordResetComplete}
      />
    )
  }

  if (showLogin) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <Bot className="h-12 w-12 text-primary" />
            </div>
            <CardTitle className="text-2xl">Agent Communication</CardTitle>
            <CardDescription>
              Sign in to access your agent interface
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoggingIn}
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoggingIn}
                />
              </div>
              <Button 
                type="submit" 
                className="w-full" 
                disabled={isLoggingIn}
              >
                {isLoggingIn ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>
            
            {/* Forgot Password Link */}
            <div className="mt-3 text-center">
              <a 
                href="/auth/reset-password"
                className="text-sm text-blue-600 hover:text-blue-800 underline"
              >
                Forgot your password?
              </a>
            </div>
            
            <div className="mt-4 text-center">
              <Button
                variant="ghost"
                onClick={() => setShowLogin(false)}
                disabled={isLoggingIn}
              >
                Back to home
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Navigation */}
      <nav className="border-b bg-white/80 backdrop-blur-sm dark:bg-gray-900/80">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Bot className="h-8 w-8 text-primary" />
            <h1 className="text-xl font-bold">Agent Communication</h1>
          </div>
          <Button onClick={() => setShowLogin(true)}>
            Sign In
          </Button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Universal Agent Communication System
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 leading-relaxed">
            Connect with AI agents across your organization. Real-time communication, 
            role-based access, and intelligent routing for seamless collaboration.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" onClick={() => setShowLogin(true)}>
              Get Started
            </Button>
            <Button size="lg" variant="outline">
              Learn More
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="text-center mb-16">
          <h3 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Powerful Features
          </h3>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Everything you need for agent communication and management
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <Card className="text-center border-0 shadow-lg">
            <CardContent className="pt-8">
              <MessageSquare className="h-12 w-12 text-blue-500 mx-auto mb-4" />
              <h4 className="text-lg font-semibold mb-2">Real-time Chat</h4>
              <p className="text-gray-600 dark:text-gray-300">
                Instant messaging with AI agents and human colleagues
              </p>
            </CardContent>
          </Card>

          <Card className="text-center border-0 shadow-lg">
            <CardContent className="pt-8">
              <Users className="h-12 w-12 text-green-500 mx-auto mb-4" />
              <h4 className="text-lg font-semibold mb-2">Role-based Access</h4>
              <p className="text-gray-600 dark:text-gray-300">
                Secure access control based on organizational roles
              </p>
            </CardContent>
          </Card>

          <Card className="text-center border-0 shadow-lg">
            <CardContent className="pt-8">
              <BarChart3 className="h-12 w-12 text-purple-500 mx-auto mb-4" />
              <h4 className="text-lg font-semibold mb-2">Analytics Dashboard</h4>
              <p className="text-gray-600 dark:text-gray-300">
                Comprehensive insights and performance metrics
              </p>
            </CardContent>
          </Card>

          <Card className="text-center border-0 shadow-lg">
            <CardContent className="pt-8">
              <Shield className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h4 className="text-lg font-semibold mb-2">Enterprise Security</h4>
              <p className="text-gray-600 dark:text-gray-300">
                Bank-grade security with Supabase authentication
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-white dark:bg-gray-900 py-8">
        <div className="container mx-auto px-4 text-center text-gray-600 dark:text-gray-400">
          <p>&copy; 2024 Agent Communication System. Built with Next.js and Supabase.</p>
        </div>
      </footer>
    </div>
  )
} 