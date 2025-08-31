'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import LoginForm from '@/components/forms/LoginForm'
import { Container, Section } from '@/components/layout'
import { Loading } from '@/components/ui'

const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, isLoading, router])

  // Show loading while checking authentication
  if (isLoading) {
    return (
      <Loading
        variant="spinner"
        size="lg"
        text="Loading..."
        fullScreen
      />
    )
  }

  // Don't render login form if user is authenticated
  if (isAuthenticated) {
    return (
      <Loading
        variant="spinner"
        size="lg"
        text="Redirecting to dashboard..."
        fullScreen
      />
    )
  }

  const handleLoginSuccess = () => {
    router.push('/dashboard')
  }

  return (
    <Section variant="muted" spacing="none" className="min-h-screen">
      <Container centerContent>
        <div className="w-full max-w-md space-y-8">
          {/* Header */}
          <div className="text-center">
            <div className="mx-auto w-16 h-16 bg-primary-500 text-white rounded-xl flex items-center justify-center mb-4">
              <span className="font-bold text-xl">AI</span>
            </div>
            <h1 className="text-3xl font-bold text-neutral-900">
              AI Resume Review
            </h1>
            <p className="mt-2 text-neutral-600">
              Intelligent resume analysis powered by AI
            </p>
          </div>

          {/* Login Form */}
          <LoginForm 
            onSuccess={handleLoginSuccess}
            showTitle={false}
            className="shadow-xl"
          />

          {/* Footer */}
          <div className="text-center text-sm text-neutral-500">
            <p>
              Secure authentication powered by JWT
            </p>
          </div>
        </div>
      </Container>
    </Section>
  )
}

export default LoginPage