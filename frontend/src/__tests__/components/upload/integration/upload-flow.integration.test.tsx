// Integration tests for complete upload flow
// Testing FileUpload + FilePreview + API integration

import React, { useState } from 'react'
import { render, screen, waitFor } from '../../../utils/test-utils'
import userEvent from '@testing-library/user-event'
import { server } from '../../../utils/setup-tests'
import { rest } from 'msw'
import { FileUpload, FilePreview } from '../../../../components/upload'
import { testFiles, mockApiResponses } from '../../../utils/test-fixtures'
import { UploadedFile } from '../../../../types'

// Test component that combines FileUpload and FilePreview
const UploadFlowTestComponent: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<UploadedFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)

  const handleFilesSelected = (files: File[]) => {
    const newFiles: UploadedFile[] = files.map(file => ({
      file,
      id: `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      status: 'pending',
      progress: 0
    }))

    setSelectedFiles(prev => [...prev, ...newFiles])
  }

  const handleRemoveFile = (fileId: string) => {
    setSelectedFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const handleRetryFile = (fileId: string) => {
    setSelectedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'pending', progress: 0, error: undefined }
          : f
      )
    )
  }

  const handleProcessFiles = async () => {
    setIsProcessing(true)

    // Simulate processing each file
    for (const file of selectedFiles) {
      if (file.status !== 'pending') continue

      // Update status through processing phases
      setSelectedFiles(prev => 
        prev.map(f => f.id === file.id ? { ...f, status: 'uploading', progress: 0 } : f)
      )

      // Simulate upload progress
      for (let progress = 0; progress <= 100; progress += 25) {
        await new Promise(resolve => setTimeout(resolve, 50))
        setSelectedFiles(prev => 
          prev.map(f => f.id === file.id ? { ...f, progress } : f)
        )
      }

      // Validation phase
      setSelectedFiles(prev => 
        prev.map(f => f.id === file.id ? { ...f, status: 'validating' } : f)
      )
      await new Promise(resolve => setTimeout(resolve, 200))

      // Text extraction phase
      setSelectedFiles(prev => 
        prev.map(f => f.id === file.id ? { ...f, status: 'extracting' } : f)
      )
      await new Promise(resolve => setTimeout(resolve, 300))

      // Complete or error based on file type
      const isValid = file.file.type.startsWith('application/')
      
      setSelectedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { 
                ...f, 
                status: isValid ? 'completed' : 'error',
                progress: 100,
                error: isValid ? undefined : 'File processing failed',
                extractedText: isValid ? 'Mock extracted resume text content...' : undefined
              }
            : f
        )
      )
    }

    setIsProcessing(false)
  }

  return (
    <div className="space-y-6">
      <FileUpload
        onFilesSelected={handleFilesSelected}
        disabled={isProcessing}
        data-testid="file-upload"
      />
      
      {selectedFiles.length > 0 && (
        <FilePreview
          files={selectedFiles}
          onRemove={handleRemoveFile}
          onRetry={handleRetryFile}
          readOnly={isProcessing}
          data-testid="file-preview"
        />
      )}

      {selectedFiles.length > 0 && selectedFiles.some(f => f.status === 'pending') && (
        <button
          onClick={handleProcessFiles}
          disabled={isProcessing}
          data-testid="process-button"
        >
          {isProcessing ? 'Processing...' : 'Process Files'}
        </button>
      )}
    </div>
  )
}

describe('Upload Flow - Integration Tests', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Complete Upload Workflow', () => {
    it('handles end-to-end upload workflow successfully', async () => {
      render(<UploadFlowTestComponent />)

      // Step 1: Upload files
      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      const files = [testFiles.validPdf, testFiles.validDocx]
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files }
      })

      // Step 2: Verify files appear in preview
      await waitFor(() => {
        expect(screen.getByTestId('file-preview')).toBeInTheDocument()
        expect(screen.getByText(testFiles.validPdf.name)).toBeInTheDocument()
        expect(screen.getByText(testFiles.validDocx.name)).toBeInTheDocument()
      })

      // Verify files are in pending state
      expect(screen.getAllByText(/pending/i)).toHaveLength(2)

      // Step 3: Process files
      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Step 4: Watch progress through all phases
      // Should see uploading phase
      await waitFor(() => {
        expect(screen.getByText(/uploading/i)).toBeInTheDocument()
      })

      // Should see validating phase
      await waitFor(() => {
        expect(screen.getByText(/validating/i)).toBeInTheDocument()
      })

      // Should see extracting phase
      await waitFor(() => {
        expect(screen.getByText(/extracting/i)).toBeInTheDocument()
      })

      // Step 5: Files should complete successfully
      await waitFor(() => {
        expect(screen.getAllByText(/ready/i)).toHaveLength(2)
      }, { timeout: 3000 })

      // Should show extracted text
      expect(screen.getAllByText('Text Preview:')).toHaveLength(2)
    })

    it('handles mixed success/failure scenarios', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      // Mix of valid and invalid files
      const files = [testFiles.validPdf, testFiles.invalidTxt]
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files }
      })

      await waitFor(() => {
        expect(screen.getByTestId('file-preview')).toBeInTheDocument()
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Wait for processing to complete
      await waitFor(() => {
        expect(screen.getByText(/ready/i)).toBeInTheDocument()
        expect(screen.getByText(/failed/i)).toBeInTheDocument()
      }, { timeout: 3000 })

      // Should have one success and one failure
      expect(screen.getByText('Mock extracted resume text content...')).toBeInTheDocument()
      expect(screen.getByText('File processing failed')).toBeInTheDocument()
    })

    it('allows retry of failed files', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.invalidTxt] }
      })

      await waitFor(() => {
        expect(screen.getByTestId('file-preview')).toBeInTheDocument()
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Wait for failure
      await waitFor(() => {
        expect(screen.getByText(/failed/i)).toBeInTheDocument()
      }, { timeout: 3000 })

      // Click retry button
      const retryButton = screen.getByText('Retry')
      await user.click(retryButton)

      // File should be back to pending state
      await waitFor(() => {
        expect(screen.getByText(/pending/i)).toBeInTheDocument()
      })

      // Process button should be available again
      expect(screen.getByTestId('process-button')).toBeInTheDocument()
    })

    it('allows file removal during and after processing', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      const files = [testFiles.validPdf, testFiles.validDocx]
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files }
      })

      await waitFor(() => {
        expect(screen.getAllByLabelText(/remove/i)).toHaveLength(2)
      })

      // Remove one file before processing
      const removeButtons = screen.getAllByLabelText(/remove/i)
      await user.click(removeButtons[0])

      await waitFor(() => {
        expect(screen.getAllByLabelText(/remove/i)).toHaveLength(1)
      })

      // Process remaining file
      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      await waitFor(() => {
        expect(screen.getByText(/ready/i)).toBeInTheDocument()
      }, { timeout: 3000 })

      // Should be able to remove completed file
      const remainingRemoveButton = screen.getByLabelText(/remove/i)
      await user.click(remainingRemoveButton)

      await waitFor(() => {
        expect(screen.queryByTestId('file-preview')).not.toBeInTheDocument()
      })
    })
  })

  describe('User Experience Flows', () => {
    it('provides clear progress feedback throughout the process', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByText('1 file selected')).toBeInTheDocument()
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Should show processing state
      await waitFor(() => {
        expect(screen.getByText('Processing...')).toBeInTheDocument()
      })

      // Progress indicators should be visible
      await waitFor(() => {
        const progressBar = document.querySelector('.bg-primary-500')
        expect(progressBar).toBeInTheDocument()
      })

      // Should show completion
      await waitFor(() => {
        expect(screen.getByText('1 ready')).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('handles multiple file batches correctly', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      // First batch
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByText('1 file selected')).toBeInTheDocument()
      })

      // Second batch
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validDocx] }
      })

      await waitFor(() => {
        expect(screen.getByText('2 files selected')).toBeInTheDocument()
      })

      // Process all files
      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      await waitFor(() => {
        expect(screen.getByText('2 ready')).toBeInTheDocument()
      }, { timeout: 5000 })
    })

    it('maintains state consistency during rapid interactions', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      // Rapid file additions and removals
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByLabelText(/remove/i)).toBeInTheDocument()
      })

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validDocx] }
      })

      await waitFor(() => {
        expect(screen.getAllByLabelText(/remove/i)).toHaveLength(2)
      })

      // Remove one file quickly
      const removeButton = screen.getAllByLabelText(/remove/i)[0]
      await user.click(removeButton)

      await waitFor(() => {
        expect(screen.getAllByLabelText(/remove/i)).toHaveLength(1)
      })

      // Add another file
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validDoc] }
      })

      await waitFor(() => {
        expect(screen.getAllByLabelText(/remove/i)).toHaveLength(2)
      })

      // State should be consistent
      expect(screen.getByText('2 files selected')).toBeInTheDocument()
    })
  })

  describe('Error Recovery Workflows', () => {
    it('handles processing interruption gracefully', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Start processing
      await waitFor(() => {
        expect(screen.getByText('Processing...')).toBeInTheDocument()
      })

      // Component should handle state correctly during processing
      expect(screen.getByTestId('file-upload')).toHaveClass('opacity-50')
    })

    it('allows clear all functionality', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      const files = [testFiles.validPdf, testFiles.validDocx, testFiles.validDoc]
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files }
      })

      await waitFor(() => {
        expect(screen.getByText('3 files selected')).toBeInTheDocument()
      })

      // Clear all files
      const clearAllButton = screen.getByText('Clear All')
      await user.click(clearAllButton)

      await waitFor(() => {
        expect(screen.queryByTestId('file-preview')).not.toBeInTheDocument()
      })

      // Upload component should be ready for new files
      expect(screen.getByText(/drag.*drop.*resume.*files/i)).toBeInTheDocument()
    })

    it('handles file processing with network simulation', async () => {
      // Add network delay to simulate real conditions
      server.use(
        rest.post('/api/v1/upload/resume', async (req, res, ctx) => {
          await new Promise(resolve => setTimeout(resolve, 500))
          return res(ctx.json(mockApiResponses.uploadSuccess))
        })
      )

      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Should handle longer processing times
      await waitFor(() => {
        expect(screen.getByText(/ready/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Accessibility in Complete Flow', () => {
    it('maintains accessibility throughout upload process', async () => {
      render(<UploadFlowTestComponent />)

      // Upload should be keyboard accessible
      const uploadComponent = screen.getByTestId('file-upload')
      const fileInput = uploadComponent.querySelector('input[type="file"]') as HTMLInputElement
      
      fileInput.focus()
      expect(document.activeElement).toBe(fileInput)

      // Add files via drop
      const dropzone = uploadComponent.querySelector('[role="button"]')!
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      // Preview should have proper ARIA attributes
      await waitFor(() => {
        expect(screen.getByLabelText(/remove/i)).toBeInTheDocument()
      })

      // Process button should be focusable
      const processButton = screen.getByTestId('process-button')
      processButton.focus()
      expect(document.activeElement).toBe(processButton)

      await user.keyboard('{Enter}')

      // Processing state should be announced
      await waitFor(() => {
        expect(screen.getByText('Processing...')).toBeInTheDocument()
      })

      // Completion should be accessible
      await waitFor(() => {
        expect(screen.getByText(/ready/i)).toBeInTheDocument()
      }, { timeout: 3000 })
    })

    it('provides proper screen reader announcements', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      // Should announce file selection
      await waitFor(() => {
        expect(screen.getByText('1 file selected')).toBeInTheDocument()
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      // Should announce processing stages
      await waitFor(() => {
        expect(screen.getByText(/uploading/i)).toBeInTheDocument()
      })

      await waitFor(() => {
        expect(screen.getByText(/validating/i)).toBeInTheDocument()
      })

      // Should announce completion
      await waitFor(() => {
        expect(screen.getByText('1 ready')).toBeInTheDocument()
      }, { timeout: 3000 })
    })
  })

  describe('Performance in Complete Flow', () => {
    it('handles large file uploads efficiently', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      const largeFile = new File([new ArrayBuffer(9 * 1024 * 1024)], 'large-resume.pdf', {
        type: 'application/pdf'
      })

      const startTime = performance.now()

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [largeFile] }
      })

      await waitFor(() => {
        expect(screen.getByTestId('file-preview')).toBeInTheDocument()
      })

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(200) // Should handle large files quickly
    })

    it('maintains performance with multiple simultaneous operations', async () => {
      render(<UploadFlowTestComponent />)

      const uploadComponent = screen.getByTestId('file-upload')
      const dropzone = uploadComponent.querySelector('[role="button"]')!

      // Add multiple files quickly
      const files = Array(5).fill(null).map((_, i) => 
        new File(['content'], `resume${i}.pdf`, { type: 'application/pdf' })
      )

      const startTime = performance.now()

      fireEvent.drop(dropzone, {
        dataTransfer: { files }
      })

      await waitFor(() => {
        expect(screen.getByText('5 files selected')).toBeInTheDocument()
      })

      const processButton = screen.getByTestId('process-button')
      await user.click(processButton)

      await waitFor(() => {
        expect(screen.getByText('5 ready')).toBeInTheDocument()
      }, { timeout: 5000 })

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(6000) // Should complete within reasonable time
    })
  })
})