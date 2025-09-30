import { uploadApi } from '@/lib/api'
import { ApiResult, UploadStatusResponse } from '@/types'

export interface FileUploadResult {
  id: string
  filename: string
  size: number
  content_type: string
  uploaded_at: string
  extractedText?: string
  candidate_id: string
  upload_id: string
}

/**
 * Upload Service
 * Handles file upload operations
 */
export const uploadService = {
  /**
   * Upload a single file with progress tracking
   */
  async uploadFile(
    file: File,
    candidateId: string,
    onProgress?: (progressEvent: { loaded: number; total?: number }) => void,
    abortController?: AbortController
  ): Promise<ApiResult<FileUploadResult>> {
    return uploadApi.uploadFile(file, candidateId, onProgress, abortController)
  },

  /**
   * Get upload status
   */
  async getUploadStatus(uploadId: string): Promise<ApiResult<UploadStatusResponse>> {
    return uploadApi.getUploadStatus(uploadId)
  },

  /**
   * Delete uploaded file
   */
  async deleteFile(fileId: string): Promise<ApiResult<void>> {
    return uploadApi.deleteFile(fileId)
  }
}

export default uploadService