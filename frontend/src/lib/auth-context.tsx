'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { authApi, isAuthenticated, TokenStorage } from '@/lib/api'
import { User, LoginRequest, LoadingState } from '@/types'

// Auth context types
interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  error: string | null
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  clearError: () => void
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
export function AuthProvider({ children }: AuthProviderProps): JSX.Element {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Clear error helper
  const clearError = () => setError(null)

  // Check if user is authenticated
  const checkAuthStatus = (): boolean => {
    return isAuthenticated()
  }

  // Initialize auth state on mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsLoading(true)
        setError(null)

        // Check if user has valid token
        if (checkAuthStatus()) {
          // Try to get current user info
          const currentUser = await authApi.getCurrentUser()
          setUser(currentUser)
        } else {
          // No valid token, user is not authenticated
          setUser(null)
        }
      } catch (error) {
        console.error('Auth initialization error:', error)
        // Clear tokens if they're invalid
        TokenStorage.clearTokens()
        setUser(null)
        setError('Session expired. Please login again.')
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()
  }, [])

  // Login function
  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await authApi.login(credentials)
      setUser(response.user)
    } catch (error: any) {
      console.error('Login error:', error)
      
      // Handle specific error cases
      if (error.response?.status === 401) {
        setError('Invalid email or password')
      } else if (error.response?.status === 423) {
        setError('Account is locked due to too many failed attempts')
      } else if (error.response?.status === 429) {
        setError('Too many login attempts. Please try again later.')
      } else if (error.response?.data?.detail) {
        setError(error.response.data.detail)
      } else {
        setError('Login failed. Please try again.')
      }
      
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // Logout function
  const logout = async (): Promise<void> => {
    try {
      setIsLoading(true)
      setError(null)

      await authApi.logout()
    } catch (error) {
      console.error('Logout error:', error)
      // Don't show error to user for logout failures
    } finally {
      // Always clear user state even if API call fails
      setUser(null)
      setIsLoading(false)
    }
  }

  // Refresh user info
  const refreshUser = async (): Promise<void> => {
    try {
      if (checkAuthStatus()) {
        const currentUser = await authApi.getCurrentUser()
        setUser(currentUser)
      }
    } catch (error) {
      console.error('Refresh user error:', error)
      // If refresh fails, user might need to login again
      TokenStorage.clearTokens()
      setUser(null)
      setError('Session expired. Please login again.')
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

export function ProtectedRoute({ children, fallback }: ProtectedRouteProps): JSX.Element {
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