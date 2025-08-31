import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/Card'

describe('Card Components', () => {
  describe('Card', () => {
    it('renders with default props', () => {
      render(
        <Card>
          <div>Card content</div>
        </Card>
      )
      
      const card = screen.getByText('Card content').parentElement
      expect(card).toBeInTheDocument()
      expect(card).toHaveClass('bg-white', 'border', 'border-neutral-200')
    })

    it('renders with different variants', () => {
      const { rerender } = render(<Card variant="outlined">Content</Card>)
      let card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('border-2', 'border-neutral-300')
      
      rerender(<Card variant="elevated">Content</Card>)
      card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('shadow-lg')
    })

    it('renders with different padding sizes', () => {
      const { rerender } = render(<Card padding="sm">Content</Card>)
      let card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('p-4')
      
      rerender(<Card padding="lg">Content</Card>)
      card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('p-8')
      
      rerender(<Card padding="none">Content</Card>)
      card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('p-0')
    })

    it('handles hover effect', () => {
      render(<Card hover>Hoverable Card</Card>)
      
      const card = screen.getByText('Hoverable Card').parentElement
      expect(card).toHaveClass('hover:shadow-md')
    })

    it('handles click events when clickable', () => {
      const handleClick = jest.fn()
      render(
        <Card clickable onClick={handleClick}>
          Clickable Card
        </Card>
      )
      
      const card = screen.getByRole('button')
      expect(card).toHaveClass('cursor-pointer')
      
      fireEvent.click(card)
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('handles keyboard navigation when clickable', () => {
      const handleClick = jest.fn()
      render(
        <Card clickable onClick={handleClick}>
          Clickable Card
        </Card>
      )
      
      const card = screen.getByRole('button')
      
      // Test Enter key
      fireEvent.keyDown(card, { key: 'Enter' })
      expect(handleClick).toHaveBeenCalledTimes(1)
      
      // Test Space key
      fireEvent.keyDown(card, { key: ' ' })
      expect(handleClick).toHaveBeenCalledTimes(2)
    })

    it('applies custom className', () => {
      render(<Card className="custom-card">Content</Card>)
      
      const card = screen.getByText('Content').parentElement
      expect(card).toHaveClass('custom-card')
    })

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>()
      render(<Card ref={ref}>Content</Card>)
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement)
    })
  })

  describe('CardHeader', () => {
    it('renders with title and subtitle', () => {
      render(
        <CardHeader 
          title="Card Title" 
          subtitle="Card subtitle" 
        />
      )
      
      expect(screen.getByText('Card Title')).toBeInTheDocument()
      expect(screen.getByText('Card subtitle')).toBeInTheDocument()
    })

    it('renders with children', () => {
      render(
        <CardHeader>
          <div>Custom header content</div>
        </CardHeader>
      )
      
      expect(screen.getByText('Custom header content')).toBeInTheDocument()
    })

    it('renders title with correct styling', () => {
      render(<CardHeader title="Styled Title" />)
      
      const title = screen.getByText('Styled Title')
      expect(title).toHaveClass('text-lg', 'font-semibold', 'text-neutral-900')
    })

    it('renders subtitle with correct styling', () => {
      render(<CardHeader subtitle="Styled Subtitle" />)
      
      const subtitle = screen.getByText('Styled Subtitle')
      expect(subtitle).toHaveClass('text-sm', 'text-neutral-500')
    })

    it('applies custom className', () => {
      render(<CardHeader className="custom-header" title="Title" />)
      
      const header = screen.getByText('Title').parentElement
      expect(header).toHaveClass('custom-header')
    })
  })

  describe('CardContent', () => {
    it('renders children correctly', () => {
      render(
        <CardContent>
          <p>Card content text</p>
        </CardContent>
      )
      
      expect(screen.getByText('Card content text')).toBeInTheDocument()
    })

    it('has correct default styling', () => {
      render(
        <CardContent>
          Content
        </CardContent>
      )
      
      const content = screen.getByText('Content').parentElement
      expect(content).toHaveClass('text-neutral-700')
    })

    it('applies custom className', () => {
      render(<CardContent className="custom-content">Content</CardContent>)
      
      const content = screen.getByText('Content').parentElement
      expect(content).toHaveClass('custom-content')
    })
  })

  describe('CardFooter', () => {
    it('renders children correctly', () => {
      render(
        <CardFooter>
          <button>Action</button>
        </CardFooter>
      )
      
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('has correct default styling', () => {
      render(
        <CardFooter>
          <span>Footer content</span>
        </CardFooter>
      )
      
      const footer = screen.getByText('Footer content').parentElement
      expect(footer).toHaveClass('flex', 'items-center', 'justify-between')
      expect(footer).toHaveClass('pt-4', 'border-t', 'border-neutral-100')
    })

    it('applies custom className', () => {
      render(<CardFooter className="custom-footer">Content</CardFooter>)
      
      const footer = screen.getByText('Content').parentElement
      expect(footer).toHaveClass('custom-footer')
    })
  })

  describe('Full Card Composition', () => {
    it('renders complete card with all sections', () => {
      render(
        <Card>
          <CardHeader title="Test Card" subtitle="Testing composition" />
          <CardContent>
            <p>Main content area</p>
          </CardContent>
          <CardFooter>
            <button>Action</button>
          </CardFooter>
        </Card>
      )
      
      expect(screen.getByText('Test Card')).toBeInTheDocument()
      expect(screen.getByText('Testing composition')).toBeInTheDocument()
      expect(screen.getByText('Main content area')).toBeInTheDocument()
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('maintains proper structure and styling in composition', () => {
      render(
        <Card variant="elevated" padding="lg">
          <CardHeader title="Composed Card" />
          <CardContent>Content</CardContent>
          <CardFooter>Footer</CardFooter>
        </Card>
      )
      
      const card = screen.getByText('Composed Card').closest('[class*="shadow-lg"]')
      expect(card).toHaveClass('p-8', 'shadow-lg')
    })
  })
})