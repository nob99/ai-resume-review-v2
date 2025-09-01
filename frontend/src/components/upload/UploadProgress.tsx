'use client'

import React from 'react'

export type UploadStatus = 'idle' | 'uploading' | 'validating' | 'extracting' | 'success' | 'error'

interface UploadProgressProps {
  status: UploadStatus
  progress: number // 0-100
  message?: string
}

const statusMessages: Record<UploadStatus, string> = {
  idle: 'Ready to upload',
  uploading: 'Uploading file...',
  validating: 'Validating file...',
  extracting: 'Extracting text content...',
  success: 'Upload completed successfully!',
  error: 'Upload failed'
}

const statusColors: Record<UploadStatus, string> = {
  idle: 'bg-gray-200',
  uploading: 'bg-blue-500',
  validating: 'bg-yellow-500',
  extracting: 'bg-indigo-500',
  success: 'bg-green-500',
  error: 'bg-red-500'
}

export const UploadProgress: React.FC<UploadProgressProps> = ({ 
  status, 
  progress, 
  message 
}) => {
  const displayMessage = message || statusMessages[status]
  const isActive = status !== 'idle' && status !== 'error' && status !== 'success'
  
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {displayMessage}
        </span>
        {status !== 'idle' && (
          <span className="text-sm text-gray-500">
            {progress}%
          </span>
        )}
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
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
      
      {status === 'error' && message && (
        <p className="mt-2 text-sm text-red-600">{message}</p>
      )}
      
      {status === 'success' && (
        <p className="mt-2 text-sm text-green-600 flex items-center">
          <svg 
            className="w-4 h-4 mr-1" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path 
              fillRule="evenodd" 
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" 
              clipRule="evenodd" 
            />
          </svg>
          File ready for analysis
        </p>
      )}
    </div>
  )
}