import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Card variant types
type CardVariant = 'default' | 'outlined' | 'elevated'
type CardPadding = 'none' | 'sm' | 'md' | 'lg'

export interface CardProps extends BaseComponentProps {
  variant?: CardVariant
  padding?: CardPadding
  hover?: boolean
  clickable?: boolean
  onClick?: () => void
}

export interface CardHeaderProps extends BaseComponentProps {
  title?: string
  subtitle?: string
}

export interface CardContentProps extends BaseComponentProps {}

export interface CardFooterProps extends BaseComponentProps {}

// Variant styles mapping
const variantStyles: Record<CardVariant, string> = {
  default: 'bg-white border border-neutral-200',
  outlined: 'bg-white border-2 border-neutral-300',
  elevated: 'bg-white border border-neutral-100 shadow-lg',
}

// Padding styles mapping
const paddingStyles: Record<CardPadding, string> = {
  none: 'p-0',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

// Main Card component
const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'default',
      padding = 'md',
      hover = false,
      clickable = false,
      onClick,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        onClick={clickable ? onClick : undefined}
        className={cn(
          // Base card styles
          'rounded-lg transition-all duration-200',
          
          // Variant styles
          variantStyles[variant],
          
          // Padding styles
          paddingStyles[padding],
          
          // Interactive states
          {
            'hover:shadow-md hover:border-neutral-300': hover && !clickable,
            'cursor-pointer hover:shadow-md hover:border-neutral-300 hover:bg-neutral-50': clickable,
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2': clickable,
          },
          
          className
        )}
        role={clickable ? 'button' : undefined}
        tabIndex={clickable ? 0 : undefined}
        onKeyDown={
          clickable
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onClick?.()
                }
              }
            : undefined
        }
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

// Card Header component
const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, subtitle, className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('flex flex-col space-y-1.5', className)}
        {...props}
      >
        {title && (
          <h3 className="text-lg font-semibold leading-none tracking-tight text-neutral-900">
            {title}
          </h3>
        )}
        {subtitle && (
          <p className="text-sm text-neutral-500">
            {subtitle}
          </p>
        )}
        {children}
      </div>
    )
  }
)

CardHeader.displayName = 'CardHeader'

// Card Content component
const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('text-neutral-700', className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardContent.displayName = 'CardContent'

// Card Footer component
const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex items-center justify-between',
          'pt-4 border-t border-neutral-100',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardFooter.displayName = 'CardFooter'

// Export all components
export { Card, CardHeader, CardContent, CardFooter }
export default Card