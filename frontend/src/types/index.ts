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

// File upload types
export interface FileUploadError extends Error {
  code: 'INVALID_TYPE' | 'FILE_TOO_LARGE' | 'UPLOAD_FAILED' | 'VALIDATION_FAILED' | 'CANCELLED'
}

export interface UploadedFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'validating' | 'extracting' | 'completed' | 'error' | 'cancelled'
  progress: number
  error?: string
  extractedText?: string
}

// Enhanced progress tracking types for UPLOAD-004
export interface DetailedProgressInfo {
  fileId: string
  fileName: string
  stage: 'queued' | 'uploading' | 'validating' | 'extracting' | 'completed' | 'error' | 'cancelled'
  percentage: number
  bytesUploaded: number
  totalBytes: number
  timeElapsed: number // milliseconds
  estimatedTimeRemaining: number // milliseconds
  speed: number // bytes per second
  retryCount: number
  maxRetries: number
}

export interface UploadProgressState {
  files: Map<string, DetailedProgressInfo>
  overallProgress: number
  totalFiles: number
  completedFiles: number
  failedFiles: number
  isUploading: boolean
  startTime: number
  estimatedTotalTime: number
}

export interface TimeEstimation {
  remaining: number // milliseconds
  percentage: number
  speed: number // bytes per second
  formattedRemaining: string // "2m 30s"
}

export interface UploadCancellationToken {
  fileId: string
  abortController: AbortController
  timestamp: number
}

// Enhanced file type with detailed progress
export interface UploadedFileV2 extends UploadedFile {
  progressInfo?: DetailedProgressInfo
  cancellationToken?: UploadCancellationToken
  startTime?: number
  endTime?: number
  retryAttempts?: number
}

// Progress event types
export interface UploadProgressEvent {
  type: 'progress' | 'stage-change' | 'error' | 'complete' | 'cancelled'
  fileId: string
  data: Partial<DetailedProgressInfo>
  timestamp: number
}

// WebSocket message types for real-time updates
export interface ProgressWebSocketMessage {
  type: 'progress_update' | 'status_change' | 'error' | 'batch_complete'
  payload: {
    fileId?: string
    progress?: number
    stage?: string
    message?: string
    timestamp: number
  }
}

export interface FileValidationResult {
  isValid: boolean
  errors: string[]
}

export interface FileUploadProps extends BaseComponentProps {
  onFilesSelected?: (files: File[]) => void
  onUploadComplete?: (files: UploadedFile[]) => void
  onError?: (error: FileUploadError) => void
  acceptedTypes?: string[]
  maxFileSize?: number
  maxFiles?: number
  multiple?: boolean
  disabled?: boolean
}