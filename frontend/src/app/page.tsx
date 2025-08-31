'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { Loading } from '@/components/ui'

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.push('/dashboard')
      } else {
        router.push('/login')
      }
    }
  }, [isAuthenticated, isLoading, router])

  // Show loading while determining where to redirect
  return (
    <Loading
      variant="spinner"
      size="lg"
      text="Loading AI Resume Review..."
      fullScreen
    />
  )
}
