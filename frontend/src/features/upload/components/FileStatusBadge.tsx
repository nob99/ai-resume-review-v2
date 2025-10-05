'use client'

import React from 'react'
import { UploadFile } from '@/types'

export interface FileStatusBadgeProps {
  status: UploadFile['status']
}

/**
 * File Status Badge Component
 * Shows visual status indicator for uploaded files
 */
const FileStatusBadge: React.FC<FileStatusBadgeProps> = ({ status }) => {
  const styles = {
    pending: 'bg-gray-100 text-gray-800',
    uploading: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800'
  }

  const labels = {
    pending: 'Pending',
    uploading: 'Uploading',
    success: 'Success',
    error: 'Error',
    cancelled: 'Cancelled'
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

export default FileStatusBadge