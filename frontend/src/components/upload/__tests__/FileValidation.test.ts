import {
  validateFileType,
  validateFileSize,
  validateFile,
  formatFileSize,
  getFileExtension,
  getFileTypeIcon,
  MAX_FILE_SIZE
} from '../FileValidation'

describe('FileValidation', () => {
  describe('validateFileType', () => {
    it('should accept PDF files', () => {
      const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
      const result = validateFileType(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should accept DOC files', () => {
      const file = new File(['content'], 'test.doc', { type: 'application/msword' })
      const result = validateFileType(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should accept DOCX files', () => {
      const file = new File(['content'], 'test.docx', { 
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
      })
      const result = validateFileType(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should reject unsupported file types', () => {
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })
      const result = validateFileType(file)
      expect(result.isValid).toBe(false)
      expect(result.error).toContain('File type not supported')
    })

    it('should reject image files', () => {
      const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' })
      const result = validateFileType(file)
      expect(result.isValid).toBe(false)
      expect(result.error).toContain('File type not supported')
    })
  })

  describe('validateFileSize', () => {
    it('should accept files under size limit', () => {
      const content = new Array(1024 * 1024).join('a') // 1MB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' })
      const result = validateFileSize(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should accept files at exactly size limit', () => {
      const content = new Array(MAX_FILE_SIZE).join('a')
      const file = new File([content], 'test.pdf', { type: 'application/pdf' })
      const result = validateFileSize(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should reject files over size limit', () => {
      const content = new Array(MAX_FILE_SIZE + 1024).join('a') // 10MB + 1KB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' })
      const result = validateFileSize(file)
      expect(result.isValid).toBe(false)
      expect(result.error).toContain('exceeds maximum allowed size')
      expect(result.error).toContain('10MB')
    })
  })

  describe('validateFile', () => {
    it('should validate both type and size for valid files', () => {
      const content = new Array(1024).join('a') // 1KB
      const file = new File([content], 'test.pdf', { type: 'application/pdf' })
      const result = validateFile(file)
      expect(result.isValid).toBe(true)
      expect(result.error).toBeUndefined()
    })

    it('should fail validation if type is invalid', () => {
      const content = new Array(1024).join('a')
      const file = new File([content], 'test.txt', { type: 'text/plain' })
      const result = validateFile(file)
      expect(result.isValid).toBe(false)
      expect(result.error).toContain('File type not supported')
    })

    it('should fail validation if size is invalid', () => {
      const content = new Array(MAX_FILE_SIZE + 1024).join('a')
      const file = new File([content], 'test.pdf', { type: 'application/pdf' })
      const result = validateFile(file)
      expect(result.isValid).toBe(false)
      expect(result.error).toContain('exceeds maximum allowed size')
    })
  })

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 Bytes')
      expect(formatFileSize(512)).toBe('512 Bytes')
    })

    it('should format KB correctly', () => {
      expect(formatFileSize(1024)).toBe('1 KB')
      expect(formatFileSize(1536)).toBe('1.5 KB')
      expect(formatFileSize(2048)).toBe('2 KB')
    })

    it('should format MB correctly', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(formatFileSize(1.5 * 1024 * 1024)).toBe('1.5 MB')
      expect(formatFileSize(10 * 1024 * 1024)).toBe('10 MB')
    })

    it('should format GB correctly', () => {
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
      expect(formatFileSize(2.5 * 1024 * 1024 * 1024)).toBe('2.5 GB')
    })
  })

  describe('getFileExtension', () => {
    it('should extract file extensions correctly', () => {
      expect(getFileExtension('document.pdf')).toBe('pdf')
      expect(getFileExtension('resume.doc')).toBe('doc')
      expect(getFileExtension('file.docx')).toBe('docx')
      expect(getFileExtension('test')).toBe('')
      expect(getFileExtension('file.with.dots.pdf')).toBe('pdf')
    })

    it('should handle edge cases', () => {
      expect(getFileExtension('')).toBe('')
      expect(getFileExtension('.')).toBe('')
      expect(getFileExtension('.hidden')).toBe('')
    })
  })

  describe('getFileTypeIcon', () => {
    it('should return correct icon for PDF files', () => {
      const file = new File([''], 'test.pdf', { type: 'application/pdf' })
      expect(getFileTypeIcon(file)).toBe('📄')
    })

    it('should return correct icon for DOC files', () => {
      const file = new File([''], 'test.doc', { type: 'application/msword' })
      expect(getFileTypeIcon(file)).toBe('📝')
    })

    it('should return correct icon for DOCX files', () => {
      const file = new File([''], 'test.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      expect(getFileTypeIcon(file)).toBe('📝')
    })

    it('should return default icon for unknown files', () => {
      const file = new File([''], 'test.txt', { type: 'text/plain' })
      expect(getFileTypeIcon(file)).toBe('📎')
    })
  })
})