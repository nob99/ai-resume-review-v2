/**
 * Upload Feature Types
 */

// Re-export constants and types from constants file
export { INDUSTRY_OPTIONS } from '../constants'
export type { IndustryOption } from '../constants'

export interface UploadPageState {
  selectedCandidate: string
  files: UploadFile[]
  isUploading: boolean
  selectedIndustry: string
  isAnalyzing: boolean
  analysisId: string | null
  analysisResult: AnalysisStatusResponse | null
  analysisStatus: string
}

export interface FileUploadHandlers {
  onFilesSelected: (files: File[]) => void
  onUploadError: (error: FileUploadError) => void
  onStartUpload: () => void
  onRemoveFile: (fileId: string) => void
  onCancelFile: (fileId: string) => void
  onRetryFile: (fileId: string) => void
}

export interface AnalysisHandlers {
  onStartAnalysis: () => void
  onAnalyzeAgain: () => void
  onUploadNew: () => void
}

// Re-export commonly used types from main types
export type {
  UploadFile,
  FileUploadError,
  AnalysisStatusResponse,
  AnalysisResult
} from '@/types'