'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { TokenStorage } from '@/lib/api'
import { authApi } from '@/lib/api'
import { User, LoginRequest, LoadingState, AuthExpiredError, AuthInvalidError, NetworkError } from '@/types'

// Auth context types
interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null
  login: (credentials: LoginRequest) => Promise<boolean>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  clearError: () => void
  handleAuthExpired: () => void
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Auth provider props
interface AuthProviderProps {
  children: ReactNode
}

// Custom hook to use auth context
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Auth provider component
export function AuthProvider({ children }: AuthProviderProps): React.JSX.Element {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  // Wrapper for setError to track all calls
  const setErrorWithLog = (value: string | null) => {
    console.log('🔴 SET ERROR CALLED:', value, 'Stack trace:', new Error().stack?.split('\n')[2])
    setError(value)
  }

  // Clear error helper
  const clearError = () => {
    console.log('🔴 CLEAR ERROR CALLED from clearError()')
    setErrorWithLog(null)
  }

  // Handle auth expiration - centralized navigation logic
  const handleAuthExpired = () => {
    TokenStorage.clearTokens()
    setUser(null)
    setErrorWithLog('Session expired. Please login again.')
    router.push('/login')
  }

  // Check if user is authenticated
  const checkAuthStatus = (): boolean => {
    const hasToken = TokenStorage.getAccessToken() !== null
    console.log('🔐 CHECK AUTH: TokenStorage.getAccessToken() !== null =', hasToken)
    return hasToken
  }

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      console.log('🔧 INIT: AuthProvider initialization started')
      console.log('🔧 INIT: Current error value in closure:', error)
      try {
        setIsLoading(true)
        // Don't clear error here - preserve any existing login errors

        // Check if user has valid token
        if (checkAuthStatus()) {
          console.log('🔧 INIT: User has token, fetching current user')
          // Try to get current user info
          const result = await authApi.getCurrentUser()
          if (result.success && result.data) {
            console.log('🔧 INIT: getCurrentUser successful')
            setUser(result.data)
            // Only clear error if we successfully authenticated
            // Don't clear login errors - they should persist until user action
            console.log('🔧 INIT: Checking if should clear error. Current error:', error)
            if (!error || !error.includes('Invalid email or password')) {
              console.log('🔧 INIT: ⚠️ CLEARING ERROR - error was:', error)
              setErrorWithLog(null)
            } else {
              console.log('🔧 INIT: Preserving login error:', error)
            }
          } else if (result.error instanceof AuthExpiredError) {
            // Session expired during initialization
            handleAuthExpired()
          } else {
            // Other errors during user fetch
            console.error('Failed to get current user:', result.error)
            TokenStorage.clearTokens()
            setUser(null)
          }
        } else {
          console.log('🔧 INIT: No valid token found')
          // No valid token, user is not authenticated
          setUser(null)
          // Don't set or clear error here - preserve any login errors
        }
      } catch (error) {
        console.error('🔧 INIT: Auth initialization error:', error)
        // Clear tokens if they're invalid
        TokenStorage.clearTokens()
        setUser(null)
        // Only set error for actual session expiration, not initial load
        if (user !== null) {
          console.log('🔧 INIT: Setting session expired error')
          setErrorWithLog('Session expired. Please login again.')
        }
      } finally {
        console.log('🔧 INIT: Setting isLoading to false')
        setIsLoading(false)
      }
    }

    console.log('🔧 INIT: useEffect running, calling initializeAuth()')
    initializeAuth()
  }, [])

  // Login function
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    console.log('🔐 LOGIN START:', credentials.email)
    try {
      setIsLoading(true)
      console.log('🔄 LOGIN: setIsLoading(true)')
      setErrorWithLog(null) // Clear previous error at start of new attempt
      console.log('🔄 LOGIN: setError(null) - cleared previous error')

      const result = await authApi.login(credentials)
      console.log('🔄 LOGIN: API result:', { success: result.success, hasData: !!result.data, errorType: result.error?.constructor.name })

      if (result.success && result.data) {
        console.log('✅ LOGIN SUCCESS: Setting user')
        setUser(result.data.user)
        console.log('✅ LOGIN SUCCESS: User set, returning true')
        return true  // Login successful
      } else if (result.error) {
        console.log('❌ LOGIN FAILED: Handling error:', result.error.message)
        // Handle specific error types
        if (result.error instanceof AuthInvalidError) {
          console.log('❌ LOGIN FAILED: Setting AuthInvalidError:', result.error.message)
          setErrorWithLog(result.error.message)
        } else if (result.error instanceof NetworkError) {
          console.log('❌ LOGIN FAILED: Setting NetworkError')
          setErrorWithLog('Network error. Please check your connection.')
        } else {
          console.log('❌ LOGIN FAILED: Setting generic error:', result.error.message)
          setErrorWithLog(result.error.message || 'Login failed. Please try again.')
        }
        console.log('❌ LOGIN FAILED: Error set, returning false')
        return false  // Login failed
      }

      // Should not reach here, but handle just in case
      console.log('❌ LOGIN FAILED: Unexpected path - no success and no error')
      setErrorWithLog('Unexpected login error')
      return false
    } catch (error) {
      console.error('❌ LOGIN EXCEPTION:', error)
      setErrorWithLog('Login failed. Please try again.')
      return false
    } finally {
      setIsLoading(false)
      console.log('🔄 LOGIN: setIsLoading(false) - login process complete')
    }
  }

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      setIsLoading(true)
      setErrorWithLog(null)

      const result = await authApi.logout()
      if (!result.success) {
        console.error('Logout error:', result.error)
        // Don't show error to user for logout failures
      }
    } catch (error) {
      console.error('Logout error:', error)
      // Don't show error to user for logout failures
    } finally {
      // Always clear user state even if API call fails
      setUser(null)
      setIsLoading(false)
      
      // Navigate to login page after logout - using router instead of window.location
      router.push('/login')
    }
  }

  // Refresh user info
  const refreshUser = async (): Promise<void> => {
    try {
      if (checkAuthStatus()) {
        const result = await authApi.getCurrentUser()
        if (result.success && result.data) {
          setUser(result.data)
        } else if (result.error instanceof AuthExpiredError) {
          // Session expired, handle centrally
          handleAuthExpired()
        } else {
          console.error('Refresh user error:', result.error)
          setErrorWithLog('Failed to refresh user information')
        }
      }
    } catch (error) {
      console.error('Refresh user error:', error)
      setErrorWithLog('Failed to refresh user information')
    }
  }

  // Add logging for state changes
  React.useEffect(() => {
    console.log('🔄 AUTH STATE: user changed:', user?.email || 'null')
  }, [user])

  React.useEffect(() => {
    console.log('🔄 AUTH STATE: isLoading changed:', isLoading)
  }, [isLoading])

  React.useEffect(() => {
    console.log('🔄 AUTH STATE: error changed:', error)
  }, [error])

  React.useEffect(() => {
    const isAuth = user !== null
    console.log('🔄 AUTH STATE: isAuthenticated changed:', isAuth)
  }, [user])

  // Context value
  const contextValue: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    error,
    login,
    logout,
    refreshUser,
    clearError,
    handleAuthExpired,
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

// HOC to protect routes
export function withAuth<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth()

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        </div>
      )
    }

    if (!isAuthenticated) {
      // Redirect to login will be handled by the router
      return null
    }

    return <Component {...props} />
  }
}

// Protected route component
interface ProtectedRouteProps {
  children: ReactNode
  fallback?: ReactNode
}

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps): React.JSX.Element {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        {fallback || (
          <div className="text-center">
            <h2 className="text-xl font-semibold text-neutral-900 mb-2">
              Authentication Required
            </h2>
            <p className="text-neutral-600">
              Please login to access this page.
            </p>
          </div>
        )}
      </div>
    )
  }

  return <>{children}</>
}