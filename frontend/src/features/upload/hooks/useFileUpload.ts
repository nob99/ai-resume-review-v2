import { useState, useCallback, useMemo } from 'react'
import { UploadFile, FileUploadError } from '@/types'
import { uploadApi } from '@/lib/api'
import { FileUploadStatus } from '../constants'

/**
 * File Upload State
 */
export interface FileUploadState {
  files: UploadFile[]
  isUploading: boolean
}

/**
 * File Upload Actions
 */
export interface FileUploadActions {
  onFilesSelected: (files: File[]) => void
  onUploadError: (error: FileUploadError) => void
  onStartUpload: () => Promise<void>
  onRemoveFile: (fileId: string) => void
  onCancelFile: (fileId: string) => void
  onRetryFile: (fileId: string) => void
  clearFiles: () => void
}

/**
 * Computed File Arrays
 */
export interface ComputedFileArrays {
  pendingFiles: UploadFile[]
  uploadingFiles: UploadFile[]
  successFiles: UploadFile[]
  errorFiles: UploadFile[]
}

/**
 * Custom hook for managing file upload operations
 * Handles file selection, upload progress, cancellation, and retry
 *
 * Note: Toast notifications removed - UI feedback provided by:
 * - FileList component (file selection, inline errors)
 * - FileStatusBadge component (upload status)
 * - Progress bars (upload completion)
 */
export function useFileUpload(
  candidateId: string
): {
  state: FileUploadState
  actions: FileUploadActions
  computed: ComputedFileArrays
} {
  const [state, setState] = useState<FileUploadState>({
    files: [],
    isUploading: false
  })

  // Generate unique file ID using Web Crypto API
  const generateFileId = useCallback(() => {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID()
    }
    // Fallback for older browsers
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }, [])

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

    // File selection feedback provided by FileList component rendering
    // toast.success('Files Selected', `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} added`)
  }, [generateFileId])

  // Handle upload errors
  const handleUploadError = useCallback((error: FileUploadError) => {
    // Error handling - UI feedback provided by FileUpload component
    console.error('Upload error:', error.message)
  }, [])

  // Upload a single file
  const uploadSingleFile = useCallback(async (uploadFile: UploadFile): Promise<void> => {
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
      const result = await uploadApi.uploadFile(
        uploadFile.file,
        candidateId,
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

        // Upload success feedback provided by FileStatusBadge and progress bar
        // toast.success('Upload Complete', `${uploadFile.file.name} uploaded successfully`)
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

        // Upload error feedback provided by inline error message in FileList component
        // toast.error('Upload Failed', `Failed to upload ${uploadFile.file.name}: ${errorMessage}`)
      }
    }
  }, [candidateId])

  // Start uploading all pending files
  const handleStartUpload = useCallback(async () => {
    // Defensive check - UI should prevent this, but guard against edge cases
    if (!candidateId) {
      console.error('Upload attempted without candidate selection')
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
      // Simplified: Just update isUploading state
      // File status badges and inline errors provide all necessary feedback
      setState(prev => ({ ...prev, isUploading: false }))

      /* OLD BATCH SUMMARY LOGIC (commented out - kept for reference):
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
        toast.success(
          'All Uploads Complete',
          `${successCount} file${successCount !== 1 ? 's' : ''} uploaded successfully!`
        )
      } else if (successCount > 0 && errorCount > 0) {
        toast.warning(
          'Partial Success',
          `${successCount} succeeded, ${errorCount} failed. Check files below.`
        )
      } else if (errorCount > 0) {
        toast.error(
          'Upload Failed',
          `${errorCount} file${errorCount !== 1 ? 's' : ''} failed to upload. Please retry.`
        )
      }
      */
    }
  }, [candidateId, state.files, uploadSingleFile])

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

  const clearFiles = useCallback(() => {
    setState({
      files: [],
      isUploading: false
    })
  }, [])

  // Computed values (memoized to prevent unnecessary recalculations)
  const computed = useMemo(() => ({
    pendingFiles: state.files.filter(f => f.status === FileUploadStatus.PENDING),
    uploadingFiles: state.files.filter(f => f.status === FileUploadStatus.UPLOADING),
    successFiles: state.files.filter(f => f.status === FileUploadStatus.SUCCESS),
    errorFiles: state.files.filter(f => f.status === FileUploadStatus.ERROR)
  }), [state.files])

  // Create action object
  const actions: FileUploadActions = {
    onFilesSelected: handleFilesSelected,
    onUploadError: handleUploadError,
    onStartUpload: handleStartUpload,
    onRemoveFile: handleRemoveFile,
    onCancelFile: handleCancelFile,
    onRetryFile: handleRetryFile,
    clearFiles
  }

  return {
    state,
    actions,
    computed
  }
}

export default useFileUpload