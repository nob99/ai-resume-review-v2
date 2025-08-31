'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'
import Alert from './Alert'

// Toast types
export interface Toast {
  id: string
  variant: 'info' | 'success' | 'warning' | 'error'
  title?: string
  message: string
  duration?: number
  dismissible?: boolean
  actions?: ReactNode
}

type ToastInput = Omit<Toast, 'id'>

// Toast context types
interface ToastContextType {
  toasts: Toast[]
  addToast: (toast: ToastInput) => string
  removeToast: (id: string) => void
  removeAllToasts: () => void
}

// Create context
const ToastContext = createContext<ToastContextType | undefined>(undefined)

// Toast provider props
interface ToastProviderProps {
  children: ReactNode
  maxToasts?: number
  defaultDuration?: number
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
}

// Custom hook to use toast context
export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

// Position styles mapping
const positionStyles = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 transform -translate-x-1/2',
  'bottom-center': 'bottom-4 left-1/2 transform -translate-x-1/2',
}

// Generate unique ID for toasts
function generateId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

// Individual Toast component
interface ToastItemProps {
  toast: Toast
  onRemove: (id: string) => void
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  const [isVisible, setIsVisible] = useState(false)
  const [isRemoving, setIsRemoving] = useState(false)

  // Show toast with animation
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timer)
  }, [])

  // Auto-remove toast after duration
  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        handleRemove()
      }, toast.duration)
      return () => clearTimeout(timer)
    }
  }, [toast.duration])

  const handleRemove = () => {
    setIsRemoving(true)
    setIsVisible(false)
    setTimeout(() => {
      onRemove(toast.id)
    }, 300) // Match animation duration
  }

  return (
    <div
      className={cn(
        'transition-all duration-300 ease-in-out transform',
        'mb-2 max-w-sm w-full',
        {
          'translate-x-0 opacity-100': isVisible && !isRemoving,
          'translate-x-full opacity-0': !isVisible || isRemoving,
        }
      )}
    >
      <Alert
        variant={toast.variant}
        title={toast.title}
        dismissible={toast.dismissible !== false}
        onDismiss={handleRemove}
        actions={toast.actions}
        className="shadow-lg border-0 shadow-black/10"
      >
        {toast.message}
      </Alert>
    </div>
  )
}

// Toast container component
interface ToastContainerProps {
  toasts: Toast[]
  position: string
  onRemove: (id: string) => void
}

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, position, onRemove }) => {
  if (toasts.length === 0) return null

  const content = (
    <div
      className={cn(
        'fixed z-50 flex flex-col',
        'pointer-events-none', // Allow clicks to pass through empty space
        position
      )}
      role="region"
      aria-label="Toast notifications"
      aria-live="polite"
    >
      <div className="flex flex-col-reverse pointer-events-auto">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
        ))}
      </div>
    </div>
  )

  if (typeof window !== 'undefined') {
    return createPortal(content, document.body)
  }

  return null
}

// Toast provider component
export function ToastProvider({
  children,
  maxToasts = 5,
  defaultDuration = 5000,
  position = 'top-right',
}: ToastProviderProps): JSX.Element {
  const [toasts, setToasts] = useState<Toast[]>([])

  // Add toast
  const addToast = (toastInput: ToastInput): string => {
    const id = generateId()
    const toast: Toast = {
      id,
      duration: defaultDuration,
      dismissible: true,
      ...toastInput,
    }

    setToasts((current) => {
      const updated = [toast, ...current]
      // Limit number of toasts
      return updated.slice(0, maxToasts)
    })

    return id
  }

  // Remove toast
  const removeToast = (id: string): void => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }

  // Remove all toasts
  const removeAllToasts = (): void => {
    setToasts([])
  }

  const contextValue: ToastContextType = {
    toasts,
    addToast,
    removeToast,
    removeAllToasts,
  }

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <ToastContainer
        toasts={toasts}
        position={positionStyles[position]}
        onRemove={removeToast}
      />
    </ToastContext.Provider>
  )
}

// Convenience hooks for different toast types
export const useToastActions = () => {
  const { addToast } = useToast()

  return {
    showSuccess: (message: string, options?: Partial<ToastInput>) =>
      addToast({ variant: 'success', message, ...options }),
    
    showError: (message: string, options?: Partial<ToastInput>) =>
      addToast({ variant: 'error', message, ...options }),
    
    showWarning: (message: string, options?: Partial<ToastInput>) =>
      addToast({ variant: 'warning', message, ...options }),
    
    showInfo: (message: string, options?: Partial<ToastInput>) =>
      addToast({ variant: 'info', message, ...options }),
  }
}

export default ToastProvider