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