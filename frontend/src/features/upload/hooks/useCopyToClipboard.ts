import { useState, useCallback } from 'react'

type CopyStatus = 'idle' | 'copied' | 'error'

interface UseCopyToClipboardReturn {
  copyText: (text: string) => Promise<void>
  status: CopyStatus
}

/**
 * Simple clipboard copy hook with fallback support
 * - Uses modern Clipboard API when available
 * - Falls back to document.execCommand for older browsers
 * - Auto-resets status after 2 seconds
 */
export function useCopyToClipboard(): UseCopyToClipboardReturn {
  const [status, setStatus] = useState<CopyStatus>('idle')

  const copyText = useCallback(async (text: string) => {
    try {
      // Modern Clipboard API
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
        setStatus('copied')
      } else {
        // Fallback for older browsers
        fallbackCopyToClipboard(text)
        setStatus('copied')
      }

      // Auto-reset after 2 seconds
      setTimeout(() => {
        setStatus('idle')
      }, 2000)
    } catch (error) {
      console.error('Failed to copy text:', error)
      setStatus('error')

      // Reset error state after 1 second
      setTimeout(() => {
        setStatus('idle')
      }, 1000)
    }
  }, [])

  return { copyText, status }
}

/**
 * Fallback copy method using deprecated execCommand
 * Used for older browsers that don't support Clipboard API
 */
function fallbackCopyToClipboard(text: string): void {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '-9999px'
  textarea.setAttribute('readonly', '')

  document.body.appendChild(textarea)

  try {
    textarea.select()
    textarea.setSelectionRange(0, text.length)

    const successful = document.execCommand('copy')
    if (!successful) {
      throw new Error('execCommand copy failed')
    }
  } finally {
    document.body.removeChild(textarea)
  }
}
