// File validation utilities for UPLOAD-001

export const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
}

export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB in bytes

export interface FileValidationResult {
  isValid: boolean
  error?: string
}

export function validateFileType(file: File): FileValidationResult {
  const acceptedTypes = Object.keys(ACCEPTED_FILE_TYPES)
  
  if (!acceptedTypes.includes(file.type)) {
    return {
      isValid: false,
      error: `File type not supported. Please upload PDF, DOC, or DOCX files only.`
    }
  }
  
  return { isValid: true }
}

export function validateFileSize(file: File): FileValidationResult {
  if (file.size > MAX_FILE_SIZE) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1)
    const maxMB = (MAX_FILE_SIZE / (1024 * 1024)).toFixed(0)
    return {
      isValid: false,
      error: `File size (${sizeMB}MB) exceeds maximum allowed size of ${maxMB}MB`
    }
  }
  
  return { isValid: true }
}

export function validateFile(file: File): FileValidationResult {
  // Check file type first
  const typeValidation = validateFileType(file)
  if (!typeValidation.isValid) {
    return typeValidation
  }
  
  // Then check file size
  const sizeValidation = validateFileSize(file)
  if (!sizeValidation.isValid) {
    return sizeValidation
  }
  
  return { isValid: true }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function getFileExtension(filename: string): string {
  return filename.slice(((filename.lastIndexOf(".") - 1) >>> 0) + 2)
}

export function getFileTypeIcon(file: File): string {
  const extension = getFileExtension(file.name).toLowerCase()
  
  switch (extension) {
    case 'pdf':
      return '📄'
    case 'doc':
    case 'docx':
      return '📝'
    default:
      return '📎'
  }
}