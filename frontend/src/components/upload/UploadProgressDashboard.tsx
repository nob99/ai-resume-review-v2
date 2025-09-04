'use client'

import React from 'react'
import { DetailedProgressInfo, UploadProgressState } from '@/types'

interface UploadProgressDashboardProps {
  progressState: UploadProgressState
  onCancelUpload: (fileId: string) => void
  onRetryUpload: (fileId: string) => void
  className?: string
}

export default function UploadProgressDashboard({
  progressState,
  onCancelUpload,
  onRetryUpload,
  className = '',
}: UploadProgressDashboardProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatSpeed = (bytesPerSecond: number): string => {
    if (bytesPerSecond === 0) return '0 KB/s'
    const kbps = bytesPerSecond / 1024
    if (kbps < 1024) {
      return `${kbps.toFixed(1)} KB/s`
    }
    const mbps = kbps / 1024
    return `${mbps.toFixed(1)} MB/s`
  }

  const formatTime = (milliseconds: number): string => {
    const seconds = Math.floor(milliseconds / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    
    if (minutes === 0) {
      return `${remainingSeconds}s`
    }
    return `${minutes}m ${remainingSeconds}s`
  }

  const getStageIcon = (stage: DetailedProgressInfo['stage']) => {
    switch (stage) {
      case 'completed':
        return (
          <svg className="h-5 w-5 text-green-600" fill="currentColor" viewBox="0 0 24 24">
            <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-1.518 13.982L7 12.5l1.414-1.414 2.068 2.068 4.618-4.618L16.514 9.95l-6.032 6.032z" clipRule="evenodd" />
          </svg>
        )
      case 'error':
        return (
          <svg className="h-5 w-5 text-red-600" fill="currentColor" viewBox="0 0 24 24">
            <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zM8.485 8.485l7.07 7.07-1.414 1.414-7.07-7.07 1.414-1.414z" clipRule="evenodd" />
            <path fillRule="evenodd" d="M15.555 8.485l-7.07 7.07-1.414-1.414 7.07-7.07 1.414 1.414z" clipRule="evenodd" />
          </svg>
        )
      case 'cancelled':
        return (
          <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )
      case 'queued':
        return (
          <svg className="h-5 w-5 text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
            <path fillRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm1 5h-2v6l4 4 1.414-1.414L13 12.586V7z" clipRule="evenodd" />
          </svg>
        )
      default:
        return (
          <div className="relative h-5 w-5">
            <div className="absolute inset-0 rounded-full border-2 border-gray-200"></div>
            <div 
              className="absolute inset-0 rounded-full border-2 border-indigo-600 animate-spin"
              style={{ borderRightColor: 'transparent', borderBottomColor: 'transparent' }}
            ></div>
          </div>
        )
    }
  }

  const getStageLabel = (stage: DetailedProgressInfo['stage']) => {
    const labels: Record<DetailedProgressInfo['stage'], string> = {
      queued: 'Queued',
      uploading: 'Uploading',
      validating: 'Validating',
      extracting: 'Processing',
      completed: 'Completed',
      error: 'Error',
      cancelled: 'Cancelled',
    }
    return labels[stage]
  }

  const getStageColor = (stage: DetailedProgressInfo['stage']) => {
    const colors: Record<DetailedProgressInfo['stage'], string> = {
      queued: 'bg-yellow-100 text-yellow-800',
      uploading: 'bg-blue-100 text-blue-800',
      validating: 'bg-indigo-100 text-indigo-800',
      extracting: 'bg-purple-100 text-purple-800',
      completed: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      cancelled: 'bg-gray-100 text-gray-800',
    }
    return colors[stage]
  }

  if (progressState.files.size === 0) {
    return (
      <div className={`bg-gray-50 rounded-lg p-8 text-center ${className}`}>
        <p className="text-gray-500">No files uploading</p>
      </div>
    )
  }

  const filesArray = Array.from(progressState.files.values())

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overall Progress Summary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-semibold text-gray-900">Overall Progress</h3>
            <span className="text-sm text-gray-500">
              {progressState.completedFiles} of {progressState.totalFiles} files
            </span>
          </div>
          
          <div className="relative h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${progressState.overallProgress}%` }}
            />
          </div>
          
          <div className="flex justify-between items-center mt-2">
            <span className="text-sm font-medium text-gray-700">
              {Math.round(progressState.overallProgress)}% Complete
            </span>
            {progressState.failedFiles > 0 && (
              <span className="text-sm text-red-600">
                {progressState.failedFiles} failed
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">{progressState.totalFiles}</p>
            <p className="text-sm text-gray-500">Total Files</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{progressState.completedFiles}</p>
            <p className="text-sm text-gray-500">Completed</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {progressState.totalFiles - progressState.completedFiles - progressState.failedFiles}
            </p>
            <p className="text-sm text-gray-500">In Progress</p>
          </div>
        </div>
      </div>

      {/* Individual File Progress */}
      <div className="space-y-4">
        {filesArray.map((file) => (
          <div
            key={file.fileId}
            className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 transition-all duration-200 hover:shadow-md"
          >
            {/* File Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start space-x-3 flex-1">
                {getStageIcon(file.stage)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.fileName}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.totalBytes)}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStageColor(file.stage)}`}>
                  {getStageLabel(file.stage)}
                </span>

                {/* Action Buttons */}
                {(file.stage === 'uploading' || file.stage === 'validating' || file.stage === 'extracting') && (
                  <button
                    onClick={() => onCancelUpload(file.fileId)}
                    className="p-1 rounded-full hover:bg-gray-100 transition-colors"
                    aria-label="Cancel upload"
                  >
                    <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                {file.stage === 'error' && file.retryCount < file.maxRetries && (
                  <button
                    onClick={() => onRetryUpload(file.fileId)}
                    className="p-1 rounded-full hover:bg-gray-100 transition-colors"
                    aria-label="Retry upload"
                  >
                    <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            {/* Progress Bar */}
            {(file.stage === 'uploading' || file.stage === 'validating' || file.stage === 'extracting') && (
              <div className="mb-3">
                <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${file.percentage}%` }}
                  />
                </div>
                <div className="flex justify-between items-center mt-2">
                  <span className="text-xs text-gray-600">
                    {Math.round(file.percentage)}%
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatFileSize(file.bytesUploaded)} / {formatFileSize(file.totalBytes)}
                  </span>
                </div>
              </div>
            )}

            {/* Stats Row */}
            {file.stage !== 'queued' && file.stage !== 'cancelled' && (
              <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                <div className="flex items-center space-x-4 text-xs text-gray-500">
                  {file.speed > 0 && (
                    <span>Speed: {formatSpeed(file.speed)}</span>
                  )}
                  {file.timeElapsed > 0 && (
                    <span>Elapsed: {formatTime(file.timeElapsed)}</span>
                  )}
                  {file.estimatedTimeRemaining > 0 && file.stage !== 'completed' && file.stage !== 'error' && (
                    <span>Remaining: {formatTime(file.estimatedTimeRemaining)}</span>
                  )}
                </div>
                {file.retryCount > 0 && (
                  <span className="text-xs text-yellow-600">
                    Retry {file.retryCount}/{file.maxRetries}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}