'use client'

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Card, CardContent } from '@/components/ui'
import { cn } from '@/lib/utils'
import { FileUploadProps, FileValidationResult, FileUploadError } from '@/types'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE } from '../constants'
import { formatFileSize } from './FileValidation'

const FileUpload = React.forwardRef<HTMLDivElement, FileUploadProps>(
  ({
    className,
    onFilesSelected,
    onError,
    acceptedTypes = ['pdf', 'doc', 'docx'],
    maxFileSize = MAX_FILE_SIZE,
    maxFiles = 5,
    multiple = true,
    disabled = false,
    ...props
  }, ref) => {
    const [isDragActive, setIsDragActive] = useState(false)

    const validateFile = useCallback((file: File): FileValidationResult => {
      const errors: string[] = []

      // Check file type
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      const isValidType = Object.values(ACCEPTED_FILE_TYPES)
        .flat()
        .includes(fileExtension)

      if (!isValidType) {
        errors.push(`File type not supported. Please upload PDF, DOC, or DOCX files only.`)
      }

      // Check file size
      if (file.size > maxFileSize) {
        const maxSizeMB = maxFileSize / (1024 * 1024)
        errors.push(`File size exceeds ${maxSizeMB}MB limit. Current size: ${(file.size / (1024 * 1024)).toFixed(1)}MB`)
      }

      return {
        isValid: errors.length === 0,
        errors
      }
    }, [maxFileSize])

    const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
      setIsDragActive(false)

      // Handle rejected files - show ALL errors, not just first
      if (rejectedFiles.length > 0) {
        const errorMessages = rejectedFiles.map(rejection =>
          `${rejection.file.name}: ${rejection.errors?.[0]?.message || 'Invalid file'}`
        )

        const error: FileUploadError = {
          name: 'FileUploadError',
          message: `${rejectedFiles.length} file${rejectedFiles.length !== 1 ? 's' : ''} rejected:\n${errorMessages.join('\n')}`,
          code: 'VALIDATION_FAILED'
        }
        onError?.(error)
        return
      }

      // Validate accepted files
      const validFiles: File[] = []
      const validationErrors: string[] = []

      for (const file of acceptedFiles) {
        const validation = validateFile(file)
        if (validation.isValid) {
          validFiles.push(file)
        } else {
          validationErrors.push(...validation.errors)
        }
      }

      if (validationErrors.length > 0) {
        const error: FileUploadError = {
          name: 'FileUploadError',
          message: validationErrors.join(' '),
          code: 'VALIDATION_FAILED'
        }
        onError?.(error)
        return
      }

      if (validFiles.length > 0) {
        onFilesSelected?.(validFiles)
      }
    }, [validateFile, onFilesSelected, onError])

    const { getRootProps, getInputProps, isDragAccept, isDragReject } = useDropzone({
      onDrop,
      accept: ACCEPTED_FILE_TYPES,
      maxSize: maxFileSize,
      maxFiles,
      multiple,
      disabled,
      onDragEnter: () => setIsDragActive(true),
      onDragLeave: () => setIsDragActive(false)
    })

    const dropzoneClasses = cn(
      // Base classes
      'relative w-full min-h-[240px] p-8',
      'border-2 border-dashed border-neutral-300',
      'rounded-lg transition-all duration-200',
      'cursor-pointer bg-white shadow-sm',
      
      // Hover and focus states
      'hover:border-primary-400 hover:bg-primary-50',
      'focus-within:outline-none focus-within:ring-2 focus-within:ring-primary-500 focus-within:ring-offset-2',
      
      // Drag states
      isDragActive && 'border-primary-500 bg-primary-50',
      isDragAccept && 'border-success-500 bg-success-50',
      isDragReject && 'border-error-500 bg-error-50',
      
      // Disabled state
      disabled && 'opacity-50 cursor-not-allowed hover:border-neutral-300 hover:bg-transparent',
      
      className
    )


    return (
      <Card ref={ref} className="w-full" {...props}>
        <CardContent className="p-0">
          <div {...getRootProps({ className: dropzoneClasses })}>
            <input {...getInputProps()} />
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              {/* Upload Icon */}
              <div className={cn(
                'p-4 rounded-full transition-colors',
                isDragActive ? 'bg-primary-100' : 'bg-neutral-100',
                disabled && 'bg-neutral-50'
              )}>
                <svg
                  className={cn(
                    'w-8 h-8 transition-colors',
                    isDragActive ? 'text-primary-600' : 'text-neutral-400',
                    disabled && 'text-neutral-300'
                  )}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
              </div>

              {/* Main text */}
              <div className="space-y-2">
                <p className={cn(
                  'text-lg font-bold',
                  isDragActive ? 'text-primary-700' : 'text-neutral-700',
                  disabled && 'text-neutral-400'
                )}>
                  {isDragActive ? 'Drop files here to upload' : 'ファイルのドラッグ&ドロップ / Drag & drop resume files here'}
                </p>
                <p className={cn(
                  'text-base',
                  isDragActive ? 'text-primary-600' : 'text-neutral-600',
                  disabled && 'text-neutral-300'
                )}>
                  or{' '}
                  <span className={cn(
                    'font-semibold underline text-blue-600',
                    !disabled && 'hover:text-blue-700 cursor-pointer'
                  )}>
                    ファイルの選択 / click here to browse files
                  </span>
                </p>
              </div>

              {/* File requirements */}
              <div className={cn(
                'text-xs space-y-1',
                'text-neutral-400',
                disabled && 'text-neutral-300'
              )}>
                <p>サポートされるファイル形式: Supported formats: PDF, DOC, DOCX</p>
                <p>最大ファイルサイズ: Maximum file size: {formatFileSize(maxFileSize)}</p>
                {multiple && <p>最大ファイル数: Maximum files: {maxFiles}</p>}
              </div>

              {/* Drag state indicators */}
              {isDragAccept && (
                <div className="flex items-center space-x-2 text-success-600">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sm font-medium">Files look good!</span>
                </div>
              )}

              {isDragReject && (
                <div className="flex items-center space-x-2 text-error-600">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-sm font-medium">Invalid file type or size</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }
)

FileUpload.displayName = 'FileUpload'

export default FileUpload