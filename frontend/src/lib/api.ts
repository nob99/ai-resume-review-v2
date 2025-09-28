import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosProgressEvent } from 'axios'
import {
  LoginRequest,
  LoginResponse,
  User,
  Candidate,
  CandidateListResponse,
  CandidateCreateRequest,
  CandidateCreateResponse,
  AuthExpiredError,
  AuthInvalidError,
  NetworkError,
  ApiResult,
} from '@/types'

// Base API URL - will be configurable via environment variable
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance with default configuration
const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  // Don't set default Content-Type - let axios auto-detect based on request data
  // This allows FormData to use multipart/form-data automatically
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

// File upload API functions with progress tracking
export const uploadApi = {
  async uploadFile(
    file: File,
    candidateId: string,
    onProgress?: (progress: AxiosProgressEvent) => void,
    abortController?: AbortController
  ): Promise<ApiResult<any>> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      // Debug logging
      console.log('Upload debug - File:', file.name, file.size, 'bytes, type:', file.type)
      console.log('Upload debug - FormData has file:', formData.has('file'))

      const response = await api.post(`/resume_upload/candidates/${candidateId}/resumes`, formData, {
        // Don't set Content-Type header - let axios handle it for FormData
        onUploadProgress: onProgress,
        signal: abortController?.signal,
      })

      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (axios.isCancel(error)) {
        return {
          success: false,
          error: new Error('Upload cancelled')
        }
      }

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

      return {
        success: false,
        error: new Error('Upload failed')
      }
    }
  },

  async uploadMultipleFiles(
    files: File[],
    candidateId: string,
    onProgress?: (fileId: string, progress: AxiosProgressEvent) => void,
    abortControllers?: Map<string, AbortController>
  ): Promise<ApiResult<any[]>> {
    try {
      const uploadPromises = files.map(async (file) => {
        const fileId = `${file.name}-${Date.now()}`
        const abortController = abortControllers?.get(fileId)

        const result = await this.uploadFile(
          file,
          candidateId,
          (progress) => onProgress?.(fileId, progress),
          abortController
        )

        if (!result.success) {
          throw result.error
        }

        return result.data!
      })

      const results = await Promise.all(uploadPromises)

      return {
        success: true,
        data: results
      }
    } catch (error) {
      return {
        success: false,
        error: error as Error
      }
    }
  },

  async getFileStatus(fileId: string): Promise<ApiResult<any>> {
    try {
      const response = await api.get(`/resume_upload/${fileId}/status`)
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

      return {
        success: false,
        error: new Error('Failed to get file status')
      }
    }
  },

  async cancelUpload(fileId: string): Promise<ApiResult<void>> {
    try {
      await api.delete(`/resume_upload/${fileId}/cancel`)
      return {
        success: true
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

      return {
        success: false,
        error: new Error('Failed to cancel upload')
      }
    }
  },

  async deleteFile(fileId: string): Promise<ApiResult<void>> {
    try {
      await api.delete(`/resume_upload/${fileId}`)
      return {
        success: true
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

      return {
        success: false,
        error: new Error('Failed to delete file')
      }
    }
  },

  async retryUpload(
    file: File,
    fileId: string,
    onProgress?: (progress: AxiosProgressEvent) => void,
    abortController?: AbortController
  ): Promise<ApiResult<any>> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('retry_file_id', fileId)

      const response = await api.post('/resume_upload/batch', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: onProgress,
        signal: abortController?.signal,
      })

      return {
        success: true,
        data: response.data
      }
    } catch (error) {
      if (axios.isCancel(error)) {
        return {
          success: false,
          error: new Error('Upload cancelled')
        }
      }

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

      return {
        success: false,
        error: new Error('Retry upload failed')
      }
    }
  },
}

// Candidate API functions
export const candidateApi = {
  async getCandidates(): Promise<ApiResult<Candidate[]>> {
    try {
      const response = await api.get<CandidateListResponse>('/candidates')

      if (response.data.candidates) {
        return {
          success: true,
          data: response.data.candidates
        }
      } else {
        return {
          success: false,
          error: new Error('Invalid response format')
        }
      }
    } catch (error: any) {
      console.error('Error fetching candidates:', error)

      // Handle different error types
      if (error.response?.status === 401) {
        return {
          success: false,
          error: new AuthExpiredError('Authentication required')
        }
      } else if (error.code === 'ECONNABORTED' || error.code === 'ENOTFOUND') {
        return {
          success: false,
          error: new NetworkError('Network connection failed')
        }
      } else {
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to load candidates'
        return {
          success: false,
          error: new Error(errorMessage)
        }
      }
    }
  },

  async createCandidate(data: CandidateCreateRequest): Promise<ApiResult<CandidateCreateResponse>> {
    try {
      const response = await api.post<CandidateCreateResponse>('/candidates/', data)
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
  }
}

// Analysis API functions
export const analysisApi = {
  async requestAnalysis(
    resumeId: string,
    industry: string,
    analysisDepth: string = 'standard'
  ): Promise<ApiResult<any>> {
    try {
      const response = await api.post(`/analysis/resumes/${resumeId}/analyze`, {
        industry,
        analysis_depth: analysisDepth,
        compare_to_market: false
      })

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

  async getAnalysisStatus(analysisId: string): Promise<ApiResult<any>> {
    try {
      const response = await api.get(`/analysis/analysis/${analysisId}/status`)

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

  async getAnalysisResult(analysisId: string): Promise<ApiResult<any>> {
    try {
      const response = await api.get(`/analysis/analysis/${analysisId}`)

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
  }
}

// WebSocket connection for real-time progress updates
export class UploadWebSocket {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(
    private onMessage: (data: any) => void,
    private onError?: (error: Event) => void,
    private onClose?: () => void
  ) {}

  connect(): void {
    const wsUrl = BASE_URL.replace('http', 'ws') + '/ws/upload-progress'
    
    try {
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected for upload progress')
        this.reconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.onError?.(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.onClose?.()
        this.attemptReconnect()
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      this.attemptReconnect()
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
      
      setTimeout(() => {
        this.connect()
      }, this.reconnectDelay * this.reconnectAttempts)
    }
  }

  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// Admin user management API functions
export const adminApi = {
  async getUsers(params?: {
    page?: number
    page_size?: number
    search?: string
    role?: string
    is_active?: boolean
  }): Promise<ApiResult<any>> {
    try {
      const response = await api.get('/admin/users', { params })
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

      return {
        success: false,
        error: new Error('Failed to load users')
      }
    }
  },

  async createUser(userData: {
    email: string
    first_name: string
    last_name: string
    role: string
    temporary_password: string
  }): Promise<ApiResult<any>> {
    try {
      const response = await api.post('/admin/users', userData)
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

      return {
        success: false,
        error: new Error('Failed to create user')
      }
    }
  },

  async updateUser(userId: string, userData: {
    is_active?: boolean
    role?: string
    email_verified?: boolean
  }): Promise<ApiResult<any>> {
    try {
      const response = await api.patch(`/admin/users/${userId}`, userData)
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

      return {
        success: false,
        error: new Error('Failed to update user')
      }
    }
  },

  async getUserDetail(userId: string): Promise<ApiResult<any>> {
    try {
      const response = await api.get(`/admin/users/${userId}`)
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

      return {
        success: false,
        error: new Error('Failed to get user details')
      }
    }
  },

  async resetPassword(userId: string, passwordData: {
    new_password: string
    force_password_change?: boolean
  }): Promise<ApiResult<any>> {
    try {
      const response = await api.post(`/admin/users/${userId}/reset-password`, passwordData)
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

      return {
        success: false,
        error: new Error('Failed to reset password')
      }
    }
  }
}

// Export the configured axios instance for custom requests
export default api

// Export token storage for auth context
export { TokenStorage }