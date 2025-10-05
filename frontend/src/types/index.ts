// Common types for the application
import { FileUploadStatus, FileUploadStatusType } from '@/features/upload/constants'

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

export interface Candidate {
  id: string
  first_name: string
  last_name: string
  email?: string
  phone?: string
  current_company?: string
  current_position?: string
  years_experience?: number
  status: string
  created_at: string
}

export interface CandidateListResponse {
  candidates: Candidate[]
  total_count: number
  limit: number
  offset: number
}

// Candidate form types
export interface CandidateFormData {
  firstName: string
  lastName: string
  email?: string
  phone?: string
  currentCompany?: string
  currentPosition?: string
  yearsExperience?: number
}

export interface CandidateCreateRequest {
  first_name: string
  last_name: string
  email?: string
  phone?: string
  current_company?: string
  current_position?: string
  years_experience?: number
}

export interface CandidateCreateResponse {
  success: boolean
  message: string
  candidate?: Candidate
  error?: string
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

// Simplified file upload types
export interface FileUploadError extends Error {
  code: 'INVALID_TYPE' | 'FILE_TOO_LARGE' | 'UPLOAD_FAILED' | 'VALIDATION_FAILED' | 'CANCELLED'
}

// Single, simple file upload state
export interface UploadFile {
  id: string
  file: File
  status: FileUploadStatus | FileUploadStatusType
  progress: number
  error?: string
  result?: {
    id?: string
    filename?: string
    size?: number
    content_type?: string
    uploaded_at?: string
    extractedText?: string
    candidate_id?: string
    upload_id?: string
    [key: string]: any
  }
  abortController?: AbortController
}

export interface FileValidationResult {
  isValid: boolean
  errors: string[]
}

export interface FileUploadProps extends BaseComponentProps {
  onFilesSelected?: (files: File[]) => void
  onUploadComplete?: (files: UploadFile[]) => void
  onError?: (error: FileUploadError) => void
  acceptedTypes?: string[]
  maxFileSize?: number
  maxFiles?: number
  multiple?: boolean
  disabled?: boolean
}

// Upload status response from API
export interface UploadStatusResponse {
  upload_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  file_id?: string
  filename: string
  size: number
  content_type: string
  uploaded_at: string
  extracted_text?: string
  error?: string
}

// AI Analysis Types
export interface StructureScores {
  format: number
  organization: number
  tone: number
  completeness: number
}

export interface AppealScores {
  achievement_relevance: number
  skills_alignment: number
  experience_fit: number
  competitive_positioning: number
}

export interface StructureFeedback {
  issues: string[]
  recommendations: string[]
  missing_sections: string[]
  strengths: string[]
}

export interface AppealFeedback {
  relevant_achievements: string[]
  missing_skills: string[]
  competitive_advantages: string[]
  improvement_areas: string[]
  transferable_experience: string[]
}

export interface StructureAnalysis {
  scores: StructureScores
  feedback: StructureFeedback
  metadata: {
    total_sections: number
    word_count: number
    reading_time: number
  }
}

export interface AppealAnalysis {
  scores: AppealScores
  feedback: AppealFeedback
}

export interface DetailedScores {
  structure_analysis: StructureAnalysis
  appeal_analysis: AppealAnalysis
  market_tier: string
  ai_analysis_id: string
  conversion_timestamp: string
}

export interface AnalysisResult {
  analysis_id: string
  overall_score: number
  ats_score: number
  content_score: number
  formatting_score: number
  industry: string
  executive_summary: string
  detailed_scores: DetailedScores
  ai_model_used: string
  processing_time_ms: number
  completed_at: string
}

export interface AnalysisStatusResponse {
  analysis_id: string
  status: string
  requested_at: string
  completed_at?: string
  result?: AnalysisResult
}

export interface ParsedAIFeedback {
  // Structure feedback
  issues: string[]
  recommendations: string[]
  missingSection: string[]
  strengths: string[]

  // Appeal feedback
  relevantAchievements: string[]
  missingSkills: string[]
  competitiveAdvantages: string[]
  improvementAreas: string[]
  transferableExperience: string[]

  // Detailed scores
  structureScores: StructureScores
  appealScores: AppealScores

  // Metadata
  marketTier: string
  metadata: {
    total_sections: number
    word_count: number
    reading_time: number
  }
}