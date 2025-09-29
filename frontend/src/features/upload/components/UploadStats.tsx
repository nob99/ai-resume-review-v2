'use client'

import React from 'react'
import { UploadFile } from '@/types'

export interface UploadStatsProps {
  files: UploadFile[]
  uploadingFiles: UploadFile[]
  successFiles: UploadFile[]
  errorFiles: UploadFile[]
}

/**
 * Upload Stats Component
 * Shows summary statistics for file uploads
 */
const UploadStats: React.FC<UploadStatsProps> = ({
  files,
  uploadingFiles,
  successFiles,
  errorFiles
}) => {
  if (files.length === 0) return null

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-gray-600">{files.length}</div>
          <div className="text-sm text-gray-500">Total Files</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-blue-600">{uploadingFiles.length}</div>
          <div className="text-sm text-gray-500">Uploading</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-600">{successFiles.length}</div>
          <div className="text-sm text-gray-500">Completed</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-red-600">{errorFiles.length}</div>
          <div className="text-sm text-gray-500">Failed</div>
        </div>
      </div>
    </div>
  )
}

export default UploadStats