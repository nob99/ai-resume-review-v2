import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { FilePreview, FileWithPreview } from '../FilePreview'

describe('FilePreview', () => {
  const mockFile: FileWithPreview = Object.assign(
    new File(['content'], 'test-document.pdf', { type: 'application/pdf' }),
    { id: 'test-file-1' }
  )

  const mockOnRemove = jest.fn()

  beforeEach(() => {
    mockOnRemove.mockClear()
  })

  it('should render file information correctly', () => {
    render(<FilePreview file={mockFile} onRemove={mockOnRemove} />)
    
    expect(screen.getByText('test-document.pdf')).toBeInTheDocument()
    expect(screen.getByText('7 Bytes')).toBeInTheDocument() // "content" is 7 bytes
    expect(screen.getByText('📄')).toBeInTheDocument() // PDF icon
  })

  it('should display error message when provided', () => {
    const errorMessage = 'File size exceeds limit'
    render(
      <FilePreview 
        file={mockFile} 
        onRemove={mockOnRemove} 
        error={errorMessage}
      />
    )
    
    expect(screen.getByText(errorMessage)).toBeInTheDocument()
  })

  it('should apply error styling when error is present', () => {
    const { container } = render(
      <FilePreview 
        file={mockFile} 
        onRemove={mockOnRemove} 
        error="Test error"
      />
    )
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('border-red-300', 'bg-red-50')
  })

  it('should apply normal styling when no error', () => {
    const { container } = render(
      <FilePreview file={mockFile} onRemove={mockOnRemove} />
    )
    
    const wrapper = container.firstChild
    expect(wrapper).toHaveClass('border-gray-200', 'bg-gray-50')
  })

  it('should call onRemove when remove button is clicked', () => {
    render(<FilePreview file={mockFile} onRemove={mockOnRemove} />)
    
    const removeButton = screen.getByLabelText('Remove test-document.pdf')
    fireEvent.click(removeButton)
    
    expect(mockOnRemove).toHaveBeenCalledWith('test-file-1')
    expect(mockOnRemove).toHaveBeenCalledTimes(1)
  })

  it('should display correct icon for different file types', () => {
    const docFile: FileWithPreview = Object.assign(
      new File([''], 'document.doc', { type: 'application/msword' }),
      { id: 'doc-file' }
    )
    
    const { rerender } = render(
      <FilePreview file={docFile} onRemove={mockOnRemove} />
    )
    expect(screen.getByText('📝')).toBeInTheDocument()
    
    const unknownFile: FileWithPreview = Object.assign(
      new File([''], 'unknown.xyz', { type: 'application/unknown' }),
      { id: 'unknown-file' }
    )
    
    rerender(<FilePreview file={unknownFile} onRemove={mockOnRemove} />)
    expect(screen.getByText('📎')).toBeInTheDocument()
  })

  it('should truncate long file names', () => {
    const longNameFile: FileWithPreview = Object.assign(
      new File([''], 'this-is-a-very-long-file-name-that-should-be-truncated-in-the-ui.pdf', { 
        type: 'application/pdf' 
      }),
      { id: 'long-name-file' }
    )
    
    render(<FilePreview file={longNameFile} onRemove={mockOnRemove} />)
    
    const fileName = screen.getByText(/this-is-a-very-long-file-name/i)
    expect(fileName).toHaveClass('truncate')
  })

  it('should format file sizes correctly', () => {
    const largeFile: FileWithPreview = Object.assign(
      new File([new Array(1024 * 1024 + 1).join('a')], 'large.pdf', { 
        type: 'application/pdf' 
      }),
      { id: 'large-file' }
    )
    
    render(<FilePreview file={largeFile} onRemove={mockOnRemove} />)
    expect(screen.getByText('1 MB')).toBeInTheDocument()
  })
})