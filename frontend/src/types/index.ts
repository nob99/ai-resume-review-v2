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

// Text Extraction Types
export interface TextExtractionRequest {
  upload_id: string
  force_reextraction?: boolean
  timeout_seconds?: number
}

export interface BatchTextExtractionRequest {
  upload_ids: string[]
  force_reextraction?: boolean
  timeout_seconds?: number
}

export interface ResumeSection {
  section_name: string
  content: string
  start_position: number
  end_position: number
  confidence: number
}

export interface TextExtractionResult {
  upload_id: string
  extraction_status: 'pending' | 'processing' | 'completed' | 'failed'
  extracted_text?: string
  processed_text?: string
  sections: ResumeSection[]
  word_count: number
  error_message?: string
  extraction_time?: number
  created_at: string
  updated_at: string
}

export interface TextExtractionResponse {
  message: string
  extraction_result: TextExtractionResult
}

export interface TextExtractionStatusResponse {
  upload_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  extraction_result?: TextExtractionResult
}

export interface BatchTextExtractionResponse {
  message: string
  batch_id: string
  results: TextExtractionResult[]
  total_files: number
  successful: number
  failed: number
}

export interface UploadWithExtractionResponse {
  upload: FileUploadResponse
  extraction: TextExtractionResult | null
}

// Upload types from OpenAPI (matching existing backend)
export interface FileUploadResponse {
  id: string
  original_filename: string
  file_size: number
  mime_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  target_role?: string
  target_industry?: string
  experience_level?: 'entry' | 'mid' | 'senior' | 'executive'
  created_at: string
  validation_info: FileValidationInfo
}

export interface FileValidationInfo {
  is_valid: boolean
  errors: string[]
  warnings: string[]
  file_size: number
  mime_type: string
  file_extension: string
  file_hash: string
}

// Custom error types for text extraction
export class ExtractionTimeoutError extends Error {
  constructor(message = 'Text extraction timed out') {
    super(message)
    this.name = 'ExtractionTimeoutError'
  }
}

export class UnsupportedFileTypeError extends Error {
  constructor(message = 'File type not supported for text extraction') {
    super(message)
    this.name = 'UnsupportedFileTypeError'
  }
}

export class ExtractionFailedError extends Error {
  constructor(message = 'Text extraction failed') {
    super(message)
    this.name = 'ExtractionFailedError'
  }
}

export class ProcessingQueueFullError extends Error {
  constructor(message = 'Processing queue is full. Please try again later.') {
    super(message)
    this.name = 'ProcessingQueueFullError'
  }
}