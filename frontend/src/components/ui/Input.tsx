import React, { useState } from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Input types
type InputType = 'text' | 'email' | 'password' | 'search' | 'tel' | 'url'
type InputSize = 'sm' | 'md' | 'lg'

export interface InputProps extends BaseComponentProps {
  type?: InputType
  size?: InputSize
  placeholder?: string
  value?: string
  defaultValue?: string
  disabled?: boolean
  readOnly?: boolean
  required?: boolean
  autoComplete?: string
  autoFocus?: boolean
  id?: string
  name?: string
  // Validation states
  error?: boolean
  errorMessage?: string
  success?: boolean
  // Icons
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  // Event handlers
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void
  onFocus?: (event: React.FocusEvent<HTMLInputElement>) => void
  onBlur?: (event: React.FocusEvent<HTMLInputElement>) => void
  onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement>) => void
}

// Size styles mapping
const sizeStyles: Record<InputSize, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-3 py-2 text-base',
  lg: 'px-4 py-3 text-lg',
}

// Password visibility toggle icon
const EyeIcon: React.FC<{ visible: boolean }> = ({ visible }) => {
  if (visible) {
    return (
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
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
        />
      </svg>
    )
  }

  return (
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
        d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
      />
    </svg>
  )
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      type = 'text',
      size = 'md',
      placeholder,
      value,
      defaultValue,
      disabled = false,
      readOnly = false,
      required = false,
      autoComplete,
      autoFocus = false,
      id,
      name,
      error = false,
      errorMessage,
      success = false,
      leftIcon,
      rightIcon,
      className,
      onChange,
      onFocus,
      onBlur,
      onKeyDown,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false)
    const [isFocused, setIsFocused] = useState(false)

    const isPassword = type === 'password'
    const inputType = isPassword && showPassword ? 'text' : type

    const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true)
      onFocus?.(event)
    }

    const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false)
      onBlur?.(event)
    }

    const togglePasswordVisibility = () => {
      setShowPassword(!showPassword)
    }

    return (
      <div className="relative">
        <div
          className={cn(
            // Base container styles
            'relative flex items-center',
            'border rounded-md',
            'transition-all duration-200',
            
            // Size styles
            sizeStyles[size],
            
            // State styles
            {
              // Default state
              'border-neutral-300 bg-white': !error && !success && !isFocused,
              
              // Focus state
              'border-primary-500 ring-2 ring-primary-500 ring-opacity-20': isFocused && !error && !success,
              
              // Error state
              'border-error-500 ring-2 ring-error-500 ring-opacity-20': error,
              
              // Success state
              'border-secondary-500 ring-2 ring-secondary-500 ring-opacity-20': success,
              
              // Disabled state
              'bg-neutral-50 border-neutral-200 cursor-not-allowed': disabled,
            }
          )}
        >
          {leftIcon && (
            <div className="flex items-center pl-3 text-neutral-400">
              {leftIcon}
            </div>
          )}
          
          <input
            ref={ref}
            type={inputType}
            id={id}
            name={name}
            placeholder={placeholder}
            value={value}
            defaultValue={defaultValue}
            disabled={disabled}
            readOnly={readOnly}
            required={required}
            autoComplete={autoComplete}
            autoFocus={autoFocus}
            onChange={onChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={onKeyDown}
            className={cn(
              // Base input styles
              'flex-1 w-full bg-transparent',
              'placeholder:text-neutral-400',
              'focus:outline-none',
              'disabled:cursor-not-allowed disabled:opacity-50',
              
              // Padding adjustments for icons
              {
                'pl-0': leftIcon,
                'pr-10': isPassword || rightIcon,
                'pl-3': !leftIcon,
                'pr-3': !isPassword && !rightIcon,
              },
              
              className
            )}
            {...props}
          />
          
          {isPassword && (
            <button
              type="button"
              onClick={togglePasswordVisibility}
              className={cn(
                'absolute right-3 flex items-center text-neutral-400 hover:text-neutral-600',
                'focus:outline-none focus:text-neutral-600',
                'disabled:cursor-not-allowed disabled:opacity-50'
              )}
              disabled={disabled}
              tabIndex={-1}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              <EyeIcon visible={showPassword} />
            </button>
          )}
          
          {rightIcon && !isPassword && (
            <div className="absolute right-3 flex items-center text-neutral-400">
              {rightIcon}
            </div>
          )}
        </div>
        
        {errorMessage && (
          <p className="mt-1 text-sm text-error-500" role="alert">
            {errorMessage}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input