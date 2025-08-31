'use client'

import React, { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'
import Button from './Button'

// Modal size types
type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

export interface ModalProps extends BaseComponentProps {
  isOpen: boolean
  onClose: () => void
  size?: ModalSize
  title?: string
  description?: string
  showCloseButton?: boolean
  closeOnOverlayClick?: boolean
  closeOnEscape?: boolean
  preventBodyScroll?: boolean
}

export interface ModalHeaderProps extends BaseComponentProps {
  title?: string
  description?: string
  onClose?: () => void
  showCloseButton?: boolean
}

export interface ModalContentProps extends BaseComponentProps {}

export interface ModalFooterProps extends BaseComponentProps {}

// Modal size styles mapping
const sizeStyles: Record<ModalSize, string> = {
  sm: 'max-w-sm',     // ~384px
  md: 'max-w-md',     // ~448px
  lg: 'max-w-lg',     // ~512px
  xl: 'max-w-xl',     // ~576px
  full: 'max-w-full mx-4', // Full width with margin
}

// Close icon component
const CloseIcon: React.FC = () => (
  <svg
    className="w-5 h-5"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M6 18L18 6M6 6l12 12"
    />
  </svg>
)

// Custom hook for managing body scroll
function useBodyScrollLock(isLocked: boolean) {
  useEffect(() => {
    if (!isLocked) return

    const originalStyle = window.getComputedStyle(document.body).overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = originalStyle
    }
  }, [isLocked])
}

// Custom hook for focus management
function useFocusManagement(isOpen: boolean, modalRef: React.RefObject<HTMLDivElement>) {
  useEffect(() => {
    if (!isOpen || !modalRef.current) return

    const modal = modalRef.current
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0] as HTMLElement
    const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

    // Focus first element when modal opens
    firstElement?.focus()

    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault()
          lastElement?.focus()
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault()
          firstElement?.focus()
        }
      }
    }

    modal.addEventListener('keydown', handleTabKey)
    return () => modal.removeEventListener('keydown', handleTabKey)
  }, [isOpen, modalRef])
}

// Modal Header component
const ModalHeader = React.forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ title, description, onClose, showCloseButton = true, className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-start justify-between p-6 border-b border-neutral-200',
          className
        )}
        {...props}
      >
        <div className="flex-1 min-w-0">
          {title && (
            <h2 className="text-xl font-semibold text-neutral-900 mb-1">
              {title}
            </h2>
          )}
          {description && (
            <p className="text-sm text-neutral-600">
              {description}
            </p>
          )}
          {children}
        </div>
        
        {showCloseButton && onClose && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="ml-4 p-1 -mt-1 -mr-1 hover:bg-neutral-100"
            aria-label="Close modal"
          >
            <CloseIcon />
          </Button>
        )}
      </div>
    )
  }
)

ModalHeader.displayName = 'ModalHeader'

// Modal Content component
const ModalContent = React.forwardRef<HTMLDivElement, ModalContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('flex-1 p-6 overflow-y-auto', className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

ModalContent.displayName = 'ModalContent'

// Modal Footer component
const ModalFooter = React.forwardRef<HTMLDivElement, ModalFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-end gap-3 p-6 border-t border-neutral-200 bg-neutral-50',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

ModalFooter.displayName = 'ModalFooter'

// Main Modal component
const Modal = React.forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      isOpen,
      onClose,
      size = 'md',
      title,
      description,
      showCloseButton = true,
      closeOnOverlayClick = true,
      closeOnEscape = true,
      preventBodyScroll = true,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const modalRef = useRef<HTMLDivElement>(null)
    const combinedRef = (ref as React.RefObject<HTMLDivElement>) || modalRef

    // Lock body scroll when modal is open
    useBodyScrollLock(isOpen && preventBodyScroll)

    // Manage focus within modal
    useFocusManagement(isOpen, combinedRef)

    // Handle escape key
    useEffect(() => {
      if (!isOpen || !closeOnEscape) return

      const handleEscape = (event: KeyboardEvent) => {
        if (event.key === 'Escape') {
          onClose()
        }
      }

      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }, [isOpen, closeOnEscape, onClose])

    // Handle overlay click
    const handleOverlayClick = (event: React.MouseEvent<HTMLDivElement>) => {
      if (closeOnOverlayClick && event.target === event.currentTarget) {
        onClose()
      }
    }

    if (!isOpen) return null

    const modalContent = (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center"
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'modal-title' : undefined}
        aria-describedby={description ? 'modal-description' : undefined}
      >
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={handleOverlayClick}
          aria-hidden="true"
        />

        {/* Modal */}
        <div
          ref={combinedRef}
          className={cn(
            // Base modal styles
            'relative w-full bg-white rounded-lg shadow-xl',
            'flex flex-col max-h-[90vh]',
            'transform transition-all',
            
            // Size styles
            sizeStyles[size],
            
            className
          )}
          {...props}
        >
          {/* Auto-render header if title provided */}
          {(title || description) && (
            <ModalHeader
              title={title}
              description={description}
              onClose={onClose}
              showCloseButton={showCloseButton}
            />
          )}
          
          {children}
        </div>
      </div>
    )

    // Render modal in portal
    if (typeof window !== 'undefined') {
      return createPortal(modalContent, document.body)
    }

    return null
  }
)

Modal.displayName = 'Modal'

// Export all components
export { Modal, ModalHeader, ModalContent, ModalFooter }
export default Modal