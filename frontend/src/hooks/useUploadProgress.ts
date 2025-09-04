import { useState, useCallback, useRef, useEffect } from 'react'
import {
  DetailedProgressInfo,
  UploadProgressState,
  UploadCancellationToken,
  UploadProgressEvent,
  TimeEstimation,
} from '../types'

interface UseUploadProgressOptions {
  maxRetries?: number
  retryDelay?: number
  onProgressUpdate?: (fileId: string, progress: DetailedProgressInfo) => void
  onComplete?: (fileId: string) => void
  onError?: (fileId: string, error: Error) => void
}

export const useUploadProgress = (options: UseUploadProgressOptions = {}) => {
  const {
    maxRetries = 3,
    retryDelay = 1000,
    onProgressUpdate,
    onComplete,
    onError,
  } = options

  const [progressState, setProgressState] = useState<UploadProgressState>({
    files: new Map(),
    overallProgress: 0,
    totalFiles: 0,
    completedFiles: 0,
    failedFiles: 0,
    isUploading: false,
    startTime: 0,
    estimatedTotalTime: 0,
  })

  const cancellationTokens = useRef<Map<string, UploadCancellationToken>>(new Map())
  const progressIntervals = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Calculate time estimation for a single file
  const calculateTimeEstimation = useCallback((
    bytesUploaded: number,
    totalBytes: number,
    startTime: number
  ): TimeEstimation => {
    const now = Date.now()
    const timeElapsed = Math.max(now - startTime, 1) // Ensure minimum 1ms
    const speed = bytesUploaded > 0 ? (bytesUploaded / timeElapsed) * 1000 : 0
    const remainingBytes = totalBytes - bytesUploaded
    const remaining = speed > 0 ? (remainingBytes / speed) * 1000 : 0
    const percentage = totalBytes > 0 ? (bytesUploaded / totalBytes) * 100 : 0

    // Format remaining time as "2m 30s"
    const minutes = Math.floor(remaining / 60000)
    const seconds = Math.floor((remaining % 60000) / 1000)
    const formattedRemaining = 
      minutes > 0 
        ? `${minutes}m ${seconds}s`
        : `${seconds}s`

    return {
      remaining,
      percentage,
      speed,
      formattedRemaining,
    }
  }, [])

  // Initialize progress for a new file
  const initializeProgress = useCallback((fileId: string, fileName: string, fileSize: number) => {
    const progressInfo: DetailedProgressInfo = {
      fileId,
      fileName,
      stage: 'queued',
      percentage: 0,
      bytesUploaded: 0,
      totalBytes: fileSize,
      timeElapsed: 0,
      estimatedTimeRemaining: 0,
      speed: 0,
      retryCount: 0,
      maxRetries,
    }

    setProgressState(prev => {
      const newFiles = new Map(prev.files)
      newFiles.set(fileId, progressInfo)
      return {
        ...prev,
        files: newFiles,
        totalFiles: newFiles.size,
        isUploading: true,
        startTime: prev.startTime || Date.now(),
      }
    })

    // Create cancellation token
    const abortController = new AbortController()
    cancellationTokens.current.set(fileId, {
      fileId,
      abortController,
      timestamp: Date.now(),
    })

    return abortController
  }, [maxRetries])

  // Update progress for a specific file
  const updateProgress = useCallback((
    fileId: string,
    updates: Partial<DetailedProgressInfo>
  ) => {
    setProgressState(prev => {
      const currentFile = prev.files.get(fileId)
      if (!currentFile) return prev

      const updatedFile = {
        ...currentFile,
        ...updates,
      }

      // Calculate time estimation if bytes updated
      if (updates.bytesUploaded !== undefined) {
        const startTime = prev.startTime || Date.now()
        const timeEstimation = calculateTimeEstimation(
          updates.bytesUploaded,
          currentFile.totalBytes,
          startTime
        )
        updatedFile.speed = timeEstimation.speed
        updatedFile.estimatedTimeRemaining = timeEstimation.remaining
        updatedFile.percentage = timeEstimation.percentage
        updatedFile.timeElapsed = Date.now() - startTime
      }

      const newFiles = new Map(prev.files)
      newFiles.set(fileId, updatedFile)

      // Calculate overall progress
      let totalProgress = 0
      let completedFiles = 0
      let failedFiles = 0
      
      newFiles.forEach(file => {
        totalProgress += file.percentage
        if (file.stage === 'completed') completedFiles++
        if (file.stage === 'error') failedFiles++
      })

      const overallProgress = newFiles.size > 0 ? totalProgress / newFiles.size : 0
      const isUploading = Array.from(newFiles.values()).some(
        file => file.stage === 'uploading' || file.stage === 'validating' || file.stage === 'extracting'
      )

      // Trigger callback if provided
      if (onProgressUpdate) {
        onProgressUpdate(fileId, updatedFile)
      }

      // Check for completion
      if (updatedFile.stage === 'completed' && onComplete) {
        onComplete(fileId)
      }

      return {
        ...prev,
        files: newFiles,
        overallProgress,
        completedFiles,
        failedFiles,
        isUploading,
      }
    })
  }, [calculateTimeEstimation, onProgressUpdate, onComplete])

  // Update stage for a file
  const updateStage = useCallback((
    fileId: string,
    stage: DetailedProgressInfo['stage']
  ) => {
    updateProgress(fileId, { stage })
  }, [updateProgress])

  // Cancel upload for a specific file
  const cancelUpload = useCallback((fileId: string) => {
    const token = cancellationTokens.current.get(fileId)
    if (token) {
      token.abortController.abort()
      cancellationTokens.current.delete(fileId)
    }

    // Clear any progress interval
    const interval = progressIntervals.current.get(fileId)
    if (interval) {
      clearInterval(interval)
      progressIntervals.current.delete(fileId)
    }

    updateProgress(fileId, {
      stage: 'cancelled',
      percentage: 0,
    })
  }, [updateProgress])

  // Cancel all uploads
  const cancelAllUploads = useCallback(() => {
    cancellationTokens.current.forEach((token, fileId) => {
      cancelUpload(fileId)
    })
  }, [cancelUpload])

  // Retry upload for a failed file
  const retryUpload = useCallback((fileId: string): AbortController | null => {
    const file = progressState.files.get(fileId)
    if (!file || file.retryCount >= maxRetries) {
      return null
    }

    // Create new abort controller
    const abortController = new AbortController()
    cancellationTokens.current.set(fileId, {
      fileId,
      abortController,
      timestamp: Date.now(),
    })

    // Reset progress with incremented retry count
    updateProgress(fileId, {
      stage: 'queued',
      percentage: 0,
      bytesUploaded: 0,
      retryCount: file.retryCount + 1,
      error: undefined,
    })

    return abortController
  }, [progressState.files, maxRetries, updateProgress])

  // Handle error with retry logic
  const handleError = useCallback((fileId: string, error: Error) => {
    const file = progressState.files.get(fileId)
    if (!file) return

    if (file.retryCount < maxRetries) {
      // Schedule retry
      setTimeout(() => {
        retryUpload(fileId)
      }, retryDelay * Math.pow(2, file.retryCount)) // Exponential backoff
    } else {
      // Max retries reached
      updateProgress(fileId, {
        stage: 'error',
        percentage: 0,
      })
      
      if (onError) {
        onError(fileId, error)
      }
    }
  }, [progressState.files, maxRetries, retryDelay, retryUpload, updateProgress, onError])

  // Simulate progress for demo/testing
  const simulateProgress = useCallback((
    fileId: string,
    duration: number = 5000
  ) => {
    const stages: Array<DetailedProgressInfo['stage']> = [
      'uploading',
      'validating',
      'extracting',
      'completed'
    ]
    
    let currentStageIndex = 0
    let progress = 0
    const totalSteps = 40
    const increment = 100 / totalSteps
    const fileSize = 1024 * 1024 // 1MB for simulation
    let stepCount = 0

    // Start with uploading stage
    updateStage(fileId, 'uploading')

    const interval = setInterval(() => {
      stepCount++
      progress += increment
      
      // Update stage based on progress thresholds
      const stageThresholds = [25, 50, 75, 100] // 25% each stage
      const newStageIndex = stageThresholds.findIndex(threshold => progress < threshold)
      const targetStageIndex = newStageIndex === -1 ? stages.length - 1 : newStageIndex
      
      if (targetStageIndex !== currentStageIndex && targetStageIndex < stages.length) {
        currentStageIndex = targetStageIndex
        updateStage(fileId, stages[currentStageIndex])
      }

      if (progress >= 100 || stepCount >= totalSteps) {
        clearInterval(interval)
        progressIntervals.current.delete(fileId)
        updateProgress(fileId, {
          stage: 'completed',
          percentage: 100,
          bytesUploaded: fileSize,
        })
        updateStage(fileId, 'completed')
      } else {
        updateProgress(fileId, {
          percentage: Math.min(progress, 100),
          bytesUploaded: Math.floor((progress / 100) * fileSize),
        })
      }
    }, duration / totalSteps)

    progressIntervals.current.set(fileId, interval)
  }, [updateStage, updateProgress])

  // Get progress for a specific file
  const getFileProgress = useCallback((fileId: string): DetailedProgressInfo | undefined => {
    return progressState.files.get(fileId)
  }, [progressState.files])

  // Get cancellation token for a file
  const getCancellationToken = useCallback((fileId: string): AbortController | undefined => {
    return cancellationTokens.current.get(fileId)?.abortController
  }, [])

  // Reset all progress
  const resetProgress = useCallback(() => {
    // Cancel all active uploads
    cancelAllUploads()
    
    // Clear all intervals
    progressIntervals.current.forEach(interval => clearInterval(interval))
    progressIntervals.current.clear()
    
    // Reset state
    setProgressState({
      files: new Map(),
      overallProgress: 0,
      totalFiles: 0,
      completedFiles: 0,
      failedFiles: 0,
      isUploading: false,
      startTime: 0,
      estimatedTotalTime: 0,
    })
  }, [cancelAllUploads])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAllUploads()
      progressIntervals.current.forEach(interval => clearInterval(interval))
    }
  }, [cancelAllUploads])

  return {
    progressState,
    initializeProgress,
    updateProgress,
    updateStage,
    cancelUpload,
    cancelAllUploads,
    retryUpload,
    handleError,
    simulateProgress,
    getFileProgress,
    getCancellationToken,
    resetProgress,
    calculateTimeEstimation,
  }
}