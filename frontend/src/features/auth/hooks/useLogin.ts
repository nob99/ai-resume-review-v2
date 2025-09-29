import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { LoginRequest } from '@/types'

/**
 * Custom hook for handling login functionality
 * Provides login state and error handling
 */
export function useLogin() {
  const { login, isLoading, error, clearError } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleLogin = async (credentials: LoginRequest): Promise<boolean> => {
    setIsSubmitting(true)

    try {
      const success = await login(credentials)
      return success
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    login: handleLogin,
    isLoading: isLoading || isSubmitting,
    error,
    clearError
  }
}

export default useLogin