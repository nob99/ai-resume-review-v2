'use client'

import React, { useState, useCallback } from 'react'
import { extractionApi } from '@/lib/api'
import { TextExtractionResult, BatchTextExtractionResponse } from '@/types'
import { Button } from '@/components/ui'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { TextExtractionStatus } from './TextExtractionStatus'
import { ExtractedTextPreview } from './ExtractedTextPreview'

interface BatchExtractionManagerProps {
  uploadIds: string[]
  filenames?: Record<string, string> // uploadId -> filename mapping
  onBatchComplete?: (results: TextExtractionResult[]) => void
  onError?: (error: Error) => void
  className?: string
}

interface FileExtractionState {
  uploadId: string
  filename: string
  status: 'idle' | 'pending' | 'processing' | 'completed' | 'failed'
  result?: TextExtractionResult
  error?: string
}

export const BatchExtractionManager: React.FC<BatchExtractionManagerProps> = ({
  uploadIds,
  filenames = {},
  onBatchComplete,
  onError,
  className = ''
}) => {
  const [fileStates, setFileStates] = useState<FileExtractionState[]>(() =>
    uploadIds.map(id => ({
      uploadId: id,
      filename: filenames[id] || `File ${id.slice(0, 8)}...`,
      status: 'idle'
    }))
  )
  const [batchResult, setBatchResult] = useState<BatchTextExtractionResponse | null>(null)
  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set())

  const updateFileState = useCallback((uploadId: string, updates: Partial<FileExtractionState>) => {
    setFileStates(prev => prev.map(file => 
      file.uploadId === uploadId ? { ...file, ...updates } : file
    ))
  }, [])

  const startBatchExtraction = useCallback(async () => {
    if (uploadIds.length === 0) return

    setIsBatchRunning(true)
    setBatchResult(null)
    
    // Reset all file states
    setFileStates(prev => prev.map(file => ({ ...file, status: 'pending', error: undefined, result: undefined })))

    try {
      const result = await extractionApi.requestBatchExtraction(uploadIds, {
        timeoutSeconds: 120 // 2 minutes for batch processing
      })

      if (!result.success) {
        throw result.error || new Error('Failed to start batch extraction')
      }

      setBatchResult(result.data)
      
      // Process individual results
      result.data.results.forEach(extractionResult => {
        updateFileState(extractionResult.upload_id, {
          status: extractionResult.extraction_status as any,
          result: extractionResult,
          error: extractionResult.error_message
        })
      })

      onBatchComplete?.(result.data.results)
    } catch (err) {
      const error = err as Error
      console.error('Batch extraction failed:', error)
      
      // Mark all files as failed
      setFileStates(prev => prev.map(file => ({ 
        ...file, 
        status: 'failed', 
        error: error.message 
      })))
      
      onError?.(error)
    } finally {
      setIsBatchRunning(false)
    }
  }, [uploadIds, updateFileState, onBatchComplete, onError])

  const handleIndividualExtractionComplete = useCallback((result: TextExtractionResult) => {
    updateFileState(result.upload_id, {
      status: 'completed',
      result
    })
  }, [updateFileState])

  const handleIndividualError = useCallback((uploadId: string) => (error: Error) => {
    updateFileState(uploadId, {
      status: 'failed',
      error: error.message
    })
  }, [updateFileState])

  const toggleFileExpanded = (uploadId: string) => {
    const newExpanded = new Set(expandedFiles)
    if (newExpanded.has(uploadId)) {
      newExpanded.delete(uploadId)
    } else {
      newExpanded.add(uploadId)
    }
    setExpandedFiles(newExpanded)
  }

  const completedCount = fileStates.filter(f => f.status === 'completed').length
  const failedCount = fileStates.filter(f => f.status === 'failed').length
  const processingCount = fileStates.filter(f => f.status === 'processing' || f.status === 'pending').length

  if (uploadIds.length === 0) {
    return (
      <div className={`text-center py-8 text-gray-500 ${className}`}>
        <p>No files selected for batch extraction</p>
      </div>
    )
  }

  return (
    <div className={`w-full space-y-4 ${className}`}>
      {/* Batch Summary */}
      <Card variant="elevated">
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Batch Text Extraction ({uploadIds.length} files)
            </h3>
            <Button
              onClick={startBatchExtraction}
              disabled={isBatchRunning}
              loading={isBatchRunning}
              size="sm"
            >
              {isBatchRunning ? 'Processing...' : 'Start Batch Extraction'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Total Files:</span>
              <p className="text-gray-900">{uploadIds.length}</p>
            </div>
            <div>
              <span className="font-medium text-green-600">Completed:</span>
              <p className="text-gray-900">{completedCount}</p>
            </div>
            <div>
              <span className="font-medium text-red-600">Failed:</span>
              <p className="text-gray-900">{failedCount}</p>
            </div>
            <div>
              <span className="font-medium text-blue-600">Processing:</span>
              <p className="text-gray-900">{processingCount}</p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Progress</span>
              <span>{Math.round((completedCount + failedCount) / uploadIds.length * 100)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="flex h-full rounded-full overflow-hidden">
                <div 
                  className="bg-green-500 transition-all duration-300"
                  style={{ width: `${(completedCount / uploadIds.length) * 100}%` }}
                />
                <div 
                  className="bg-red-500 transition-all duration-300"
                  style={{ width: `${(failedCount / uploadIds.length) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Individual File Results */}
      <div className="space-y-3">
        {fileStates.map((fileState) => {
          const isExpanded = expandedFiles.has(fileState.uploadId)
          
          return (
            <Card key={fileState.uploadId} variant="outlined">
              <div 
                className="px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => toggleFileExpanded(fileState.uploadId)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      {fileState.status === 'completed' ? (
                        <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        </div>
                      ) : fileState.status === 'failed' ? (
                        <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </div>
                      ) : fileState.status === 'processing' || fileState.status === 'pending' ? (
                        <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                          <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        </div>
                      ) : (
                        <div className="w-6 h-6 bg-gray-300 rounded-full" />
                      )}
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">
                        {fileState.filename}
                      </h4>
                      <p className="text-xs text-gray-500">
                        {fileState.uploadId.slice(0, 8)}... • {fileState.status}
                        {fileState.result && (
                          <span> • {fileState.result.word_count} words • {fileState.result.sections.length} sections</span>
                        )}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {fileState.error && (
                      <span className="text-xs text-red-600 max-w-xs truncate">
                        {fileState.error}
                      </span>
                    )}
                    <svg
                      className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-gray-200 px-4 py-4">
                  {fileState.status === 'idle' || (fileState.status === 'pending' && !isBatchRunning) ? (
                    <TextExtractionStatus
                      uploadId={fileState.uploadId}
                      onExtractionComplete={handleIndividualExtractionComplete}
                      onError={handleIndividualError(fileState.uploadId)}
                      autoStart={false}
                    />
                  ) : fileState.result ? (
                    <ExtractedTextPreview extractionResult={fileState.result} />
                  ) : fileState.error ? (
                    <div className="bg-red-50 border border-red-200 rounded p-3">
                      <p className="text-sm text-red-700">{fileState.error}</p>
                    </div>
                  ) : (
                    <div className="text-center py-4 text-gray-500">
                      <p className="text-sm">Processing...</p>
                    </div>
                  )}
                </div>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}