'use client'

import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui'
import { FilePreview, FileWithPreview } from './FilePreview'
import { UploadProgress, UploadStatus } from './UploadProgress'
import { 
  ACCEPTED_FILE_TYPES, 
  MAX_FILE_SIZE, 
  validateFile,
  formatFileSize 
} from './FileValidation'

interface FileUploadProps {
  onFilesSelected?: (files: File[]) => void
  onUpload?: (files: File[]) => Promise<void>
  multiple?: boolean
  className?: string
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  onUpload,
  multiple = true,
  className = ''
}) => {
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadMessage, setUploadMessage] = useState<string>()
  const [fileErrors, setFileErrors] = useState<Record<string, string>>({})

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: { file: File; errors: { code: string; message: string }[] }[]) => {
    const newFileErrors: Record<string, string> = {}
    
    // Handle accepted files with validation
    const validatedFiles = acceptedFiles.map(file => {
      const validation = validateFile(file)
      const fileWithId: FileWithPreview = Object.assign(file, {
        id: `${file.name}-${file.size}-${Date.now()}`
      })
      
      if (!validation.isValid) {
        newFileErrors[fileWithId.id] = validation.error!
      }
      
      return fileWithId
    })
    
    // Handle rejected files
    rejectedFiles.forEach(rejection => {
      const file = rejection.file as File
      const fileWithId: FileWithPreview = Object.assign(file, {
        id: `${file.name}-${file.size}-${Date.now()}`
      })
      
      const errors = rejection.errors.map((e) => {
        if (e.code === 'file-too-large') {
          return `File size (${formatFileSize(file.size)}) exceeds maximum allowed size of ${formatFileSize(MAX_FILE_SIZE)}`
        }
        if (e.code === 'file-invalid-type') {
          return 'File type not supported. Please upload PDF, DOC, or DOCX files only.'
        }
        return e.message
      })
      
      newFileErrors[fileWithId.id] = errors.join('. ')
      validatedFiles.push(fileWithId)
    })
    
    setFileErrors(prev => ({ ...prev, ...newFileErrors }))
    
    const newFiles = multiple 
      ? [...files, ...validatedFiles]
      : validatedFiles.slice(0, 1)
    
    setFiles(newFiles)
    
    if (onFilesSelected) {
      const validFiles = newFiles.filter(f => !newFileErrors[f.id])
      onFilesSelected(validFiles)
    }
    
    // Reset upload status when new files are added
    setUploadStatus('idle')
    setUploadProgress(0)
  }, [files, multiple, onFilesSelected])

  const removeFile = useCallback((fileId: string) => {
    setFiles(prevFiles => prevFiles.filter(f => f.id !== fileId))
    setFileErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[fileId]
      return newErrors
    })
  }, [])

  const handleUpload = async () => {
    if (!onUpload || files.length === 0) return
    
    const validFiles = files.filter(f => !fileErrors[f.id])
    if (validFiles.length === 0) {
      setUploadMessage('Please fix file errors before uploading')
      setUploadStatus('error')
      return
    }
    
    try {
      setUploadStatus('uploading')
      setUploadProgress(20)
      
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 500)
      
      await onUpload(validFiles)
      
      clearInterval(progressInterval)
      setUploadProgress(100)
      setUploadStatus('success')
    } catch (error) {
      setUploadStatus('error')
      setUploadMessage(error instanceof Error ? error.message : 'Upload failed')
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
    multiple,
    noKeyboard: false, // Enable keyboard navigation
    noClick: false // Ensure click is enabled
  })

  const hasValidFiles = files.some(f => !fileErrors[f.id])

  return (
    <div className={`w-full ${className}`}>
      <div
        {...getRootProps()}
        className={`
          relative overflow-hidden rounded-lg border-2 border-dashed 
          p-6 sm:p-8
          transition-all duration-200 cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100'
          }
        `}
        role="button"
        tabIndex={0}
        aria-label="Upload files - drag and drop or click to browse"
        aria-describedby="upload-description"
      >
        <input {...getInputProps()} aria-label="File input" />
        
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          
          <p className="mt-2 text-sm text-gray-600">
            {isDragActive ? (
              <span className="font-semibold">Drop files here</span>
            ) : (
              <>
                <span className="font-semibold">Click to upload</span> or drag and drop
              </>
            )}
          </p>
          
          <p id="upload-description" className="mt-1 text-xs text-gray-500">
            PDF, DOC, DOCX up to {formatFileSize(MAX_FILE_SIZE)}
          </p>
        </div>
      </div>

      {files.length > 0 && (
        <div className="mt-4 space-y-2" role="region" aria-live="polite">
          <h3 className="text-sm font-medium text-gray-700">
            Selected Files ({files.length})
          </h3>
          
          {files.map(file => (
            <FilePreview
              key={file.id}
              file={file}
              onRemove={removeFile}
              error={fileErrors[file.id]}
            />
          ))}
        </div>
      )}

      {uploadStatus !== 'idle' && (
        <div className="mt-4">
          <UploadProgress
            status={uploadStatus}
            progress={uploadProgress}
            message={uploadMessage}
          />
        </div>
      )}

      {onUpload && hasValidFiles && uploadStatus !== 'uploading' && (
        <div className="mt-4">
          <Button
            onClick={handleUpload}
            disabled={!hasValidFiles || uploadStatus === 'uploading'}
            loading={uploadStatus === 'uploading'}
            size="lg"
            className="w-full"
          >
            Upload {files.filter(f => !fileErrors[f.id]).length} File{files.filter(f => !fileErrors[f.id]).length !== 1 ? 's' : ''}
          </Button>
        </div>
      )}
    </div>
  )
}