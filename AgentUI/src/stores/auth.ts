import { getCurrentUser, signIn, supabase, signOut as supabaseSignOut } from '@/lib/supabase'
import { logError } from '@/lib/utils'
import { User } from '@/types'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  isInitializing: boolean
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<{ success: boolean; requiresPasswordReset: boolean }>
  logout: () => Promise<void>
  initialize: () => Promise<void>
  clearError: () => void
  setUser: (user: User | null) => void
  updateUserTheme: (theme: 'light' | 'dark') => void
  refreshUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: false,
      isAuthenticated: false,
      isInitializing: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        
        try {
          const { data, error } = await signIn(email, password)
          
          if (error) {
            set({ error: error.message, isLoading: false })
            return { success: false, requiresPasswordReset: false }
          }

          if (data.user) {
            // Get the full user profile
            const userProfile = await getCurrentUser()
            
            if (userProfile) {
              set({ 
                user: userProfile, 
                isAuthenticated: true, 
                isLoading: false,
                error: null 
              })
              
              // Return login success with password reset flag (exception for username "admin")
              return {
                success: true,
                requiresPasswordReset: (userProfile.requires_password_reset || userProfile.is_first_login) && userProfile.username !== 'admin'
              }
            }
          }
          
          set({ error: 'Failed to load user profile', isLoading: false })
          return { success: false, requiresPasswordReset: false }
          
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed'
          logError(error, 'AuthStore.login')
          set({ error: errorMessage, isLoading: false })
          return { success: false, requiresPasswordReset: false }
        }
      },

      logout: async () => {
        set({ isLoading: true })
        
        try {
          // Clear Supabase session with timeout
          const signOutPromise = supabaseSignOut()
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Logout timeout')), 5000)
          })
          
          const { error: signOutError } = await Promise.race([signOutPromise, timeoutPromise]) as any
          if (signOutError) {
            console.warn('Supabase signOut error:', signOutError)
          }
          
          // Clear local storage data
          if (typeof window !== 'undefined') {
            try {
              // Clear any additional cached data
              localStorage.removeItem('conversation-cache')
              localStorage.removeItem('agent-cache')
              localStorage.removeItem('recent-searches')
              // Clear auth store data manually as backup
              localStorage.removeItem('auth-store')
            } catch (storageError) {
              console.warn('LocalStorage clear error:', storageError)
            }
          }
          
          // Force clear the state regardless of any errors above
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null 
          })
          
        } catch (error) {
          logError(error, 'AuthStore.logout')
          // Force logout even if everything fails
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
            error: null 
          })
        }
      },

      initialize: async () => {
        const state = get()
        
        // Prevent concurrent initialization calls
        if (state.isInitializing || state.isLoading) {
          console.log('🔄 Auth already initializing, skipping...')
          return
        }
        
        set({ isLoading: true, isInitializing: true })
        
        try {
          console.log('🔄 Initializing auth with Supabase...')
          
          // Add timeout to prevent hanging on session check (increased to 10s)
          const sessionPromise = supabase.auth.getSession()
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Session check timeout')), 10000)
          })
          
          console.log('📡 Checking existing session...')
          const { data: { session } } = await Promise.race([sessionPromise, timeoutPromise]) as any
          console.log('✅ Session check completed:', session ? 'Session found' : 'No session')
          
          if (session?.user) {
            try {
              console.log('👤 Getting current user info...')
              // Add timeout to getCurrentUser as well (increased to 10s)
              const userPromise = getCurrentUser()
              const userTimeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Get user timeout')), 10000)
              })
              
              const userProfile = await Promise.race([userPromise, userTimeoutPromise]) as User | null
              
              if (userProfile) {
              set({ 
                user: userProfile, 
                isAuthenticated: true, 
                isLoading: false,
                isInitializing: false
              })
              
              // Apply saved theme
              const typedProfile = userProfile as User
              if (typedProfile.theme) {
                if (typedProfile.theme === 'dark') {
                  document.documentElement.classList.add('dark')
                  document.documentElement.style.backgroundColor = '#000000'
                } else {
                  document.documentElement.classList.remove('dark')
                  document.documentElement.style.backgroundColor = ''
                }
              }
            } else {
              set({ 
                user: null, 
                isAuthenticated: false, 
                isLoading: false,
                isInitializing: false
              })
            }
            } catch (userError) {
              console.warn('Failed to get user profile:', userError)
              set({ 
                user: null, 
                isAuthenticated: false, 
                isLoading: false,
                isInitializing: false
              })
            }
          } else {
            console.log('📭 No existing session found - user needs to login')
            set({ 
              user: null, 
              isAuthenticated: false, 
              isLoading: false,
              isInitializing: false
            })
          }
        } catch (error) {
          console.log('⚠️ Auth initialization issue:', error)
          
          // If it's just a timeout or network issue, treat as "no session" rather than error
          if (error instanceof Error && (error.message.includes('timeout') || error.message.includes('fetch'))) {
            console.log('🔄 Treating connection issue as "no session" - user can still login')
            set({ 
              user: null, 
              isAuthenticated: false, 
              isLoading: false,
              isInitializing: false
            })
          } else {
            console.error('❌ Unexpected auth error:', error)
          // Always ensure loading state is cleared
          set({ 
            user: null, 
            isAuthenticated: false, 
            isLoading: false,
              isInitializing: false,
            error: null
          })
          }
        }
      },

      clearError: () => set({ error: null }),
      
      setUser: (user: User | null) => set({ 
        user, 
        isAuthenticated: !!user 
      }),

      updateUserTheme: (theme: 'light' | 'dark') => {
        const currentUser = get().user
        if (currentUser) {
          const updatedUser = { ...currentUser, theme }
          set({ user: updatedUser })
          
          // Apply theme to document
          if (theme === 'dark') {
            document.documentElement.classList.add('dark')
            document.documentElement.style.backgroundColor = '#000000'
          } else {
            document.documentElement.classList.remove('dark')
            document.documentElement.style.backgroundColor = ''
          }
        }
      },

      refreshUser: async () => {
        try {
          const userProfile = await getCurrentUser()
          if (userProfile) {
            set({ user: userProfile })
          }
        } catch (error) {
          console.error('Failed to refresh user:', error)
        }
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Listen to auth state changes
supabase.auth.onAuthStateChange(async (event, session) => {
  console.log('🔄 Auth state change event:', event)
  
  if (event === 'SIGNED_IN' && session?.user) {
    // Don't call initialize() here - just update state directly to avoid loops
    console.log('✅ User signed in via auth listener')
    // The initialize() in the component will handle the full setup
  } else if (event === 'SIGNED_OUT') {
    console.log('👋 User signed out')
    useAuthStore.setState({ 
      user: null, 
      isAuthenticated: false,
      isLoading: false,
      isInitializing: false,
      error: null 
    })
  }
}) 