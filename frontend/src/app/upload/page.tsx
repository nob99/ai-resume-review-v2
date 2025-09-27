'use client'

import React, { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Container, Section, Header } from '../../components/layout'
import { FileUpload } from '../../components/upload'
import { Button, Card, CardHeader, CardContent, CandidateSelector } from '../../components/ui'
import { useToast } from '../../components/ui'
import { UploadFile, FileUploadError } from '../../types'
import { uploadApi, analysisApi } from '../../lib/api'

// Industry options for analysis
const INDUSTRY_OPTIONS = [
  { value: 'strategy_tech', label: 'Strategy/Tech' },
  { value: 'ma_financial', label: 'M&A/Financial Advisory' },
  { value: 'consulting', label: 'Full Service Consulting' },
  { value: 'system_integrator', label: 'System Integrator' },
  { value: 'general', label: 'General' }
]

export default function UploadPage() {
  const router = useRouter()
  const [selectedCandidate, setSelectedCandidate] = useState<string>('')
  const [files, setFiles] = useState<UploadFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const { addToast } = useToast()

  // Analysis state
  const [selectedIndustry, setSelectedIndustry] = useState<string>('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [analysisStatus, setAnalysisStatus] = useState<string>('')

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

  // Poll for analysis status
  useEffect(() => {
    if (!analysisId || analysisResult) return

    const pollInterval = setInterval(async () => {
      try {
        const result = await analysisApi.getAnalysisStatus(analysisId)
        if (result.success) {
          setAnalysisStatus(result.data.status)

          if (result.data.status === 'completed') {
            setAnalysisResult(result.data.result)
            setIsAnalyzing(false)
            clearInterval(pollInterval)
            addToast({
              type: 'success',
              title: 'Analysis Complete',
              message: 'Your resume analysis is ready!'
            })
          } else if (result.data.status === 'error') {
            setIsAnalyzing(false)
            clearInterval(pollInterval)
            addToast({
              type: 'error',
              title: 'Analysis Failed',
              message: result.data.error || 'Analysis failed'
            })
          }
        }
      } catch (error) {
        console.error('Failed to poll analysis status:', error)
      }
    }, 3000)

    return () => clearInterval(pollInterval)
  }, [analysisId, analysisResult, addToast])

  // Start analysis
  const handleStartAnalysis = async () => {
    const resumeId = successFiles[0]?.result?.id

    if (!resumeId) {
      addToast({
        type: 'error',
        title: 'No Resume',
        message: 'Please upload a resume first'
      })
      return
    }

    if (!selectedIndustry) {
      addToast({
        type: 'error',
        title: 'Industry Required',
        message: 'Please select an industry for analysis'
      })
      return
    }

    setIsAnalyzing(true)
    setAnalysisResult(null)
    setAnalysisStatus('requesting')

    try {
      const result = await analysisApi.requestAnalysis(resumeId, selectedIndustry)

      if (result.success) {
        setAnalysisId(result.data.analysis_id)
        setAnalysisStatus(result.data.status)
        addToast({
          type: 'success',
          title: 'Analysis Started',
          message: 'Your resume is being analyzed...'
        })
      } else {
        throw result.error || new Error('Failed to start analysis')
      }
    } catch (error: any) {
      setIsAnalyzing(false)
      addToast({
        type: 'error',
        title: 'Analysis Failed',
        message: error.message || 'Failed to start analysis'
      })
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

                  {successFiles.length > 0 && uploadingFiles.length === 0 && !analysisResult && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-4">
                        <select
                          value={selectedIndustry}
                          onChange={(e) => setSelectedIndustry(e.target.value)}
                          className="flex-1 p-3 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500"
                          disabled={isAnalyzing}
                        >
                          <option value="">Select Industry...</option>
                          {INDUSTRY_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <Button
                          size="lg"
                          onClick={handleStartAnalysis}
                          disabled={!selectedIndustry || isAnalyzing}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          {isAnalyzing ? (
                            <>
                              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
                              {analysisStatus === 'processing' ? 'Analyzing...' : 'Starting...'}
                            </>
                          ) : (
                            'Analyze Resume'
                          )}
                        </Button>
                      </div>
                      {isAnalyzing && (
                        <div className="text-center text-sm text-neutral-600">
                          Status: {analysisStatus}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Analysis Results */}
              {analysisResult && (
                <Card className="border-2 border-green-500">
                  <CardHeader className="bg-green-50">
                    <h2 className="text-xl font-bold text-neutral-900">Analysis Results</h2>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    {/* Scores */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="text-center">
                        <div className="text-4xl font-bold text-primary-600">
                          {analysisResult.overall_score}/100
                        </div>
                        <div className="text-sm text-neutral-600">Overall Score</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg font-semibold text-neutral-900">
                          {INDUSTRY_OPTIONS.find(i => i.value === analysisResult.industry)?.label}
                        </div>
                        <div className="text-sm text-neutral-600">Industry</div>
                      </div>
                      <div className="text-center">
                        <div className="text-lg font-semibold text-neutral-900">
                          {analysisResult.market_tier?.replace('_', ' ').toUpperCase()}
                        </div>
                        <div className="text-sm text-neutral-600">Market Tier</div>
                      </div>
                    </div>

                    {/* Summary */}
                    {analysisResult.analysis_summary && (
                      <div>
                        <h3 className="font-semibold text-neutral-900 mb-2">Summary</h3>
                        <p className="text-neutral-700">{analysisResult.analysis_summary}</p>
                      </div>
                    )}

                    {/* Feedback */}
                    {(analysisResult.structure_feedback || analysisResult.appeal_feedback) && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {analysisResult.structure_feedback && (
                          <div>
                            <h3 className="font-semibold text-neutral-900 mb-3">Structure Feedback</h3>
                            {analysisResult.structure_feedback.strengths?.length > 0 && (
                              <div className="mb-3">
                                <h4 className="text-sm font-medium text-green-700 mb-1">Strengths</h4>
                                <ul className="text-sm text-neutral-600 space-y-1">
                                  {analysisResult.structure_feedback.strengths.map((s: string, i: number) => (
                                    <li key={i}>• {s}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {analysisResult.structure_feedback.improvements?.length > 0 && (
                              <div>
                                <h4 className="text-sm font-medium text-orange-700 mb-1">Improvements</h4>
                                <ul className="text-sm text-neutral-600 space-y-1">
                                  {analysisResult.structure_feedback.improvements.map((s: string, i: number) => (
                                    <li key={i}>• {s}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}

                        {analysisResult.appeal_feedback && (
                          <div>
                            <h3 className="font-semibold text-neutral-900 mb-3">Appeal Feedback</h3>
                            {analysisResult.appeal_feedback.strengths?.length > 0 && (
                              <div className="mb-3">
                                <h4 className="text-sm font-medium text-green-700 mb-1">Strengths</h4>
                                <ul className="text-sm text-neutral-600 space-y-1">
                                  {analysisResult.appeal_feedback.strengths.map((s: string, i: number) => (
                                    <li key={i}>• {s}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {analysisResult.appeal_feedback.improvements?.length > 0 && (
                              <div>
                                <h4 className="text-sm font-medium text-orange-700 mb-1">Improvements</h4>
                                <ul className="text-sm text-neutral-600 space-y-1">
                                  {analysisResult.appeal_feedback.improvements.map((s: string, i: number) => (
                                    <li key={i}>• {s}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="pt-4 border-t flex gap-3">
                      <Button
                        onClick={() => {
                          setAnalysisResult(null)
                          setAnalysisId(null)
                          setSelectedIndustry('')
                        }}
                        variant="secondary"
                      >
                        Analyze Again
                      </Button>
                      <Button
                        onClick={() => {
                          setFiles([])
                          setAnalysisResult(null)
                          setAnalysisId(null)
                          setSelectedIndustry('')
                        }}
                        variant="secondary"
                      >
                        Upload New Resume
                      </Button>
                    </div>
                  </CardContent>
                </Card>
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