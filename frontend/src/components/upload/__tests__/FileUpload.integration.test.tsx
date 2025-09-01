import React from 'react'
import { render, screen } from '@testing-library/react'
import { FileUpload } from '../FileUpload'

describe('FileUpload Integration', () => {
  it('should render the upload component', () => {
    render(<FileUpload />)
    
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
    expect(screen.getByText(/drag and drop/)).toBeInTheDocument()
    expect(screen.getByText(/PDF, DOC, DOCX up to/)).toBeInTheDocument()
    // Check the container that has both texts
    const sizeText = screen.getByText(/PDF, DOC, DOCX up to/)
    expect(sizeText.textContent).toContain('10 MB')
  })
  
  it('should accept onFilesSelected callback', () => {
    const mockCallback = jest.fn()
    render(<FileUpload onFilesSelected={mockCallback} />)
    
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
  })
  
  it('should accept onUpload callback', () => {
    const mockCallback = jest.fn()
    render(<FileUpload onUpload={mockCallback} />)
    
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
  })
  
  it('should accept multiple prop', () => {
    render(<FileUpload multiple={false} />)
    
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
  })
})