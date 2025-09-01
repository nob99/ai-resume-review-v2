import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { FileUpload } from '../FileUpload'

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: jest.fn()
}))

import { useDropzone } from 'react-dropzone'

describe('FileUpload', () => {
  const mockOnFilesSelected = jest.fn()
  const mockOnUpload = jest.fn()
  const mockUseDropzone = useDropzone as jest.MockedFunction<typeof useDropzone>

  beforeEach(() => {
    mockOnFilesSelected.mockClear()
    mockOnUpload.mockClear()
    
    // Default mock implementation
    mockUseDropzone.mockReturnValue({
      getRootProps: () => ({ role: 'button', tabIndex: 0 }),
      getInputProps: () => ({ type: 'file', multiple: true }),
      isDragActive: false,
      acceptedFiles: [],
      fileRejections: []
    } as any)
  })

  it('should render upload area with correct text', () => {
    render(<FileUpload />)
    
    expect(screen.getByText(/Click to upload/)).toBeInTheDocument()
    expect(screen.getByText(/drag and drop/)).toBeInTheDocument()
    expect(screen.getByText(/PDF, DOC, DOCX up to/)).toBeInTheDocument()
    expect(screen.getByText('10 MB')).toBeInTheDocument()
  })

  it('should show drag active state', () => {
    mockUseDropzone.mockReturnValue({
      getRootProps: () => ({ role: 'button', tabIndex: 0 }),
      getInputProps: () => ({ type: 'file', multiple: true }),
      isDragActive: true,
      acceptedFiles: [],
      fileRejections: []
    } as any)

    render(<FileUpload />)
    
    expect(screen.getByText('Drop files here')).toBeInTheDocument()
  })

  it('should handle file selection', () => {
    const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onFilesSelected={mockOnFilesSelected} />)
    
    // Simulate file drop
    act(() => {
      onDropCallback([mockFile], [])
    })
    
    expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(mockOnFilesSelected).toHaveBeenCalledWith([mockFile])
  })

  it('should handle multiple file selection', () => {
    const files = [
      new File(['content1'], 'test1.pdf', { type: 'application/pdf' }),
      new File(['content2'], 'test2.doc', { type: 'application/msword' })
    ]
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onFilesSelected={mockOnFilesSelected} multiple={true} />)
    
    act(() => {
      onDropCallback(files, [])
    })
    
    expect(screen.getByText('Selected Files (2)')).toBeInTheDocument()
    expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    expect(screen.getByText('test2.doc')).toBeInTheDocument()
  })

  it('should limit to single file when multiple is false', () => {
    const files = [
      new File(['content1'], 'test1.pdf', { type: 'application/pdf' }),
      new File(['content2'], 'test2.pdf', { type: 'application/pdf' })
    ]
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: false }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onFilesSelected={mockOnFilesSelected} multiple={false} />)
    
    act(() => {
      onDropCallback(files, [])
    })
    
    expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
    expect(screen.getByText('test1.pdf')).toBeInTheDocument()
    expect(screen.queryByText('test2.pdf')).not.toBeInTheDocument()
  })

  it('should handle file rejection', () => {
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload />)
    
    const rejectedFile = {
      file: new File([''], 'large.pdf', { type: 'application/pdf' }),
      errors: [{ code: 'file-too-large', message: 'File is too large' }]
    }
    
    act(() => {
      onDropCallback([], [rejectedFile])
    })
    
    expect(screen.getByText(/exceeds maximum allowed size/)).toBeInTheDocument()
  })

  it('should show upload button when onUpload is provided', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onUpload={mockOnUpload} />)
    
    // Initially no upload button
    expect(screen.queryByText(/Upload/)).not.toBeInTheDocument()
    
    // Add a file
    act(() => {
      onDropCallback([file], [])
    })
    
    // Now upload button should appear
    expect(screen.getByText('Upload 1 File & Extract Text')).toBeInTheDocument()
  })

  it('should handle upload process', async () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    mockOnUpload.mockResolvedValueOnce(['upload-id-123'])
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onUpload={mockOnUpload} />)
    
    // Add file
    act(() => {
      onDropCallback([file], [])
    })
    
    // Click upload
    const uploadButton = screen.getByText('Upload 1 File & Extract Text')
    
    await act(async () => {
      fireEvent.click(uploadButton)
    })
    
    // Should show uploading state
    expect(screen.getByText('Uploading files to server...')).toBeInTheDocument()
    
    // Wait for upload to complete
    await waitFor(() => {
      expect(screen.getByText('Extracting text from documents...')).toBeInTheDocument()
    })
    
    expect(mockOnUpload).toHaveBeenCalledWith([file])
  })

  it('should handle upload error', async () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    const errorMessage = 'Network error occurred'
    mockOnUpload.mockRejectedValueOnce(new Error(errorMessage))
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onUpload={mockOnUpload} />)
    
    // Add file
    act(() => {
      onDropCallback([file], [])
    })
    
    // Click upload
    const uploadButton = screen.getByText('Upload 1 File & Extract Text')
    
    await act(async () => {
      fireEvent.click(uploadButton)
    })
    
    // Wait for error
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })
  })

  it('should remove files from list', () => {
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' })
    
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload />)
    
    // Add file
    act(() => {
      onDropCallback([file], [])
    })
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    
    // Remove file
    const removeButton = screen.getByLabelText('Remove test.pdf')
    fireEvent.click(removeButton)
    
    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
    expect(screen.queryByText('Selected Files')).not.toBeInTheDocument()
  })

  it('should not show upload button for files with errors', () => {
    let onDropCallback: any
    mockUseDropzone.mockImplementation((config: any) => {
      onDropCallback = config.onDrop
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
        acceptedFiles: [],
        fileRejections: []
      } as any
    })

    render(<FileUpload onUpload={mockOnUpload} />)
    
    // Add invalid file that would be rejected by dropzone
    const invalidFile = new File([''], 'test.txt', { type: 'text/plain' })
    act(() => {
      // Pass as rejected file since dropzone would reject it
      onDropCallback([], [{
        file: invalidFile,
        errors: [{ code: 'file-invalid-type', message: 'File type not accepted' }]
      }])
    })
    
    // Should show error but no upload button
    expect(screen.getByText(/File type not supported/)).toBeInTheDocument()
    expect(screen.queryByText(/Upload/)).not.toBeInTheDocument()
  })
})