'use client'

import React from 'react'
import { Card, CardContent, Button } from '../ui'
import { cn } from '../../lib/utils'
import { BaseComponentProps, UploadedFile } from '../../types'
import { formatFileSize, getFileTypeDisplayName, isLikelyResume } from './FileValidation'

interface FilePreviewProps extends BaseComponentProps {
  files: UploadedFile[]
  onRemove?: (fileId: string) => void
  onRetry?: (fileId: string) => void
  showProgress?: boolean
  readOnly?: boolean
}

interface FilePreviewItemProps extends BaseComponentProps {
  uploadedFile: UploadedFile
  onRemove?: (fileId: string) => void
  onRetry?: (fileId: string) => void
  showProgress?: boolean
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

const StatusIndicator: React.FC<{ status: UploadedFile['status']; progress: number }> = ({ status, progress }) => {
  switch (status) {
    case 'pending':
      return (
        <div className="flex items-center space-x-2 text-neutral-500">
          <div className="w-2 h-2 rounded-full bg-neutral-300"></div>
          <span className="text-sm">Pending</span>
        </div>
      )
    
    case 'uploading':
      return (
        <div className="flex items-center space-x-2 text-primary-600">
          <div className="w-4 h-4 border-2 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          <span className="text-sm">Uploading... {Math.round(progress)}%</span>
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
  showProgress = true,
  readOnly = false,
  className,
  ...props
}) => {
  const { file, id, status, progress, error } = uploadedFile
  
  const cardClasses = cn(
    'transition-all duration-200',
    status === 'error' && 'border-error-200 bg-error-50',
    status === 'completed' && 'border-success-200 bg-success-50',
    className
  )

  const handleRemove = () => {
    onRemove?.(id)
  }

  const handleRetry = () => {
    onRetry?.(id)
  }

  return (
    <Card className={cardClasses} {...props}>
      <CardContent className="p-4">
        <div className="flex items-start space-x-3">
          {/* File Icon */}
          <div className="flex-shrink-0 mt-1">
            <FileIcon file={file} status={status} />
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
                </p>
              </div>
              
              {/* Actions */}
              {!readOnly && (
                <div className="flex items-center space-x-2 ml-4">
                  {status === 'error' && onRetry && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleRetry}
                      className="h-6 px-2 text-xs text-primary-600 hover:text-primary-700"
                    >
                      Retry
                    </Button>
                  )}
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
                </div>
              )}
            </div>
            
            {/* Status and Progress */}
            <div className="mt-2 space-y-2">
              <StatusIndicator status={status} progress={progress} />
              {showProgress && <ProgressBar progress={progress} status={status} />}
              
              {/* Error Message */}
              {status === 'error' && error && (
                <p className="text-xs text-error-600 bg-error-50 p-2 rounded border border-error-200">
                  {error}
                </p>
              )}
              
              {/* Extracted Text Preview */}
              {status === 'completed' && uploadedFile.extractedText && (
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
  ({ files, onRemove, onRetry, showProgress = true, readOnly = false, className, ...props }, ref) => {
    if (files.length === 0) return null

    const completedCount = files.filter(f => f.status === 'completed').length
    const errorCount = files.filter(f => f.status === 'error').length
    const processingCount = files.filter(f => ['uploading', 'validating', 'extracting'].includes(f.status)).length

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
              uploadedFile={uploadedFile}
              onRemove={onRemove}
              onRetry={onRetry}
              showProgress={showProgress}
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