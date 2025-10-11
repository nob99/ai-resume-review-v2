'use client'

import React from 'react'
import { Card, CardHeader, CardContent, Button } from '@/components/ui'
import FileUpload from './FileUpload'
import FileList from './FileList'
import { UploadFile, FileUploadError } from '@/types'

/**
 * FileUploadSection Component
 * Main section component for Step 2: File Upload
 * Orchestrates file selection, upload, and progress display
 */

interface FileUploadSectionProps {
  files: UploadFile[]
  pendingFilesCount: number
  isUploading: boolean
  disabled: boolean
  onFilesSelected: (files: File[]) => void
  onUploadError: (error: FileUploadError) => void
  onStartUpload: () => Promise<void>
  onCancelFile: (fileId: string) => void
  onRetryFile: (fileId: string) => void
  onRemoveFile: (fileId: string) => void
}

export default function FileUploadSection({
  files,
  pendingFilesCount,
  isUploading,
  disabled,
  onFilesSelected,
  onUploadError,
  onStartUpload,
  onCancelFile,
  onRetryFile,
  onRemoveFile
}: FileUploadSectionProps) {
  return (
    <Card className={!disabled ? '' : 'opacity-60'}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-neutral-900">
            Step 2: レジュメの選択
          </h2>
          {disabled && (
            <span className="text-sm text-neutral-500 bg-neutral-100 px-3 py-1 rounded-full">
              Step 1を完了してください
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        <FileUpload
          onFilesSelected={onFilesSelected}
          onError={onUploadError}
          disabled={isUploading || disabled}
          multiple={false}
          maxFiles={1}
        />
        {disabled && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-sm text-yellow-800">
              候補者を選択してからレジュメをアップロードしてください
            </p>
          </div>
        )}

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-semibold text-neutral-900">
              Selected Files ({files.length})
            </h3>
            <FileList
              files={files}
              onCancelFile={onCancelFile}
              onRetryFile={onRetryFile}
              onRemoveFile={onRemoveFile}
            />
          </div>
        )}

        {/* Upload Button */}
        {pendingFilesCount > 0 && (
          <Button
            size="lg"
            onClick={onStartUpload}
            disabled={isUploading || disabled}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {isUploading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
                Uploading...
              </>
            ) : (
              `Upload ${pendingFilesCount} File${pendingFilesCount !== 1 ? 's' : ''}`
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
