'use client'

import React from 'react'
import { Button } from '@/components/ui'
import { UploadFile } from '@/types'
import FileStatusBadge from './FileStatusBadge'

export interface FileListProps {
  files: UploadFile[]
  onCancelFile: (fileId: string) => void
  onRetryFile: (fileId: string) => void
  onRemoveFile: (fileId: string) => void
}

/**
 * File List Component
 * Displays list of files with their upload status and actions
 */
const FileList: React.FC<FileListProps> = ({
  files,
  onCancelFile,
  onRetryFile,
  onRemoveFile
}) => {
  if (files.length === 0) return null

  return (
    <div className="space-y-3">
      {files.map((file) => (
        <div key={file.id} className="border rounded-lg p-4 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3">
                <span className="font-medium text-gray-900">
                  {file.file.name}
                </span>
                <span className="text-sm text-gray-500">
                  ({(file.file.size / 1024 / 1024).toFixed(1)} MB)
                </span>
                <FileStatusBadge status={file.status} />
              </div>

              {file.status === 'uploading' && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${file.progress}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-500 mt-1">
                    {file.progress}% uploaded
                  </span>
                </div>
              )}

              {file.error && (
                <p className="text-sm text-red-600 mt-1">{file.error}</p>
              )}
            </div>

            <div className="flex items-center space-x-2">
              {file.status === 'uploading' && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onCancelFile(file.id)}
                >
                  Cancel
                </Button>
              )}

              {file.status === 'error' && (
                <Button
                  size="sm"
                  onClick={() => onRetryFile(file.id)}
                >
                  Retry
                </Button>
              )}

              {['pending', 'error', 'cancelled'].includes(file.status) && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onRemoveFile(file.id)}
                >
                  Remove
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default FileList