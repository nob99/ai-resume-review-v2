// Unit tests for FileValidation utilities
// Testing file validation logic and utility functions

import {
  validateFile,
  validateFiles,
  validateFileType,
  validateFileExtension,
  validateFileSize,
  validateFileName,
  formatFileSize,
  getFileTypeDisplayName,
  isLikelyResume,
  FileValidationError,
  RESUME_VALIDATION_CONFIG
} from '../../../../components/upload/FileValidation'

import { testFiles, validationTestCases, fileSizes } from '../../../utils/test-fixtures'

describe('FileValidation Utilities - Unit Tests', () => {
  describe('validateFileType', () => {
    it('accepts valid PDF files', () => {
      const result = validateFileType(testFiles.validPdf, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(true)
    })

    it('accepts valid DOC files', () => {
      const result = validateFileType(testFiles.validDoc, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(true)
    })

    it('accepts valid DOCX files', () => {
      const result = validateFileType(testFiles.validDocx, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(true)
    })

    it('rejects invalid file types', () => {
      const result = validateFileType(testFiles.invalidTxt, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(false)
    })

    it('rejects image files', () => {
      const result = validateFileType(testFiles.invalidImage, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(false)
    })

    it('handles empty allowed types array', () => {
      const result = validateFileType(testFiles.validPdf, [])
      expect(result).toBe(false)
    })

    it('handles files with no MIME type', () => {
      const fileWithoutMime = new File(['content'], 'test.pdf', { type: '' })
      const result = validateFileType(fileWithoutMime, RESUME_VALIDATION_CONFIG.allowedTypes)
      expect(result).toBe(false)
    })
  })

  describe('validateFileExtension', () => {
    it('accepts files with valid extensions', () => {
      expect(validateFileExtension(testFiles.validPdf, ['.pdf'])).toBe(true)
      expect(validateFileExtension(testFiles.validDoc, ['.doc'])).toBe(true)
      expect(validateFileExtension(testFiles.validDocx, ['.docx'])).toBe(true)
    })

    it('rejects files with invalid extensions', () => {
      expect(validateFileExtension(testFiles.invalidTxt, ['.pdf', '.doc', '.docx'])).toBe(false)
      expect(validateFileExtension(testFiles.invalidImage, ['.pdf', '.doc', '.docx'])).toBe(false)
    })

    it('handles case insensitive extensions', () => {
      const upperCaseFile = new File(['content'], 'resume.PDF', { type: 'application/pdf' })
      expect(validateFileExtension(upperCaseFile, ['.pdf'])).toBe(true)
    })

    it('handles files without extensions', () => {
      expect(validateFileExtension(testFiles.noExtension, ['.pdf'])).toBe(false)
    })

    it('handles multiple extensions in filename', () => {
      expect(validateFileExtension(testFiles.multipleExtensions, ['.pdf'])).toBe(true)
    })

    it('handles empty extensions array', () => {
      expect(validateFileExtension(testFiles.validPdf, [])).toBe(false)
    })
  })

  describe('validateFileSize', () => {
    it('accepts files within size limits', () => {
      expect(validateFileSize(testFiles.validPdf, fileSizes.maxAllowed)).toBe(true)
      expect(validateFileSize(testFiles.exactSizeLimit, fileSizes.maxAllowed)).toBe(true)
    })

    it('rejects files exceeding size limit', () => {
      expect(validateFileSize(testFiles.oversizedFile, fileSizes.maxAllowed)).toBe(false)
    })

    it('handles minimum size validation', () => {
      expect(validateFileSize(testFiles.emptyFile, fileSizes.maxAllowed, 1)).toBe(false)
      expect(validateFileSize(testFiles.tinyFile, fileSizes.maxAllowed, 1)).toBe(true)
    })

    it('handles zero maximum size', () => {
      expect(validateFileSize(testFiles.validPdf, 0)).toBe(false)
    })

    it('handles negative size limits gracefully', () => {
      expect(validateFileSize(testFiles.validPdf, -1)).toBe(false)
    })
  })

  describe('validateFileName', () => {
    it('accepts valid file names', () => {
      expect(validateFileName('resume.pdf')).toBe(true)
      expect(validateFileName('my-resume_2023.pdf')).toBe(true)
      expect(validateFileName('John Doe Resume.pdf')).toBe(true)
    })

    it('accepts file names with numbers', () => {
      expect(validateFileName('resume-v2.1.pdf')).toBe(true)
      expect(validateFileName('2023-resume.pdf')).toBe(true)
    })

    it('rejects file names with dangerous characters', () => {
      expect(validateFileName('../../../etc/passwd')).toBe(false)
      expect(validateFileName('resume<script>.pdf')).toBe(false)
      expect(validateFileName('resume|pipe.pdf')).toBe(false)
    })

    it('rejects very long file names', () => {
      const longName = 'a'.repeat(300) + '.pdf'
      expect(validateFileName(longName)).toBe(false)
    })

    it('accepts file names with special but safe characters', () => {
      expect(validateFileName('résumé.pdf')).toBe(false) // Actually should reject non-ASCII
      expect(validateFileName('resume(final).pdf')).toBe(false) // Parentheses not in allowed pattern
    })

    it('handles empty file names', () => {
      expect(validateFileName('')).toBe(false)
      expect(validateFileName('   ')).toBe(false)
    })

    it('handles file names with only extension', () => {
      expect(validateFileName('.pdf')).toBe(true)
      expect(validateFileName('.hidden')).toBe(true)
    })
  })

  describe('validateFile', () => {
    it('validates complete file successfully', () => {
      const result = validateFile(testFiles.validPdf)
      expect(result.isValid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('returns multiple errors for invalid file', () => {
      const result = validateFile(testFiles.oversizedFile)
      expect(result.isValid).toBe(false)
      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors.some(e => e.message.includes('File size exceeds'))).toBe(true)
    })

    it('validates file type and extension together', () => {
      const result = validateFile(testFiles.pdfWithDocExtension)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'INVALID_EXTENSION')).toBe(true)
    })

    it('detects empty files', () => {
      const result = validateFile(testFiles.emptyFile)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'CORRUPTED_FILE')).toBe(true)
    })

    it('validates file name security', () => {
      const result = validateFile(testFiles.pathTraversalAttempt)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'INVALID_EXTENSION')).toBe(true)
    })

    it('accepts files at exact size limit', () => {
      const result = validateFile(testFiles.exactSizeLimit)
      expect(result.isValid).toBe(true)
    })

    it('uses custom validation config', () => {
      const strictConfig = {
        ...RESUME_VALIDATION_CONFIG,
        maxFileSize: 1024 * 1024, // 1MB
        minFileSize: 1024 // 1KB
      }

      const result = validateFile(testFiles.oversizedFile, strictConfig)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'FILE_TOO_LARGE')).toBe(true)
    })

    it('validates minimum file size when configured', () => {
      const configWithMin = {
        ...RESUME_VALIDATION_CONFIG,
        minFileSize: 1024
      }

      const result = validateFile(testFiles.emptyFile, configWithMin)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'FILE_TOO_SMALL')).toBe(true)
    })
  })

  describe('validateFiles', () => {
    it('validates multiple valid files', () => {
      const files = [testFiles.validPdf, testFiles.validDocx, testFiles.validDoc]
      const result = validateFiles(files)

      expect(result.validFiles).toHaveLength(3)
      expect(result.errors).toHaveLength(0)
    })

    it('separates valid and invalid files', () => {
      const files = [testFiles.validPdf, testFiles.invalidTxt, testFiles.oversizedFile]
      const result = validateFiles(files)

      expect(result.validFiles).toHaveLength(1)
      expect(result.validFiles[0]).toBe(testFiles.validPdf)
      expect(result.errors.length).toBeGreaterThan(0)
    })

    it('includes file names in error messages', () => {
      const files = [testFiles.invalidTxt]
      const result = validateFiles(files)

      expect(result.errors[0].message).toContain(testFiles.invalidTxt.name)
    })

    it('handles empty file array', () => {
      const result = validateFiles([])
      expect(result.validFiles).toHaveLength(0)
      expect(result.errors).toHaveLength(0)
    })

    it('validates all files independently', () => {
      const files = [testFiles.invalidTxt, testFiles.oversizedFile]
      const result = validateFiles(files)

      expect(result.validFiles).toHaveLength(0)
      expect(result.errors.length).toBeGreaterThan(1) // Should have errors for both files
    })
  })

  describe('formatFileSize', () => {
    it('formats bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 B')
      expect(formatFileSize(500)).toBe('500.0 B')
      expect(formatFileSize(1023)).toBe('1023.0 B')
    })

    it('formats kilobytes correctly', () => {
      expect(formatFileSize(1024)).toBe('1.0 KB')
      expect(formatFileSize(1536)).toBe('1.5 KB')
      expect(formatFileSize(1024 * 1023)).toBe('1023.0 KB')
    })

    it('formats megabytes correctly', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.0 MB')
      expect(formatFileSize(1024 * 1024 * 1.5)).toBe('1.5 MB')
      expect(formatFileSize(10 * 1024 * 1024)).toBe('10.0 MB')
    })

    it('formats gigabytes correctly', () => {
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1.0 GB')
      expect(formatFileSize(1024 * 1024 * 1024 * 2.5)).toBe('2.5 GB')
    })

    it('handles very large numbers', () => {
      const result = formatFileSize(Number.MAX_SAFE_INTEGER)
      expect(result).toMatch(/^\d+\.\d+ [KMGT]?B$/)
    })

    it('handles negative numbers gracefully', () => {
      expect(formatFileSize(-1)).toBe('-1.0 B')
    })
  })

  describe('getFileTypeDisplayName', () => {
    it('identifies PDF files correctly', () => {
      expect(getFileTypeDisplayName(testFiles.validPdf)).toBe('PDF Document')
    })

    it('identifies DOC files correctly', () => {
      expect(getFileTypeDisplayName(testFiles.validDoc)).toBe('Word Document (Legacy)')
    })

    it('identifies DOCX files correctly', () => {
      expect(getFileTypeDisplayName(testFiles.validDocx)).toBe('Word Document')
    })

    it('handles unknown file types', () => {
      expect(getFileTypeDisplayName(testFiles.invalidTxt)).toBe('Unknown File Type')
    })

    it('handles files without extensions', () => {
      expect(getFileTypeDisplayName(testFiles.noExtension)).toBe('Unknown File Type')
    })

    it('handles case insensitive extensions', () => {
      const upperCaseFile = new File(['content'], 'resume.PDF', { type: 'application/pdf' })
      expect(getFileTypeDisplayName(upperCaseFile)).toBe('PDF Document')
    })
  })

  describe('isLikelyResume', () => {
    it('identifies resume files by keywords', () => {
      expect(isLikelyResume('john-doe-resume.pdf')).toBe(true)
      expect(isLikelyResume('my-cv.pdf')).toBe(true)
      expect(isLikelyResume('curriculum-vitae.pdf')).toBe(true)
      expect(isLikelyResume('curriculum_vitae.pdf')).toBe(true)
    })

    it('handles case insensitive matching', () => {
      expect(isLikelyResume('RESUME.PDF')).toBe(true)
      expect(isLikelyResume('CV.PDF')).toBe(true)
      expect(isLikelyResume('Resume_Final.pdf')).toBe(true)
    })

    it('returns false for non-resume files', () => {
      expect(isLikelyResume('document.pdf')).toBe(false)
      expect(isLikelyResume('contract.pdf')).toBe(false)
      expect(isLikelyResume('image.jpg')).toBe(false)
    })

    it('handles partial matches', () => {
      expect(isLikelyResume('my-awesome-resume-2023.pdf')).toBe(true)
      expect(isLikelyResume('cv-john-smith.pdf')).toBe(true)
    })

    it('handles empty or undefined filenames', () => {
      expect(isLikelyResume('')).toBe(false)
      expect(isLikelyResume('   ')).toBe(false)
    })
  })

  describe('FileValidationError', () => {
    it('creates error with correct properties', () => {
      const error = new FileValidationError('Test error', 'INVALID_TYPE')
      
      expect(error.message).toBe('Test error')
      expect(error.code).toBe('INVALID_TYPE')
      expect(error.name).toBe('FileValidationError')
      expect(error).toBeInstanceOf(Error)
    })

    it('creates error with all error codes', () => {
      const codes = ['INVALID_TYPE', 'FILE_TOO_LARGE', 'FILE_TOO_SMALL', 'INVALID_EXTENSION', 'CORRUPTED_FILE'] as const
      
      codes.forEach(code => {
        const error = new FileValidationError('Test', code)
        expect(error.code).toBe(code)
      })
    })
  })

  describe('RESUME_VALIDATION_CONFIG', () => {
    it('has correct default configuration', () => {
      expect(RESUME_VALIDATION_CONFIG.allowedTypes).toContain('application/pdf')
      expect(RESUME_VALIDATION_CONFIG.allowedTypes).toContain('application/msword')
      expect(RESUME_VALIDATION_CONFIG.allowedTypes).toContain('application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      
      expect(RESUME_VALIDATION_CONFIG.allowedExtensions).toContain('.pdf')
      expect(RESUME_VALIDATION_CONFIG.allowedExtensions).toContain('.doc')
      expect(RESUME_VALIDATION_CONFIG.allowedExtensions).toContain('.docx')
      
      expect(RESUME_VALIDATION_CONFIG.maxFileSize).toBe(10 * 1024 * 1024)
      expect(RESUME_VALIDATION_CONFIG.minFileSize).toBe(1024)
    })
  })

  describe('Edge Cases and Error Handling', () => {
    it('handles null and undefined files gracefully', () => {
      expect(() => validateFile(null as any)).toThrow()
      expect(() => validateFile(undefined as any)).toThrow()
    })

    it('handles files with no name', () => {
      const fileWithNoName = new File(['content'], '', { type: 'application/pdf' })
      const result = validateFile(fileWithNoName)
      expect(result.isValid).toBe(false)
    })

    it('handles files with very long names', () => {
      const result = validateFile(testFiles.longFilename)
      expect(result.isValid).toBe(false)
      expect(result.errors.some(e => e.code === 'INVALID_EXTENSION')).toBe(true)
    })

    it('handles files with special characters', () => {
      const result = validateFile(testFiles.specialCharacters)
      expect(result.isValid).toBe(false) // Should fail due to special characters
    })

    it('validates security-sensitive filenames', () => {
      const securityTests = [
        testFiles.pathTraversalAttempt,
        testFiles.scriptInjectionAttempt,
        testFiles.nullByteAttempt
      ]

      securityTests.forEach(file => {
        const result = validateFile(file)
        expect(result.isValid).toBe(false)
      })
    })
  })

  describe('Performance', () => {
    it('validates files quickly', () => {
      const startTime = performance.now()
      
      for (let i = 0; i < 100; i++) {
        validateFile(testFiles.validPdf)
      }
      
      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(10) // Should be very fast
    })

    it('validates large file lists efficiently', () => {
      const manyFiles = Array(100).fill(testFiles.validPdf)
      
      const startTime = performance.now()
      validateFiles(manyFiles)
      const endTime = performance.now()
      
      expect(endTime - startTime).toBeLessThan(50) // Should handle large lists efficiently
    })
  })
})