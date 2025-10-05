/**
 * Upload Feature Constants
 * Centralized configuration and constants for the upload feature
 */

// File validation constants
export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
export const MIN_FILE_SIZE = 1024 // 1KB
export const MAX_FILES_PER_UPLOAD = 5

export const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
} as const

export const ACCEPTED_EXTENSIONS = ['.pdf', '.doc', '.docx'] as const
export const ACCEPTED_TYPE_LABELS = ['PDF', 'DOC', 'DOCX'] as const

// Industry options
export const INDUSTRY_OPTIONS = [
  { value: 'strategy_tech', label: 'Strategy/Tech' },
  { value: 'ma_financial', label: 'M&A/Financial Advisory' },
  { value: 'consulting', label: 'Full Service Consulting' },
  { value: 'system_integrator', label: 'System Integrator' },
  { value: 'general', label: 'General' }
] as const

// Polling configuration
export const ANALYSIS_POLL_INTERVAL_MS = 3000 // 3 seconds

// File upload statuses
export enum FileUploadStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  SUCCESS = 'success',
  ERROR = 'error',
  CANCELLED = 'cancelled'
}

// Analysis statuses
export enum AnalysisStatus {
  REQUESTING = 'requesting',
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  ERROR = 'error'
}

// Type aliases for backward compatibility
export type FileUploadStatusType = `${FileUploadStatus}`
export type AnalysisStatusType = `${AnalysisStatus}`

// Industry option type
export type IndustryOption = typeof INDUSTRY_OPTIONS[number]