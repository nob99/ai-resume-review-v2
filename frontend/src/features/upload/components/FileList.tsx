'use client'

import React from 'react'
import { Button } from '@/components/ui'
import { UploadFile } from '@/types'
import FileStatusBadge from './FileStatusBadge'
import { FileUploadStatus } from '../constants'

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
  // Handle keyboard navigation for buttons
  const handleKeyDown = (
    e: React.KeyboardEvent,
    fileId: string,
    action: 'cancel' | 'retry' | 'remove'
  ) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      switch (action) {
        case 'cancel':
          onCancelFile(fileId)
          break
        case 'retry':
          onRetryFile(fileId)
          break
        case 'remove':
          onRemoveFile(fileId)
          break
      }
    }
  }

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

              {file.status === FileUploadStatus.UPLOADING && (
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
              {file.status === FileUploadStatus.UPLOADING && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onCancelFile(file.id)}
                  onKeyDown={(e) => handleKeyDown(e, file.id, 'cancel')}
                  aria-label={`Cancel upload of ${file.file.name}`}
                  title={`Cancel upload of ${file.file.name}`}
                >
                  Cancel
                </Button>
              )}

              {file.status === FileUploadStatus.ERROR && (
                <Button
                  size="sm"
                  onClick={() => onRetryFile(file.id)}
                  onKeyDown={(e) => handleKeyDown(e, file.id, 'retry')}
                  aria-label={`Retry upload of ${file.file.name}`}
                  title={`Retry failed upload of ${file.file.name}`}
                >
                  Retry
                </Button>
              )}

              {[FileUploadStatus.PENDING, FileUploadStatus.ERROR, FileUploadStatus.CANCELLED].includes(file.status) && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onRemoveFile(file.id)}
                  onKeyDown={(e) => handleKeyDown(e, file.id, 'remove')}
                  aria-label={`Remove ${file.file.name} from list`}
                  title={`Remove ${file.file.name} from upload list`}
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