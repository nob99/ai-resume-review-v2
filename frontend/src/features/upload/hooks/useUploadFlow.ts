import { useState, useCallback, useEffect, useMemo } from 'react'
import { useToast } from '@/components/ui'
import { UploadFile, FileUploadError, AnalysisStatusResponse } from '@/types'
import uploadService from '../services/uploadService'
import analysisService from '../services/analysisService'
import { UploadPageState, FileUploadHandlers, AnalysisHandlers } from '../types'
import { ANALYSIS_POLL_INTERVAL_MS, FileUploadStatus, AnalysisStatus } from '../constants'

/**
 * Custom hook for managing complete upload and analysis flow
 */
export function useUploadFlow() {
  const { addToast } = useToast()

  // State management
  const [state, setState] = useState<UploadPageState>({
    selectedCandidate: '',
    files: [],
    isUploading: false,
    selectedIndustry: '',
    isAnalyzing: false,
    analysisId: null,
    analysisResult: null,
    analysisStatus: ''
  })

  // Generate unique file ID using Web Crypto API
  // Falls back to Date.now if crypto.randomUUID is not available (older browsers)
  const generateFileId = () => {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID()
    }
    // Fallback for older browsers
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  // Handle file selection
  const handleFilesSelected = useCallback((selectedFiles: File[]) => {
    const newFiles: UploadFile[] = selectedFiles.map(file => ({
      id: generateFileId(),
      file,
      status: FileUploadStatus.PENDING,
      progress: 0
    }))

    setState(prev => ({
      ...prev,
      files: [...prev.files, ...newFiles]
    }))

    addToast({
      type: 'success',
      title: 'Files Selected',
      message: `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} added`
    })
  }, [addToast])

  // Handle upload errors
  const handleUploadError = useCallback((error: FileUploadError) => {
    addToast({
      type: 'error',
      title: 'Upload Error',
      message: error.message
    })
  }, [addToast])

  // Upload a single file
  const uploadSingleFile = async (uploadFile: UploadFile): Promise<void> => {
    // Update file status to uploading
    setState(prev => ({
      ...prev,
      files: prev.files.map(f =>
        f.id === uploadFile.id
          ? { ...f, status: FileUploadStatus.UPLOADING, progress: 0 }
          : f
      )
    }))

    // Create abort controller for this upload
    const abortController = new AbortController()

    // Store abort controller in file state
    setState(prev => ({
      ...prev,
      files: prev.files.map(f =>
        f.id === uploadFile.id
          ? { ...f, abortController }
          : f
      )
    }))

    try {
      const result = await uploadService.uploadFile(
        uploadFile.file,
        state.selectedCandidate,
        // Progress callback
        (progressEvent) => {
          const percentage = (progressEvent.loaded / (progressEvent.total || uploadFile.file.size)) * 100
          setState(prev => ({
            ...prev,
            files: prev.files.map(f =>
              f.id === uploadFile.id
                ? { ...f, progress: Math.round(percentage) }
                : f
            )
          }))
        },
        abortController
      )

      if (result.success) {
        // Upload successful
        setState(prev => ({
          ...prev,
          files: prev.files.map(f =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: FileUploadStatus.SUCCESS,
                  progress: 100,
                  result: result.data,
                  abortController: undefined
                }
              : f
          )
        }))

        addToast({
          type: 'success',
          title: 'Upload Complete',
          message: `${uploadFile.file.name} uploaded successfully`
        })
      } else {
        throw result.error || new Error('Upload failed')
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      const errorName = error instanceof Error ? error.name : ''

      // Check if upload was cancelled
      if (errorName === 'AbortError' || errorMessage.includes('cancelled')) {
        setState(prev => ({
          ...prev,
          files: prev.files.map(f =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: FileUploadStatus.CANCELLED,
                  abortController: undefined
                }
              : f
          )
        }))
      } else {
        // Upload failed
        setState(prev => ({
          ...prev,
          files: prev.files.map(f =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: FileUploadStatus.ERROR,
                  error: errorMessage,
                  abortController: undefined
                }
              : f
          )
        }))

        addToast({
          type: 'error',
          title: 'Upload Failed',
          message: `Failed to upload ${uploadFile.file.name}: ${errorMessage}`
        })
      }
    }
  }

  // Start uploading all pending files
  const handleStartUpload = async () => {
    if (!state.selectedCandidate) {
      addToast({
        type: 'error',
        title: 'Candidate Required',
        message: 'Please select a candidate before uploading files'
      })
      return
    }

    const pendingFiles = state.files.filter(f => f.status === FileUploadStatus.PENDING)
    if (pendingFiles.length === 0) return

    setState(prev => ({ ...prev, isUploading: true }))

    // Upload files concurrently
    const uploadPromises = pendingFiles.map(file => uploadSingleFile(file))

    try {
      await Promise.all(uploadPromises)
    } catch (error) {
      console.error('Batch upload error:', error)
    } finally {
      // Use ref object to capture counts from functional setState
      const countsRef = { successCount: 0, errorCount: 0 }

      // Update state and capture counts (fixes race condition)
      setState(prev => {
        countsRef.successCount = prev.files.filter(f => f.status === FileUploadStatus.SUCCESS).length
        countsRef.errorCount = prev.files.filter(f => f.status === FileUploadStatus.ERROR).length
        return { ...prev, isUploading: false }
      })

      // Show toasts AFTER setState completes (fixes React error)
      const { successCount, errorCount } = countsRef

      if (successCount > 0 && errorCount === 0) {
        addToast({
          type: 'success',
          title: 'All Uploads Complete',
          message: `${successCount} file${successCount !== 1 ? 's' : ''} uploaded successfully!`
        })
      } else if (successCount > 0 && errorCount > 0) {
        addToast({
          type: 'warning',
          title: 'Partial Success',
          message: `${successCount} succeeded, ${errorCount} failed. Check files below.`
        })
      } else if (errorCount > 0) {
        addToast({
          type: 'error',
          title: 'Upload Failed',
          message: `${errorCount} file${errorCount !== 1 ? 's' : ''} failed to upload. Please retry.`
        })
      }
    }
  }

  // File management handlers
  const handleRemoveFile = useCallback((fileId: string) => {
    setState(prev => ({
      ...prev,
      files: prev.files.filter(f => f.id !== fileId)
    }))
  }, [])

  const handleCancelFile = useCallback((fileId: string) => {
    const file = state.files.find(f => f.id === fileId)
    if (file?.abortController) {
      file.abortController.abort()
    }
  }, [state.files])

  const handleRetryFile = useCallback((fileId: string) => {
    setState(prev => ({
      ...prev,
      files: prev.files.map(f =>
        f.id === fileId && f.status === FileUploadStatus.ERROR
          ? { ...f, status: FileUploadStatus.PENDING, error: undefined }
          : f
      )
    }))
  }, [])

  // Analysis polling effect
  useEffect(() => {
    if (!state.analysisId || state.analysisResult) return

    // Track if component is still mounted to prevent state updates after unmount
    let isActive = true

    const pollInterval = setInterval(async () => {
      try {
        const result = await analysisService.getAnalysisStatus(state.analysisId!)

        // Only update state if component is still mounted
        if (!isActive) return

        if (result.success) {
          setState(prev => ({ ...prev, analysisStatus: result.data.status }))

          if (result.data.status === AnalysisStatus.COMPLETED) {
            setState(prev => ({
              ...prev,
              analysisResult: result.data,
              isAnalyzing: false
            }))
            clearInterval(pollInterval)
            addToast({
              type: 'success',
              title: 'Analysis Complete',
              message: 'Your resume analysis is ready!'
            })
          } else if (result.data.status === AnalysisStatus.ERROR) {
            setState(prev => ({ ...prev, isAnalyzing: false }))
            clearInterval(pollInterval)
            addToast({
              type: 'error',
              title: 'Analysis Failed',
              message: result.data.error || 'Analysis failed'
            })
          }
        }
      } catch (error) {
        // Only log if component is still mounted
        if (!isActive) return
        console.error('Failed to poll analysis status:', error)
      }
    }, ANALYSIS_POLL_INTERVAL_MS)

    return () => {
      isActive = false
      clearInterval(pollInterval)
    }
  }, [state.analysisId, state.analysisResult, addToast])

  // Start analysis
  const handleStartAnalysis = async () => {
    const successFiles = state.files.filter(f => f.status === FileUploadStatus.SUCCESS)
    const resumeId = successFiles[0]?.result?.id

    if (!resumeId) {
      addToast({
        type: 'error',
        title: 'No Resume',
        message: 'Please upload a resume first'
      })
      return
    }

    if (!state.selectedIndustry) {
      addToast({
        type: 'error',
        title: 'Industry Required',
        message: 'Please select an industry for analysis'
      })
      return
    }

    setState(prev => ({
      ...prev,
      isAnalyzing: true,
      analysisResult: null,
      analysisStatus: AnalysisStatus.REQUESTING
    }))

    try {
      const result = await analysisService.requestAnalysis(resumeId, state.selectedIndustry)

      if (result.success) {
        setState(prev => ({
          ...prev,
          analysisId: result.data.analysis_id,
          analysisStatus: result.data.status
        }))
        addToast({
          type: 'success',
          title: 'Analysis Started',
          message: 'Your resume is being analyzed...'
        })
      } else {
        throw result.error || new Error('Failed to start analysis')
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start analysis'
      setState(prev => ({ ...prev, isAnalyzing: false }))
      addToast({
        type: 'error',
        title: 'Analysis Failed',
        message: errorMessage
      })
    }
  }

  // Analysis result handlers
  const handleAnalyzeAgain = () => {
    setState(prev => ({
      ...prev,
      analysisResult: null,
      analysisId: null,
      selectedIndustry: ''
    }))
  }

  const handleUploadNew = () => {
    setState(prev => ({
      ...prev,
      files: [],
      analysisResult: null,
      analysisId: null,
      selectedIndustry: ''
    }))
  }

  // Update functions
  const setSelectedCandidate = (candidateId: string) => {
    setState(prev => ({ ...prev, selectedCandidate: candidateId }))
  }

  const setSelectedIndustry = (industry: string) => {
    setState(prev => ({ ...prev, selectedIndustry: industry }))
  }

  // Create handler objects
  const fileHandlers: FileUploadHandlers = {
    onFilesSelected: handleFilesSelected,
    onUploadError: handleUploadError,
    onStartUpload: handleStartUpload,
    onRemoveFile: handleRemoveFile,
    onCancelFile: handleCancelFile,
    onRetryFile: handleRetryFile
  }

  const analysisHandlers: AnalysisHandlers = {
    onStartAnalysis: handleStartAnalysis,
    onAnalyzeAgain: handleAnalyzeAgain,
    onUploadNew: handleUploadNew
  }

  // Computed values (memoized to prevent unnecessary recalculations)
  const pendingFiles = useMemo(
    () => state.files.filter(f => f.status === FileUploadStatus.PENDING),
    [state.files]
  )

  const uploadingFiles = useMemo(
    () => state.files.filter(f => f.status === FileUploadStatus.UPLOADING),
    [state.files]
  )

  const successFiles = useMemo(
    () => state.files.filter(f => f.status === FileUploadStatus.SUCCESS),
    [state.files]
  )

  const errorFiles = useMemo(
    () => state.files.filter(f => f.status === FileUploadStatus.ERROR),
    [state.files]
  )

  return {
    // State
    state,

    // Computed values
    pendingFiles,
    uploadingFiles,
    successFiles,
    errorFiles,

    // Handlers
    fileHandlers,
    analysisHandlers,

    // Direct setters
    setSelectedCandidate,
    setSelectedIndustry
  }
}

export default useUploadFlow