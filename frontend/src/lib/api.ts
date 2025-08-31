import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { LoginRequest, LoginResponse, User, ApiError, AuthExpiredError, AuthInvalidError, NetworkError, ApiResult } from '@/types'

// Base API URL - will be configurable via environment variable
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance with default configuration
const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
})

// Token storage utilities
class TokenStorage {
  private static readonly ACCESS_TOKEN_KEY = 'access_token'
  private static readonly REFRESH_TOKEN_KEY = 'refresh_token'

  static getAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(this.ACCESS_TOKEN_KEY)
  }

  static getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }

  static setTokens(accessToken: string, refreshToken: string): void {
    if (typeof window === 'undefined') return
    localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
  }

  static clearTokens(): void {
    if (typeof window === 'undefined') return
    localStorage.removeItem(this.ACCESS_TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
  }
}

// Request interceptor to add authentication token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = TokenStorage.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for token refresh and error handling
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean
    }

    // Handle 401 errors (token expired) - but NOT for login attempts
    const isLoginRequest = originalRequest.url?.includes('/auth/login')
    
    if (error.response?.status === 401 && !originalRequest._retry && !isLoginRequest) {
      originalRequest._retry = true

      const refreshToken = TokenStorage.getRefreshToken()
      if (refreshToken) {
        try {
          // Attempt to refresh the token
          const response = await axios.post(
            `${BASE_URL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken },
            { headers: { 'Content-Type': 'application/json' } }
          )

          const { access_token, refresh_token: newRefreshToken } = response.data

          // Store new tokens
          TokenStorage.setTokens(access_token, newRefreshToken)

          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed, clear tokens and throw AuthExpiredError
          TokenStorage.clearTokens()
          // Let the calling code decide how to handle auth expiration
          throw new AuthExpiredError('Session expired and refresh failed')
        }
      } else {
        // No refresh token, clear storage and throw AuthExpiredError
        TokenStorage.clearTokens()
        throw new AuthExpiredError('No valid session found')
      }
    }

    return Promise.reject(error)
  }
)

// Helper function to convert axios errors to our custom error types
function handleApiError(error: AxiosError): never {
  const responseData = error.response?.data as { detail?: string } | undefined
  
  if (error.response?.status === 401) {
    throw new AuthInvalidError(responseData?.detail || 'Invalid credentials')
  } else if (error.response?.status === 423) {
    throw new AuthInvalidError('Account is locked due to too many failed attempts')
  } else if (error.response?.status === 429) {
    throw new AuthInvalidError('Too many login attempts. Please try again later.')
  } else if (error.code === 'ECONNABORTED' || error.code === 'ENOTFOUND') {
    throw new NetworkError('Network connection failed')
  } else {
    throw new Error(responseData?.detail || error.message || 'Request failed')
  }
}

// API functions with improved error handling
export const authApi = {
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
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      // Convert axios errors to our custom types
      try {
        handleApiError(error as AxiosError)
        // This line should never be reached since handleApiError always throws
        return {
          success: false,
          error: new Error('Unexpected error occurred')
        }
      } catch (customError) {
        return {
          success: false,
          error: customError as Error
        }
      }
    }
  },

  async logout(): Promise<ApiResult<void>> {
    try {
      await api.post('/auth/logout')
      TokenStorage.clearTokens()
      return {
        success: true
      }
    } catch (error) {
      // Even if logout fails on server, clear local tokens
      console.error('Logout error:', error)
      TokenStorage.clearTokens()
      
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      // For logout, we still consider it successful if tokens are cleared
      return {
        success: true
      }
    }
  },

  async getCurrentUser(): Promise<ApiResult<User>> {
    try {
      const response = await api.get<User>('/auth/me')
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      try {
        handleApiError(error as AxiosError)
      } catch (customError) {
        return {
          success: false,
          error: customError as Error
        }
      }
      
      // Fallback for unexpected errors
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  },

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
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      try {
        handleApiError(error as AxiosError)
      } catch (customError) {
        return {
          success: false,
          error: customError as Error
        }
      }
      
      // Fallback for unexpected errors
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  },
}

// Utility function to check if user is authenticated
export function isAuthenticated(): boolean {
  return TokenStorage.getAccessToken() !== null
}

// Export the configured axios instance for custom requests
export default api

// Export token storage for auth context
export { TokenStorage }