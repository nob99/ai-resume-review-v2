import {
  LoginRequest,
  LoginResponse,
  User,
  ApiResult,
  AuthExpiredError,
  AuthInvalidError,
  NetworkError
} from '@/types'
import api, { TokenStorage, BASE_URL } from '@/lib/api'
import axios from 'axios'

/**
 * Authentication Service
 * Handles all auth-related API operations
 */
export const authService = {
  /**
   * Login user with credentials
   */
  async login(credentials: LoginRequest): Promise<ApiResult<LoginResponse>> {
    try {
      const response = await api.post<LoginResponse>('/auth/login', credentials)

      // Store tokens after successful login
      const { access_token, refresh_token } = response.data
      TokenStorage.setTokens(access_token, refresh_token)

      return {
        success: true,
        data: response.data
      }
    } catch (error: unknown) {
      // Handle specific error types
      if (axios.isAxiosError(error)) {
        // Network/connectivity error
        if (!error.response) {
          return {
            success: false,
            error: new NetworkError('Unable to connect to the server. Please check your connection.')
          }
        }

        // 401 - Invalid credentials
        if (error.response.status === 401) {
          return {
            success: false,
            error: new AuthInvalidError('Invalid email or password')
          }
        }

        // 429 - Rate limiting
        if (error.response.status === 429) {
          return {
            success: false,
            error: new AuthInvalidError('Too many login attempts. Please try again later.')
          }
        }
      }

      // Generic error fallback
      return {
        success: false,
        error: error instanceof Error ? error : new Error('An unexpected error occurred')
      }
    }
  },

  /**
   * Logout user
   */
  async logout(): Promise<ApiResult<void>> {
    try {
      await api.post('/auth/logout')
      TokenStorage.clearTokens()
      return { success: true }
    } catch (error: unknown) {
      // Even if logout fails on server, clear local tokens
      console.error('Logout error:', error)
      TokenStorage.clearTokens()

      // For logout, we still consider it successful if tokens are cleared
      return { success: true }
    }
  },

  /**
   * Get current user information
   */
  async getCurrentUser(): Promise<ApiResult<User>> {
    try {
      const response = await api.get<User>('/auth/me')
      return {
        success: true,
        data: response.data
      }
    } catch (error: unknown) {
      // Handle authentication errors
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          return {
            success: false,
            error: new AuthExpiredError()
          }
        }
      }

      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to get user information')
      }
    }
  },

  /**
   * Refresh authentication token
   */
  async refreshToken(): Promise<ApiResult<LoginResponse>> {
    const refreshToken = TokenStorage.getRefreshToken()
    if (!refreshToken) {
      return {
        success: false,
        error: new AuthExpiredError('No refresh token available')
      }
    }

    try {
      const response = await api.post<LoginResponse>('/auth/refresh', {
        refresh_token: refreshToken,
      })

      // Update stored tokens
      const { access_token, refresh_token: newRefreshToken } = response.data
      TokenStorage.setTokens(access_token, newRefreshToken)

      return {
        success: true,
        data: response.data
      }
    } catch (error: unknown) {
      // Clear tokens on refresh failure
      TokenStorage.clearTokens()

      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          return {
            success: false,
            error: new AuthExpiredError('Session expired. Please login again.')
          }
        }
      }

      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to refresh token')
      }
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return TokenStorage.getAccessToken() !== null
  }
}

export default authService