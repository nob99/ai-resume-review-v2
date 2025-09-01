import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { 
  LoginRequest, LoginResponse, User, ApiError, AuthExpiredError, AuthInvalidError, NetworkError, ApiResult,
  TextExtractionRequest, TextExtractionResponse, TextExtractionStatusResponse, BatchTextExtractionRequest, 
  BatchTextExtractionResponse, UploadWithExtractionResponse, ExtractionTimeoutError, UnsupportedFileTypeError,
  ExtractionFailedError, ProcessingQueueFullError, FileUploadResponse, UploadStatusResponse, 
  UploadListResponse, UploadDeleteResponse
} from '@/types'

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
  const responseData = error.response?.data as { detail?: string; error?: string } | undefined
  
  if (error.response?.status === 401) {
    throw new AuthInvalidError(responseData?.detail || 'Invalid credentials')
  } else if (error.response?.status === 423) {
    throw new AuthInvalidError('Account is locked due to too many failed attempts')
  } else if (error.response?.status === 429) {
    // Check if it's extraction-related rate limiting
    if (responseData?.detail?.includes('queue') || responseData?.detail?.includes('concurrent')) {
      throw new ProcessingQueueFullError(responseData.detail)
    }
    throw new AuthInvalidError('Too many requests. Please try again later.')
  } else if (error.response?.status === 408 || error.code === 'ECONNABORTED') {
    // Check if it's extraction timeout
    if (responseData?.detail?.includes('extraction') || responseData?.detail?.includes('timeout')) {
      throw new ExtractionTimeoutError(responseData.detail)
    }
    throw new NetworkError('Request timed out')
  } else if (error.response?.status === 415 || error.response?.status === 400) {
    // Check for unsupported file type
    if (responseData?.detail?.includes('file type') || responseData?.detail?.includes('format')) {
      throw new UnsupportedFileTypeError(responseData.detail)
    }
    // Check for extraction failures
    if (responseData?.detail?.includes('extraction') || responseData?.error === 'EXTRACTION_FAILED') {
      throw new ExtractionFailedError(responseData.detail)
    }
    throw new Error(responseData?.detail || 'Bad request')
  } else if (error.code === 'ENOTFOUND') {
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

// Text extraction API functions
export const extractionApi = {
  async requestTextExtraction(
    uploadId: string, 
    options: { forceReextraction?: boolean; timeoutSeconds?: number } = {}
  ): Promise<ApiResult<TextExtractionResponse>> {
    try {
      const response = await api.post<TextExtractionResponse>('/upload/extract-text', {
        upload_id: uploadId,
        force_reextraction: options.forceReextraction || false,
        timeout_seconds: options.timeoutSeconds || 30
      })
      
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError || error instanceof ExtractionTimeoutError ||
          error instanceof UnsupportedFileTypeError || error instanceof ExtractionFailedError ||
          error instanceof ProcessingQueueFullError) {
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

  async getExtractionStatus(uploadId: string): Promise<ApiResult<TextExtractionStatusResponse>> {
    try {
      const response = await api.get<TextExtractionStatusResponse>(`/upload/${uploadId}/extraction-status`)
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError || error instanceof ExtractionTimeoutError ||
          error instanceof UnsupportedFileTypeError || error instanceof ExtractionFailedError ||
          error instanceof ProcessingQueueFullError) {
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

  async requestBatchExtraction(
    uploadIds: string[],
    options: { forceReextraction?: boolean; timeoutSeconds?: number } = {}
  ): Promise<ApiResult<BatchTextExtractionResponse>> {
    try {
      const response = await api.post<BatchTextExtractionResponse>('/upload/batch-extract-text', {
        upload_ids: uploadIds,
        force_reextraction: options.forceReextraction || false,
        timeout_seconds: options.timeoutSeconds || 30
      })
      
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError || error instanceof ExtractionTimeoutError ||
          error instanceof UnsupportedFileTypeError || error instanceof ExtractionFailedError ||
          error instanceof ProcessingQueueFullError) {
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

  async getUploadWithExtraction(uploadId: string): Promise<ApiResult<UploadWithExtractionResponse>> {
    try {
      const response = await api.get<UploadWithExtractionResponse>(`/upload/${uploadId}/with-extraction`)
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError || error instanceof ExtractionTimeoutError ||
          error instanceof UnsupportedFileTypeError || error instanceof ExtractionFailedError ||
          error instanceof ProcessingQueueFullError) {
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
  }
}

// Upload API functions
export const uploadApi = {
  async uploadResume(
    file: File,
    options?: {
      targetRole?: string
      targetIndustry?: string
      experienceLevel?: 'entry' | 'mid' | 'senior' | 'executive'
    }
  ): Promise<ApiResult<FileUploadResponse>> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      if (options?.targetRole) {
        formData.append('target_role', options.targetRole)
      }
      if (options?.targetIndustry) {
        formData.append('target_industry', options.targetIndustry)
      }
      if (options?.experienceLevel) {
        formData.append('experience_level', options.experienceLevel)
      }
      
      const response = await api.post<FileUploadResponse>('/upload/resume', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 60000, // 60 second timeout for file uploads
      })
      
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      // Handle specific upload errors
      if ((error as AxiosError).response?.status === 413) {
        return {
          success: false,
          error: new Error('File size exceeds maximum allowed size (30MB)')
        }
      }
      
      if ((error as AxiosError).response?.status === 429) {
        return {
          success: false,
          error: new Error('Too many uploads. Please try again later.')
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
      
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  },

  async getUploadStatus(uploadId: string): Promise<ApiResult<UploadStatusResponse>> {
    try {
      const response = await api.get<UploadStatusResponse>(`/upload/${uploadId}/status`)
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      if ((error as AxiosError).response?.status === 404) {
        return {
          success: false,
          error: new Error('Upload not found')
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
      
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  },

  async listUploads(page: number = 1, perPage: number = 20): Promise<ApiResult<UploadListResponse>> {
    try {
      const response = await api.get<UploadListResponse>('/upload/list', {
        params: { page, per_page: perPage }
      })
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError) {
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
      
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  },

  async deleteUpload(uploadId: string): Promise<ApiResult<UploadDeleteResponse>> {
    try {
      const response = await api.delete<UploadDeleteResponse>(`/upload/${uploadId}`)
      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (error instanceof AuthExpiredError || error instanceof AuthInvalidError || 
          error instanceof NetworkError) {
        return {
          success: false,
          error
        }
      }
      
      if ((error as AxiosError).response?.status === 404) {
        return {
          success: false,
          error: new Error('Upload not found')
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
      
      return {
        success: false,
        error: new Error('Unexpected error occurred')
      }
    }
  }
}

// Export the configured axios instance for custom requests
export default api

// Export token storage for auth context
export { TokenStorage }