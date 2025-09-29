import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Alert variant types
type AlertVariant = 'info' | 'success' | 'warning' | 'error'
type AlertSize = 'sm' | 'md' | 'lg'

export interface AlertProps extends BaseComponentProps {
  variant?: AlertVariant
  size?: AlertSize
  title?: string
  dismissible?: boolean
  onDismiss?: () => void
  icon?: React.ReactNode
  actions?: React.ReactNode
}

// Variant styles mapping
const variantStyles: Record<AlertVariant, string> = {
  info: 'bg-white border-2 border-primary-400 text-primary-900',
  success: 'bg-white border-2 border-secondary-400 text-secondary-900',
  warning: 'bg-white border-2 border-warning-400 text-warning-900',
  error: 'bg-white border-2 border-error-400 text-error-900',
}

// Icon color styles mapping
const iconColorStyles: Record<AlertVariant, string> = {
  info: 'text-primary-500',
  success: 'text-secondary-500',
  warning: 'text-warning-500',
  error: 'text-error-500',
}

// Size styles mapping
const sizeStyles: Record<AlertSize, string> = {
  sm: 'p-3 text-sm',
  md: 'p-4 text-base',
  lg: 'p-6 text-lg',
}

// Default icons for each variant
const defaultIcons: Record<AlertVariant, React.ReactNode> = {
  info: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
    </svg>
  ),
  success: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  ),
}

// Close icon
const CloseIcon: React.FC = () => (
  <svg
    className="w-4 h-4"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M6 18L18 6M6 6l12 12"
    />
  </svg>
)

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      variant = 'info',
      size = 'md',
      title,
      dismissible = false,
      onDismiss,
      icon,
      actions,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const displayIcon = icon !== null ? (icon || defaultIcons[variant]) : null

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(
          // Base alert styles
          'border rounded-md',
          
          // Variant styles
          variantStyles[variant],
          
          // Size styles
          sizeStyles[size],
          
          className
        )}
        {...props}
      >
        <div className="flex items-start">
          {/* Icon */}
          {displayIcon && (
            <div className={cn('flex-shrink-0 mr-3', iconColorStyles[variant])}>
              {displayIcon}
            </div>
          )}

          {/* Content */}
          <div className="flex-1 min-w-0">
            {title && (
              <h3 className="font-medium mb-1">
                {title}
              </h3>
            )}
            <div className={cn({ 'text-sm opacity-90': title })}>
              {children}
            </div>
            
            {/* Actions */}
            {actions && (
              <div className="mt-3">
                {actions}
              </div>
            )}
          </div>

          {/* Dismiss button */}
          {dismissible && onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className={cn(
                'flex-shrink-0 ml-3 p-1 rounded-md',
                'transition-colors duration-200',
                'hover:bg-black hover:bg-opacity-10',
                'focus:outline-none focus:ring-2 focus:ring-offset-2',
                {
                  'focus:ring-primary-500': variant === 'info',
                  'focus:ring-secondary-500': variant === 'success',
                  'focus:ring-warning-500': variant === 'warning',
                  'focus:ring-error-500': variant === 'error',
                }
              )}
              aria-label="Dismiss alert"
            >
              <CloseIcon />
            </button>
          )}
        </div>
      </div>
    )
  }
)

Alert.displayName = 'Alert'

export default Alert