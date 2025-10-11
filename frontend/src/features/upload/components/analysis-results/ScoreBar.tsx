'use client'

import React from 'react'
import { getScoreColor, getScoreBarColor, formatScore } from '@/features/upload/utils/analysisParser'

/**
 * ScoreBar Component
 * Displays a single score with label and progress bar
 * Reusable across different analysis domains
 */

interface ScoreBarProps {
  label: string
  score: number
  showPercentage?: boolean
}

export default function ScoreBar({ label, score, showPercentage = false }: ScoreBarProps) {
  const scoreColor = getScoreColor(score)
  const barColor = getScoreBarColor(score)

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-lg font-bold ${scoreColor}`}>
          {formatScore(score)}{showPercentage && '/100'}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}
