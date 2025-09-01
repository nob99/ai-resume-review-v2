'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { extractionApi } from '@/lib/api'
import { TextExtractionResult } from '@/types'
import { Button } from '@/components/ui'

interface TextExtractionStatusProps {
  uploadId: string
  onExtractionComplete?: (result: TextExtractionResult) => void
  onError?: (error: Error) => void
  autoStart?: boolean
  className?: string
}

type ExtractionStatus = 'idle' | 'pending' | 'processing' | 'completed' | 'failed'

const statusMessages: Record<ExtractionStatus, string> = {
  idle: 'Ready to extract text',
  pending: 'Queued for text extraction...',
  processing: 'Extracting text content...',
  completed: 'Text extraction completed!',
  failed: 'Text extraction failed'
}

const statusColors: Record<ExtractionStatus, string> = {
  idle: 'bg-gray-200 text-gray-700',
  pending: 'bg-yellow-500 text-white',
  processing: 'bg-blue-500 text-white',
  completed: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white'
}

export const TextExtractionStatus: React.FC<TextExtractionStatusProps> = ({
  uploadId,
  onExtractionComplete,
  onError,
  autoStart = false,
  className = ''
}) => {
  const [status, setStatus] = useState<ExtractionStatus>('idle')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [extractionResult, setExtractionResult] = useState<TextExtractionResult | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const handleError = useCallback((err: Error) => {
    console.error('Text extraction error:', err)
    setError(err.message)
    setStatus('failed')
    setIsPolling(false)
    onError?.(err)
  }, [onError])

  const startExtraction = useCallback(async () => {
    try {
      setError(null)
      setStatus('pending')
      setProgress(10)

      const result = await extractionApi.requestTextExtraction(uploadId, {
        timeoutSeconds: 60
      })

      if (!result.success) {
        throw result.error || new Error('Failed to start text extraction')
      }

      setProgress(30)
      setIsPolling(true)
    } catch (err) {
      handleError(err as Error)
    }
  }, [uploadId, handleError])

  const checkStatus = useCallback(async () => {
    if (!isPolling) return

    try {
      const result = await extractionApi.getExtractionStatus(uploadId)

      if (!result.success) {
        throw result.error || new Error('Failed to check extraction status')
      }

      const statusData = result.data
      const extractionStatus = statusData.extraction_result?.extraction_status || statusData.status

      setStatus(extractionStatus as ExtractionStatus)

      // Update progress based on status
      switch (extractionStatus) {
        case 'pending':
          setProgress(20)
          break
        case 'processing':
          setProgress(Math.min(progress + 10, 90))
          break
        case 'completed':
          setProgress(100)
          setIsPolling(false)
          if (statusData.extraction_result) {
            setExtractionResult(statusData.extraction_result)
            onExtractionComplete?.(statusData.extraction_result)
          }
          break
        case 'failed':
          setIsPolling(false)
          const errorMsg = statusData.extraction_result?.error_message || 'Text extraction failed'
          setError(errorMsg)
          handleError(new Error(errorMsg))
          break
      }
    } catch (err) {
      handleError(err as Error)
    }
  }, [uploadId, isPolling, progress, onExtractionComplete, handleError])

  // Polling effect
  useEffect(() => {
    if (!isPolling) return

    const interval = setInterval(checkStatus, 2000) // Poll every 2 seconds
    return () => clearInterval(interval)
  }, [isPolling, checkStatus])

  // Auto-start extraction
  useEffect(() => {
    if (autoStart && status === 'idle') {
      startExtraction()
    }
  }, [autoStart, status, startExtraction])

  const retry = () => {
    setError(null)
    setProgress(0)
    startExtraction()
  }

  const isActive = status === 'pending' || status === 'processing'

  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {error ? `Error: ${error}` : statusMessages[status]}
        </span>
        {status !== 'idle' && (
          <span className="text-sm text-gray-500">
            {progress}%
          </span>
        )}
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden mb-3">
        <div
          className={`h-full transition-all duration-300 ease-out ${statusColors[status]} ${
            isActive ? 'animate-pulse' : ''
          }`}
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {status === 'completed' && extractionResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
          <div className="flex items-center text-green-600 mb-2">
            <svg 
              className="w-4 h-4 mr-2" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path 
                fillRule="evenodd" 
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" 
                clipRule="evenodd" 
              />
            </svg>
            <span className="text-sm font-semibold">Text extraction successful!</span>
          </div>
          <div className="text-sm text-green-700">
            <p><strong>Word count:</strong> {extractionResult.word_count}</p>
            <p><strong>Sections detected:</strong> {extractionResult.sections.length}</p>
            {extractionResult.extraction_time && (
              <p><strong>Processing time:</strong> {(extractionResult.extraction_time * 1000).toFixed(0)}ms</p>
            )}
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center text-red-600">
              <svg 
                className="w-4 h-4 mr-2" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path 
                  fillRule="evenodd" 
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" 
                  clipRule="evenodd" 
                />
              </svg>
              <span className="text-sm font-semibold">Extraction failed</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={retry}
              disabled={isActive}
            >
              Retry
            </Button>
          </div>
          {error && (
            <p className="text-sm text-red-700 mt-2">{error}</p>
          )}
        </div>
      )}

      {status === 'idle' && !autoStart && (
        <div className="flex justify-center">
          <Button
            onClick={startExtraction}
            disabled={isActive}
            size="sm"
            className="w-full"
          >
            Start Text Extraction
          </Button>
        </div>
      )}
    </div>
  )
}