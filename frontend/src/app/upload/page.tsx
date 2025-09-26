'use client'

import React, { useState, useCallback } from 'react'
import { Container, Section, Header } from '../../components/layout'
import { FileUpload } from '../../components/upload'
import { Button, Card, CardHeader, CardContent, CandidateSelector } from '../../components/ui'
import { useToast } from '../../components/ui'
import { UploadFile, FileUploadError } from '../../types'
import { uploadApi } from '../../lib/api'

export default function UploadPage() {
  const [selectedCandidate, setSelectedCandidate] = useState<string>('')
  const [files, setFiles] = useState<UploadFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const { addToast } = useToast()

  // Generate unique file ID
  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  // Handle file selection from FileUpload component
  const handleFilesSelected = useCallback((selectedFiles: File[]) => {
    const newFiles: UploadFile[] = selectedFiles.map(file => ({
      id: generateFileId(),
      file,
      status: 'pending',
      progress: 0
    }))

    setFiles(prev => [...prev, ...newFiles])

    addToast({
      type: 'success',
      title: 'Files Selected',
      message: `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} added`
    })
  }, [addToast])

  // Handle file upload errors
  const handleUploadError = (error: FileUploadError) => {
    addToast({
      type: 'error',
      title: 'Upload Error',
      message: error.message
    })
  }

  // Upload a single file
  const uploadSingleFile = async (uploadFile: UploadFile): Promise<void> => {
    // Update file status to uploading
    setFiles(prev => prev.map(f =>
      f.id === uploadFile.id
        ? { ...f, status: 'uploading' as const, progress: 0 }
        : f
    ))

    // Create abort controller for this upload
    const abortController = new AbortController()

    // Store abort controller in file state
    setFiles(prev => prev.map(f =>
      f.id === uploadFile.id
        ? { ...f, abortController }
        : f
    ))

    try {
      const result = await uploadApi.uploadFile(
        uploadFile.file,
        selectedCandidate,
        // Progress callback
        (progressEvent) => {
          const percentage = (progressEvent.loaded / (progressEvent.total || uploadFile.file.size)) * 100
          setFiles(prev => prev.map(f =>
            f.id === uploadFile.id
              ? { ...f, progress: Math.round(percentage) }
              : f
          ))
        },
        abortController
      )

      if (result.success) {
        // Upload successful
        setFiles(prev => prev.map(f =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: 'success' as const,
                progress: 100,
                result: result.data,
                abortController: undefined
              }
            : f
        ))

        addToast({
          type: 'success',
          title: 'Upload Complete',
          message: `${uploadFile.file.name} uploaded successfully`
        })
      } else {
        throw result.error || new Error('Upload failed')
      }
    } catch (error: any) {
      // Check if upload was cancelled
      if (error.name === 'AbortError' || error.message.includes('cancelled')) {
        setFiles(prev => prev.map(f =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: 'cancelled' as const,
                abortController: undefined
              }
            : f
        ))
      } else {
        // Upload failed
        setFiles(prev => prev.map(f =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: 'error' as const,
                error: error.message || 'Upload failed',
                abortController: undefined
              }
            : f
        ))

        addToast({
          type: 'error',
          title: 'Upload Failed',
          message: `Failed to upload ${uploadFile.file.name}: ${error.message}`
        })
      }
    }
  }

  // Start uploading all pending files
  const handleStartUpload = async () => {
    if (!selectedCandidate) {
      addToast({
        type: 'error',
        title: 'Candidate Required',
        message: 'Please select a candidate before uploading files'
      })
      return
    }

    const pendingFiles = files.filter(f => f.status === 'pending')
    if (pendingFiles.length === 0) return

    setIsUploading(true)

    // Upload files concurrently with limit of 3
    const uploadPromises = pendingFiles.map(file => uploadSingleFile(file))

    try {
      await Promise.all(uploadPromises)

      const successCount = files.filter(f => f.status === 'success').length
      addToast({
        type: 'success',
        title: 'Uploads Complete',
        message: `${successCount} file${successCount !== 1 ? 's' : ''} uploaded successfully!`
      })
    } catch (error) {
      // Individual file errors are already handled in uploadSingleFile
      console.error('Batch upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  // Remove file from list
  const handleRemoveFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  // Cancel file upload
  const handleCancelFile = (fileId: string) => {
    const file = files.find(f => f.id === fileId)
    if (file?.abortController) {
      file.abortController.abort()
    }
  }

  // Retry failed upload
  const handleRetryFile = (fileId: string) => {
    const file = files.find(f => f.id === fileId)
    if (file && file.status === 'error') {
      setFiles(prev => prev.map(f =>
        f.id === fileId
          ? { ...f, status: 'pending' as const, error: undefined }
          : f
      ))
    }
  }

  const pendingFiles = files.filter(f => f.status === 'pending')
  const uploadingFiles = files.filter(f => f.status === 'uploading')
  const successFiles = files.filter(f => f.status === 'success')
  const errorFiles = files.filter(f => f.status === 'error')

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

            <div className="space-y-8">
              {/* Candidate Selection */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Step 1: Select Candidate
                  </h2>
                </CardHeader>
                <CardContent>
                  <CandidateSelector
                    value={selectedCandidate}
                    onSelect={setSelectedCandidate}
                    placeholder="Select a candidate..."
                    required={true}
                  />
                </CardContent>
              </Card>

              {/* File Upload */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Step 2: Select Resume Files
                  </h2>
                </CardHeader>
                <CardContent>
                  <FileUpload
                    onFilesSelected={handleFilesSelected}
                    onError={handleUploadError}
                    disabled={isUploading || !selectedCandidate}
                    multiple={true}
                    maxFiles={5}
                  />
                  {!selectedCandidate && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm text-yellow-800">
                        Please select a candidate first before uploading files.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* File List */}
              {files.length > 0 && (
                <Card>
                  <CardHeader>
                    <h2 className="text-xl font-semibold text-neutral-900">
                      Selected Files ({files.length})
                    </h2>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {files.map((file) => (
                        <div key={file.id} className="border rounded-lg p-4 bg-white">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center space-x-3">
                                <span className="font-medium text-gray-900">
                                  {file.file.name}
                                </span>
                                <span className="text-sm text-gray-500">
                                  ({(file.file.size / 1024 / 1024).toFixed(1)} MB)
                                </span>
                                <StatusBadge status={file.status} />
                              </div>

                              {file.status === 'uploading' && (
                                <div className="mt-2">
                                  <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                      style={{ width: `${file.progress}%` }}
                                    ></div>
                                  </div>
                                  <span className="text-sm text-gray-500 mt-1">
                                    {file.progress}% uploaded
                                  </span>
                                </div>
                              )}

                              {file.error && (
                                <p className="text-sm text-red-600 mt-1">{file.error}</p>
                              )}
                            </div>

                            <div className="flex items-center space-x-2">
                              {file.status === 'uploading' && (
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => handleCancelFile(file.id)}
                                >
                                  Cancel
                                </Button>
                              )}

                              {file.status === 'error' && (
                                <Button
                                  size="sm"
                                  onClick={() => handleRetryFile(file.id)}
                                >
                                  Retry
                                </Button>
                              )}

                              {['pending', 'error', 'cancelled'].includes(file.status) && (
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => handleRemoveFile(file.id)}
                                >
                                  Remove
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Upload Actions */}
              {files.length > 0 && (
                <div className="flex justify-center space-x-4">
                  {pendingFiles.length > 0 && (
                    <Button
                      size="lg"
                      onClick={handleStartUpload}
                      disabled={isUploading || !selectedCandidate}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white"
                    >
                      {isUploading ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
                          Uploading...
                        </>
                      ) : (
                        `Upload ${pendingFiles.length} File${pendingFiles.length !== 1 ? 's' : ''}`
                      )}
                    </Button>
                  )}

                  {successFiles.length > 0 && uploadingFiles.length === 0 && (
                    <Button
                      size="lg"
                      variant="secondary"
                      className="bg-green-600 hover:bg-green-700 text-white"
                      onClick={() => {
                        addToast({
                          type: 'success',
                          title: 'Ready for Analysis',
                          message: `${successFiles.length} resume${successFiles.length !== 1 ? 's' : ''} ready for AI analysis`
                        })
                      }}
                    >
                      Proceed to Analysis ({successFiles.length} ready)
                    </Button>
                  )}
                </div>
              )}

              {/* Summary Stats */}
              {files.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-gray-600">{files.length}</div>
                      <div className="text-sm text-gray-500">Total Files</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-blue-600">{uploadingFiles.length}</div>
                      <div className="text-sm text-gray-500">Uploading</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-600">{successFiles.length}</div>
                      <div className="text-sm text-gray-500">Completed</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-red-600">{errorFiles.length}</div>
                      <div className="text-sm text-gray-500">Failed</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Container>
      </main>
    </div>
  )
}

// Status badge component
function StatusBadge({ status }: { status: UploadFile['status'] }) {
  const styles = {
    pending: 'bg-gray-100 text-gray-800',
    uploading: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800'
  }

  const labels = {
    pending: 'Pending',
    uploading: 'Uploading',
    success: 'Success',
    error: 'Error',
    cancelled: 'Cancelled'
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}