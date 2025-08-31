import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Section spacing types
type SectionSpacing = 'none' | 'sm' | 'md' | 'lg' | 'xl'
type SectionVariant = 'default' | 'muted' | 'primary'

export interface SectionProps extends BaseComponentProps {
  spacing?: SectionSpacing
  variant?: SectionVariant
  as?: keyof JSX.IntrinsicElements
}

// Spacing styles mapping
const spacingStyles: Record<SectionSpacing, string> = {
  none: 'py-0',
  sm: 'py-8',      // 32px
  md: 'py-12',     // 48px
  lg: 'py-16',     // 64px
  xl: 'py-24',     // 96px
}

// Variant styles mapping
const variantStyles: Record<SectionVariant, string> = {
  default: 'bg-white',
  muted: 'bg-neutral-50',
  primary: 'bg-primary-50',
}

const Section = React.forwardRef<HTMLElement, SectionProps>(
  (
    {
      spacing = 'md',
      variant = 'default',
      as: Component = 'section',
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <Component
        ref={ref}
        className={cn(
          // Base section styles
          'w-full',
          
          // Spacing styles
          spacingStyles[spacing],
          
          // Variant styles
          variantStyles[variant],
          
          className
        )}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Section.displayName = 'Section'

export default Section