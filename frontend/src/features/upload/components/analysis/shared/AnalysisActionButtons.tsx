'use client'

import React from 'react'
import { Card, CardContent } from '@/components/ui'
import { AnalysisActionButtonsProps } from './types'

/**
 * AnalysisActionButtons Component
 * Displays action buttons for analysis results
 * Conditionally renders based on provided handlers (undefined = hidden)
 */

export default function AnalysisActionButtons({
  onAnalyzeAgain,
  onUploadNew,
  className = ''
}: AnalysisActionButtonsProps) {
  // Don't render if no actions provided
  if (!onAnalyzeAgain && !onUploadNew) {
    return null
  }

  return (
    <Card className={className}>
      <CardContent className="p-6">
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {onAnalyzeAgain && (
            <button
              onClick={onAnalyzeAgain}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
            >
              異なる業界で分析
            </button>
          )}
          {onUploadNew && (
            <button
              onClick={onUploadNew}
              className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-md font-medium transition-colors"
            >
              新しいレジュメをアップロード
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
