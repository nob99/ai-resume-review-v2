/**
 * Upload Feature Types
 */

export interface IndustryOption {
  value: string
  label: string
}

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

export const INDUSTRY_OPTIONS: IndustryOption[] = [
  { value: 'strategy_tech', label: 'Strategy/Tech' },
  { value: 'ma_financial', label: 'M&A/Financial Advisory' },
  { value: 'consulting', label: 'Full Service Consulting' },
  { value: 'system_integrator', label: 'System Integrator' },
  { value: 'general', label: 'General' }
]