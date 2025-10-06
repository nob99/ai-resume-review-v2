import { useState, useCallback } from 'react'
import { UploadPageState, FileUploadHandlers, AnalysisHandlers } from '../types'
import useFileUpload from './useFileUpload'
import useAnalysisPoll from './useAnalysisPoll'

/**
 * Custom hook for managing complete upload and analysis flow
 * Orchestrates file upload and analysis polling
 *
 * Note: Toast notifications removed from upload workflow.
 * UI feedback provided by file status badges, progress bars, and inline errors.
 */
export function useUploadFlow() {
  // Page-level state
  const [selectedCandidate, setSelectedCandidate] = useState<string>('')
  const [selectedIndustry, setSelectedIndustry] = useState<string>('')

  // Delegate to specialized hooks
  const fileUpload = useFileUpload(selectedCandidate)
  const analysisPoll = useAnalysisPoll()

  // Coordinated analysis actions
  const handleStartAnalysis = useCallback(async () => {
    const resumeId = fileUpload.computed.successFiles[0]?.result?.id

    // Defensive checks - UI should prevent these, but guard against edge cases
    if (!resumeId) {
      console.error('Analysis attempted without resume upload')
      return
    }

    if (!selectedIndustry) {
      console.error('Analysis attempted without industry selection')
      return
    }

    await analysisPoll.actions.startAnalysis(resumeId, selectedIndustry)
  }, [fileUpload.computed.successFiles, selectedIndustry, analysisPoll.actions])

  const handleAnalyzeAgain = useCallback(() => {
    analysisPoll.actions.resetAnalysis()
    setSelectedIndustry('')
  }, [analysisPoll.actions])

  const handleUploadNew = useCallback(() => {
    fileUpload.actions.clearFiles()
    analysisPoll.actions.resetAnalysis()
    setSelectedIndustry('')
  }, [fileUpload.actions, analysisPoll.actions])

  // Combine state for backward compatibility
  const combinedState: UploadPageState = {
    selectedCandidate,
    files: fileUpload.state.files,
    isUploading: fileUpload.state.isUploading,
    selectedIndustry,
    isAnalyzing: analysisPoll.state.isAnalyzing,
    analysisId: analysisPoll.state.analysisId,
    analysisResult: analysisPoll.state.analysisResult,
    analysisStatus: analysisPoll.state.analysisStatus,
    elapsedTime: analysisPoll.state.elapsedTime
  }

  // Create handler objects for backward compatibility
  const fileHandlers: FileUploadHandlers = fileUpload.actions

  const analysisHandlers: AnalysisHandlers = {
    onStartAnalysis: handleStartAnalysis,
    onAnalyzeAgain: handleAnalyzeAgain,
    onUploadNew: handleUploadNew
  }

  return {
    // State
    state: combinedState,

    // Computed values
    pendingFiles: fileUpload.computed.pendingFiles,
    uploadingFiles: fileUpload.computed.uploadingFiles,
    successFiles: fileUpload.computed.successFiles,
    errorFiles: fileUpload.computed.errorFiles,

    // Handlers
    fileHandlers,
    analysisHandlers,

    // Direct setters
    setSelectedCandidate,
    setSelectedIndustry
  }
}

export default useUploadFlow