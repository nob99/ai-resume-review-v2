// Testing utilities for upload components
// Custom render function with providers and common test setup

import React, { ReactElement } from 'react'
import { render, RenderOptions, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToastProvider } from '../../components/ui'
import { UploadedFile } from '../../types'

/**
 * All the providers needed for testing upload components
 */
const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <ToastProvider>
      {children}
    </ToastProvider>
  )
}

/**
 * Custom render function that includes all necessary providers
 */
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options })

/**
 * Create a user event instance for consistent testing
 */
export const createUser = () => userEvent.setup()

/**
 * Helper to simulate file selection in file input
 */
export const selectFiles = async (input: HTMLInputElement, files: File[]) => {
  const user = createUser()
  
  // Create a FileList-like object
  const fileList = {
    ...files,
    length: files.length,
    item: (index: number) => files[index] || null,
    [Symbol.iterator]: function* () {
      for (let i = 0; i < files.length; i++) {
        yield files[i]
      }
    }
  } as FileList

  // Simulate file selection
  Object.defineProperty(input, 'files', {
    value: fileList,
    writable: false,
  })

  await user.upload(input, files)
}

/**
 * Helper to simulate drag and drop events
 */
export const simulateDragDrop = async (
  dropzone: HTMLElement,
  files: File[]
) => {
  const user = createUser()

  // Create DataTransfer object with files
  const dataTransfer = {
    files: {
      ...files,
      length: files.length,
      item: (index: number) => files[index] || null,
      [Symbol.iterator]: function* () {
        for (let i = 0; i < files.length; i++) {
          yield files[i]
        }
      }
    } as FileList,
    items: files.map(file => ({
      kind: 'file' as const,
      type: file.type,
      getAsFile: () => file
    })),
    types: ['Files']
  }

  // Simulate drag enter
  await user.hover(dropzone)
  
  // Simulate drag over
  const dragOverEvent = new DragEvent('dragover', {
    bubbles: true,
    dataTransfer: dataTransfer as any
  })
  dropzone.dispatchEvent(dragOverEvent)

  // Simulate drop
  const dropEvent = new DragEvent('drop', {
    bubbles: true,
    dataTransfer: dataTransfer as any
  })
  dropzone.dispatchEvent(dropEvent)
}

/**
 * Helper to wait for file processing to complete
 */
export const waitForProcessingComplete = async (
  files: UploadedFile[],
  timeout: number = 5000
) => {
  await waitFor(
    () => {
      const allComplete = files.every(file => 
        file.status === 'completed' || file.status === 'error'
      )
      expect(allComplete).toBe(true)
    },
    { timeout }
  )
}

/**
 * Helper to wait for upload progress
 */
export const waitForUploadProgress = async (
  fileId: string,
  targetProgress: number,
  timeout: number = 3000
) => {
  await waitFor(
    () => {
      const progressElement = screen.getByTestId(`progress-${fileId}`)
      const currentProgress = parseInt(progressElement.getAttribute('aria-valuenow') || '0')
      expect(currentProgress).toBeGreaterThanOrEqual(targetProgress)
    },
    { timeout }
  )
}

/**
 * Mock file reader for testing text extraction
 */
export const mockFileReader = () => {
  const mockReader = {
    readAsText: jest.fn(),
    readAsDataURL: jest.fn(),
    readAsArrayBuffer: jest.fn(),
    result: null,
    error: null,
    onload: null as ((this: FileReader, ev: ProgressEvent<FileReader>) => any) | null,
    onerror: null as ((this: FileReader, ev: ProgressEvent<FileReader>) => any) | null,
    onprogress: null as ((this: FileReader, ev: ProgressEvent<FileReader>) => any) | null,
    abort: jest.fn(),
    readyState: FileReader.EMPTY
  }

  Object.defineProperty(window, 'FileReader', {
    writable: true,
    value: jest.fn(() => mockReader)
  })

  return mockReader
}

/**
 * Mock URL.createObjectURL for file preview testing
 */
export const mockCreateObjectURL = () => {
  const mockUrls: string[] = []
  const mockCreateObjectURL = jest.fn((file: File) => {
    const url = `blob:mock-url-${file.name}-${Date.now()}`
    mockUrls.push(url)
    return url
  })
  const mockRevokeObjectURL = jest.fn()

  Object.defineProperty(window.URL, 'createObjectURL', {
    writable: true,
    value: mockCreateObjectURL
  })

  Object.defineProperty(window.URL, 'revokeObjectURL', {
    writable: true,
    value: mockRevokeObjectURL
  })

  return {
    createObjectURL: mockCreateObjectURL,
    revokeObjectURL: mockRevokeObjectURL,
    urls: mockUrls
  }
}

/**
 * Helper to find file upload input element
 */
export const getFileInput = () => {
  return screen.getByLabelText(/upload|browse|select/i, { hidden: true }) as HTMLInputElement
}

/**
 * Helper to find drag and drop area
 */
export const getDropzone = () => {
  return screen.getByRole('button', { name: /drag.*drop|upload/i })
}

/**
 * Helper to check if an element has drag-active styling
 */
export const expectDragActive = (element: HTMLElement) => {
  expect(element).toHaveClass(/drag.*active|dragging/)
}

/**
 * Helper to check if an element has drag-accept styling  
 */
export const expectDragAccept = (element: HTMLElement) => {
  expect(element).toHaveClass(/drag.*accept|accept/)
}

/**
 * Helper to check if an element has drag-reject styling
 */
export const expectDragReject = (element: HTMLElement) => {
  expect(element).toHaveClass(/drag.*reject|reject/)
}

/**
 * Helper to get file preview item by filename
 */
export const getFilePreviewItem = (filename: string) => {
  return screen.getByTestId(`file-preview-${filename}`) || 
         screen.getByText(filename).closest('[data-testid^="file-preview"]')
}

/**
 * Helper to check file status in preview
 */
export const expectFileStatus = (filename: string, status: UploadedFile['status']) => {
  const fileItem = getFilePreviewItem(filename)
  const statusText = {
    pending: /pending/i,
    uploading: /uploading/i,
    validating: /validating/i,
    extracting: /extracting/i,
    completed: /ready|completed|success/i,
    error: /failed|error/i
  }
  
  expect(fileItem).toHaveTextContent(statusText[status])
}

/**
 * Helper to simulate network delay for async operations
 */
export const simulateNetworkDelay = (ms: number = 100) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Helper to mock console methods for testing error handling
 */
export const mockConsole = () => {
  const originalConsole = { ...console }
  const mockMethods = {
    log: jest.spyOn(console, 'log').mockImplementation(),
    warn: jest.spyOn(console, 'warn').mockImplementation(),
    error: jest.spyOn(console, 'error').mockImplementation(),
    info: jest.spyOn(console, 'info').mockImplementation()
  }

  const restore = () => {
    Object.assign(console, originalConsole)
    Object.values(mockMethods).forEach(mock => mock.mockRestore())
  }

  return { ...mockMethods, restore }
}

/**
 * Helper to create mock intersection observer for visibility testing
 */
export const mockIntersectionObserver = () => {
  const mockObserve = jest.fn()
  const mockUnobserve = jest.fn()
  const mockDisconnect = jest.fn()

  Object.defineProperty(window, 'IntersectionObserver', {
    writable: true,
    value: jest.fn(() => ({
      observe: mockObserve,
      unobserve: mockUnobserve,
      disconnect: mockDisconnect
    }))
  })

  return { mockObserve, mockUnobserve, mockDisconnect }
}

/**
 * Helper to create mock resize observer for responsive testing
 */
export const mockResizeObserver = () => {
  const mockObserve = jest.fn()
  const mockUnobserve = jest.fn()
  const mockDisconnect = jest.fn()

  Object.defineProperty(window, 'ResizeObserver', {
    writable: true,
    value: jest.fn(() => ({
      observe: mockObserve,
      unobserve: mockUnobserve,
      disconnect: mockDisconnect
    }))
  })

  return { mockObserve, mockUnobserve, mockDisconnect }
}

/**
 * Helper to test component accessibility
 */
export const testAccessibility = {
  async checkAriaLabels(container: HTMLElement) {
    const interactiveElements = container.querySelectorAll('button, input, [role="button"]')
    interactiveElements.forEach(element => {
      const hasLabel = element.getAttribute('aria-label') || 
                      element.getAttribute('aria-labelledby') ||
                      element.textContent?.trim()
      expect(hasLabel).toBeTruthy()
    })
  },

  async checkFocusManagement(container: HTMLElement) {
    const focusableElements = container.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
    
    expect(focusableElements.length).toBeGreaterThan(0)
    
    // Check that elements can receive focus
    for (const element of Array.from(focusableElements)) {
      const htmlElement = element as HTMLElement
      htmlElement.focus()
      expect(document.activeElement).toBe(htmlElement)
    }
  },

  async checkKeyboardNavigation() {
    const user = createUser()
    const focusableElements = document.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )

    if (focusableElements.length > 1) {
      // Tab through elements
      for (let i = 0; i < focusableElements.length - 1; i++) {
        await user.tab()
      }
    }
  }
}

/**
 * Helper to mock performance timing for testing
 */
export const mockPerformance = () => {
  const mockNow = jest.fn(() => Date.now())
  const mockMark = jest.fn()
  const mockMeasure = jest.fn()

  Object.defineProperty(window, 'performance', {
    writable: true,
    value: {
      now: mockNow,
      mark: mockMark,
      measure: mockMeasure
    }
  })

  return { mockNow, mockMark, mockMeasure }
}

// Re-export everything from React Testing Library
export * from '@testing-library/react'

// Override render with our custom version
export { customRender as render }