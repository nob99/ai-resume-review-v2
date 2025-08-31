'use client'

import React from 'react'
import { useAuth } from '@/lib/auth-context'
import { ProtectedRoute } from '@/lib/auth-context'
import { Container, Section, Header } from '@/components/layout'
import { Card, CardHeader, CardContent, Button } from '@/components/ui'
import { useToastActions } from '@/components/ui/Toast'

const DashboardPage: React.FC = () => {
  const { user } = useAuth()
  const { showInfo } = useToastActions()

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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <Card 
                  hover 
                  clickable
                  onClick={() => handleFeatureClick('Upload Resume')}
                  className="text-center"
                >
                  <CardContent className="p-6">
                    <div className="w-16 h-16 bg-primary-100 text-primary-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                      Upload Resume
                    </h3>
                    <p className="text-neutral-600 text-sm">
                      Upload a PDF or Word document to get AI-powered analysis and feedback
                    </p>
                  </CardContent>
                </Card>

                <Card 
                  hover 
                  clickable
                  onClick={() => handleFeatureClick('Review History')}
                  className="text-center"
                >
                  <CardContent className="p-6">
                    <div className="w-16 h-16 bg-secondary-100 text-secondary-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                      Review History
                    </h3>
                    <p className="text-neutral-600 text-sm">
                      View past resume analyses and track improvements over time
                    </p>
                  </CardContent>
                </Card>

                <Card 
                  hover 
                  clickable
                  onClick={() => handleFeatureClick('Analytics')}
                  className="text-center"
                >
                  <CardContent className="p-6">
                    <div className="w-16 h-16 bg-warning-100 text-warning-600 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-neutral-900 mb-2">
                      Analytics
                    </h3>
                    <p className="text-neutral-600 text-sm">
                      View detailed insights and trends from your resume reviews
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Recent Activity Placeholder */}
              <Card>
                <CardHeader 
                  title="Recent Activity"
                  subtitle="Your latest resume reviews and activities"
                />
                <CardContent>
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-neutral-100 text-neutral-400 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-neutral-900 mb-2">
                      No activity yet
                    </h3>
                    <p className="text-neutral-500 mb-4">
                      Upload your first resume to start seeing activity here
                    </p>
                    <Button 
                      onClick={() => handleFeatureClick('Upload Resume')}
                      className="mx-auto"
                    >
                      Upload Resume
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* System Status */}
              <Card variant="outlined">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 bg-secondary-500 rounded-full"></div>
                      <span className="text-sm font-medium text-neutral-700">
                        All systems operational
                      </span>
                    </div>
                    <span className="text-sm text-neutral-500">
                      Sprint 2 - Authentication System Active
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </Container>
        </Section>
      </div>
    </ProtectedRoute>
  )
}

export default DashboardPage