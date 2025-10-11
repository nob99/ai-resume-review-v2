'use client'

import React from 'react'
import { Card, CardContent } from '@/components/ui'
import { AnalysisStatusResponse } from '@/types'
import AnalysisOverview from './analysis-results/AnalysisOverview'
import StructureAnalysisCard from './analysis-results/StructureAnalysisCard'
import AppealAnalysisCard from './analysis-results/AppealAnalysisCard'
import AnalysisActionButtons from './analysis-results/AnalysisActionButtons'

/**
 * AnalysisResults Component
 * Layout orchestrator for analysis results
 * Composes domain-specific analysis cards
 */

interface AnalysisResultsProps {
  analysis: AnalysisStatusResponse
  industryOptions?: Array<{ value: string; label: string }>
  onAnalyzeAgain?: () => void
  onUploadNew?: () => void
  className?: string
  elapsedTime?: number
}

export default function AnalysisResults({
  analysis,
  industryOptions = [],
  onAnalyzeAgain,
  onUploadNew,
  className = '',
  elapsedTime = 0
}: AnalysisResultsProps) {
  const result = analysis.result

  // Empty state
  if (!result) {
    return (
      <Card className={`border-2 border-gray-300 ${className}`}>
        <CardContent className="p-6 text-center">
          <p className="text-gray-500">閲覧可能な分析結果がありません</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overview Domain: Overall scores and summary */}
      <AnalysisOverview
        analysis={analysis}
        industryOptions={industryOptions}
        elapsedTime={elapsedTime}
      />

      {/* Structure Domain: Resume quality and formatting */}
      <StructureAnalysisCard analysis={analysis} />

      {/* Appeal Domain: Industry-specific evaluation */}
      <AppealAnalysisCard analysis={analysis} />

      {/* Action Buttons: Conditional rendering based on handlers */}
      <AnalysisActionButtons
        onAnalyzeAgain={onAnalyzeAgain}
        onUploadNew={onUploadNew}
      />
    </div>
  )
}
