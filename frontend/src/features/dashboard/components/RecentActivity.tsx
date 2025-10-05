'use client'

import React from 'react'
import { Card, CardHeader, CardContent, Button } from '@/components/ui'

export interface RecentActivityProps {
  onUploadClick: () => void
}

/**
 * Recent Activity Component
 * Shows recent resume reviews and activities
 */
const RecentActivity: React.FC<RecentActivityProps> = ({ onUploadClick }) => {
  // In the future, this will fetch actual activity data
  const hasActivity = false

  return (
    <Card>
      <CardHeader
        title="Recent Activity"
        subtitle="Your latest resume reviews and activities"
      />
      <CardContent>
        {hasActivity ? (
          // TODO: Implement activity list when data is available
          <div>Activity list will go here</div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-neutral-100 text-neutral-400 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-neutral-900 mb-2">
              No activity yet
            </h3>
            <p className="text-neutral-500 mb-4">
              Upload your first resume to start seeing activity here
            </p>
            <Button
              onClick={onUploadClick}
              className="mx-auto"
            >
              Upload Resume
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default RecentActivity