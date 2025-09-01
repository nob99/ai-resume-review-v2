import React from 'react'
import { render, screen } from '@testing-library/react'
import { UploadProgress, UploadStatus } from '../UploadProgress'

describe('UploadProgress', () => {
  it('should display correct message for each status', () => {
    const statuses: UploadStatus[] = ['idle', 'uploading', 'validating', 'extracting', 'success', 'error']
    const expectedMessages = {
      idle: 'Ready to upload',
      uploading: 'Uploading file...',
      validating: 'Validating file...',
      extracting: 'Extracting text content...',
      success: 'Upload completed successfully!',
      error: 'Upload failed'
    }

    statuses.forEach(status => {
      const { rerender } = render(
        <UploadProgress status={status} progress={50} />
      )
      expect(screen.getByText(expectedMessages[status])).toBeInTheDocument()
      rerender(<UploadProgress status="idle" progress={0} />)
    })
  })

  it('should display custom message when provided', () => {
    const customMessage = 'Custom upload message'
    render(
      <UploadProgress 
        status="uploading" 
        progress={75} 
        message={customMessage}
      />
    )
    
    expect(screen.getByText(customMessage)).toBeInTheDocument()
    expect(screen.queryByText('Uploading file...')).not.toBeInTheDocument()
  })

  it('should display progress percentage', () => {
    render(<UploadProgress status="uploading" progress={42} />)
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('should not display percentage for idle status', () => {
    render(<UploadProgress status="idle" progress={0} />)
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
  })

  it('should render progress bar with correct width', () => {
    const { container } = render(
      <UploadProgress status="uploading" progress={75} />
    )
    
    const progressBar = container.querySelector('[role="progressbar"]')
    expect(progressBar).toHaveStyle({ width: '75%' })
    expect(progressBar).toHaveAttribute('aria-valuenow', '75')
    expect(progressBar).toHaveAttribute('aria-valuemin', '0')
    expect(progressBar).toHaveAttribute('aria-valuemax', '100')
  })

  it('should apply correct color classes for each status', () => {
    const statusColors = {
      idle: 'bg-gray-200',
      uploading: 'bg-blue-500',
      validating: 'bg-yellow-500',
      extracting: 'bg-indigo-500',
      success: 'bg-green-500',
      error: 'bg-red-500'
    }

    Object.entries(statusColors).forEach(([status, colorClass]) => {
      const { container } = render(
        <UploadProgress status={status as UploadStatus} progress={50} />
      )
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveClass(colorClass)
    })
  })

  it('should show error message when status is error', () => {
    const errorMessage = 'File validation failed'
    render(
      <UploadProgress 
        status="error" 
        progress={0} 
        message={errorMessage}
      />
    )
    
    const errorElements = screen.getAllByText(errorMessage)
    const errorParagraph = errorElements.find(el => el.tagName === 'P')
    expect(errorParagraph).toHaveClass('text-red-600')
  })

  it('should show success message with icon when status is success', () => {
    render(<UploadProgress status="success" progress={100} />)
    
    expect(screen.getByText('File ready for analysis')).toBeInTheDocument()
    expect(screen.getByText('File ready for analysis')).toHaveClass('text-green-600')
    
    // Check for checkmark icon
    const successIcon = screen.getByText('File ready for analysis').previousElementSibling
    expect(successIcon).toBeInTheDocument()
  })

  it('should animate progress bar for active statuses', () => {
    const activeStatuses: UploadStatus[] = ['uploading', 'validating', 'extracting']
    
    activeStatuses.forEach(status => {
      const { container } = render(
        <UploadProgress status={status} progress={50} />
      )
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).toHaveClass('animate-pulse')
    })
  })

  it('should not animate progress bar for inactive statuses', () => {
    const inactiveStatuses: UploadStatus[] = ['idle', 'success', 'error']
    
    inactiveStatuses.forEach(status => {
      const { container } = render(
        <UploadProgress status={status} progress={50} />
      )
      const progressBar = container.querySelector('[role="progressbar"]')
      expect(progressBar).not.toHaveClass('animate-pulse')
    })
  })
})