import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import UploadProgressDashboard from '../../../../components/upload/UploadProgressDashboard'
import { DetailedProgressInfo, UploadProgressState } from '../../../../types'

describe('UploadProgressDashboard', () => {
  const mockOnCancelUpload = jest.fn()
  const mockOnRetryUpload = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  const createProgressInfo = (overrides: Partial<DetailedProgressInfo> = {}): DetailedProgressInfo => ({
    fileId: 'file-1',
    fileName: 'resume.pdf',
    stage: 'uploading',
    percentage: 50,
    bytesUploaded: 512000,
    totalBytes: 1024000,
    timeElapsed: 2000,
    estimatedTimeRemaining: 2000,
    speed: 256000,
    retryCount: 0,
    maxRetries: 3,
    ...overrides,
  })

  const createProgressState = (files: DetailedProgressInfo[] = []): UploadProgressState => {
    const fileMap = new Map<string, DetailedProgressInfo>()
    files.forEach(file => fileMap.set(file.fileId, file))
    
    const completedFiles = files.filter(f => f.stage === 'completed').length
    const failedFiles = files.filter(f => f.stage === 'error').length
    const overallProgress = files.length > 0 
      ? files.reduce((sum, f) => sum + f.percentage, 0) / files.length 
      : 0

    return {
      files: fileMap,
      overallProgress,
      totalFiles: files.length,
      completedFiles,
      failedFiles,
      isUploading: files.some(f => ['uploading', 'validating', 'extracting'].includes(f.stage)),
      startTime: Date.now() - 5000,
      estimatedTotalTime: 10000,
    }
  }

  describe('rendering', () => {
    it('should render empty state when no files', () => {
      const progressState = createProgressState([])
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('No files uploading')).toBeInTheDocument()
    })

    it('should render overall progress summary', () => {
      const files = [
        createProgressInfo({ fileId: 'file-1', percentage: 75, stage: 'uploading' }),
        createProgressInfo({ fileId: 'file-2', percentage: 25, stage: 'validating' }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('Overall Progress')).toBeInTheDocument()
      expect(screen.getByText('0 of 2 files')).toBeInTheDocument()
      expect(screen.getByText('50% Complete')).toBeInTheDocument()
      
      // Check stats
      expect(screen.getByText('2')).toBeInTheDocument() // Total files
      expect(screen.getByText('0')).toBeInTheDocument() // Completed files
      expect(screen.getByText('2')).toBeInTheDocument() // In progress
    })

    it('should display individual file progress', () => {
      const files = [
        createProgressInfo({
          fileId: 'file-1',
          fileName: 'resume.pdf',
          stage: 'uploading',
          percentage: 65,
          bytesUploaded: 665600,
          totalBytes: 1024000,
          speed: 102400, // 100 KB/s
          estimatedTimeRemaining: 3500,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('resume.pdf')).toBeInTheDocument()
      expect(screen.getByText('1.00 MB')).toBeInTheDocument()
      expect(screen.getByText('65%')).toBeInTheDocument()
      expect(screen.getByText(/650\.00 KB \/ 1\.00 MB/)).toBeInTheDocument()
      expect(screen.getByText('Speed: 100.0 KB/s')).toBeInTheDocument()
      expect(screen.getByText('Remaining: 3s')).toBeInTheDocument()
    })
  })

  describe('file stages', () => {
    const stageTests = [
      { stage: 'queued', label: 'Queued', color: 'bg-yellow-100 text-yellow-800' },
      { stage: 'uploading', label: 'Uploading', color: 'bg-blue-100 text-blue-800' },
      { stage: 'validating', label: 'Validating', color: 'bg-indigo-100 text-indigo-800' },
      { stage: 'extracting', label: 'Processing', color: 'bg-purple-100 text-purple-800' },
      { stage: 'completed', label: 'Completed', color: 'bg-green-100 text-green-800' },
      { stage: 'error', label: 'Error', color: 'bg-red-100 text-red-800' },
      { stage: 'cancelled', label: 'Cancelled', color: 'bg-gray-100 text-gray-800' },
    ] as const

    stageTests.forEach(({ stage, label }) => {
      it(`should display correct stage: ${stage}`, () => {
        const files = [createProgressInfo({ stage: stage as any })]
        const progressState = createProgressState(files)
        
        render(
          <UploadProgressDashboard
            progressState={progressState}
            onCancelUpload={mockOnCancelUpload}
            onRetryUpload={mockOnRetryUpload}
          />
        )
        
        expect(screen.getByText(label)).toBeInTheDocument()
      })
    })
  })

  describe('progress bars', () => {
    it('should show progress bar for active uploads', () => {
      const files = [
        createProgressInfo({
          stage: 'uploading',
          percentage: 42,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      const progressBar = screen.getByRole('progressbar', { hidden: true })
      expect(progressBar).toHaveStyle('width: 42%')
    })

    it('should not show progress bar for completed files', () => {
      const files = [
        createProgressInfo({
          stage: 'completed',
          percentage: 100,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      // Should not have individual progress bar for completed files
      const progressBars = screen.queryAllByRole('progressbar', { hidden: true })
      expect(progressBars).toHaveLength(1) // Only overall progress bar
    })
  })

  describe('file actions', () => {
    it('should show cancel button for uploading files', () => {
      const files = [
        createProgressInfo({
          stage: 'uploading',
          fileId: 'file-1',
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      const cancelButton = screen.getByLabelText('Cancel upload')
      expect(cancelButton).toBeInTheDocument()
      
      fireEvent.click(cancelButton)
      expect(mockOnCancelUpload).toHaveBeenCalledWith('file-1')
    })

    it('should show retry button for failed files', () => {
      const files = [
        createProgressInfo({
          stage: 'error',
          fileId: 'file-1',
          retryCount: 1,
          maxRetries: 3,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      const retryButton = screen.getByLabelText('Retry upload')
      expect(retryButton).toBeInTheDocument()
      
      fireEvent.click(retryButton)
      expect(mockOnRetryUpload).toHaveBeenCalledWith('file-1')
    })

    it('should not show retry button when max retries reached', () => {
      const files = [
        createProgressInfo({
          stage: 'error',
          fileId: 'file-1',
          retryCount: 3,
          maxRetries: 3,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.queryByLabelText('Retry upload')).not.toBeInTheDocument()
    })
  })

  describe('time and speed formatting', () => {
    it('should format speeds correctly', () => {
      const files = [
        createProgressInfo({
          speed: 1024, // 1 KB/s
        }),
        createProgressInfo({
          fileId: 'file-2',
          speed: 1024 * 1024 * 2.5, // 2.5 MB/s
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('Speed: 1.0 KB/s')).toBeInTheDocument()
      expect(screen.getByText('Speed: 2.5 MB/s')).toBeInTheDocument()
    })

    it('should format time correctly', () => {
      const files = [
        createProgressInfo({
          estimatedTimeRemaining: 45000, // 45 seconds
          timeElapsed: 5000, // 5 seconds
        }),
        createProgressInfo({
          fileId: 'file-2',
          estimatedTimeRemaining: 125000, // 2 minutes 5 seconds
          timeElapsed: 65000, // 1 minute 5 seconds
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('Remaining: 45s')).toBeInTheDocument()
      expect(screen.getByText('Elapsed: 5s')).toBeInTheDocument()
      expect(screen.getByText('Remaining: 2m 5s')).toBeInTheDocument()
      expect(screen.getByText('Elapsed: 1m 5s')).toBeInTheDocument()
    })
  })

  describe('retry count display', () => {
    it('should show retry count for failed files', () => {
      const files = [
        createProgressInfo({
          stage: 'error',
          retryCount: 2,
          maxRetries: 3,
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText('Retry 2/3')).toBeInTheDocument()
    })
  })

  describe('accessibility', () => {
    it('should have proper ARIA labels', () => {
      const files = [
        createProgressInfo({
          stage: 'uploading',
          fileName: 'resume.pdf',
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByLabelText('Cancel upload')).toBeInTheDocument()
    })

    it('should support keyboard navigation', () => {
      const files = [
        createProgressInfo({
          stage: 'uploading',
          fileId: 'file-1',
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      const cancelButton = screen.getByLabelText('Cancel upload')
      cancelButton.focus()
      
      fireEvent.keyDown(cancelButton, { key: 'Enter' })
      expect(mockOnCancelUpload).toHaveBeenCalledWith('file-1')
    })
  })

  describe('file size formatting', () => {
    it('should format file sizes correctly', () => {
      const files = [
        createProgressInfo({
          totalBytes: 1024, // 1 KB
          bytesUploaded: 512, // 512 bytes
        }),
        createProgressInfo({
          fileId: 'file-2',
          totalBytes: 1024 * 1024 * 2.5, // 2.5 MB
          bytesUploaded: 1024 * 1024, // 1 MB
        }),
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      expect(screen.getByText(/512 Bytes \/ 1 KB/)).toBeInTheDocument()
      expect(screen.getByText(/1\.00 MB \/ 2\.50 MB/)).toBeInTheDocument()
    })
  })

  describe('overall progress calculation', () => {
    it('should calculate overall progress correctly with mixed states', () => {
      const files = [
        createProgressInfo({ percentage: 100, stage: 'completed' }), // 100%
        createProgressInfo({ fileId: 'file-2', percentage: 50, stage: 'uploading' }), // 50%
        createProgressInfo({ fileId: 'file-3', percentage: 0, stage: 'error' }), // 0%
      ]
      const progressState = createProgressState(files)
      
      render(
        <UploadProgressDashboard
          progressState={progressState}
          onCancelUpload={mockOnCancelUpload}
          onRetryUpload={mockOnRetryUpload}
        />
      )
      
      // (100 + 50 + 0) / 3 = 50%
      expect(screen.getByText('50% Complete')).toBeInTheDocument()
      expect(screen.getByText('1 of 3 files')).toBeInTheDocument()
    })
  })
})