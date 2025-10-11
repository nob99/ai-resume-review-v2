/**
 * Upload Feature Components
 * Barrel exports for all upload workflow sections
 */

// Section components (main workflow steps)
export * from './candidate-selection'
export * from './file-upload'
export * from './industry-selection'
export * from './analysis-results'

// Legacy exports (for backward compatibility - can be removed later)
export { default as FileUpload } from './file-upload/FileUpload'
export { default as FileList } from './file-upload/FileList'
export { default as FileStatusBadge } from './file-upload/FileStatusBadge'
export { default as IndustrySelector } from './industry-selection/IndustrySelector'
export { default as AnalysisResults } from './AnalysisResults'
export * from './file-upload/FileValidation'
