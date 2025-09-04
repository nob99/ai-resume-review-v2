'use client'

import React, { useState, useCallback } from 'react'
import { Container, Section, Header } from '../../components/layout'
import { FileUpload, FilePreview, UploadProgressDashboard } from '../../components/upload'
import { Button, Card, CardHeader, CardContent, Alert } from '../../components/ui'
import { useToast } from '../../components/ui'
import { UploadedFile, UploadedFileV2, FileUploadError } from '../../types'
import { useUploadProgress } from '../../hooks/useUploadProgress'
import { uploadApi } from '../../lib/api'

export default function UploadPage() {
  const [selectedFiles, setSelectedFiles] = useState<UploadedFileV2[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [showDetailedProgress, setShowDetailedProgress] = useState(false)
  const { addToast } = useToast()
  
  // Initialize upload progress hook
  const {
    progressState,
    initializeProgress,
    updateProgress,
    updateStage,
    cancelUpload,
    retryUpload,
    handleError,
    resetProgress,
    getFileProgress,
    simulateProgress
  } = useUploadProgress({
    maxRetries: 3,
    onComplete: (fileId) => {
      addToast({
        type: 'success',
        title: 'Upload Complete',
        message: `File ${fileId} uploaded successfully`
      })
    },
    onError: (fileId, error) => {
      addToast({
        type: 'error', 
        title: 'Upload Failed',
        message: `Failed to upload file: ${error.message}`
      })
    }
  })

  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  const handleFilesSelected = useCallback((files: File[]) => {
    const newFiles: UploadedFileV2[] = files.map(file => {
      const fileId = generateFileId()
      const uploadedFile: UploadedFileV2 = {
        file,
        id: fileId,
        status: 'pending',
        progress: 0,
        progressInfo: {
          fileId,
          fileName: file.name,
          stage: 'queued',
          percentage: 0,
          bytesUploaded: 0,
          totalBytes: file.size,
          timeElapsed: 0,
          estimatedTimeRemaining: 0,
          speed: 0,
          retryCount: 0,
          maxRetries: 3
        }
      }
      
      return uploadedFile
    })

    setSelectedFiles(prev => [...prev, ...newFiles])
    
    addToast({
      type: 'success',
      title: 'Files Selected',
      message: `${files.length} file${files.length !== 1 ? 's' : ''} selected successfully`
    })
  }, [addToast])

  const handleUploadError = (error: FileUploadError) => {
    addToast({
      type: 'error',
      title: 'Upload Error',
      message: error.message
    })
  }

  const handleRemoveFile = useCallback((fileId: string) => {
    // Cancel any ongoing upload
    cancelUpload(fileId)
    
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId))
    
    addToast({
      type: 'info',
      title: 'File Removed',
      message: 'File removed from upload queue'
    })
  }, [cancelUpload, addToast])

  const handleRetryFile = useCallback((fileId: string) => {
    const file = selectedFiles.find(f => f.id === fileId)
    if (!file) return
    
    // Reset the file status and start upload process
    setSelectedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { 
              ...f, 
              status: 'pending', 
              progress: 0, 
              error: undefined,
              progressInfo: {
                ...f.progressInfo!,
                stage: 'queued',
                percentage: 0,
                bytesUploaded: 0,
                retryCount: (f.progressInfo?.retryCount || 0) + 1
              }
            }
          : f
      )
    )
    
    // Start the upload process for this file
    processFile(file.file, fileId)
  }, [selectedFiles])

  const handleCancelFile = useCallback((fileId: string) => {
    cancelUpload(fileId)
    
    setSelectedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { 
              ...f, 
              status: 'cancelled',
              progressInfo: {
                ...f.progressInfo!,
                stage: 'cancelled'
              }
            }
          : f
      )
    )
    
    addToast({
      type: 'info',
      title: 'Upload Cancelled',
      message: 'File upload has been cancelled'
    })
  }, [cancelUpload, addToast])

  // Process a single file with real upload or simulation
  const processFile = useCallback(async (file: File, fileId: string): Promise<void> => {
    const updateFileStatus = (updates: Partial<UploadedFileV2>) => {
      setSelectedFiles(prev => 
        prev.map(f => f.id === fileId ? { ...f, ...updates } : f)
      )
    }

    // Initialize progress tracking
    const abortController = initializeProgress(fileId, file.name, file.size)
    
    try {
      // Update file with cancellation token
      updateFileStatus({
        cancellationToken: {
          fileId,
          abortController,
          timestamp: Date.now()
        },
        startTime: Date.now()
      })

      // Use real upload API or simulation based on environment
      const useSimulation = process.env.NODE_ENV === 'development' || !process.env.NEXT_PUBLIC_API_URL
      
      if (useSimulation) {
        // Simulate upload with detailed progress
        simulateProgress(fileId, 8000) // 8 second simulation
        
        // Wait for simulation to complete
        await new Promise(resolve => {
          const checkProgress = () => {
            const progress = getFileProgress(fileId)
            if (progress?.stage === 'completed' || progress?.stage === 'error') {
              // Add mock extracted text
              if (progress.stage === 'completed') {
                const mockExtractedText = `This is a sample resume for ${file.name}.
                
John Doe
Software Engineer

Experience:
- 5+ years in full-stack development
- Expertise in React, Node.js, TypeScript
- Led teams of 3-5 developers

Education:
- Computer Science, University of Technology
- Graduated Magna Cum Laude

Skills: JavaScript, Python, AWS, Docker, Kubernetes`

                updateFileStatus({
                  status: 'completed',
                  extractedText: mockExtractedText,
                  endTime: Date.now()
                })
              }
              resolve(undefined)
            } else {
              setTimeout(checkProgress, 100)
            }
          }
          checkProgress()
        })
      } else {
        // Real upload implementation
        updateStage(fileId, 'uploading')
        
        const result = await uploadApi.uploadFile(
          file,
          (progressEvent) => {
            const percentage = (progressEvent.loaded / (progressEvent.total || file.size)) * 100
            updateProgress(fileId, {
              bytesUploaded: progressEvent.loaded,
              percentage
            })
          },
          abortController
        )

        if (!result.success) {
          throw result.error
        }

        // Update with completed file data
        updateFileStatus({
          status: 'completed',
          progress: 100,
          extractedText: result.data?.extractedText,
          endTime: Date.now()
        })
        
        updateStage(fileId, 'completed')
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        // Upload was cancelled
        updateFileStatus({
          status: 'cancelled'
        })
        updateStage(fileId, 'cancelled')
      } else {
        // Upload failed
        updateFileStatus({
          status: 'error',
          error: error.message || 'Failed to upload file. Please try again.',
          endTime: Date.now()
        })
        updateStage(fileId, 'error')
        handleError(fileId, error)
      }
    }
  }, [initializeProgress, simulateProgress, getFileProgress, updateStage, updateProgress, handleError])

  const handleStartUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return

    setIsProcessing(true)
    setShowDetailedProgress(true)
    
    const pendingFiles = selectedFiles.filter(f => f.status === 'pending')
    
    addToast({
      type: 'info',
      title: 'Upload Started',
      message: `Uploading ${pendingFiles.length} file${pendingFiles.length !== 1 ? 's' : ''}...`
    })

    // Process files concurrently with a limit
    const concurrentLimit = 3
    const processingPromises: Promise<void>[] = []
    
    for (let i = 0; i < pendingFiles.length; i += concurrentLimit) {
      const batch = pendingFiles.slice(i, i + concurrentLimit)
      const batchPromises = batch.map(file => processFile(file.file, file.id))
      processingPromises.push(...batchPromises)
      
      // Add slight delay between batches to prevent overwhelming the server
      if (i + concurrentLimit < pendingFiles.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }

    try {
      await Promise.all(processingPromises)
      
      const completedCount = selectedFiles.filter(f => {
        const progressInfo = getFileProgress(f.id)
        return progressInfo?.stage === 'completed'
      }).length
      
      addToast({
        type: 'success',
        title: 'Upload Complete',
        message: `${completedCount} file${completedCount !== 1 ? 's' : ''} uploaded successfully!`
      })
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Upload Error',
        message: 'Some files failed to upload. Check individual files for details.'
      })
    } finally {
      setIsProcessing(false)
    }
  }, [selectedFiles, processFile, getFileProgress, addToast])

  const handleProceedToAnalysis = () => {
    const completedFiles = selectedFiles.filter(f => f.status === 'completed')
    
    addToast({
      type: 'success',
      title: 'Ready for Analysis',
      message: `${completedFiles.length} resume${completedFiles.length !== 1 ? 's' : ''} ready for AI analysis`
    })

    // In a real app, this would navigate to the analysis page
    console.log('Proceeding to analysis with files:', completedFiles)
  }

  // Helper functions to get current file status
  const getFileDisplayStatus = (file: UploadedFileV2) => {
    const progressInfo = getFileProgress(file.id)
    return progressInfo?.stage || file.status
  }

  const pendingFiles = selectedFiles.filter(f => getFileDisplayStatus(f) === 'pending' || getFileDisplayStatus(f) === 'queued')
  const completedFiles = selectedFiles.filter(f => getFileDisplayStatus(f) === 'completed')
  const processingFiles = selectedFiles.filter(f => ['uploading', 'validating', 'extracting'].includes(getFileDisplayStatus(f)))
  const errorFiles = selectedFiles.filter(f => getFileDisplayStatus(f) === 'error')
  const cancelledFiles = selectedFiles.filter(f => getFileDisplayStatus(f) === 'cancelled')
  const hasProcessingFiles = processingFiles.length > 0

  return (
    <div className="min-h-screen bg-neutral-50">
      <Header />
      
      <main className="py-8">
        <Container size="lg">
          <div className="max-w-4xl mx-auto">
            {/* Page Header */}
            <Section className="text-center mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                Upload Resume Files
              </h1>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                Upload your resume files to get started with AI-powered analysis. 
                Support for PDF and Word documents up to 10MB each.
              </p>
            </Section>

            {/* Upload Progress Steps */}
            <div className="mb-8">
              <div className="flex items-center justify-center space-x-8">
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    selectedFiles.length > 0 
                      ? 'bg-success-500 text-white' 
                      : 'bg-neutral-200 text-neutral-500'
                  }`}>
                    1
                  </div>
                  <span className="text-sm font-medium text-neutral-700">Select Files</span>
                </div>
                
                <div className={`w-12 h-0.5 ${
                  pendingFiles.length === 0 && selectedFiles.length > 0
                    ? 'bg-success-500' 
                    : 'bg-neutral-200'
                }`}></div>
                
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    pendingFiles.length === 0 && selectedFiles.length > 0
                      ? 'bg-success-500 text-white'
                      : hasProcessingFiles
                        ? 'bg-primary-500 text-white'
                        : 'bg-neutral-200 text-neutral-500'
                  }`}>
                    {hasProcessingFiles ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    ) : (
                      '2'
                    )}
                  </div>
                  <span className="text-sm font-medium text-neutral-700">Upload Files</span>
                </div>
                
                <div className={`w-12 h-0.5 ${
                  completedFiles.length > 0 ? 'bg-success-500' : 'bg-neutral-200'
                }`}></div>
                
                <div className="flex items-center space-x-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    completedFiles.length > 0 
                      ? 'bg-success-500 text-white' 
                      : 'bg-neutral-200 text-neutral-500'
                  }`}>
                    3
                  </div>
                  <span className="text-sm font-medium text-neutral-700">AI Analysis</span>
                </div>
              </div>
            </div>

            {/* Upload Area */}
            <div className="space-y-8">
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Select Resume Files
                  </h2>
                  <p className="text-sm text-neutral-600">
                    Drag and drop your resume files or click to browse
                  </p>
                </CardHeader>
                <CardContent>
                  <FileUpload
                    onFilesSelected={handleFilesSelected}
                    onError={handleUploadError}
                    disabled={isProcessing}
                    multiple={true}
                    maxFiles={5}
                  />
                </CardContent>
              </Card>

              {/* Progress Dashboard */}
              {showDetailedProgress && progressState.files.size > 0 && (
                <UploadProgressDashboard
                  progressState={progressState}
                  onCancelUpload={handleCancelFile}
                  onRetryUpload={handleRetryFile}
                />
              )}

              {/* File Preview */}
              {selectedFiles.length > 0 && (
                <FilePreview
                  files={selectedFiles}
                  onRemove={handleRemoveFile}
                  onRetry={handleRetryFile}
                  onCancel={handleCancelFile}
                  showDetailedProgress={showDetailedProgress}
                  readOnly={isProcessing}
                />
              )}

              {/* Action Buttons */}
              {selectedFiles.length > 0 && (
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                    {pendingFiles.length > 0 && (
                      <Button
                        size="lg"
                        onClick={handleStartUpload}
                        disabled={isProcessing}
                        className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                      >
                        {isProcessing ? (
                          <>
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
                            Uploading Files...
                          </>
                        ) : (
                          <>
                            <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            Upload {pendingFiles.length} File{pendingFiles.length !== 1 ? 's' : ''}
                          </>
                        )}
                      </Button>
                    )}

                    {completedFiles.length > 0 && !hasProcessingFiles && (
                      <Button
                        size="lg"
                        variant="secondary"
                        onClick={handleProceedToAnalysis}
                        className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-8 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                      >
                        <>
                          <svg className="w-5 h-5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                          Proceed to Analysis ({completedFiles.length} ready)
                        </>
                      </Button>
                    )}
                  </div>

                  {/* Progress View Toggle */}
                  {(hasProcessingFiles || progressState.files.size > 0) && (
                    <div className="flex justify-center">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowDetailedProgress(!showDetailedProgress)}
                        className="text-sm"
                      >
                        {showDetailedProgress ? 'Hide' : 'Show'} Detailed Progress
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Help Text */}
              {selectedFiles.length === 0 && (
                <Alert>
                  <h3 className="font-medium mb-2">Getting Started</h3>
                  <ul className="text-sm space-y-1 list-disc list-inside">
                    <li>Upload PDF, DOC, or DOCX resume files</li>
                    <li>Maximum file size: 10MB per file</li>
                    <li>You can upload up to 5 files at once</li>
                    <li>Files are processed securely and not stored permanently</li>
                  </ul>
                </Alert>
              )}
            </div>
          </div>
        </Container>
      </main>
    </div>
  )
}