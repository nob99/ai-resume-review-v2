import React from 'react'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { AuthProvider } from '@/lib/auth-context'
import { ToastProvider } from '@/components/ui/Toast'
import LoginForm from '@/components/forms/LoginForm'
import Header from '@/components/layout/Header'
import * as api from '@/lib/api'

// Mock the API module
jest.mock('@/lib/api', () => ({
  authApi: {
    login: jest.fn(),
    logout: jest.fn(),
    getCurrentUser: jest.fn(),
  },
  isAuthenticated: jest.fn(),
  TokenStorage: {
    getAccessToken: jest.fn(),
    getRefreshToken: jest.fn(),
    setTokens: jest.fn(),
    clearTokens: jest.fn(),
  },
}))

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
  }),
}))

const mockApi = api.authApi as jest.Mocked<typeof api.authApi>
const mockIsAuthenticated = api.isAuthenticated as jest.MockedFunction<typeof api.isAuthenticated>

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthProvider>
      <ToastProvider>
        {children}
      </ToastProvider>
    </AuthProvider>
  )
}

const user = userEvent.setup()

describe('Authentication Flow Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Default to not authenticated
    mockIsAuthenticated.mockReturnValue(false)
  })

  describe('Login Flow', () => {
    it('successfully logs in user with valid credentials', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'consultant' as const,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const mockLoginResponse = {
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        expires_in: 1800,
        user: mockUser,
      }

      mockApi.login.mockResolvedValueOnce(mockLoginResponse)
      
      const onSuccess = jest.fn()
      render(
        <TestWrapper>
          <LoginForm onSuccess={onSuccess} />
        </TestWrapper>
      )

      // Fill in the form
      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validpassword')

      // Submit the form
      await user.click(submitButton)

      // Wait for API call
      await waitFor(() => {
        expect(mockApi.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'validpassword',
        })
      })

      // Success callback should be called
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled()
      })
    })

    it('displays error for invalid credentials', async () => {
      const mockError = {
        response: {
          status: 401,
          data: { detail: 'Invalid email or password' },
        },
      }

      mockApi.login.mockRejectedValueOnce(mockError)

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByText('Invalid email or password')).toBeInTheDocument()
      })
    })

    it('handles account locked error', async () => {
      const mockError = {
        response: {
          status: 423,
          data: { detail: 'Account is locked' },
        },
      }

      mockApi.login.mockRejectedValueOnce(mockError)

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'locked@example.com')
      await user.type(passwordInput, 'password')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Account is locked due to too many failed attempts')).toBeInTheDocument()
      })
    })

    it('handles rate limiting error', async () => {
      const mockError = {
        response: {
          status: 429,
          data: { detail: 'Too many requests' },
        },
      }

      mockApi.login.mockRejectedValueOnce(mockError)

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Too many login attempts. Please try again later.')).toBeInTheDocument()
      })
    })

    it('shows loading state during login', async () => {
      // Create a promise we can control
      let resolveLogin: (value: any) => void
      const loginPromise = new Promise((resolve) => {
        resolveLogin = resolve
      })
      
      mockApi.login.mockReturnValueOnce(loginPromise)

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password')
      await user.click(submitButton)

      // Button should show loading state
      expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument()
      expect(submitButton).toBeDisabled()

      // Resolve the promise to cleanup
      act(() => {
        resolveLogin!({
          access_token: 'token',
          refresh_token: 'refresh',
          token_type: 'bearer',
          expires_in: 1800,
          user: { email: 'test@example.com' },
        })
      })
    })

    it('validates email format', async () => {
      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const emailInput = screen.getByLabelText(/email address/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })

      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)

      expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
      expect(mockApi.login).not.toHaveBeenCalled()
    })

    it('validates required fields', async () => {
      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      )

      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      // Try to submit without filling fields
      await user.click(submitButton)

      expect(screen.getByText('Email address is required')).toBeInTheDocument()
      expect(screen.getByText('Password is required')).toBeInTheDocument()
      expect(mockApi.login).not.toHaveBeenCalled()
    })
  })

  describe('Logout Flow', () => {
    it('successfully logs out user', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'consultant' as const,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      // Mock authenticated state
      mockIsAuthenticated.mockReturnValue(true)
      mockApi.getCurrentUser.mockResolvedValueOnce(mockUser)
      mockApi.logout.mockResolvedValueOnce(undefined)

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      )

      // Wait for user to load
      await waitFor(() => {
        expect(screen.getByText('John')).toBeInTheDocument()
      })

      // Open user menu
      const userMenuButton = screen.getByRole('button', { name: /John/i })
      await user.click(userMenuButton)

      // Click logout
      const logoutButton = screen.getByText('Sign Out')
      await user.click(logoutButton)

      await waitFor(() => {
        expect(mockApi.logout).toHaveBeenCalled()
      })
    })

    it('handles logout errors gracefully', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'consultant' as const,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      mockIsAuthenticated.mockReturnValue(true)
      mockApi.getCurrentUser.mockResolvedValueOnce(mockUser)
      mockApi.logout.mockRejectedValueOnce(new Error('Network error'))

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(screen.getByText('John')).toBeInTheDocument()
      })

      const userMenuButton = screen.getByRole('button', { name: /John/i })
      await user.click(userMenuButton)

      const logoutButton = screen.getByText('Sign Out')
      await user.click(logoutButton)

      // Should still attempt logout even if it fails
      await waitFor(() => {
        expect(mockApi.logout).toHaveBeenCalled()
      })
    })
  })

  describe('Authentication State Management', () => {
    it('initializes with unauthenticated state', async () => {
      mockIsAuthenticated.mockReturnValue(false)

      render(
        <TestWrapper>
          <div>App content</div>
        </TestWrapper>
      )

      // Should render without authenticated content
      expect(screen.getByText('App content')).toBeInTheDocument()
    })

    it('initializes with authenticated state when tokens exist', async () => {
      const mockUser = {
        id: '1',
        email: 'test@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'consultant' as const,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      mockIsAuthenticated.mockReturnValue(true)
      mockApi.getCurrentUser.mockResolvedValueOnce(mockUser)

      render(
        <TestWrapper>
          <Header />
        </TestWrapper>
      )

      await waitFor(() => {
        expect(mockApi.getCurrentUser).toHaveBeenCalled()
        expect(screen.getByText('John')).toBeInTheDocument()
      })
    })

    it('handles expired tokens during initialization', async () => {
      mockIsAuthenticated.mockReturnValue(true)
      mockApi.getCurrentUser.mockRejectedValueOnce(new Error('Token expired'))

      render(
        <TestWrapper>
          <div>App content</div>
        </TestWrapper>
      )

      // Should handle error gracefully
      await waitFor(() => {
        expect(mockApi.getCurrentUser).toHaveBeenCalled()
      })
    })
  })
})