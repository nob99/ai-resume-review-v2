'use client'

import React from 'react'

interface AnalysisTimerProps {
  elapsedTime: number // in milliseconds
  isAnalyzing: boolean
  status: string
}

/**
 * Format milliseconds to MM:SS display
 */
function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

/**
 * AnalysisTimer Component
 * Displays elapsed time during analysis with visual feedback
 */
export default function AnalysisTimer({
  elapsedTime,
  isAnalyzing,
  status
}: AnalysisTimerProps) {
  if (!isAnalyzing && elapsedTime === 0) {
    return null
  }

  const formattedTime = formatTime(elapsedTime)
  const timeInSeconds = Math.floor(elapsedTime / 1000)

  // Determine status message and color
  let statusMessage = 'Processing...'
  let statusColor = 'text-blue-600'
  let bgColor = 'bg-blue-50'
  let borderColor = 'border-blue-200'

  if (status === 'processing') {
    statusMessage = 'AI 分析中... / AI is analyzing your resume...'
    statusColor = 'text-blue-600'
  } else if (status === 'pending') {
    statusMessage = '待機中... / Waiting to start...'
    statusColor = 'text-yellow-600'
    bgColor = 'bg-yellow-50'
    borderColor = 'border-yellow-200'
  } else if (status === 'completed') {
    statusMessage = '完了！ / Completed!'
    statusColor = 'text-green-600'
    bgColor = 'bg-green-50'
    borderColor = 'border-green-200'
  }

  // Show warning if taking too long
  const isSlowWarning = isAnalyzing && timeInSeconds > 120 // 2 minutes
  const isCriticalWarning = isAnalyzing && timeInSeconds > 180 // 3 minutes

  if (isSlowWarning) {
    statusMessage = '通常より時間がかかっています... / Taking longer than usual...'
    statusColor = 'text-orange-600'
    bgColor = 'bg-orange-50'
    borderColor = 'border-orange-200'
  }

  if (isCriticalWarning) {
    statusMessage = 'エラーの可能性があります / Something might be wrong'
    statusColor = 'text-red-600'
    bgColor = 'bg-red-50'
    borderColor = 'border-red-200'
  }

  return (
    <div className={`flex items-center justify-between p-4 rounded-lg border-2 ${bgColor} ${borderColor}`}>
      {/* Left side: Status and timer */}
      <div className="flex items-center space-x-4">
        {/* Animated spinner when analyzing */}
        {isAnalyzing && (
          <div className="relative">
            <div className="w-6 h-6 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
        )}

        {/* Status message */}
        <div className="flex flex-col">
          <span className={`text-sm font-medium ${statusColor}`}>
            {statusMessage}
          </span>
          {isSlowWarning && (
            <span className="text-xs text-neutral-500 mt-1">
              通常は1-2分で完了します / Usually completes in 1-2 minutes
            </span>
          )}
        </div>
      </div>

      {/* Right side: Timer display */}
      <div className="flex items-center space-x-2">
        <svg
          className={`w-5 h-5 ${statusColor}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span className={`text-2xl font-mono font-bold ${statusColor}`}>
          {formattedTime}
        </span>
      </div>
    </div>
  )
}
