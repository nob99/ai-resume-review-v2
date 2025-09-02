// Additional test setup for upload component testing
// Extends jest.setup.js with upload-specific configuration

import { setupServer } from 'msw/node'
import { handlers } from './mock-handlers'

// Setup MSW server for API mocking
export const server = setupServer(...handlers)

// Global test setup
beforeAll(() => {
  // Start MSW server
  server.listen({ onUnhandledRequest: 'error' })
  
  // Mock window.matchMedia for responsive design testing
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(), // deprecated
      removeListener: jest.fn(), // deprecated
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  })

  // Mock scrollTo for testing scroll behavior
  Object.defineProperty(window, 'scrollTo', {
    writable: true,
    value: jest.fn()
  })

  // Mock getBoundingClientRect for layout testing
  Element.prototype.getBoundingClientRect = jest.fn(() => ({
    width: 1024,
    height: 768,
    top: 0,
    left: 0,
    bottom: 768,
    right: 1024,
    x: 0,
    y: 0,
    toJSON: jest.fn()
  }))

  // Suppress console.error during tests unless explicitly needed
  const originalError = console.error
  beforeEach(() => {
    console.error = (...args: any[]) => {
      if (
        typeof args[0] === 'string' &&
        args[0].includes('Warning: ReactDOM.render is deprecated')
      ) {
        return
      }
      originalError.call(console, ...args)
    }
  })

  afterEach(() => {
    console.error = originalError
  })
})

// Reset handlers after each test
afterEach(() => {
  server.resetHandlers()
  
  // Clear all mocks
  jest.clearAllMocks()
  
  // Clean up any global state
  delete (window as any).FileReader
  delete (window as any).URL.createObjectURL
  delete (window as any).URL.revokeObjectURL
})

// Close server after all tests
afterAll(() => {
  server.close()
})

// Custom matchers for upload testing
declare global {
  namespace jest {
    interface Matchers<R> {
      toBeValidFile(): R
      toHaveFileSize(expectedSize: number): R
      toHaveFileType(expectedType: string): R
      toBeInUploadState(expectedState: string): R
      toHaveUploadProgress(expectedProgress: number): R
    }
  }
}

// File validation matcher
expect.extend({
  toBeValidFile(received: File) {
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    
    const pass = validTypes.includes(received.type) && 
                 received.size > 0 && 
                 received.size <= 10 * 1024 * 1024

    if (pass) {
      return {
        message: () => `expected ${received.name} not to be a valid file`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected ${received.name} to be a valid file`,
        pass: false,
      }
    }
  },

  toHaveFileSize(received: File, expectedSize: number) {
    const pass = received.size === expectedSize

    if (pass) {
      return {
        message: () => `expected ${received.name} not to have size ${expectedSize}`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected ${received.name} to have size ${expectedSize}, but got ${received.size}`,
        pass: false,
      }
    }
  },

  toHaveFileType(received: File, expectedType: string) {
    const pass = received.type === expectedType

    if (pass) {
      return {
        message: () => `expected ${received.name} not to have type ${expectedType}`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected ${received.name} to have type ${expectedType}, but got ${received.type}`,
        pass: false,
      }
    }
  },

  toBeInUploadState(received: HTMLElement, expectedState: string) {
    const stateClasses = {
      pending: 'pending',
      uploading: 'uploading',
      validating: 'validating', 
      extracting: 'extracting',
      completed: 'completed',
      error: 'error'
    }

    const expectedClass = stateClasses[expectedState as keyof typeof stateClasses]
    const pass = received.classList.contains(expectedClass) || 
                 received.textContent?.toLowerCase().includes(expectedState.toLowerCase())

    if (pass) {
      return {
        message: () => `expected element not to be in ${expectedState} state`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to be in ${expectedState} state`,
        pass: false,
      }
    }
  },

  toHaveUploadProgress(received: HTMLElement, expectedProgress: number) {
    const progressElement = received.querySelector('[role="progressbar"]') ||
                           received.querySelector('[aria-valuenow]')
    
    const actualProgress = progressElement?.getAttribute('aria-valuenow')
    const pass = actualProgress && parseInt(actualProgress) === expectedProgress

    if (pass) {
      return {
        message: () => `expected element not to have progress ${expectedProgress}`,
        pass: true,
      }
    } else {
      return {
        message: () => `expected element to have progress ${expectedProgress}, but got ${actualProgress}`,
        pass: false,
      }
    }
  }
})

// Global test utilities
export const testUtils = {
  // Create a mock file with specific properties
  createMockFile: (
    name: string = 'test.pdf',
    type: string = 'application/pdf',
    size: number = 1024,
    content: string = 'test content'
  ) => {
    const buffer = new ArrayBuffer(size)
    return new File([buffer], name, { type, lastModified: Date.now() })
  },

  // Wait for animation/transition to complete
  waitForAnimation: async (ms: number = 300) => {
    return new Promise(resolve => setTimeout(resolve, ms))
  },

  // Get current viewport size for responsive testing
  getViewportSize: () => ({
    width: window.innerWidth || 1024,
    height: window.innerHeight || 768
  }),

  // Simulate different viewport sizes
  setViewportSize: (width: number, height: number) => {
    Object.defineProperty(window, 'innerWidth', { writable: true, value: width })
    Object.defineProperty(window, 'innerHeight', { writable: true, value: height })
    
    // Trigger resize event
    window.dispatchEvent(new Event('resize'))
  },

  // Check if element is visible in viewport
  isElementVisible: (element: HTMLElement): boolean => {
    const rect = element.getBoundingClientRect()
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.right <= window.innerWidth
    )
  }
}

// Performance monitoring for tests
export const performanceMonitor = {
  start: (label: string) => {
    performance.mark(`${label}-start`)
  },
  
  end: (label: string) => {
    performance.mark(`${label}-end`)
    performance.measure(label, `${label}-start`, `${label}-end`)
    
    const measure = performance.getEntriesByName(label)[0]
    return measure?.duration || 0
  },
  
  clear: () => {
    performance.clearMarks()
    performance.clearMeasures()
  }
}

// Memory leak detection helper
export const memoryLeakDetector = {
  listeners: new Set<string>(),
  
  trackEventListener: (element: HTMLElement, event: string) => {
    const key = `${element.tagName}-${event}`
    memoryLeakDetector.listeners.add(key)
  },
  
  checkForLeaks: () => {
    const activeListeners = Array.from(memoryLeakDetector.listeners)
    if (activeListeners.length > 0) {
      console.warn('Potential memory leaks detected:', activeListeners)
    }
    return activeListeners.length === 0
  },
  
  clear: () => {
    memoryLeakDetector.listeners.clear()
  }
}

// Accessibility testing helpers
export const accessibilityHelpers = {
  // Check if element has proper ARIA attributes
  hasProperAria: (element: HTMLElement): boolean => {
    const hasLabel = !!(
      element.getAttribute('aria-label') ||
      element.getAttribute('aria-labelledby') ||
      element.textContent?.trim()
    )
    
    const hasRole = !!(
      element.getAttribute('role') ||
      ['BUTTON', 'INPUT', 'A'].includes(element.tagName)
    )
    
    return hasLabel && hasRole
  },
  
  // Check color contrast (simplified)
  hasGoodContrast: (element: HTMLElement): boolean => {
    const styles = getComputedStyle(element)
    const color = styles.color
    const backgroundColor = styles.backgroundColor
    
    // This is a simplified check - in real tests you'd use a proper contrast checker
    return color !== backgroundColor
  },
  
  // Check if element is keyboard accessible
  isKeyboardAccessible: (element: HTMLElement): boolean => {
    const tabIndex = element.getAttribute('tabindex')
    return (
      element.tagName === 'BUTTON' ||
      element.tagName === 'INPUT' ||
      element.tagName === 'A' ||
      (tabIndex !== null && tabIndex !== '-1')
    )
  }
}