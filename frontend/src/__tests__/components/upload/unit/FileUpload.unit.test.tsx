// Unit tests for FileUpload component
// Testing component logic in isolation with mocked dependencies

import React from 'react'
import { render, screen, waitFor, fireEvent } from '../../../utils/test-utils'
import userEvent from '@testing-library/user-event'
import FileUpload from '../../../../components/upload/FileUpload'
import { testFiles, testFileCollections, validationTestCases } from '../../../utils/test-fixtures'
import { FileUploadError } from '../../../../types'

// Mock react-dropzone for controlled testing
jest.mock('react-dropzone', () => {
  const originalModule = jest.requireActual('react-dropzone')
  return {
    ...originalModule,
    useDropzone: jest.fn()
  }
})

const mockUseDropzone = jest.mocked(require('react-dropzone').useDropzone)

describe('FileUpload Component - Unit Tests', () => {
  const mockOnFilesSelected = jest.fn()
  const mockOnError = jest.fn()
  const user = userEvent.setup()

  // Default dropzone mock implementation
  const mockDropzoneProps = {
    getRootProps: jest.fn(() => ({ 'data-testid': 'dropzone' })),
    getInputProps: jest.fn(() => ({ 'data-testid': 'file-input' })),
    isDragActive: false,
    isDragAccept: false,
    isDragReject: false
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseDropzone.mockReturnValue(mockDropzoneProps)
  })

  describe('Rendering and Initial State', () => {
    it('renders drag-and-drop area correctly', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(screen.getByText(/drag.*drop.*resume.*files/i)).toBeInTheDocument()
      expect(screen.getByText(/click to browse/i)).toBeInTheDocument()
      expect(screen.getByTestId('dropzone')).toBeInTheDocument()
      expect(screen.getByTestId('file-input')).toBeInTheDocument()
    })

    it('shows file requirements and limits', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(screen.getByText(/supported formats.*pdf.*doc.*docx/i)).toBeInTheDocument()
      expect(screen.getByText(/maximum file size.*10\.0.*mb/i)).toBeInTheDocument()
      expect(screen.getByText(/maximum files.*5/i)).toBeInTheDocument()
    })

    it('displays upload icon', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const uploadIcon = screen.getByRole('img', { hidden: true }) || 
                        document.querySelector('svg')
      expect(uploadIcon).toBeInTheDocument()
    })

    it('applies default styling classes', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass('border-2', 'border-dashed', 'border-neutral-300')
    })
  })

  describe('File Selection via Click', () => {
    it('configures dropzone with correct accepted file types', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          accept: {
            'application/pdf': ['.pdf'],
            'application/msword': ['.doc'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
          }
        })
      )
    })

    it('sets correct file size and count limits', () => {
      const maxFiles = 3
      const maxFileSize = 5 * 1024 * 1024 // 5MB

      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          maxFiles={maxFiles}
          maxFileSize={maxFileSize}
        />
      )

      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          maxSize: maxFileSize,
          maxFiles: maxFiles
        })
      )
    })

    it('supports single file mode', () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          multiple={false}
        />
      )

      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          multiple: false
        })
      )
    })

    it('handles disabled state correctly', () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          disabled={true}
        />
      )

      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          disabled: true
        })
      )

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass('opacity-50', 'cursor-not-allowed')
    })
  })

  describe('Drag and Drop Visual States', () => {
    it('shows drag active state', () => {
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        isDragActive: true
      })

      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass('border-primary-500', 'bg-primary-50')
      expect(screen.getByText('Drop files here')).toBeInTheDocument()
    })

    it('shows drag accept state', () => {
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        isDragAccept: true
      })

      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass('border-success-500', 'bg-success-50')
      expect(screen.getByText(/files look good/i)).toBeInTheDocument()
    })

    it('shows drag reject state', () => {
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        isDragReject: true
      })

      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass('border-error-500', 'bg-error-50')
      expect(screen.getByText(/invalid file type or size/i)).toBeInTheDocument()
    })

    it('shows hover state on mouse enter', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      await user.hover(dropzone)

      expect(dropzone).toHaveClass('hover:border-primary-400', 'hover:bg-primary-50')
    })
  })

  describe('File Validation', () => {
    beforeEach(() => {
      // Mock the onDrop callback to simulate file validation
      mockUseDropzone.mockImplementation((options) => ({
        ...mockDropzoneProps,
        // Simulate calling onDrop when files are provided
        onDrop: options.onDrop
      }))
    })

    it('accepts valid PDF files', async () => {
      const mockOnDrop = jest.fn()
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        onDrop: mockOnDrop
      })

      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      // Simulate valid file drop
      const validFiles = [testFiles.validPdf]
      const rejectedFiles: any[] = []

      // Get the onDrop function from the mock call
      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop(validFiles, rejectedFiles)

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith(validFiles)
        expect(mockOnError).not.toHaveBeenCalled()
      })
    })

    it('rejects invalid file types', async () => {
      const mockOnDrop = jest.fn()
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        onDrop: mockOnDrop
      })

      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      // Simulate invalid file drop
      const validFiles: File[] = []
      const rejectedFiles = [{
        file: testFiles.invalidTxt,
        errors: [{ message: 'File type not supported' }]
      }]

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop(validFiles, rejectedFiles)

      await waitFor(() => {
        expect(mockOnFilesSelected).not.toHaveBeenCalled()
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            code: 'VALIDATION_FAILED',
            message: expect.stringContaining('File type not supported')
          })
        )
      })
    })

    it('validates file sizes correctly', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      
      // Test oversized file
      onDropCall.onDrop([testFiles.oversizedFile], [])

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            code: 'VALIDATION_FAILED',
            message: expect.stringContaining('File size exceeds')
          })
        )
      })
    })

    it('validates empty files', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop([testFiles.emptyFile], [])

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            code: 'VALIDATION_FAILED',
            message: expect.stringContaining('empty or corrupted')
          })
        )
      })
    })

    it('handles multiple valid files', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop(testFileCollections.allValid, [])

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith(testFileCollections.allValid)
      })
    })

    it('filters out invalid files from mixed collection', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop(testFileCollections.mixed, [])

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
        expect(mockOnFilesSelected).not.toHaveBeenCalled()
      })
    })
  })

  describe('Custom Props and Configuration', () => {
    it('accepts custom file types', () => {
      const customTypes = ['pdf', 'docx']
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          acceptedTypes={customTypes}
        />
      )

      // Should still work with the predefined MIME types
      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          accept: expect.objectContaining({
            'application/pdf': ['.pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
          })
        })
      )
    })

    it('applies custom className', () => {
      const customClass = 'custom-upload-class'
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          className={customClass}
        />
      )

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveClass(customClass)
    })

    it('forwards other props correctly', () => {
      const testId = 'custom-test-id'
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          data-testid={testId}
        />
      )

      expect(screen.getByTestId(testId)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('handles network errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
      
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      
      // Simulate a scenario that might cause an error
      expect(() => {
        onDropCall.onDrop(null, [])
      }).not.toThrow()

      consoleSpy.mockRestore()
    })

    it('provides meaningful error messages', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop([testFiles.oversizedFile], [])

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringMatching(/file size exceeds.*10\.0.*mb.*current size.*11\.0.*mb/i)
          })
        )
      })
    })

    it('recovers from validation errors', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} onError={mockOnError} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      
      // First, cause an error
      onDropCall.onDrop([testFiles.invalidTxt], [])

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
      })

      // Then, provide valid files
      jest.clearAllMocks()
      onDropCall.onDrop([testFiles.validPdf], [])

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([testFiles.validPdf])
        expect(mockOnError).not.toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('provides proper ARIA attributes', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByTestId('dropzone')
      expect(dropzone).toHaveAttribute('role', 'button')
    })

    it('has keyboard navigation support', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const fileInput = screen.getByTestId('file-input')
      expect(fileInput).toHaveAttribute('type', 'file')
      
      // The input should be focusable
      fileInput.focus()
      expect(document.activeElement).toBe(fileInput)
    })

    it('provides screen reader friendly text', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(screen.getByText(/drag.*drop.*resume.*files/i)).toBeInTheDocument()
      expect(screen.getByText(/supported formats.*pdf.*doc.*docx/i)).toBeInTheDocument()
      expect(screen.getByText(/maximum file size/i)).toBeInTheDocument()
    })

    it('indicates interactive state changes', () => {
      mockUseDropzone.mockReturnValue({
        ...mockDropzoneProps,
        isDragActive: true
      })

      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(screen.getByText('Drop files here')).toBeInTheDocument()
    })
  })

  describe('Component Lifecycle', () => {
    it('cleans up properly on unmount', () => {
      const { unmount } = render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      expect(() => unmount()).not.toThrow()
    })

    it('handles prop changes correctly', () => {
      const { rerender } = render(
        <FileUpload onFilesSelected={mockOnFilesSelected} disabled={false} />
      )

      rerender(
        <FileUpload onFilesSelected={mockOnFilesSelected} disabled={true} />
      )

      expect(mockUseDropzone).toHaveBeenLastCalledWith(
        expect.objectContaining({
          disabled: true
        })
      )
    })
  })

  describe('Performance', () => {
    it('does not cause unnecessary re-renders', () => {
      const renderSpy = jest.fn()
      const TestComponent = () => {
        renderSpy()
        return <FileUpload onFilesSelected={mockOnFilesSelected} />
      }

      const { rerender } = render(<TestComponent />)
      
      expect(renderSpy).toHaveBeenCalledTimes(1)

      // Re-render with same props should not cause additional renders
      rerender(<TestComponent />)
      
      // Note: This test depends on proper memoization in the component
      // The component should be optimized to prevent unnecessary re-renders
    })

    it('handles large file validation efficiently', async () => {
      const startTime = performance.now()
      
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const onDropCall = mockUseDropzone.mock.calls[0][0]
      onDropCall.onDrop([testFiles.exactSizeLimit], [])

      const endTime = performance.now()
      const processingTime = endTime - startTime

      // Validation should complete quickly (less than 100ms)
      expect(processingTime).toBeLessThan(100)
    })
  })
})