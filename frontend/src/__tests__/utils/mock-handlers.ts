// Mock Service Worker handlers for API testing
// Following backend patterns for comprehensive API mocking

import { rest } from 'msw'
import { mockApiResponses } from './test-fixtures'

/**
 * Mock handlers for file upload API endpoints
 * Simulates various success and error scenarios
 */
export const uploadHandlers = [
  // Successful file upload
  rest.post('/api/v1/upload/resume', async (req, res, ctx) => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 100))
    
    return res(
      ctx.status(200),
      ctx.json({
        ...mockApiResponses.uploadSuccess,
        id: `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      })
    )
  }),

  // File validation error (invalid type)
  rest.post('/api/v1/upload/resume-invalid-type', (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({
        detail: 'File type not supported. Please upload PDF, DOC, or DOCX files only.',
        status_code: 400
      })
    )
  }),

  // File size error (too large)
  rest.post('/api/v1/upload/resume-too-large', (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({
        detail: 'File size exceeds 10.0 MB limit. Current size: 11.0 MB',
        status_code: 400
      })
    )
  }),

  // Server processing error
  rest.post('/api/v1/upload/resume-server-error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({
        detail: 'Internal server error during file processing',
        status_code: 500
      })
    )
  }),

  // Network timeout simulation
  rest.post('/api/v1/upload/resume-timeout', (req, res, ctx) => {
    return res(
      ctx.delay('infinite')
    )
  }),

  // Rate limiting error
  rest.post('/api/v1/upload/resume-rate-limit', (req, res, ctx) => {
    return res(
      ctx.status(429),
      ctx.json({
        detail: 'Too many upload requests. Please try again later.',
        status_code: 429
      })
    )
  }),

  // Virus scanning failure
  rest.post('/api/v1/upload/resume-virus-detected', (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({
        detail: 'File failed security scan. Upload rejected.',
        status_code: 400
      })
    )
  }),

  // Text extraction failure
  rest.post('/api/v1/upload/resume-extraction-failed', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 'upload_extraction_failed',
        status: 'error',
        filename: 'corrupted-resume.pdf',
        error: 'Text extraction failed. File may be corrupted or password-protected.'
      })
    )
  }),

  // Get upload status endpoint
  rest.get('/api/v1/upload/:uploadId/status', (req, res, ctx) => {
    const { uploadId } = req.params
    
    // Simulate different statuses based on ID
    if (uploadId.includes('completed')) {
      return res(
        ctx.status(200),
        ctx.json({
          id: uploadId,
          status: 'completed',
          progress: 100,
          extractedText: mockApiResponses.uploadSuccess.extractedText
        })
      )
    } else if (uploadId.includes('error')) {
      return res(
        ctx.status(200),
        ctx.json({
          id: uploadId,
          status: 'error',
          progress: 0,
          error: 'Processing failed'
        })
      )
    } else {
      return res(
        ctx.status(200),
        ctx.json({
          id: uploadId,
          status: 'processing',
          progress: 75
        })
      )
    }
  }),

  // Delete upload endpoint
  rest.delete('/api/v1/upload/:uploadId', (req, res, ctx) => {
    return res(
      ctx.status(204)
    )
  }),

  // List uploads endpoint
  rest.get('/api/v1/upload/list', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        uploads: [
          {
            id: 'upload_1',
            filename: 'resume-1.pdf',
            status: 'completed',
            uploadedAt: new Date().toISOString()
          },
          {
            id: 'upload_2',
            filename: 'resume-2.docx',
            status: 'processing',
            uploadedAt: new Date().toISOString()
          }
        ],
        total: 2
      })
    )
  }),

  // Health check endpoint
  rest.get('/api/health', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ status: 'ok', timestamp: new Date().toISOString() })
    )
  })
]

/**
 * Error handlers for testing network failures
 */
export const errorHandlers = [
  // Network error
  rest.post('/api/v1/upload/network-error', (req, res, ctx) => {
    return res.networkError('Network request failed')
  }),

  // Generic server error
  rest.post('/api/v1/upload/generic-error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json(mockApiResponses.serverError)
    )
  })
]

/**
 * Handlers for progressive upload simulation
 * Useful for testing upload progress indicators
 */
export const progressiveUploadHandlers = [
  // Simulate progressive upload with status updates
  rest.post('/api/v1/upload/progressive', async (req, res, ctx) => {
    const uploadId = `progressive_${Date.now()}`
    
    // Return initial upload response
    return res(
      ctx.status(202), // Accepted
      ctx.json({
        id: uploadId,
        status: 'uploading',
        progress: 0
      })
    )
  }),

  // Status endpoint that simulates progress
  rest.get('/api/v1/upload/progressive/:uploadId/status', async (req, res, ctx) => {
    const { uploadId } = req.params
    const startTime = parseInt(uploadId.split('_')[1])
    const elapsed = Date.now() - startTime
    
    // Simulate different phases of upload processing
    if (elapsed < 1000) {
      return res(
        ctx.json({
          id: uploadId,
          status: 'uploading',
          progress: Math.min(90, elapsed / 10)
        })
      )
    } else if (elapsed < 2000) {
      return res(
        ctx.json({
          id: uploadId,
          status: 'validating',
          progress: 95
        })
      )
    } else if (elapsed < 3000) {
      return res(
        ctx.json({
          id: uploadId,
          status: 'extracting',
          progress: 98
        })
      )
    } else {
      return res(
        ctx.json({
          id: uploadId,
          status: 'completed',
          progress: 100,
          extractedText: mockApiResponses.uploadSuccess.extractedText
        })
      )
    }
  })
]

/**
 * Handlers for testing batch upload scenarios
 */
export const batchUploadHandlers = [
  // Batch upload endpoint
  rest.post('/api/v1/upload/batch', async (req, res, ctx) => {
    const formData = await req.formData()
    const files = formData.getAll('files') as File[]
    
    const uploadResults = files.map((file, index) => ({
      id: `batch_${Date.now()}_${index}`,
      filename: file.name,
      status: Math.random() > 0.8 ? 'error' : 'completed', // 20% failure rate
      progress: 100,
      ...(Math.random() > 0.8 && { error: 'Processing failed for this file' })
    }))
    
    return res(
      ctx.status(200),
      ctx.json({
        uploads: uploadResults,
        totalFiles: files.length,
        successCount: uploadResults.filter(r => r.status === 'completed').length,
        errorCount: uploadResults.filter(r => r.status === 'error').length
      })
    )
  })
]

/**
 * Authentication-related handlers for testing protected endpoints
 */
export const authHandlers = [
  // Protected upload endpoint requiring authentication
  rest.post('/api/v1/upload/protected', (req, res, ctx) => {
    const authHeader = req.headers.get('Authorization')
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res(
        ctx.status(401),
        ctx.json({
          detail: 'Authentication required',
          status_code: 401
        })
      )
    }
    
    return res(
      ctx.status(200),
      ctx.json(mockApiResponses.uploadSuccess)
    )
  })
]

/**
 * Default handlers combining all scenarios
 */
export const handlers = [
  ...uploadHandlers,
  ...progressiveUploadHandlers,
  ...batchUploadHandlers,
  ...authHandlers
]

/**
 * Helper functions for dynamic handler management
 */
export const createCustomHandler = (
  endpoint: string,
  response: any,
  status: number = 200,
  delay: number = 0
) => {
  return rest.post(endpoint, async (req, res, ctx) => {
    if (delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay))
    }
    return res(ctx.status(status), ctx.json(response))
  })
}

export const createErrorHandler = (endpoint: string, error: string, status: number = 500) => {
  return rest.post(endpoint, (req, res, ctx) => {
    return res(
      ctx.status(status),
      ctx.json({ detail: error, status_code: status })
    )
  })
}

export const createNetworkErrorHandler = (endpoint: string) => {
  return rest.post(endpoint, (req, res, ctx) => {
    return res.networkError('Network request failed')
  })
}

/**
 * Test scenarios for different upload conditions
 */
export const testScenarios = {
  // Happy path: everything works
  success: [...uploadHandlers.slice(0, 1)],
  
  // Error scenarios
  fileValidationError: [uploadHandlers[1]], // Invalid file type
  fileSizeError: [uploadHandlers[2]], // File too large  
  serverError: [uploadHandlers[3]], // Server processing error
  networkError: [errorHandlers[0]], // Network failure
  rateLimitError: [uploadHandlers[5]], // Rate limiting
  
  // Progressive upload testing
  progressive: [...progressiveUploadHandlers],
  
  // Batch upload testing
  batch: [...batchUploadHandlers],
  
  // Authentication testing
  requiresAuth: [...authHandlers]
}