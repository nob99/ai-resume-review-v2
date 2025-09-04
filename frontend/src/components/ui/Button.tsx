import React from 'react'
import { cn } from '../../lib/utils'
import { BaseComponentProps } from '../../types'

// Button variant types
type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends BaseComponentProps {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void
}

// Variant styles mapping
const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-primary-500 hover:bg-primary-600 focus:ring-primary-500 text-white border-transparent',
  secondary: 'bg-secondary-500 hover:bg-secondary-600 focus:ring-secondary-500 text-white border-transparent',
  danger: 'bg-error-500 hover:bg-error-600 focus:ring-error-500 text-white border-transparent',
  outline: 'bg-transparent hover:bg-neutral-50 focus:ring-primary-500 text-neutral-700 border-neutral-300 hover:border-neutral-400',
  ghost: 'bg-transparent hover:bg-neutral-100 focus:ring-primary-500 text-neutral-700 border-transparent',
}

// Size styles mapping
const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-sm font-medium',
  md: 'px-4 py-2 text-base font-medium',
  lg: 'px-6 py-3 text-lg font-semibold',
}

// Loading spinner component
const LoadingSpinner: React.FC<{ size: ButtonSize }> = ({ size }) => {
  const spinnerSize = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  }[size]

  return (
    <svg
      className={cn('animate-spin text-current', spinnerSize)}
      fill="none"
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      type = 'button',
      className,
      children,
      onClick,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        onClick={onClick}
        className={cn(
          // Base button styles
          'inline-flex items-center justify-center gap-2',
          'border rounded-md font-medium',
          'transition-all duration-200',
          'focus:outline-none focus:ring-2 focus:ring-offset-2',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
          
          // Variant styles
          variantStyles[variant],
          
          // Size styles
          sizeStyles[size],
          
          // Custom className
          className
        )}
        {...props}
      >
        {loading && <LoadingSpinner size={size} />}
        {loading ? (
          <span className="opacity-0">{children}</span>
        ) : (
          <span>{children}</span>
        )}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button