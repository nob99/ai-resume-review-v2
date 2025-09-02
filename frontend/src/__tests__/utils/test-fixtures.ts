// Test fixtures for upload component testing
// Following backend patterns for comprehensive test data

import { UploadedFile } from '../../types'

/**
 * Mock File objects for testing file upload functionality
 * Covers valid files, invalid files, and edge cases
 */
export const testFiles = {
  // Valid resume files
  validPdf: new File(['%PDF-1.4 mock PDF content'], 'john-doe-resume.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  validDocx: new File(['PK mock DOCX content'], 'jane-smith-cv.docx', {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    lastModified: Date.now()
  }),

  validDoc: new File(['mock DOC content'], 'resume-2023.doc', {
    type: 'application/msword',
    lastModified: Date.now()
  }),

  // Valid files with resume-like names
  resumeWithKeywords: new File(['PDF content'], 'my-resume-final.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  cvFile: new File(['PDF content'], 'curriculum-vitae.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  // Invalid file types
  invalidTxt: new File(['Plain text content'], 'resume.txt', {
    type: 'text/plain',
    lastModified: Date.now()
  }),

  invalidImage: new File(['mock image data'], 'resume.jpg', {
    type: 'image/jpeg',
    lastModified: Date.now()
  }),

  invalidExecutable: new File(['executable content'], 'resume.exe', {
    type: 'application/x-msdownload',
    lastModified: Date.now()
  }),

  // File size edge cases
  oversizedFile: new File([new ArrayBuffer(11 * 1024 * 1024)], 'large-resume.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  exactSizeLimit: new File([new ArrayBuffer(10 * 1024 * 1024)], 'exactly-10mb.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  emptyFile: new File([''], 'empty-resume.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  tinyFile: new File(['x'], 'tiny-resume.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  // Filename edge cases
  noExtension: new File(['PDF content'], 'resume', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  multipleExtensions: new File(['PDF content'], 'resume.backup.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  longFilename: new File(['PDF content'], 'a'.repeat(200) + '-resume.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  specialCharacters: new File(['PDF content'], 'résumé_v2.1[final]@company.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  // Security test cases
  pathTraversalAttempt: new File(['PDF content'], '../../../etc/passwd.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  scriptInjectionAttempt: new File(['PDF content'], '<script>alert("xss")</script>.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  nullByteAttempt: new File(['PDF content'], 'resume\0.pdf', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  // Files with mismatched extensions and MIME types
  pdfWithDocExtension: new File(['%PDF-1.4 content'], 'resume.doc', {
    type: 'application/pdf',
    lastModified: Date.now()
  }),

  docxWithPdfExtension: new File(['PK DOCX content'], 'resume.pdf', {
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    lastModified: Date.now()
  })
}

/**
 * Mock UploadedFile objects for testing file preview and progress
 */
export const mockUploadedFiles: Record<string, UploadedFile> = {
  pending: {
    file: testFiles.validPdf,
    id: 'upload_pending_123',
    status: 'pending',
    progress: 0
  },

  uploading: {
    file: testFiles.validDocx,
    id: 'upload_uploading_456',
    status: 'uploading',
    progress: 45
  },

  validating: {
    file: testFiles.validDoc,
    id: 'upload_validating_789',
    status: 'validating',
    progress: 100
  },

  extracting: {
    file: testFiles.resumeWithKeywords,
    id: 'upload_extracting_012',
    status: 'extracting',
    progress: 75
  },

  completed: {
    file: testFiles.cvFile,
    id: 'upload_completed_345',
    status: 'completed',
    progress: 100,
    extractedText: `John Smith
Senior Software Engineer

Contact Information:
Email: john.smith@email.com
Phone: (555) 123-4567
LinkedIn: linkedin.com/in/johnsmith

Professional Summary:
Experienced full-stack developer with 8+ years in web technologies.
Specialized in React, Node.js, and cloud architecture.

Work Experience:
Senior Software Engineer - TechCorp (2020-Present)
• Led development of microservices architecture
• Mentored team of 5 junior developers
• Implemented CI/CD pipelines reducing deployment time by 60%

Software Engineer - StartupXYZ (2018-2020)
• Built responsive web applications using React and TypeScript
• Developed RESTful APIs with Node.js and Express
• Collaborated with designers to implement pixel-perfect UIs

Education:
Bachelor of Computer Science
State University (2014-2018)

Technical Skills:
• Languages: JavaScript, TypeScript, Python, Java
• Frontend: React, Vue.js, HTML5, CSS3, Tailwind
• Backend: Node.js, Express, Django, PostgreSQL
• Cloud: AWS, Docker, Kubernetes, Terraform
• Tools: Git, Jenkins, JIRA, VS Code`
  },

  error: {
    file: testFiles.invalidTxt,
    id: 'upload_error_678',
    status: 'error',
    progress: 0,
    error: 'File type not supported. Please upload PDF, DOC, or DOCX files only.'
  },

  errorOversized: {
    file: testFiles.oversizedFile,
    id: 'upload_error_oversized_901',
    status: 'error',
    progress: 0,
    error: 'File size exceeds 10.0 MB limit. Current size: 11.0 MB'
  },

  errorCorrupted: {
    file: testFiles.emptyFile,
    id: 'upload_error_corrupted_234',
    status: 'error',
    progress: 0,
    error: 'File appears to be empty or corrupted.'
  }
}

/**
 * Collections of files for testing various scenarios
 */
export const testFileCollections = {
  // Valid file collection
  allValid: [
    testFiles.validPdf,
    testFiles.validDocx,
    testFiles.validDoc
  ],

  // Mixed valid and invalid files
  mixed: [
    testFiles.validPdf,
    testFiles.invalidTxt,
    testFiles.validDocx,
    testFiles.oversizedFile
  ],

  // All invalid files
  allInvalid: [
    testFiles.invalidTxt,
    testFiles.invalidImage,
    testFiles.oversizedFile,
    testFiles.emptyFile
  ],

  // Maximum file count (5 files)
  maxCount: [
    testFiles.validPdf,
    testFiles.validDocx,
    testFiles.validDoc,
    testFiles.resumeWithKeywords,
    testFiles.cvFile
  ],

  // Over maximum file count (6 files)
  overMaxCount: [
    testFiles.validPdf,
    testFiles.validDocx,
    testFiles.validDoc,
    testFiles.resumeWithKeywords,
    testFiles.cvFile,
    testFiles.exactSizeLimit
  ],

  // Edge cases
  edgeCases: [
    testFiles.noExtension,
    testFiles.longFilename,
    testFiles.specialCharacters,
    testFiles.exactSizeLimit
  ],

  // Security test cases
  securityTests: [
    testFiles.pathTraversalAttempt,
    testFiles.scriptInjectionAttempt,
    testFiles.nullByteAttempt,
    testFiles.pdfWithDocExtension
  ]
}

/**
 * Mock uploaded file collections for testing FilePreview component
 */
export const mockUploadedFileCollections = {
  // All files in different states
  mixedStates: [
    mockUploadedFiles.completed,
    mockUploadedFiles.uploading,
    mockUploadedFiles.pending,
    mockUploadedFiles.error
  ],

  // All files completed successfully
  allCompleted: [
    mockUploadedFiles.completed,
    { ...mockUploadedFiles.completed, id: 'completed_2', file: testFiles.validDocx },
    { ...mockUploadedFiles.completed, id: 'completed_3', file: testFiles.validDoc }
  ],

  // All files with errors
  allErrors: [
    mockUploadedFiles.error,
    mockUploadedFiles.errorOversized,
    mockUploadedFiles.errorCorrupted
  ],

  // Files in progress
  inProgress: [
    mockUploadedFiles.uploading,
    mockUploadedFiles.validating,
    mockUploadedFiles.extracting
  ],

  // Single file scenarios
  singleCompleted: [mockUploadedFiles.completed],
  singleError: [mockUploadedFiles.error],
  singleUploading: [mockUploadedFiles.uploading]
}

/**
 * Test data for file validation scenarios
 */
export const validationTestCases = {
  validFiles: [
    { file: testFiles.validPdf, expectedValid: true, description: 'Valid PDF file' },
    { file: testFiles.validDocx, expectedValid: true, description: 'Valid DOCX file' },
    { file: testFiles.validDoc, expectedValid: true, description: 'Valid DOC file' },
  ],

  invalidFiles: [
    { file: testFiles.invalidTxt, expectedValid: false, expectedError: 'File type not supported', description: 'Text file' },
    { file: testFiles.invalidImage, expectedValid: false, expectedError: 'File type not supported', description: 'Image file' },
    { file: testFiles.oversizedFile, expectedValid: false, expectedError: 'File size exceeds', description: 'Oversized file' },
    { file: testFiles.emptyFile, expectedValid: false, expectedError: 'File appears to be empty', description: 'Empty file' },
  ],

  edgeCases: [
    { file: testFiles.exactSizeLimit, expectedValid: true, description: 'File at exact size limit' },
    { file: testFiles.tinyFile, expectedValid: true, description: 'Very small file' },
    { file: testFiles.specialCharacters, expectedValid: true, description: 'File with special characters' },
    { file: testFiles.longFilename, expectedValid: false, expectedError: 'File name', description: 'Very long filename' },
  ]
}

/**
 * Mock API responses for testing
 */
export const mockApiResponses = {
  uploadSuccess: {
    id: 'upload_success_123',
    status: 'completed',
    filename: 'resume.pdf',
    size: 1024 * 1024, // 1MB
    extractedText: 'Mock extracted resume content...',
    processingTime: 2500
  },

  uploadError: {
    detail: 'File validation failed: Invalid file format',
    status_code: 400
  },

  networkError: {
    message: 'Network request failed',
    code: 'NETWORK_ERROR'
  },

  serverError: {
    detail: 'Internal server error during file processing',
    status_code: 500
  }
}

/**
 * Utility functions for creating test data
 */
export const createMockFile = (
  name: string,
  type: string,
  content: string = 'mock content',
  size?: number
): File => {
  const buffer = size ? new ArrayBuffer(size) : content
  return new File([buffer], name, { type, lastModified: Date.now() })
}

export const createMockUploadedFile = (
  file: File,
  status: UploadedFile['status'] = 'pending',
  progress: number = 0,
  error?: string,
  extractedText?: string
): UploadedFile => ({
  file,
  id: `mock_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
  status,
  progress,
  error,
  extractedText
})

/**
 * Test file size constants
 */
export const fileSizes = {
  tiny: 1024, // 1KB
  small: 100 * 1024, // 100KB
  medium: 1024 * 1024, // 1MB
  large: 5 * 1024 * 1024, // 5MB
  maxAllowed: 10 * 1024 * 1024, // 10MB
  overLimit: 11 * 1024 * 1024, // 11MB
  huge: 50 * 1024 * 1024 // 50MB
}

/**
 * Accepted file types for validation testing
 */
export const acceptedMimeTypes = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

export const acceptedExtensions = ['.pdf', '.doc', '.docx']

/**
 * Rejected file types for validation testing
 */
export const rejectedMimeTypes = [
  'text/plain',
  'image/jpeg',
  'image/png',
  'application/zip',
  'application/x-msdownload',
  'text/html',
  'application/javascript'
]