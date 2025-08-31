'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, isAuthenticated, TokenStorage } from '@/lib/api'
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

  // Clear error helper
  const clearError = () => setError(null)

  // Handle auth expiration - centralized navigation logic
  const handleAuthExpired = () => {
    TokenStorage.clearTokens()
    setUser(null)
    setError('Session expired. Please login again.')
    router.push('/login')
  }

  // Check if user is authenticated
  const checkAuthStatus = (): boolean => {
    return isAuthenticated()
  }

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsLoading(true)
        // Don't clear error here - preserve any existing login errors

        // Check if user has valid token
        if (checkAuthStatus()) {
          // Try to get current user info
          const result = await authApi.getCurrentUser()
          if (result.success && result.data) {
            setUser(result.data)
            // Only clear error if we successfully authenticated
            setError(null)
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
          // No valid token, user is not authenticated
          setUser(null)
          // Don't set or clear error here - preserve any login errors
        }
      } catch (error) {
        console.error('Auth initialization error:', error)
        // Clear tokens if they're invalid
        TokenStorage.clearTokens()
        setUser(null)
        // Only set error for actual session expiration, not initial load
        if (user !== null) {
          setError('Session expired. Please login again.')
        }
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()
  }, [])

  // Login function
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    try {
      setIsLoading(true)
      setError(null) // Clear previous error at start of new attempt

      const result = await authApi.login(credentials)
      if (result.success && result.data) {
        setUser(result.data.user)
        return true  // Login successful
      } else if (result.error) {
        // Handle specific error types
        if (result.error instanceof AuthInvalidError) {
          setError(result.error.message)
        } else if (result.error instanceof NetworkError) {
          setError('Network error. Please check your connection.')
        } else {
          setError(result.error.message || 'Login failed. Please try again.')
        }
        return false  // Login failed
      }
      
      // Should not reach here, but handle just in case
      setError('Unexpected login error')
      return false
    } catch (error) {
      console.error('Unexpected login error:', error)
      setError('Login failed. Please try again.')
      return false
    } finally {
      setIsLoading(false)
    }
  }

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      setIsLoading(true)
      setError(null)

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
          setError('Failed to refresh user information')
        }
      }
    } catch (error) {
      console.error('Refresh user error:', error)
      setError('Failed to refresh user information')
    }
  }

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