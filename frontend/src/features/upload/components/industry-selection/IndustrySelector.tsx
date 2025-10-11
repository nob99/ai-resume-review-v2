'use client'

import React from 'react'
import { Button } from '@/components/ui'
import { IndustryOption } from '../types'
import AnalysisTimer from './AnalysisTimer'

export interface IndustrySelectorProps {
  selectedIndustry: string
  onIndustryChange: (industry: string) => void
  onStartAnalysis: () => void
  isAnalyzing: boolean
  analysisStatus: string
  industryOptions: IndustryOption[]
  disabled?: boolean
  elapsedTime?: number
}

/**
 * Industry Selector Component
 * Allows selection of industry for resume analysis
 */
const IndustrySelector: React.FC<IndustrySelectorProps> = ({
  selectedIndustry,
  onIndustryChange,
  onStartAnalysis,
  isAnalyzing,
  analysisStatus,
  industryOptions,
  disabled = false,
  elapsedTime = 0
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <select
          value={selectedIndustry}
          onChange={(e) => onIndustryChange(e.target.value)}
          className="flex-1 p-3 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500"
          disabled={isAnalyzing || disabled}
        >
          <option value="">Select Industry...</option>
          {industryOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Button
          size="lg"
          onClick={onStartAnalysis}
          disabled={!selectedIndustry || isAnalyzing || disabled}
          className="bg-green-600 hover:bg-green-700 text-white"
        >
          {isAnalyzing ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
              {analysisStatus === 'processing' ? 'AIが分析中...' : '分析依頼中...'}
            </>
          ) : (
            '分析開始'
          )}
        </Button>
      </div>

      {/* Timer display when analyzing */}
      {isAnalyzing && (
        <AnalysisTimer
          elapsedTime={elapsedTime}
          isAnalyzing={isAnalyzing}
          status={analysisStatus}
        />
      )}
    </div>
  )
}

export default IndustrySelector