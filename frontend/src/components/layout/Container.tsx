import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Container size types
type ContainerSize = 'sm' | 'md' | 'lg' | 'xl' | 'full'

export interface ContainerProps extends BaseComponentProps {
  size?: ContainerSize
  centerContent?: boolean
  as?: keyof JSX.IntrinsicElements
}

// Container size styles mapping
const sizeStyles: Record<ContainerSize, string> = {
  sm: 'max-w-2xl',     // ~672px
  md: 'max-w-4xl',     // ~896px
  lg: 'max-w-6xl',     // ~1152px
  xl: 'max-w-7xl',     // ~1280px
  full: 'max-w-none',  // No max width
}

const Container = React.forwardRef<HTMLElement, ContainerProps>(
  (
    {
      size = 'lg',
      centerContent = false,
      as: Component = 'div',
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
          // Base container styles
          'mx-auto px-4 sm:px-6 lg:px-8',
          
          // Size styles
          sizeStyles[size],
          
          // Center content vertically if specified
          {
            'flex flex-col items-center justify-center min-h-screen': centerContent,
          },
          
          className
        )}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Container.displayName = 'Container'

export default Container