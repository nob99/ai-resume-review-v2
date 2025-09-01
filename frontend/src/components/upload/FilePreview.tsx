'use client'

import React from 'react'
import { formatFileSize, getFileTypeIcon } from './FileValidation'
import { Button } from '@/components/ui'

export interface FileWithPreview extends File {
  preview?: string
  id: string
}

interface FilePreviewProps {
  file: FileWithPreview
  onRemove: (fileId: string) => void
  error?: string
}

export const FilePreview: React.FC<FilePreviewProps> = ({ file, onRemove, error }) => {
  return (
    <div 
      className={`
        flex items-center justify-between p-3 sm:p-4 rounded-lg border
        ${error ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-gray-50'}
        transition-colors duration-200
      `}
    >
      <div className="flex items-center space-x-2 sm:space-x-3 flex-1 min-w-0">
        <span className="text-xl sm:text-2xl flex-shrink-0">{getFileTypeIcon(file)}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">
            {file.name}
          </p>
          <p className="text-xs sm:text-sm text-gray-500">
            {formatFileSize(file.size)}
          </p>
          {error && (
            <p className="text-xs sm:text-sm text-red-600 mt-1">{error}</p>
          )}
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onRemove(file.id)}
        className="ml-2 text-gray-400 hover:text-red-600"
        aria-label={`Remove ${file.name}`}
      >
        <svg 
          className="w-5 h-5" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth={2} 
            d="M6 18L18 6M6 6l12 12" 
          />
        </svg>
      </Button>
    </div>
  )
}