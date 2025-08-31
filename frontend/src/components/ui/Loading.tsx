import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Loading variant types
type LoadingVariant = 'spinner' | 'dots' | 'pulse' | 'skeleton'
type LoadingSize = 'sm' | 'md' | 'lg' | 'xl'

export interface LoadingProps extends BaseComponentProps {
  variant?: LoadingVariant
  size?: LoadingSize
  text?: string
  fullScreen?: boolean
  overlay?: boolean
}

export interface SkeletonProps extends BaseComponentProps {
  height?: string | number
  width?: string | number
  rounded?: boolean
  lines?: number
}

// Size styles mapping for spinners
const sizeStyles: Record<LoadingSize, string> = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6', 
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
}

// Text size styles mapping
const textSizeStyles: Record<LoadingSize, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-xl',
}

// Spinner component
const Spinner: React.FC<{ size: LoadingSize; className?: string }> = ({ size, className }) => (
  <svg
    className={cn(
      'animate-spin text-current',
      sizeStyles[size],
      className
    )}
    fill="none"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    role="status"
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

// Dots component
const Dots: React.FC<{ size: LoadingSize; className?: string }> = ({ size, className }) => {
  const dotSize = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
    xl: 'w-4 h-4',
  }[size]

  return (
    <div className={cn('flex items-center justify-center gap-1', className)}>
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={cn(
            'bg-current rounded-full animate-pulse',
            dotSize
          )}
          style={{
            animationDelay: `${index * 0.2}s`,
            animationDuration: '1.4s',
          }}
        />
      ))}
    </div>
  )
}

// Pulse component
const Pulse: React.FC<{ size: LoadingSize; className?: string }> = ({ size, className }) => (
  <div
    className={cn(
      'bg-current rounded-full animate-pulse',
      sizeStyles[size],
      className
    )}
    role="status"
    aria-hidden="true"
  />
)

// Skeleton component
const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ height = '1rem', width = '100%', rounded = false, lines = 1, className, ...props }, ref) => {
    if (lines > 1) {
      return (
        <div ref={ref} className={cn('space-y-2', className)} {...props}>
          {Array.from({ length: lines }, (_, index) => (
            <div
              key={index}
              className={cn(
                'bg-neutral-200 animate-pulse',
                rounded ? 'rounded-full' : 'rounded'
              )}
              style={{
                height: index === lines - 1 ? `calc(${height} * 0.75)` : height,
                width: index === lines - 1 ? '75%' : width,
              }}
            />
          ))}
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={cn(
          'bg-neutral-200 animate-pulse',
          rounded ? 'rounded-full' : 'rounded',
          className
        )}
        style={{ height, width }}
        {...props}
      />
    )
  }
)

Skeleton.displayName = 'Skeleton'

// Main Loading component
const Loading = React.forwardRef<HTMLDivElement, LoadingProps>(
  (
    {
      variant = 'spinner',
      size = 'md',
      text,
      fullScreen = false,
      overlay = false,
      className,
      ...props
    },
    ref
  ) => {
    const LoadingIcon = () => {
      switch (variant) {
        case 'dots':
          return <Dots size={size} />
        case 'pulse':
          return <Pulse size={size} />
        case 'skeleton':
          return <Skeleton height={sizeStyles[size]} width={sizeStyles[size]} rounded />
        default:
          return <Spinner size={size} />
      }
    }

    const loadingContent = (
      <div
        ref={ref}
        className={cn(
          'flex flex-col items-center justify-center text-neutral-600',
          {
            // Full screen styles
            'fixed inset-0 z-50': fullScreen,
            'bg-white': fullScreen && !overlay,
            'bg-black bg-opacity-50': fullScreen && overlay,
            
            // Regular styles
            'p-4': !fullScreen,
          },
          className
        )}
        role="status"
        aria-live="polite"
        aria-label={text || 'Loading'}
        {...props}
      >
        <div className={cn(
          'flex flex-col items-center justify-center gap-3',
          {
            'bg-white rounded-lg p-6 shadow-lg': fullScreen && overlay,
          }
        )}>
          <LoadingIcon />
          {text && (
            <p className={cn(
              'font-medium text-neutral-700',
              textSizeStyles[size]
            )}>
              {text}
            </p>
          )}
        </div>
      </div>
    )

    return loadingContent
  }
)

Loading.displayName = 'Loading'

// Export components
export { Loading, Skeleton }
export default Loading