'use client'

import React from 'react'
import { Card, CardContent, Button } from '../../../components/ui'
import { cn } from '../../../lib/utils'
import { BaseComponentProps, UploadFile } from '../../../types'
import { formatFileSize, getFileTypeDisplayName, isLikelyResume } from './FileValidation'

// Legacy compatibility types
type UploadedFile = UploadFile & {
  extractedText?: string
}

type DetailedProgressInfo = any
type UploadedFileV2 = UploadedFile & {
  progressInfo?: DetailedProgressInfo
}

interface FilePreviewProps extends BaseComponentProps {
  files: (UploadedFile | UploadedFileV2)[]
  onRemove?: (fileId: string) => void
  onRetry?: (fileId: string) => void
  onCancel?: (fileId: string) => void
  showProgress?: boolean
  showDetailedProgress?: boolean
  readOnly?: boolean
}

interface FilePreviewItemProps extends BaseComponentProps {
  uploadedFile: UploadedFile | UploadedFileV2
  onRemove?: (fileId: string) => void
  onRetry?: (fileId: string) => void
  onCancel?: (fileId: string) => void
  showProgress?: boolean
  showDetailedProgress?: boolean
  readOnly?: boolean
}

const FileIcon: React.FC<{ file: File; status: UploadedFile['status'] }> = ({ file, status }) => {
  const extension = file.name.split('.').pop()?.toLowerCase()
  
  const getIconColor = () => {
    switch (status) {
      case 'completed':
        return 'text-success-500'
      case 'error':
        return 'text-error-500'
      case 'uploading':
      case 'validating':
      case 'extracting':
        return 'text-primary-500'
      default:
        return 'text-neutral-400'
    }
  }

  const iconClasses = cn('w-8 h-8', getIconColor())

  switch (extension) {
    case 'pdf':
      return (
        <svg className={iconClasses} fill="currentColor" viewBox="0 0 24 24">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
        </svg>
      )
    case 'doc':
    case 'docx':
      return (
        <svg className={iconClasses} fill="currentColor" viewBox="0 0 24 24">
          <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
        </svg>
      )
    default:
      return (
        <svg className={iconClasses} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
  }
}

const StatusIndicator: React.FC<{ 
  status: UploadedFile['status'] | 'cancelled' | 'queued'
  progress: number
  detailedProgress?: DetailedProgressInfo
}> = ({ status, progress, detailedProgress }) => {
  const formatSpeed = (bytesPerSecond: number): string => {
    if (bytesPerSecond === 0) return ''
    const kbps = bytesPerSecond / 1024
    if (kbps < 1024) {
      return ` (${kbps.toFixed(1)} KB/s)`
    }
    const mbps = kbps / 1024
    return ` (${mbps.toFixed(1)} MB/s)`
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

  switch (status) {
    case 'pending':
    case 'queued':
      return (
        <div className="flex items-center space-x-2 text-neutral-500">
          <div className="w-2 h-2 rounded-full bg-neutral-300"></div>
          <span className="text-sm">Queued</span>
        </div>
      )
    
    case 'uploading':
      return (
        <div className="flex items-center space-x-2 text-primary-600">
          <div className="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          <span className="text-sm">
            Uploading... {Math.round(progress)}%
            {detailedProgress?.speed ? formatSpeed(detailedProgress.speed) : ''}
          </span>
          {detailedProgress?.estimatedTimeRemaining && detailedProgress.estimatedTimeRemaining > 0 && (
            <span className="text-xs text-neutral-500">
              • {formatTime(detailedProgress.estimatedTimeRemaining)} remaining
            </span>
          )}
        </div>
      )
    
    case 'validating':
      return (
        <div className="flex items-center space-x-2 text-primary-600">
          <div className="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          <span className="text-sm">Validating...</span>
        </div>
      )
    
    case 'extracting':
      return (
        <div className="flex items-center space-x-2 text-primary-600">
          <div className="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          <span className="text-sm">Extracting text...</span>
        </div>
      )
    
    case 'completed':
      return (
        <div className="flex items-center space-x-2 text-success-600">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm font-medium">Ready</span>
        </div>
      )
    
    case 'error':
      return (
        <div className="flex items-center space-x-2 text-error-600">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="text-sm font-medium">Failed</span>
          {detailedProgress?.retryCount && detailedProgress.retryCount > 0 && (
            <span className="text-xs text-error-500">
              (Retry {detailedProgress.retryCount}/{detailedProgress.maxRetries})
            </span>
          )}
        </div>
      )
    
    case 'cancelled':
      return (
        <div className="flex items-center space-x-2 text-neutral-600">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium">Cancelled</span>
        </div>
      )
    
    default:
      return null
  }
}

const ProgressBar: React.FC<{ progress: number; status: UploadedFile['status'] }> = ({ progress, status }) => {
  if (!['uploading', 'validating', 'extracting'].includes(status)) return null

  const getProgressColor = () => {
    switch (status) {
      case 'uploading':
        return 'bg-primary-500'
      case 'validating':
        return 'bg-warning-500'
      case 'extracting':
        return 'bg-secondary-500'
      default:
        return 'bg-primary-500'
    }
  }

  return (
    <div className="w-full bg-neutral-200 rounded-full h-1.5">
      <div
        className={cn('h-1.5 rounded-full transition-all duration-300', getProgressColor())}
        style={{ width: `${Math.min(progress, 100)}%` }}
      />
    </div>
  )
}

const FilePreviewItem: React.FC<FilePreviewItemProps> = ({
  uploadedFile,
  onRemove,
  onRetry,
  onCancel,
  showProgress = true,
  showDetailedProgress = false,
  readOnly = false,
  className,
  ...props
}) => {
  const { file, id, status, progress, error } = uploadedFile
  const detailedProgress = 'progressInfo' in uploadedFile ? uploadedFile.progressInfo : undefined
  const displayStatus = detailedProgress?.stage || status
  const displayProgress = detailedProgress?.percentage || progress
  
  const cardClasses = cn(
    'transition-all duration-200',
    displayStatus === 'error' && 'border-error-200 bg-error-50',
    displayStatus === 'completed' && 'border-success-200 bg-success-50',
    displayStatus === 'cancelled' && 'border-neutral-300 bg-neutral-50',
    className
  )

  const handleRemove = () => {
    onRemove?.(id)
  }

  const handleRetry = () => {
    onRetry?.(id)
  }

  const handleCancel = () => {
    onCancel?.(id)
  }

  const isProcessing = ['uploading', 'validating', 'extracting'].includes(displayStatus)

  return (
    <Card className={cardClasses} {...props}>
      <CardContent className="p-4">
        <div className="flex items-start space-x-3">
          {/* File Icon */}
          <div className="flex-shrink-0 mt-1">
            <FileIcon file={file} status={displayStatus as UploadedFile['status']} />
          </div>
          
          {/* File Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-neutral-900 truncate">
                  {file.name}
                  {isLikelyResume(file.name) && (
                    <span className="ml-2 px-1.5 py-0.5 text-xs bg-primary-100 text-primary-700 rounded">
                      Resume
                    </span>
                  )}
                </h4>
                <p className="text-xs text-neutral-500 mt-0.5">
                  {getFileTypeDisplayName(file)} • {formatFileSize(file.size)}
                  {detailedProgress?.bytesUploaded && detailedProgress.bytesUploaded > 0 && (
                    <span className="text-primary-600">
                      {' '}• {formatFileSize(detailedProgress.bytesUploaded)} uploaded
                    </span>
                  )}
                </p>
              </div>
              
              {/* Actions */}
              {!readOnly && (
                <div className="flex items-center space-x-2 ml-4">
                  {isProcessing && onCancel && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleCancel}
                      className="h-6 px-2 text-xs text-warning-600 hover:text-warning-700"
                    >
                      Cancel
                    </Button>
                  )}
                  {displayStatus === 'error' && onRetry && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleRetry}
                      className="h-6 px-2 text-xs text-primary-600 hover:text-primary-700"
                    >
                      Retry
                    </Button>
                  )}
                  {!isProcessing && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleRemove}
                      className="h-6 w-6 p-0 text-neutral-400 hover:text-error-600"
                      aria-label={`Remove ${file.name}`}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </Button>
                  )}
                </div>
              )}
            </div>
            
            {/* Status and Progress */}
            <div className="mt-2 space-y-2">
              <StatusIndicator 
                status={displayStatus as any} 
                progress={displayProgress} 
                detailedProgress={showDetailedProgress ? detailedProgress : undefined}
              />
              {showProgress && <ProgressBar progress={displayProgress} status={displayStatus as UploadedFile['status']} />}
              
              {/* Detailed Progress Stats */}
              {showDetailedProgress && detailedProgress && isProcessing && (
                <div className="flex items-center space-x-3 text-xs text-neutral-600">
                  {detailedProgress.speed > 0 && (
                    <span>Speed: {formatFileSize(detailedProgress.speed)}/s</span>
                  )}
                  {detailedProgress.timeElapsed > 0 && (
                    <span>Elapsed: {Math.floor(detailedProgress.timeElapsed / 1000)}s</span>
                  )}
                </div>
              )}
              
              {/* Error Message */}
              {displayStatus === 'error' && error && (
                <p className="text-xs text-error-600 bg-error-50 p-2 rounded border border-error-200">
                  {error}
                </p>
              )}
              
              {/* Extracted Text Preview */}
              {displayStatus === 'completed' && uploadedFile.extractedText && (
                <div className="mt-3 p-3 bg-neutral-50 border border-neutral-200 rounded">
                  <h5 className="text-xs font-medium text-neutral-700 mb-2">Text Preview:</h5>
                  <p className="text-xs text-neutral-600 line-clamp-3">
                    {uploadedFile.extractedText.substring(0, 150)}
                    {uploadedFile.extractedText.length > 150 && '...'}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

const FilePreview = React.forwardRef<HTMLDivElement, FilePreviewProps>(
  ({ 
    files, 
    onRemove, 
    onRetry, 
    onCancel,
    showProgress = true, 
    showDetailedProgress = false,
    readOnly = false, 
    className, 
    ...props 
  }, ref) => {
    if (files.length === 0) return null

    // Helper function to get status from file (handles both UploadedFile and UploadedFileV2)
    const getFileStatus = (file: UploadedFile | UploadedFileV2) => {
      if ('progressInfo' in file && file.progressInfo) {
        return file.progressInfo.stage
      }
      return file.status
    }

    const completedCount = files.filter(f => getFileStatus(f) === 'completed').length
    const errorCount = files.filter(f => getFileStatus(f) === 'error').length
    const cancelledCount = files.filter(f => getFileStatus(f) === 'cancelled').length
    const processingCount = files.filter(f => ['uploading', 'validating', 'extracting'].includes(getFileStatus(f))).length

    return (
      <div ref={ref} className={cn('space-y-4', className)} {...props}>
        {/* Summary Header */}
        <div className="flex items-center justify-between p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
          <div className="flex items-center space-x-4">
            <h3 className="text-sm font-medium text-neutral-900">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </h3>
            
            {completedCount > 0 && (
              <div className="flex items-center space-x-1 text-success-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm">{completedCount} ready</span>
              </div>
            )}
            
            {processingCount > 0 && (
              <div className="flex items-center space-x-1 text-primary-600">
                <div className="w-3 h-3 border border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                <span className="text-sm">{processingCount} processing</span>
              </div>
            )}
            
            {errorCount > 0 && (
              <div className="flex items-center space-x-1 text-error-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span className="text-sm">{errorCount} failed</span>
              </div>
            )}

            {cancelledCount > 0 && (
              <div className="flex items-center space-x-1 text-neutral-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm">{cancelledCount} cancelled</span>
              </div>
            )}
          </div>
          
          {!readOnly && files.length > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => files.forEach(f => onRemove?.(f.id))}
              className="text-xs text-neutral-500 hover:text-error-600"
            >
              Clear All
            </Button>
          )}
        </div>
        
        {/* File List */}
        <div className="space-y-2">
          {files.map((uploadedFile) => (
            <FilePreviewItem
              key={uploadedFile.id}
              uploadedFile={uploadedFile as any}
              onRemove={onRemove}
              onRetry={onRetry}
              onCancel={onCancel}
              showProgress={showProgress}
              showDetailedProgress={showDetailedProgress}
              readOnly={readOnly}
            />
          ))}
        </div>
      </div>
    )
  }
)

FilePreview.displayName = 'FilePreview'

export default FilePreview
export { FilePreviewItem }
export type { FilePreviewProps, FilePreviewItemProps }