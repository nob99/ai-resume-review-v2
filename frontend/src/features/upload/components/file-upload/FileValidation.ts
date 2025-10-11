// File validation utilities for upload components
import {
  ACCEPTED_FILE_TYPES,
  ACCEPTED_EXTENSIONS,
  MAX_FILE_SIZE,
  MIN_FILE_SIZE
} from '../../constants'

export interface FileValidationConfig {
  allowedTypes: string[]
  maxFileSize: number
  minFileSize?: number
  allowedExtensions: string[]
}

/**
 * Default validation configuration for resume files
 */
export const RESUME_VALIDATION_CONFIG: FileValidationConfig = {
  allowedTypes: Object.keys(ACCEPTED_FILE_TYPES),
  allowedExtensions: [...ACCEPTED_EXTENSIONS],
  maxFileSize: MAX_FILE_SIZE,
  minFileSize: MIN_FILE_SIZE
}

/**
 * Format file size in human readable format
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  if (bytes < 0) return `${Math.abs(bytes).toFixed(1)} B`

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  // Ensure i is within bounds
  const sizeIndex = Math.min(i, sizes.length - 1)

  return `${(bytes / Math.pow(k, sizeIndex)).toFixed(1)} ${sizes[sizeIndex]}`
}