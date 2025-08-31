import React from 'react'
import { cn } from '@/lib/utils'
import { BaseComponentProps } from '@/types'

// Grid column types
type GridCols = 1 | 2 | 3 | 4 | 5 | 6 | 12
type GridGap = 'none' | 'sm' | 'md' | 'lg' | 'xl'

export interface GridProps extends BaseComponentProps {
  cols?: GridCols | { sm?: GridCols; md?: GridCols; lg?: GridCols; xl?: GridCols }
  gap?: GridGap
  as?: keyof JSX.IntrinsicElements
}

// Grid columns mapping
const colsStyles: Record<GridCols, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
  6: 'grid-cols-6',
  12: 'grid-cols-12',
}

// Responsive columns mapping
const responsiveColsStyles = {
  sm: {
    1: 'sm:grid-cols-1',
    2: 'sm:grid-cols-2',
    3: 'sm:grid-cols-3',
    4: 'sm:grid-cols-4',
    5: 'sm:grid-cols-5',
    6: 'sm:grid-cols-6',
    12: 'sm:grid-cols-12',
  },
  md: {
    1: 'md:grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-4',
    5: 'md:grid-cols-5',
    6: 'md:grid-cols-6',
    12: 'md:grid-cols-12',
  },
  lg: {
    1: 'lg:grid-cols-1',
    2: 'lg:grid-cols-2',
    3: 'lg:grid-cols-3',
    4: 'lg:grid-cols-4',
    5: 'lg:grid-cols-5',
    6: 'lg:grid-cols-6',
    12: 'lg:grid-cols-12',
  },
  xl: {
    1: 'xl:grid-cols-1',
    2: 'xl:grid-cols-2',
    3: 'xl:grid-cols-3',
    4: 'xl:grid-cols-4',
    5: 'xl:grid-cols-5',
    6: 'xl:grid-cols-6',
    12: 'xl:grid-cols-12',
  },
}

// Gap styles mapping
const gapStyles: Record<GridGap, string> = {
  none: 'gap-0',
  sm: 'gap-2',     // 8px
  md: 'gap-4',     // 16px
  lg: 'gap-6',     // 24px
  xl: 'gap-8',     // 32px
}

const Grid = React.forwardRef<HTMLElement, GridProps>(
  (
    {
      cols = 1,
      gap = 'md',
      as: Component = 'div',
      className,
      children,
      ...props
    },
    ref
  ) => {
    // Handle responsive columns
    const getColumnClasses = () => {
      if (typeof cols === 'number') {
        return colsStyles[cols]
      }
      
      const classes: string[] = []
      
      // Default to mobile-first 1 column if no base is specified
      if (!cols.sm && !cols.md && !cols.lg && !cols.xl) {
        classes.push('grid-cols-1')
      }
      
      // Add responsive classes
      if (cols.sm) classes.push(responsiveColsStyles.sm[cols.sm])
      if (cols.md) classes.push(responsiveColsStyles.md[cols.md])
      if (cols.lg) classes.push(responsiveColsStyles.lg[cols.lg])
      if (cols.xl) classes.push(responsiveColsStyles.xl[cols.xl])
      
      return classes.join(' ')
    }

    return (
      <Component
        ref={ref}
        className={cn(
          // Base grid styles
          'grid',
          
          // Column styles
          getColumnClasses(),
          
          // Gap styles
          gapStyles[gap],
          
          className
        )}
        {...props}
      >
        {children}
      </Component>
    )
  }
)

Grid.displayName = 'Grid'

export default Grid