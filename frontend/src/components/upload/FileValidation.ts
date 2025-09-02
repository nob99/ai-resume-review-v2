// File validation utilities for upload components

export interface FileValidationRule {
  validate: (file: File) => boolean
  errorMessage: string
}

export interface FileValidationConfig {
  allowedTypes: string[]
  maxFileSize: number
  minFileSize?: number
  allowedExtensions: string[]
}

export class FileValidationError extends Error {
  constructor(
    message: string, 
    public code: 'INVALID_TYPE' | 'FILE_TOO_LARGE' | 'FILE_TOO_SMALL' | 'INVALID_EXTENSION' | 'CORRUPTED_FILE'
  ) {
    super(message)
    this.name = 'FileValidationError'
  }
}

/**
 * Default validation configuration for resume files
 */
export const RESUME_VALIDATION_CONFIG: FileValidationConfig = {
  allowedTypes: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  allowedExtensions: ['.pdf', '.doc', '.docx'],
  maxFileSize: 10 * 1024 * 1024, // 10MB
  minFileSize: 1024 // 1KB minimum
}

/**
 * Validates file type based on MIME type
 */
export const validateFileType = (file: File, allowedTypes: string[]): boolean => {
  return allowedTypes.includes(file.type)
}

/**
 * Validates file extension
 */
export const validateFileExtension = (file: File, allowedExtensions: string[]): boolean => {
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  return allowedExtensions.includes(fileExtension)
}

/**
 * Validates file size
 */
export const validateFileSize = (file: File, maxSize: number, minSize: number = 0): boolean => {
  return file.size >= minSize && file.size <= maxSize
}

/**
 * Validates file name for security (no special characters that could be dangerous)
 */
export const validateFileName = (fileName: string): boolean => {
  // Check for empty or whitespace-only strings
  if (!fileName || !fileName.trim()) {
    return false
  }
  
  // Allow letters, numbers, spaces, dots, hyphens, underscores
  const safeNamePattern = /^[a-zA-Z0-9\s._-]+$/
  return safeNamePattern.test(fileName) && fileName.length <= 255
}

/**
 * Comprehensive file validation
 */
export const validateFile = (
  file: File, 
  config: FileValidationConfig = RESUME_VALIDATION_CONFIG
): { isValid: boolean; errors: FileValidationError[] } => {
  const errors: FileValidationError[] = []

  // File name validation
  if (!validateFileName(file.name)) {
    errors.push(new FileValidationError(
      'File name contains invalid characters. Use only letters, numbers, spaces, dots, hyphens, and underscores.',
      'INVALID_EXTENSION'
    ))
  }

  // File type validation (MIME type)
  if (!validateFileType(file, config.allowedTypes)) {
    errors.push(new FileValidationError(
      'File type not supported. Please upload PDF, DOC, or DOCX files only.',
      'INVALID_TYPE'
    ))
  }

  // File extension validation (additional security check)
  if (!validateFileExtension(file, config.allowedExtensions)) {
    errors.push(new FileValidationError(
      'File extension not supported. Please upload files with .pdf, .doc, or .docx extensions.',
      'INVALID_EXTENSION'
    ))
  }

  // File size validation
  if (config.minFileSize && file.size < config.minFileSize) {
    errors.push(new FileValidationError(
      `File is too small. Minimum size is ${formatFileSize(config.minFileSize)}.`,
      'FILE_TOO_SMALL'
    ))
  }

  if (file.size > config.maxFileSize) {
    const maxSizeMB = formatFileSize(config.maxFileSize)
    const currentSizeMB = formatFileSize(file.size)
    errors.push(new FileValidationError(
      `File size exceeds ${maxSizeMB} limit. Current size: ${currentSizeMB}`,
      'FILE_TOO_LARGE'
    ))
  }

  // Basic file corruption check (file size 0)
  if (file.size === 0) {
    errors.push(new FileValidationError(
      'File appears to be empty or corrupted.',
      'CORRUPTED_FILE'
    ))
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}

/**
 * Validates multiple files at once
 */
export const validateFiles = (
  files: File[], 
  config: FileValidationConfig = RESUME_VALIDATION_CONFIG
): { validFiles: File[]; errors: FileValidationError[] } => {
  const validFiles: File[] = []
  const allErrors: FileValidationError[] = []

  for (const file of files) {
    const { isValid, errors } = validateFile(file, config)
    if (isValid) {
      validFiles.push(file)
    } else {
      // Prefix errors with filename for clarity
      const fileErrors = errors.map(error => 
        new FileValidationError(
          `${file.name}: ${error.message}`,
          error.code
        )
      )
      allErrors.push(...fileErrors)
    }
  }

  return { validFiles, errors: allErrors }
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

/**
 * Get file type display name
 */
export const getFileTypeDisplayName = (file: File): string => {
  const extension = file.name.split('.').pop()?.toLowerCase()
  
  switch (extension) {
    case 'pdf':
      return 'PDF Document'
    case 'doc':
      return 'Word Document (Legacy)'
    case 'docx':
      return 'Word Document'
    default:
      return 'Unknown File Type'
  }
}

/**
 * Check if file is likely a resume based on name patterns
 */
export const isLikelyResume = (fileName: string): boolean => {
  const resumeKeywords = ['resume', 'cv', 'curriculum', 'vitae']
  const lowerName = fileName.toLowerCase()
  
  return resumeKeywords.some(keyword => lowerName.includes(keyword))
}