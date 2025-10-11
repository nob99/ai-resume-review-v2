import { AnalysisStatusResponse } from '@/types'

/**
 * Shared types for analysis components
 */

export interface BaseAnalysisCardProps {
  analysis: AnalysisStatusResponse
  className?: string
}

export interface AnalysisOverviewProps extends BaseAnalysisCardProps {
  industryOptions?: Array<{ value: string; label: string }>
  elapsedTime?: number
}

export interface AnalysisActionButtonsProps {
  onAnalyzeAgain?: () => void
  onUploadNew?: () => void
  className?: string
}
