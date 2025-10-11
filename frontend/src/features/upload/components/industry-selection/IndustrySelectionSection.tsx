'use client'

import React from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui'
import IndustrySelector from './IndustrySelector'

/**
 * IndustrySelectionSection Component
 * Main section component for Step 3: Industry Selection & Analysis
 * Wraps IndustrySelector with proper card layout
 */

interface IndustrySelectionSectionProps {
  selectedIndustry: string
  onIndustryChange: (industry: string) => void
  onStartAnalysis: () => Promise<void>
  isAnalyzing: boolean
  analysisStatus: string
  industryOptions: Array<{ value: string; label: string }>
  elapsedTime: number
  disabled: boolean
  hasResults?: boolean
}

export default function IndustrySelectionSection({
  selectedIndustry,
  onIndustryChange,
  onStartAnalysis,
  isAnalyzing,
  analysisStatus,
  industryOptions,
  elapsedTime,
  disabled,
  hasResults = false
}: IndustrySelectionSectionProps) {
  return (
    <Card className={disabled ? 'opacity-60' : ''}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-neutral-900">
            Step 3: 応募する業界の選択 & AI分析
          </h2>
          {disabled && (
            <span className="text-sm text-neutral-500 bg-neutral-100 px-3 py-1 rounded-full">
              Step 2を完了してください
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        {disabled ? (
          <div className="p-8 text-center bg-neutral-50 rounded-lg border-2 border-dashed border-neutral-200">
            <div className="text-4xl mb-3">📊</div>
            <p className="text-neutral-600 font-medium mb-1">
              業界の選択
            </p>
            <p className="text-sm text-neutral-500">
              レジュメをアップロードしてStep 2を完了してください
            </p>
          </div>
        ) : (
          <IndustrySelector
            selectedIndustry={selectedIndustry}
            onIndustryChange={onIndustryChange}
            onStartAnalysis={onStartAnalysis}
            isAnalyzing={isAnalyzing}
            analysisStatus={analysisStatus}
            industryOptions={industryOptions}
            elapsedTime={elapsedTime}
            disabled={hasResults}
          />
        )}
      </CardContent>
    </Card>
  )
}
