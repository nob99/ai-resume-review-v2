'use client'

import React, { useState } from 'react'
import { Container, Section, Header } from '../../components/layout'
import { FileUpload, FilePreview } from '../../components/upload'
import { Button, Card, CardHeader, CardContent, Alert } from '../../components/ui'
import { useToast } from '../../components/ui'
import { UploadedFile, FileUploadError } from '../../types'

export default function UploadPage() {
  const [selectedFiles, setSelectedFiles] = useState<UploadedFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const { addToast } = useToast()

  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

  const handleFilesSelected = (files: File[]) => {
    const newFiles: UploadedFile[] = files.map(file => ({
      file,
      id: generateFileId(),
      status: 'pending',
      progress: 0
    }))

    setSelectedFiles(prev => [...prev, ...newFiles])
    
    addToast({
      type: 'success',
      title: 'Files Selected',
      message: `${files.length} file${files.length !== 1 ? 's' : ''} selected successfully`
    })
  }

  const handleUploadError = (error: FileUploadError) => {
    addToast({
      type: 'error',
      title: 'Upload Error',
      message: error.message
    })
  }

  const handleRemoveFile = (fileId: string) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId))
    
    addToast({
      type: 'info',
      title: 'File Removed',
      message: 'File removed from upload queue'
    })
  }

  const handleRetryFile = (fileId: string) => {
    setSelectedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'pending', progress: 0, error: undefined }
          : f
      )
    )
  }

  const simulateUploadProcess = async (file: UploadedFile): Promise<void> => {
    const updateFileStatus = (updates: Partial<UploadedFile>) => {
      setSelectedFiles(prev => 
        prev.map(f => f.id === file.id ? { ...f, ...updates } : f)
      )
    }

    try {
      // Simulate uploading phase
      updateFileStatus({ status: 'uploading', progress: 0 })
      
      for (let progress = 0; progress <= 100; progress += 10) {
        await new Promise(resolve => setTimeout(resolve, 100))
        updateFileStatus({ progress })
      }

      // Simulate validation phase
      updateFileStatus({ status: 'validating', progress: 0 })
      await new Promise(resolve => setTimeout(resolve, 800))

      // Simulate text extraction phase
      updateFileStatus({ status: 'extracting', progress: 50 })
      await new Promise(resolve => setTimeout(resolve, 1200))

      // Complete with mock extracted text
      const mockExtractedText = `This is a sample resume for ${file.file.name}. 
        
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
        progress: 100,
        extractedText: mockExtractedText
      })

    } catch (error) {
      updateFileStatus({ 
        status: 'error', 
        error: 'Failed to process file. Please try again.' 
      })
    }
  }

  const handleStartProcessing = async () => {
    if (selectedFiles.length === 0) return

    setIsProcessing(true)
    
    addToast({
      type: 'info',
      title: 'Processing Started',
      message: `Processing ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}...`
    })

    // Process files concurrently
    const processingPromises = selectedFiles
      .filter(f => f.status === 'pending')
      .map(file => simulateUploadProcess(file))

    try {
      await Promise.all(processingPromises)
      
      addToast({
        type: 'success',
        title: 'Processing Complete',
        message: 'All files have been processed successfully!'
      })
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Processing Error',
        message: 'Some files failed to process. Please retry failed files.'
      })
    } finally {
      setIsProcessing(false)
    }
  }

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

  const pendingFiles = selectedFiles.filter(f => f.status === 'pending')
  const completedFiles = selectedFiles.filter(f => f.status === 'completed')
  const hasProcessingFiles = selectedFiles.some(f => 
    ['uploading', 'validating', 'extracting'].includes(f.status)
  )

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
                  <span className="text-sm font-medium text-neutral-700">Process Files</span>
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

              {/* File Preview */}
              {selectedFiles.length > 0 && (
                <FilePreview
                  files={selectedFiles}
                  onRemove={handleRemoveFile}
                  onRetry={handleRetryFile}
                  readOnly={isProcessing}
                />
              )}

              {/* Action Buttons */}
              {selectedFiles.length > 0 && (
                <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-4">
                  {pendingFiles.length > 0 && (
                    <Button
                      size="lg"
                      onClick={handleStartProcessing}
                      disabled={isProcessing}
                      className="w-full sm:w-auto"
                    >
                      {isProcessing ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                          Processing Files...
                        </>
                      ) : (
                        `Process ${pendingFiles.length} File${pendingFiles.length !== 1 ? 's' : ''}`
                      )}
                    </Button>
                  )}

                  {completedFiles.length > 0 && !hasProcessingFiles && (
                    <Button
                      size="lg"
                      variant="secondary"
                      onClick={handleProceedToAnalysis}
                      className="w-full sm:w-auto"
                    >
                      Proceed to Analysis ({completedFiles.length} ready)
                    </Button>
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