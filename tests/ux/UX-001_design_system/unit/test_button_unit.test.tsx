import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import Button from '@/components/ui/Button'

describe('Button Component', () => {
  it('renders with default props', () => {
    render(<Button>Click me</Button>)
    
    const button = screen.getByRole('button', { name: 'Click me' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveClass('bg-primary-500')
  })

  it('renders with correct variant styles', () => {
    render(<Button variant="secondary">Secondary Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-secondary-500')
  })

  it('renders with correct size styles', () => {
    render(<Button size="lg">Large Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
  })

  it('handles click events', () => {
    const handleClick = jest.fn()
    render(<Button onClick={handleClick}>Clickable</Button>)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('shows loading state correctly', () => {
    render(<Button loading>Loading Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    
    // Check for loading spinner
    const spinner = screen.getByRole('status')
    expect(spinner).toBeInTheDocument()
  })

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button).toHaveClass('disabled:opacity-50')
  })

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLButtonElement>()
    render(<Button ref={ref}>Ref Button</Button>)
    
    expect(ref.current).toBeInstanceOf(HTMLButtonElement)
  })

  it('renders all variant styles correctly', () => {
    const variants = ['primary', 'secondary', 'danger', 'outline', 'ghost'] as const
    
    variants.forEach((variant) => {
      const { rerender } = render(<Button variant={variant}>Test</Button>)
      const button = screen.getByRole('button')
      
      switch (variant) {
        case 'primary':
          expect(button).toHaveClass('bg-primary-500')
          break
        case 'secondary':
          expect(button).toHaveClass('bg-secondary-500')
          break
        case 'danger':
          expect(button).toHaveClass('bg-error-500')
          break
        case 'outline':
          expect(button).toHaveClass('bg-transparent', 'border-neutral-300')
          break
        case 'ghost':
          expect(button).toHaveClass('bg-transparent', 'border-transparent')
          break
      }
      
      rerender(<div />) // Clean up for next iteration
    })
  })

  it('renders all size styles correctly', () => {
    const sizes = ['sm', 'md', 'lg'] as const
    
    sizes.forEach((size) => {
      const { rerender } = render(<Button size={size}>Test</Button>)
      const button = screen.getByRole('button')
      
      switch (size) {
        case 'sm':
          expect(button).toHaveClass('px-3', 'py-1.5', 'text-sm')
          break
        case 'md':
          expect(button).toHaveClass('px-4', 'py-2', 'text-base')
          break
        case 'lg':
          expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
          break
      }
      
      rerender(<div />) // Clean up for next iteration
    })
  })

  it('handles different button types', () => {
    render(<Button type="submit">Submit Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'submit')
  })

  it('has proper accessibility attributes', () => {
    render(<Button>Accessible Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('type', 'button')
    expect(button).not.toHaveAttribute('aria-disabled')
  })

  it('has proper accessibility when disabled', () => {
    render(<Button disabled>Disabled Button</Button>)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })
})