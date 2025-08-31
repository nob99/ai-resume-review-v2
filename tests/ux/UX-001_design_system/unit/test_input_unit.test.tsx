import React from 'react'
import { render, screen, fireEvent, userEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import Input from '@/components/ui/Input'

// Setup user-event
const user = userEvent.setup()

describe('Input Component', () => {
  it('renders with default props', () => {
    render(<Input placeholder="Enter text" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('placeholder', 'Enter text')
    expect(input).toHaveAttribute('type', 'text')
  })

  it('renders different input types correctly', () => {
    render(<Input type="email" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('type', 'email')
  })

  it('renders password type with visibility toggle', () => {
    render(<Input type="password" />)
    
    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('type', 'password')
    
    // Should have a toggle button
    const toggleButton = screen.getByLabelText('Show password')
    expect(toggleButton).toBeInTheDocument()
  })

  it('toggles password visibility', async () => {
    render(<Input type="password" />)
    
    const input = screen.getByLabelText('Password')
    const toggleButton = screen.getByLabelText('Show password')
    
    // Initially password is hidden
    expect(input).toHaveAttribute('type', 'password')
    
    // Click to show password
    await user.click(toggleButton)
    expect(input).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText('Hide password')).toBeInTheDocument()
    
    // Click to hide password again
    await user.click(toggleButton)
    expect(input).toHaveAttribute('type', 'password')
  })

  it('handles onChange events', async () => {
    const handleChange = jest.fn()
    render(<Input onChange={handleChange} />)
    
    const input = screen.getByRole('textbox')
    await user.type(input, 'test')
    
    expect(handleChange).toHaveBeenCalledTimes(4) // One for each character
  })

  it('handles focus and blur events', async () => {
    const handleFocus = jest.fn()
    const handleBlur = jest.fn()
    render(<Input onFocus={handleFocus} onBlur={handleBlur} />)
    
    const input = screen.getByRole('textbox')
    
    await user.click(input)
    expect(handleFocus).toHaveBeenCalledTimes(1)
    
    await user.tab()
    expect(handleBlur).toHaveBeenCalledTimes(1)
  })

  it('shows error state and message', () => {
    render(<Input error errorMessage="This field is required" />)
    
    const input = screen.getByRole('textbox')
    const errorMessage = screen.getByRole('alert')
    
    expect(input.parentElement).toHaveClass('border-error-500')
    expect(errorMessage).toHaveTextContent('This field is required')
  })

  it('shows success state', () => {
    render(<Input success />)
    
    const input = screen.getByRole('textbox')
    expect(input.parentElement).toHaveClass('border-secondary-500')
  })

  it('is disabled when disabled prop is true', () => {
    render(<Input disabled />)
    
    const input = screen.getByRole('textbox')
    expect(input).toBeDisabled()
    expect(input.parentElement).toHaveClass('bg-neutral-50')
  })

  it('is read-only when readOnly prop is true', () => {
    render(<Input readOnly value="read only text" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('readOnly')
    expect(input).toHaveValue('read only text')
  })

  it('renders with different sizes', () => {
    const { rerender } = render(<Input size="sm" />)
    let input = screen.getByRole('textbox')
    expect(input.parentElement).toHaveClass('px-3', 'py-1.5', 'text-sm')
    
    rerender(<Input size="lg" />)
    input = screen.getByRole('textbox')
    expect(input.parentElement).toHaveClass('px-4', 'py-3', 'text-lg')
  })

  it('renders with left icon', () => {
    const leftIcon = <span data-testid="left-icon">📧</span>
    render(<Input leftIcon={leftIcon} />)
    
    const icon = screen.getByTestId('left-icon')
    expect(icon).toBeInTheDocument()
  })

  it('renders with right icon', () => {
    const rightIcon = <span data-testid="right-icon">🔍</span>
    render(<Input rightIcon={rightIcon} />)
    
    const icon = screen.getByTestId('right-icon')
    expect(icon).toBeInTheDocument()
  })

  it('applies custom className', () => {
    render(<Input className="custom-input" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveClass('custom-input')
  })

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLInputElement>()
    render(<Input ref={ref} />)
    
    expect(ref.current).toBeInstanceOf(HTMLInputElement)
  })

  it('handles autoComplete attribute', () => {
    render(<Input autoComplete="email" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('autoComplete', 'email')
  })

  it('handles required attribute', () => {
    render(<Input required />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('required')
  })

  it('handles focus styling', async () => {
    render(<Input />)
    
    const input = screen.getByRole('textbox')
    await user.click(input)
    
    // Focus styling should be applied to parent container
    expect(input.parentElement).toHaveClass('border-primary-500')
  })

  it('shows placeholder text', () => {
    render(<Input placeholder="Enter your email" />)
    
    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('placeholder', 'Enter your email')
  })

  it('handles value and defaultValue correctly', () => {
    const { rerender } = render(<Input defaultValue="default" />)
    let input = screen.getByRole('textbox')
    expect(input).toHaveValue('default')
    
    rerender(<Input value="controlled" onChange={() => {}} />)
    input = screen.getByRole('textbox')
    expect(input).toHaveValue('controlled')
  })
})