// Common types for the application

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'admin' | 'consultant'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface ApiError {
  detail: string
  status_code?: number
}

// Component prop types
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

// Form types
export interface ValidationError {
  field: string
  message: string
}

// Loading states
export type LoadingState = 'idle' | 'loading' | 'success' | 'error'

// Custom error types for better separation of concerns
export class AuthExpiredError extends Error {
  constructor(message = 'Authentication token has expired') {
    super(message)
    this.name = 'AuthExpiredError'
  }
}

export class AuthInvalidError extends Error {
  constructor(message = 'Invalid authentication credentials') {
    super(message)
    this.name = 'AuthInvalidError'
  }
}

export class NetworkError extends Error {
  constructor(message = 'Network request failed') {
    super(message)
    this.name = 'NetworkError'
  }
}

// API Result pattern for consistent error handling
export interface ApiResult<T> {
  success: boolean
  data?: T
  error?: AuthExpiredError | AuthInvalidError | NetworkError | Error
}