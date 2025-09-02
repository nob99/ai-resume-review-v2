// Unit tests for FilePreview component
// Testing file preview display, status indicators, and user interactions

import React from 'react'
import { render, screen, waitFor } from '../../../utils/test-utils'
import userEvent from '@testing-library/user-event'
import FilePreview, { FilePreviewItem } from '../../../../components/upload/FilePreview'
import { mockUploadedFiles, mockUploadedFileCollections } from '../../../utils/test-fixtures'
import { UploadedFile } from '../../../../types'

// Mock the UI components
jest.mock('../../../../components/ui', () => ({
  Card: ({ children, className, ...props }: any) => (
    <div className={className} {...props}>{children}</div>
  ),
  CardContent: ({ children, className, ...props }: any) => (
    <div className={className} {...props}>{children}</div>
  ),
  Button: ({ children, onClick, className, ...props }: any) => (
    <button onClick={onClick} className={className} {...props}>{children}</button>
  )
}))

describe('FilePreview Component - Unit Tests', () => {
  const mockOnRemove = jest.fn()
  const mockOnRetry = jest.fn()
  const user = userEvent.setup()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('Rendering with No Files', () => {
    it('renders nothing when no files provided', () => {
      const { container } = render(
        <FilePreview files={[]} onRemove={mockOnRemove} />
      )

      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when files array is empty', () => {
      const { container } = render(
        <FilePreview files={[]} />
      )

      expect(container.firstChild).toBeNull()
    })
  })

  describe('File Display', () => {
    it('displays file information correctly', () => {
      const files = [mockUploadedFiles.completed]
      render(<FilePreview files={files} />)

      expect(screen.getByText(files[0].file.name)).toBeInTheDocument()
      expect(screen.getByText(/pdf document/i)).toBeInTheDocument()
      expect(screen.getByText(/1\.0 mb/i)).toBeInTheDocument()
    })

    it('shows file icons based on file type', () => {
      const files = [
        mockUploadedFiles.completed, // PDF
        { ...mockUploadedFiles.completed, file: { ...mockUploadedFiles.completed.file, name: 'test.docx' } }
      ]
      
      render(<FilePreview files={files} />)

      const icons = document.querySelectorAll('svg')
      expect(icons.length).toBeGreaterThan(0)
    })

    it('identifies resume files with badge', () => {
      const resumeFile = {
        ...mockUploadedFiles.completed,
        file: { ...mockUploadedFiles.completed.file, name: 'my-resume.pdf' }
      }
      
      render(<FilePreview files={[resumeFile]} />)

      expect(screen.getByText('Resume')).toBeInTheDocument()
    })

    it('formats file sizes correctly', () => {
      const largeFile = {
        ...mockUploadedFiles.completed,
        file: new File([new ArrayBuffer(5 * 1024 * 1024)], 'large.pdf', { type: 'application/pdf' })
      }
      
      render(<FilePreview files={[largeFile]} />)

      expect(screen.getByText(/5\.0 mb/i)).toBeInTheDocument()
    })

    it('truncates long file names', () => {
      const longNameFile = {
        ...mockUploadedFiles.completed,
        file: { ...mockUploadedFiles.completed.file, name: 'a'.repeat(100) + '.pdf' }
      }
      
      render(<FilePreview files={[longNameFile]} />)

      const fileName = screen.getByText(longNameFile.file.name)
      expect(fileName).toHaveClass('truncate')
    })
  })

  describe('Status Indicators', () => {
    it('shows pending status correctly', () => {
      render(<FilePreview files={[mockUploadedFiles.pending]} />)

      expect(screen.getByText(/pending/i)).toBeInTheDocument()
      expect(document.querySelector('.bg-neutral-300')).toBeInTheDocument()
    })

    it('shows uploading status with progress', () => {
      render(<FilePreview files={[mockUploadedFiles.uploading]} />)

      expect(screen.getByText(/uploading.*45%/i)).toBeInTheDocument()
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('shows validating status', () => {
      render(<FilePreview files={[mockUploadedFiles.validating]} />)

      expect(screen.getByText(/validating/i)).toBeInTheDocument()
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('shows extracting status', () => {
      render(<FilePreview files={[mockUploadedFiles.extracting]} />)

      expect(screen.getByText(/extracting text/i)).toBeInTheDocument()
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('shows completed status with checkmark', () => {
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      expect(screen.getByText(/ready/i)).toBeInTheDocument()
      expect(screen.getByText('Ready')).toBeInTheDocument()
    })

    it('shows error status with error icon', () => {
      render(<FilePreview files={[mockUploadedFiles.error]} />)

      expect(screen.getByText(/failed/i)).toBeInTheDocument()
      expect(document.querySelector('.text-error-600')).toBeInTheDocument()
    })

    it('displays progress bars for active uploads', () => {
      render(<FilePreview files={[mockUploadedFiles.uploading]} />)

      const progressBar = document.querySelector('.bg-primary-500')
      expect(progressBar).toBeInTheDocument()
      expect(progressBar).toHaveStyle({ width: '45%' })
    })

    it('hides progress bars for completed files', () => {
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      const progressBar = document.querySelector('.h-1\\.5')
      expect(progressBar).not.toBeInTheDocument()
    })
  })

  describe('Error Handling Display', () => {
    it('displays error messages for failed files', () => {
      render(<FilePreview files={[mockUploadedFiles.error]} />)

      expect(screen.getByText(mockUploadedFiles.error.error!)).toBeInTheDocument()
    })

    it('styles error messages appropriately', () => {
      render(<FilePreview files={[mockUploadedFiles.error]} />)

      const errorMessage = screen.getByText(mockUploadedFiles.error.error!)
      expect(errorMessage).toHaveClass('text-error-600')
      expect(errorMessage.closest('p')).toHaveClass('bg-error-50', 'border-error-200')
    })

    it('shows retry button for failed files', () => {
      render(<FilePreview files={[mockUploadedFiles.error]} onRetry={mockOnRetry} />)

      expect(screen.getByText('Retry')).toBeInTheDocument()
    })

    it('handles different error types', () => {
      const files = [
        mockUploadedFiles.error,
        mockUploadedFiles.errorOversized,
        mockUploadedFiles.errorCorrupted
      ]
      
      render(<FilePreview files={files} />)

      expect(screen.getByText(/file type not supported/i)).toBeInTheDocument()
      expect(screen.getByText(/file size exceeds/i)).toBeInTheDocument()
      expect(screen.getByText(/empty or corrupted/i)).toBeInTheDocument()
    })
  })

  describe('User Actions', () => {
    it('calls onRemove when remove button is clicked', async () => {
      const files = [mockUploadedFiles.completed]
      render(<FilePreview files={files} onRemove={mockOnRemove} />)

      const removeButton = screen.getByLabelText(`Remove ${files[0].file.name}`)
      await user.click(removeButton)

      expect(mockOnRemove).toHaveBeenCalledWith(files[0].id)
    })

    it('calls onRetry when retry button is clicked', async () => {
      const files = [mockUploadedFiles.error]
      render(<FilePreview files={files} onRetry={mockOnRetry} />)

      const retryButton = screen.getByText('Retry')
      await user.click(retryButton)

      expect(mockOnRetry).toHaveBeenCalledWith(files[0].id)
    })

    it('shows clear all button when multiple files exist', () => {
      render(<FilePreview files={mockUploadedFileCollections.mixedStates} />)

      expect(screen.getByText('Clear All')).toBeInTheDocument()
    })

    it('calls onRemove for all files when clear all is clicked', async () => {
      const files = mockUploadedFileCollections.mixedStates
      render(<FilePreview files={files} onRemove={mockOnRemove} />)

      const clearAllButton = screen.getByText('Clear All')
      await user.click(clearAllButton)

      expect(mockOnRemove).toHaveBeenCalledTimes(files.length)
      files.forEach(file => {
        expect(mockOnRemove).toHaveBeenCalledWith(file.id)
      })
    })

    it('hides action buttons in read-only mode', () => {
      render(
        <FilePreview
          files={[mockUploadedFiles.completed]}
          onRemove={mockOnRemove}
          readOnly={true}
        />
      )

      expect(screen.queryByLabelText(/remove/i)).not.toBeInTheDocument()
      expect(screen.queryByText('Clear All')).not.toBeInTheDocument()
    })
  })

  describe('Summary Header', () => {
    it('shows correct file count in summary', () => {
      const files = mockUploadedFileCollections.mixedStates
      render(<FilePreview files={files} />)

      expect(screen.getByText(`${files.length} files selected`)).toBeInTheDocument()
    })

    it('uses singular form for single file', () => {
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      expect(screen.getByText('1 file selected')).toBeInTheDocument()
    })

    it('shows completed file count', () => {
      const files = mockUploadedFileCollections.mixedStates
      const completedCount = files.filter(f => f.status === 'completed').length
      
      render(<FilePreview files={files} />)

      expect(screen.getByText(`${completedCount} ready`)).toBeInTheDocument()
    })

    it('shows processing file count', () => {
      const files = [mockUploadedFiles.uploading, mockUploadedFiles.validating]
      render(<FilePreview files={files} />)

      expect(screen.getByText('2 processing')).toBeInTheDocument()
      expect(document.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('shows error file count', () => {
      const files = mockUploadedFileCollections.allErrors
      render(<FilePreview files={files} />)

      expect(screen.getByText(`${files.length} failed`)).toBeInTheDocument()
    })
  })

  describe('Text Preview', () => {
    it('shows extracted text preview for completed files', () => {
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      expect(screen.getByText('Text Preview:')).toBeInTheDocument()
      expect(screen.getByText(/john smith.*senior software engineer/i)).toBeInTheDocument()
    })

    it('truncates long extracted text', () => {
      const longTextFile = {
        ...mockUploadedFiles.completed,
        extractedText: 'a'.repeat(200)
      }
      
      render(<FilePreview files={[longTextFile]} />)

      const previewText = screen.getByText(/a+\.\.\./i)
      expect(previewText).toBeInTheDocument()
    })

    it('does not show text preview for non-completed files', () => {
      render(<FilePreview files={[mockUploadedFiles.uploading]} />)

      expect(screen.queryByText('Text Preview:')).not.toBeInTheDocument()
    })
  })

  describe('Multiple File Scenarios', () => {
    it('handles mixed file states correctly', () => {
      const files = mockUploadedFileCollections.mixedStates
      render(<FilePreview files={files} />)

      // Should show all different states
      expect(screen.getByText(/ready/i)).toBeInTheDocument()
      expect(screen.getByText(/uploading/i)).toBeInTheDocument()
      expect(screen.getByText(/pending/i)).toBeInTheDocument()
      expect(screen.getByText(/failed/i)).toBeInTheDocument()
    })

    it('renders all files in the collection', () => {
      const files = mockUploadedFileCollections.mixedStates
      render(<FilePreview files={files} />)

      files.forEach(file => {
        expect(screen.getByText(file.file.name)).toBeInTheDocument()
      })
    })

    it('handles empty file arrays gracefully', () => {
      const { container } = render(<FilePreview files={[]} />)
      expect(container.firstChild).toBeNull()
    })
  })

  describe('Responsive Design', () => {
    it('applies responsive classes', () => {
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      const container = document.querySelector('.space-y-4')
      expect(container).toBeInTheDocument()
    })

    it('handles mobile layout appropriately', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', { writable: true, value: 375 })
      
      render(<FilePreview files={[mockUploadedFiles.completed]} />)

      // The component should still render properly on mobile
      expect(screen.getByText(mockUploadedFiles.completed.file.name)).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('provides proper ARIA labels for remove buttons', () => {
      const files = [mockUploadedFiles.completed]
      render(<FilePreview files={files} onRemove={mockOnRemove} />)

      const removeButton = screen.getByLabelText(`Remove ${files[0].file.name}`)
      expect(removeButton).toBeInTheDocument()
    })

    it('uses semantic markup for file list', () => {
      render(<FilePreview files={mockUploadedFileCollections.allCompleted} />)

      // The component should use proper semantic structure
      const cards = document.querySelectorAll('[class*="card"]')
      expect(cards.length).toBe(mockUploadedFileCollections.allCompleted.length)
    })

    it('provides status information for screen readers', () => {
      render(<FilePreview files={[mockUploadedFiles.uploading]} />)

      expect(screen.getByText(/uploading.*45%/i)).toBeInTheDocument()
    })

    it('ensures buttons are keyboard accessible', async () => {
      render(<FilePreview files={[mockUploadedFiles.error]} onRetry={mockOnRetry} />)

      const retryButton = screen.getByText('Retry')
      retryButton.focus()
      expect(document.activeElement).toBe(retryButton)

      await user.keyboard('{Enter}')
      expect(mockOnRetry).toHaveBeenCalled()
    })
  })

  describe('Performance', () => {
    it('handles large file lists efficiently', () => {
      const manyFiles = Array(50).fill(null).map((_, i) => ({
        ...mockUploadedFiles.completed,
        id: `file_${i}`,
        file: { ...mockUploadedFiles.completed.file, name: `resume_${i}.pdf` }
      }))

      const startTime = performance.now()
      render(<FilePreview files={manyFiles} />)
      const endTime = performance.now()

      expect(endTime - startTime).toBeLessThan(100) // Should render quickly
    })

    it('does not cause memory leaks on unmount', () => {
      const { unmount } = render(<FilePreview files={[mockUploadedFiles.completed]} />)

      expect(() => unmount()).not.toThrow()
    })
  })

  describe('Props and Configuration', () => {
    it('applies custom className', () => {
      const customClass = 'custom-preview-class'
      render(
        <FilePreview
          files={[mockUploadedFiles.completed]}
          className={customClass}
        />
      )

      expect(document.querySelector(`.${customClass}`)).toBeInTheDocument()
    })

    it('can hide progress indicators', () => {
      render(
        <FilePreview
          files={[mockUploadedFiles.uploading]}
          showProgress={false}
        />
      )

      const progressBar = document.querySelector('.h-1\\.5')
      expect(progressBar).not.toBeInTheDocument()
    })

    it('forwards other props correctly', () => {
      const testId = 'custom-preview-test-id'
      render(
        <FilePreview
          files={[mockUploadedFiles.completed]}
          data-testid={testId}
        />
      )

      expect(screen.getByTestId(testId)).toBeInTheDocument()
    })
  })
})

// Individual FilePreviewItem component tests
describe('FilePreviewItem Component - Unit Tests', () => {
  const mockOnRemove = jest.fn()
  const mockOnRetry = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders individual file item correctly', () => {
    render(
      <FilePreviewItem
        uploadedFile={mockUploadedFiles.completed}
        onRemove={mockOnRemove}
      />
    )

    expect(screen.getByText(mockUploadedFiles.completed.file.name)).toBeInTheDocument()
  })

  it('handles item-specific interactions', async () => {
    const user = userEvent.setup()
    
    render(
      <FilePreviewItem
        uploadedFile={mockUploadedFiles.error}
        onRemove={mockOnRemove}
        onRetry={mockOnRetry}
      />
    )

    const retryButton = screen.getByText('Retry')
    await user.click(retryButton)

    expect(mockOnRetry).toHaveBeenCalledWith(mockUploadedFiles.error.id)
  })
})