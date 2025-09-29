'use client'

import React from 'react'
import { Card, CardContent } from '@/components/ui'

export interface QuickActionsProps {
  onUploadClick: () => void
  onFeatureClick: (feature: string) => void
}

/**
 * Quick Actions Component
 * Dashboard action cards for common tasks
 */
const QuickActions: React.FC<QuickActionsProps> = ({ onUploadClick, onFeatureClick }) => {
  const actions = [
    {
      id: 'upload',
      title: 'Upload Resume',
      description: 'Upload a PDF or Word document to get AI-powered analysis and feedback',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      colorClass: 'bg-primary-100 text-primary-600',
      onClick: onUploadClick
    },
    {
      id: 'history',
      title: 'Review History',
      description: 'View past resume analyses and track improvements over time',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      colorClass: 'bg-secondary-100 text-secondary-600',
      onClick: () => onFeatureClick('Review History')
    },
    {
      id: 'analytics',
      title: 'Analytics',
      description: 'View detailed insights and trends from your resume reviews',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
      colorClass: 'bg-warning-100 text-warning-600',
      onClick: () => onFeatureClick('Analytics')
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {actions.map((action) => (
        <Card
          key={action.id}
          hover
          clickable
          onClick={action.onClick}
          className="text-center"
        >
          <CardContent className="p-6">
            <div className={`w-16 h-16 ${action.colorClass} rounded-lg flex items-center justify-center mx-auto mb-4`}>
              {action.icon}
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              {action.title}
            </h3>
            <p className="text-neutral-600 text-sm">
              {action.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export default QuickActions