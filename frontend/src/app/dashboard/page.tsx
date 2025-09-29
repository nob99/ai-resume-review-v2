'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Section, Header } from '@/components/layout'
import { useToastActions } from '@/components/ui/Toast'
import QuickActions from '@/features/dashboard/components/QuickActions'
import RecentActivity from '@/features/dashboard/components/RecentActivity'
import SystemStatus from '@/features/dashboard/components/SystemStatus'

/**
 * Dashboard Page Component
 * Main dashboard view for authenticated users
 */
const DashboardPage: React.FC = () => {
  const { user } = useAuth()
  const { showInfo } = useToastActions()
  const router = useRouter()

  const handleUploadResume = () => {
    router.push('/upload')
  }

  const handleFeatureClick = (feature: string) => {
    showInfo(`${feature} feature will be implemented in Sprint 3`)
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <Section spacing="lg">
          <Container>
            <div className="space-y-8">
              {/* Welcome Header */}
              <div className="text-center">
                <h1 className="text-4xl font-bold text-neutral-900 mb-4">
                  Welcome back, {user?.first_name || 'User'}!
                </h1>
                <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
                  Ready to analyze resumes with AI-powered insights?
                  Upload a resume to get started with intelligent feedback and scoring.
                </p>
              </div>

              {/* Quick Actions */}
              <QuickActions
                onUploadClick={handleUploadResume}
                onFeatureClick={handleFeatureClick}
              />

              {/* Recent Activity */}
              <RecentActivity onUploadClick={handleUploadResume} />

              {/* System Status */}
              <SystemStatus />
            </div>
          </Container>
        </Section>
      </div>
    </ProtectedRoute>
  )
}

export default DashboardPage