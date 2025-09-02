// Barrel export for all test utilities
// Makes it easy to import test helpers across test files

export * from './test-fixtures'
export * from './test-utils'
export * from './mock-handlers'
export * from './setup-tests'

// Re-export commonly used testing utilities
export { 
  render, 
  screen, 
  waitFor, 
  fireEvent,
  act,
  renderHook,
  cleanup
} from './test-utils'

// Common test patterns and shortcuts
export const commonTestPatterns = {
  // Standard file upload test flow
  async testFileUploadFlow(
    uploadComponent: HTMLElement,
    files: File[],
    expectedSuccess: boolean = true
  ) {
    const { selectFiles, waitForProcessingComplete } = await import('./test-utils')
    const fileInput = uploadComponent.querySelector('input[type="file"]') as HTMLInputElement
    
    // Select files
    await selectFiles(fileInput, files)
    
    // Wait for processing
    if (expectedSuccess) {
      await waitForProcessingComplete(files.map(f => ({ 
        file: f, 
        id: `test_${f.name}`, 
        status: 'pending' as const, 
        progress: 0 
      })))
    }
    
    return { fileInput }
  },

  // Standard error testing pattern
  async testErrorHandling(
    component: HTMLElement,
    triggerError: () => Promise<void>,
    expectedErrorMessage: string
  ) {
    const { screen, waitFor } = await import('./test-utils')
    
    await triggerError()
    
    await waitFor(() => {
      const errorElement = screen.getByText(new RegExp(expectedErrorMessage, 'i'))
      expect(errorElement).toBeInTheDocument()
    })
  },

  // Standard accessibility testing pattern
  async testAccessibility(container: HTMLElement) {
    const { testAccessibility } = await import('./test-utils')
    
    await testAccessibility.checkAriaLabels(container)
    await testAccessibility.checkFocusManagement(container)
    await testAccessibility.checkKeyboardNavigation()
  }
}