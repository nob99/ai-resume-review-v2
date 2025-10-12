'use client'

import React, { useState } from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui'
import { BaseAnalysisCardProps } from './types'
import { getStructureFeedback } from '@/features/upload/utils/analysisParser'
import ScoreBar from './ScoreBar'
import FeedbackItemCard from './FeedbackItemCard'
import CopyButton from './CopyButton'
import { formatStructureCard, formatListSection, formatAllFeedback } from '@/features/upload/utils/copyFormatters'

/**
 * StructureAnalysisCard Component
 * Domain: Resume structure and quality
 * Displays format, organization, tone, and completeness scores with feedback
 */

export default function StructureAnalysisCard({ analysis, className = '' }: BaseAnalysisCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const structureFeedback = getStructureFeedback(analysis)
  const structureScores = analysis.result?.detailed_scores?.structure_analysis?.scores

  // Don't render if no structure data
  if (!structureFeedback || !structureScores) {
    return null
  }

  // Category order for structure analysis: grammar → structure
  const categoryOrder: Record<string, number> = {
    grammar: 1,
    structure: 2
  }

  const sortedFeedback = structureFeedback.specific_feedback
    ? [...structureFeedback.specific_feedback].sort(
        (a, b) => (categoryOrder[a.category] || 99) - (categoryOrder[b.category] || 99)
      )
    : []

  const handleToggle = () => {
    setIsExpanded(!isExpanded)
  }

  return (
    <Card className={`border-2 border-blue-300 ${className}`}>
      <CardHeader
        className="bg-blue-50 cursor-pointer hover:bg-blue-100 transition-colors"
        onClick={handleToggle}
      >
        <h2 className="text-xl font-bold text-neutral-900 flex items-center justify-between">
          <span className="flex items-center">
            <span className="mr-3 text-gray-600">
              {isExpanded ? '▼' : '▶'}
            </span>
            <span className="text-2xl mr-2">🏗️</span>
            レジュメ構造分析
          </span>
          <CopyButton
            text={formatStructureCard(analysis)}
            variant="text"
            size="sm"
            label="Copy All"
            className="relative z-10"
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          />
        </h2>
      </CardHeader>
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          isExpanded ? 'max-h-[10000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <CardContent className="p-6 space-y-6">
        {/* 4 Structure Scores */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">📊 4つのスコア / Scores</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ScoreBar label="フォーマット" score={structureScores.format} />
            <ScoreBar label="整理" score={structureScores.organization} />
            <ScoreBar label="トーン" score={structureScores.tone} />
            <ScoreBar label="完全性" score={structureScores.completeness} />
          </div>
        </div>

        {/* Strengths */}
        {structureFeedback.strengths && structureFeedback.strengths.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center justify-between">
              <span className="flex items-center">
                <span className="mr-2">✅</span>
                強み ({structureFeedback.strengths.length})
              </span>
              <CopyButton
                text={formatListSection('✅ 強み / Strengths', structureFeedback.strengths)}
                variant="text"
                size="sm"
                label="Copy Section"
              />
            </h3>
            <ul className="space-y-2">
              {structureFeedback.strengths.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-sm">
                  <span className="text-green-500 mt-1">•</span>
                  <span className="text-gray-700">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Improvement Areas */}
        {structureFeedback.improvement_areas && structureFeedback.improvement_areas.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-orange-700 mb-3 flex items-center justify-between">
              <span className="flex items-center">
                <span className="mr-2">⚠️</span>
                改善点 ({structureFeedback.improvement_areas.length})
              </span>
              <CopyButton
                text={formatListSection('⚠️ 改善点 / Improvement Areas', structureFeedback.improvement_areas)}
                variant="text"
                size="sm"
                label="Copy Section"
              />
            </h3>
            <ul className="space-y-2">
              {structureFeedback.improvement_areas.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-sm">
                  <span className="text-orange-500 mt-1">•</span>
                  <span className="text-gray-700">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Specific Feedback */}
        {sortedFeedback.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center justify-between">
              <span className="flex items-center">
                <span className="mr-2">📝</span>
                具体的なフィードバック ({sortedFeedback.length})
              </span>
              <CopyButton
                text={formatAllFeedback(sortedFeedback)}
                variant="text"
                size="sm"
                label="Copy All"
              />
            </h3>
            <div className="space-y-3">
              {sortedFeedback.map((item, idx) => (
                <FeedbackItemCard key={idx} item={item} />
              ))}
            </div>
          </div>
        )}
        </CardContent>
      </div>
    </Card>
  )
}
