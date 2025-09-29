'use client'

import React from 'react'
import { Card, CardContent } from '@/components/ui'

/**
 * System Status Component
 * Shows current system operational status
 */
const SystemStatus: React.FC = () => {
  // In the future, this could fetch actual system status
  const isOperational = true
  const currentSprint = 'Sprint 2 - Authentication System Active'

  return (
    <Card variant="outlined">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 ${isOperational ? 'bg-secondary-500' : 'bg-error-500'} rounded-full`}></div>
            <span className="text-sm font-medium text-neutral-700">
              {isOperational ? 'All systems operational' : 'System maintenance in progress'}
            </span>
          </div>
          <span className="text-sm text-neutral-500">
            {currentSprint}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

export default SystemStatus