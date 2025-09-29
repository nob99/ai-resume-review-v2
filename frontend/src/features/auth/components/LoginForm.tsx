'use client'

import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/contexts/AuthContext'
import { LoginRequest } from '@/types'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { cn, isValidEmail } from '@/lib/utils'

export interface LoginFormProps {
  className?: string
  onSuccess?: () => void
  showTitle?: boolean
}

interface FormData {
  email: string
  password: string
}

const LoginForm: React.FC<LoginFormProps> = ({
  className,
  onSuccess,
  showTitle = true,
}) => {
  const { login, isLoading, error, clearError } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    clearErrors,
  } = useForm<FormData>({
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: {
      email: '',
      password: '',
    },
  })

  // Watch form values for real-time validation
  const emailValue = watch('email')
  const passwordValue = watch('password')
  
  // Track previous values to detect actual changes (not just existence)
  const [prevEmailValue, setPrevEmailValue] = useState('')
  const [prevPasswordValue, setPrevPasswordValue] = useState('')

  // Clear auth error only when user starts typing (values change)
  React.useEffect(() => {
    const emailChanged = emailValue !== prevEmailValue
    const passwordChanged = passwordValue !== prevPasswordValue
    
    if (error && (emailChanged || passwordChanged)) {
      clearError()
    }
    
    // Update previous values
    setPrevEmailValue(emailValue)
    setPrevPasswordValue(passwordValue)
  }, [emailValue, passwordValue, error, clearError, prevEmailValue, prevPasswordValue])

  // Submit handler
  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true)
    // Don't clear error here - let auth context handle it
    clearErrors()

    const credentials: LoginRequest = {
      email: data.email.toLowerCase().trim(),
      password: data.password,
    }

    const success = await login(credentials)
    
    // Only call success callback if login was successful
    if (success) {
      onSuccess?.()
    }
    
    setIsSubmitting(false)
  }

  const isFormLoading = isLoading || isSubmitting

  return (
    <Card className={cn('w-full max-w-md', className)}>
      {showTitle && (
        <CardHeader
          title="Welcome back"
          subtitle="Sign in to your account to continue"
        />
      )}
      
      <CardContent>
        <form 
          onSubmit={handleSubmit(onSubmit)} 
          className="space-y-4" 
          noValidate
          autoComplete="off"
        >
          {/* Email field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-neutral-700 mb-1">
              Email address
            </label>
            <Input
              id="email"
              type="email"
              placeholder="Enter your email"
              autoComplete="email"
              disabled={isFormLoading}
              error={!!errors.email}
              errorMessage={errors.email?.message}
              {...register('email', {
                required: 'Email address is required',
                validate: (value) => {
                  if (!isValidEmail(value.trim())) {
                    return 'Please enter a valid email address'
                  }
                  return true
                },
              })}
            />
          </div>

          {/* Password field */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-neutral-700 mb-1">
              Password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isFormLoading}
              error={!!errors.password}
              errorMessage={errors.password?.message}
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 1,
                  message: 'Password is required',
                },
              })}
            />
          </div>

          {/* Auth error display */}
          {error && (
            <div className="p-3 rounded-md bg-error-50 border border-error-200">
              <p className="text-sm text-error-700 flex items-center gap-2">
                <svg
                  className="w-4 h-4 flex-shrink-0"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                    clipRule="evenodd"
                  />
                </svg>
                {error}
              </p>
            </div>
          )}

          {/* Submit button */}
          <Button
            type="submit"
            size="md"
            loading={isFormLoading}
            disabled={isFormLoading}
            className="w-full"
          >
            {isFormLoading ? 'Signing in...' : 'Sign in'}
          </Button>
        </form>

        {/* Additional links */}
        <div className="mt-6 text-center">
          <p className="text-sm text-neutral-600">
            Don't have an account?{' '}
            <button
              type="button"
              className="font-medium text-primary-600 hover:text-primary-500 focus:outline-none focus:underline"
              onClick={() => {
                // TODO: Implement registration flow in future sprint
                console.log('Registration not yet implemented')
              }}
            >
              Contact your administrator
            </button>
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default LoginForm