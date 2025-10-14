'use client'

import React from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui'
import { BaseAnalysisCardProps } from './shared/types'
import { getStructureFeedback } from '@/features/upload/utils/analysisParser'
import ScoreBar from './shared/ScoreBar'
import FeedbackItemCard from './shared/FeedbackItemCard'

/**
 * StructureAnalysisCard Component
 * Domain: Resume structure and quality
 * Displays format, organization, tone, and completeness scores with feedback
 */

export default function StructureAnalysisCard({ analysis, className = '' }: BaseAnalysisCardProps) {
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

  return (
    <Card className={`border-2 border-blue-300 ${className}`}>
      <CardHeader className="bg-blue-50">
        <h2 className="text-xl font-bold text-neutral-900 flex items-center">
          <span className="text-2xl mr-2">🏗️</span>
          レジュメ構造分析
        </h2>
      </CardHeader>
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
            <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center">
              <span className="mr-2">✅</span>
              強み ({structureFeedback.strengths.length})
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
            <h3 className="text-sm font-semibold text-orange-700 mb-3 flex items-center">
              <span className="mr-2">⚠️</span>
              改善点 ({structureFeedback.improvement_areas.length})
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
            <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📝</span>
              具体的なフィードバック ({sortedFeedback.length})
            </h3>
            <div className="space-y-3">
              {sortedFeedback.map((item, idx) => (
                <FeedbackItemCard key={idx} item={item} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
