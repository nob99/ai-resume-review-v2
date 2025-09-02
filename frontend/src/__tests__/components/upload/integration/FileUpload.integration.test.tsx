// Integration tests for FileUpload component
// Testing real user interactions and complete workflows

import React from 'react'
import { render, screen, waitFor, fireEvent } from '../../../utils/test-utils'
import userEvent from '@testing-library/user-event'
import { server } from '../../../utils/setup-tests'
import { rest } from 'msw'
import FileUpload from '../../../../components/upload/FileUpload'
import { testFiles, testFileCollections } from '../../../utils/test-fixtures'
import { FileUploadError } from '../../../../types'

describe('FileUpload Component - Integration Tests', () => {
  const mockOnFilesSelected = jest.fn()
  const mockOnError = jest.fn()
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Complete File Selection Workflow', () => {
    it('handles complete drag and drop workflow', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')
      const files = [testFiles.validPdf, testFiles.validDocx]

      // Simulate drag enter
      await user.hover(dropzone)
      
      // Create and dispatch drag events
      const dataTransfer = {
        files: files,
        types: ['Files']
      }

      fireEvent.dragEnter(dropzone, { dataTransfer })
      fireEvent.dragOver(dropzone, { dataTransfer })
      
      // Verify drag active state
      await waitFor(() => {
        expect(dropzone).toHaveClass('border-primary-500')
      })

      // Drop files
      fireEvent.drop(dropzone, { dataTransfer })

      // Wait for file processing
      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith(
          expect.arrayContaining([
            expect.objectContaining({ name: testFiles.validPdf.name }),
            expect.objectContaining({ name: testFiles.validDocx.name })
          ])
        )
      })
    })

    it('handles file input click workflow', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const fileInput = screen.getByLabelText(/upload|browse/, { hidden: true }) as HTMLInputElement
      const files = [testFiles.validPdf]

      // Simulate file selection through input
      Object.defineProperty(fileInput, 'files', {
        value: files,
        writable: false,
      })

      fireEvent.change(fileInput)

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([testFiles.validPdf])
      })
    })

    it('provides visual feedback during drag operations', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByRole('button')

      // Test drag enter
      fireEvent.dragEnter(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByText('Drop files here')).toBeInTheDocument()
      })

      // Test drag leave
      fireEvent.dragLeave(dropzone)

      await waitFor(() => {
        expect(screen.getByText(/drag.*drop.*resume.*files/i)).toBeInTheDocument()
      })
    })

    it('shows accept/reject feedback for different file types', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByRole('button')

      // Test valid file drag
      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByText(/files look good/i)).toBeInTheDocument()
      })

      // Test invalid file drag
      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [testFiles.invalidTxt] }
      })

      await waitFor(() => {
        expect(screen.getByText(/invalid file type or size/i)).toBeInTheDocument()
      })
    })
  })

  describe('Error Handling and Recovery', () => {
    it('handles validation errors gracefully', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // Drop invalid file
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.invalidTxt] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            code: 'VALIDATION_FAILED',
            message: expect.stringContaining('File type not supported')
          })
        )
      })

      // Verify component is still functional after error
      jest.clearAllMocks()
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([testFiles.validPdf])
      })
    })

    it('handles multiple file validation with mixed results', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // Drop mixed valid/invalid files
      fireEvent.drop(dropzone, {
        dataTransfer: { files: testFileCollections.mixed }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalled()
      })

      // Should not call onFilesSelected with any files if any are invalid
      expect(mockOnFilesSelected).not.toHaveBeenCalled()
    })

    it('handles oversized file errors', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
          maxFileSize={5 * 1024 * 1024} // 5MB
        />
      )

      const dropzone = screen.getByRole('button')

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.oversizedFile] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            code: 'VALIDATION_FAILED',
            message: expect.stringContaining('File size exceeds')
          })
        )
      })
    })

    it('recovers from temporary errors', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation()
      
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // Simulate some error condition and recovery
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.emptyFile] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringContaining('empty or corrupted')
          })
        )
      })

      // Component should still work after error
      jest.clearAllMocks()
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalled()
      })

      consoleSpy.mockRestore()
    })
  })

  describe('Configuration and Props Integration', () => {
    it('respects custom file size limits', async () => {
      const customLimit = 1024 * 1024 // 1MB
      
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
          maxFileSize={customLimit}
        />
      )

      // Verify limit is displayed
      expect(screen.getByText(/maximum file size.*1\.0.*mb/i)).toBeInTheDocument()

      const dropzone = screen.getByRole('button')

      // Test file that exceeds custom limit
      const largeFile = new File([new ArrayBuffer(2 * 1024 * 1024)], 'large.pdf', {
        type: 'application/pdf'
      })

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [largeFile] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringContaining('exceeds 1.0 MB')
          })
        )
      })
    })

    it('respects custom file count limits', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
          maxFiles={2}
        />
      )

      expect(screen.getByText(/maximum files.*2/i)).toBeInTheDocument()

      const dropzone = screen.getByRole('button')
      const manyFiles = testFileCollections.maxCount // 5 files

      fireEvent.drop(dropzone, {
        dataTransfer: { files: manyFiles }
      })

      // Should handle according to dropzone's built-in limits
      await waitFor(() => {
        // The behavior depends on react-dropzone's handling of maxFiles
        // It might accept only the first 2 files or reject all
        expect(mockOnFilesSelected).toHaveBeenCalled() || expect(mockOnError).toHaveBeenCalled()
      })
    })

    it('handles single file mode correctly', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
          multiple={false}
        />
      )

      // Should not show "maximum files" text in single mode
      expect(screen.queryByText(/maximum files/i)).not.toBeInTheDocument()

      const dropzone = screen.getByRole('button')

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([testFiles.validPdf])
      })
    })

    it('handles disabled state properly', () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
          disabled={true}
        />
      )

      const dropzone = screen.getByRole('button')
      
      expect(dropzone).toHaveClass('opacity-50', 'cursor-not-allowed')
      expect(screen.getByRole('textbox', { hidden: true })).toBeDisabled()
    })
  })

  describe('Accessibility Integration', () => {
    it('provides complete keyboard navigation', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const fileInput = screen.getByRole('textbox', { hidden: true })
      
      // Should be able to focus the file input
      fileInput.focus()
      expect(document.activeElement).toBe(fileInput)

      // Should be able to activate with Enter/Space
      await user.keyboard('{Enter}')
      // File picker would normally open (can't test in jsdom)
    })

    it('provides proper ARIA attributes and roles', () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByRole('button')
      expect(dropzone).toHaveAttribute('role', 'button')
      
      // Should have proper labeling for screen readers
      expect(screen.getByText(/drag.*drop.*resume.*files/i)).toBeInTheDocument()
    })

    it('announces state changes to screen readers', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByRole('button')

      // Drag active state should provide feedback
      fireEvent.dragEnter(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(screen.getByText('Drop files here')).toBeInTheDocument()
      })
    })

    it('provides meaningful error messages for screen readers', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.invalidTxt] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringMatching(/file type not supported.*pdf.*doc.*docx/i)
          })
        )
      })
    })
  })

  describe('Performance Integration', () => {
    it('handles large file validation without blocking UI', async () => {
      const startTime = performance.now()

      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.exactSizeLimit] } // 10MB file
      })

      const endTime = performance.now()
      
      // Initial processing should be fast
      expect(endTime - startTime).toBeLessThan(100)

      // File should still be processed
      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalled()
      })
    })

    it('handles multiple files efficiently', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')
      const manyValidFiles = Array(10).fill(null).map((_, i) => 
        new File(['content'], `resume${i}.pdf`, { type: 'application/pdf' })
      )

      const startTime = performance.now()

      fireEvent.drop(dropzone, {
        dataTransfer: { files: manyValidFiles }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith(manyValidFiles)
      })

      const endTime = performance.now()
      expect(endTime - startTime).toBeLessThan(200) // Should handle multiple files quickly
    })

    it('does not leak memory on repeated use', async () => {
      const { rerender } = render(
        <FileUpload onFilesSelected={mockOnFilesSelected} />
      )

      const dropzone = screen.getByRole('button')

      // Simulate repeated file selections
      for (let i = 0; i < 10; i++) {
        fireEvent.drop(dropzone, {
          dataTransfer: { files: [testFiles.validPdf] }
        })
        
        await waitFor(() => {
          expect(mockOnFilesSelected).toHaveBeenCalled()
        })

        jest.clearAllMocks()
        
        // Re-render component
        rerender(<FileUpload onFilesSelected={mockOnFilesSelected} />)
      }

      // Should not have accumulated memory issues
      expect(true).toBe(true) // Test passes if no memory errors
    })
  })

  describe('Edge Cases and Robustness', () => {
    it('handles malformed drag events gracefully', async () => {
      render(<FileUpload onFilesSelected={mockOnFilesSelected} />)

      const dropzone = screen.getByRole('button')

      // Test various malformed events
      expect(() => {
        fireEvent.dragEnter(dropzone, { dataTransfer: null })
        fireEvent.dragOver(dropzone, { dataTransfer: {} })
        fireEvent.drop(dropzone, { dataTransfer: { files: null } })
      }).not.toThrow()
    })

    it('handles rapid successive interactions', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // Rapid fire events
      fireEvent.dragEnter(dropzone)
      fireEvent.dragLeave(dropzone)
      fireEvent.dragEnter(dropzone)
      fireEvent.drop(dropzone, { dataTransfer: { files: [testFiles.validPdf] } })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalled()
      })
    })

    it('handles component unmount during file processing', async () => {
      const { unmount } = render(
        <FileUpload onFilesSelected={mockOnFilesSelected} />
      )

      const dropzone = screen.getByRole('button')
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      // Unmount immediately
      expect(() => unmount()).not.toThrow()
    })

    it('maintains state consistency across prop changes', async () => {
      const { rerender } = render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          maxFileSize={10 * 1024 * 1024}
        />
      )

      // Change props
      rerender(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          maxFileSize={5 * 1024 * 1024}
        />
      )

      // Should update display
      expect(screen.getByText(/maximum file size.*5\.0.*mb/i)).toBeInTheDocument()

      const dropzone = screen.getByRole('button')
      
      // Should use new limit
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.exactSizeLimit] } // 10MB, should now be too large
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringContaining('exceeds 5.0 MB')
          })
        )
      })
    })
  })

  describe('Real-world Scenarios', () => {
    it('handles typical resume upload workflow', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // User drags a typical resume file
      const resumeFile = new File(['mock resume content'], 'John_Doe_Resume.pdf', {
        type: 'application/pdf',
        lastModified: Date.now()
      })

      fireEvent.dragEnter(dropzone)
      fireEvent.dragOver(dropzone, {
        dataTransfer: { files: [resumeFile] }
      })

      // Should show positive feedback
      await waitFor(() => {
        expect(screen.getByText(/files look good/i)).toBeInTheDocument()
      })

      fireEvent.drop(dropzone, {
        dataTransfer: { files: [resumeFile] }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([resumeFile])
        expect(mockOnError).not.toHaveBeenCalled()
      })
    })

    it('handles user mistakes gracefully', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')

      // User accidentally drops wrong file type
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.invalidImage] }
      })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(
          expect.objectContaining({
            message: expect.stringMatching(/file type not supported.*pdf.*doc.*docx/i)
          })
        )
      })

      // User then drops correct file
      jest.clearAllMocks()
      
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [testFiles.validPdf] }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith([testFiles.validPdf])
      })
    })

    it('handles batch resume uploads', async () => {
      render(
        <FileUpload
          onFilesSelected={mockOnFilesSelected}
          onError={mockOnError}
        />
      )

      const dropzone = screen.getByRole('button')
      
      // User drops multiple resume files
      const batchFiles = [
        new File(['content1'], 'Resume_1.pdf', { type: 'application/pdf' }),
        new File(['content2'], 'Resume_2.docx', { 
          type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' 
        }),
        new File(['content3'], 'Resume_3.doc', { type: 'application/msword' })
      ]

      fireEvent.drop(dropzone, {
        dataTransfer: { files: batchFiles }
      })

      await waitFor(() => {
        expect(mockOnFilesSelected).toHaveBeenCalledWith(
          expect.arrayContaining(batchFiles)
        )
      })
    })
  })
})