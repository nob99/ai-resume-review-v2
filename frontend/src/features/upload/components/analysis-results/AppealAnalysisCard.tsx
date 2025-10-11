'use client'

import React from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui'
import { BaseAnalysisCardProps } from './types'
import { getAppealFeedback } from '@/features/upload/utils/analysisParser'
import ScoreBar from './ScoreBar'
import FeedbackItemCard from './FeedbackItemCard'

/**
 * AppealAnalysisCard Component
 * Domain: Industry-specific appeal and competitive positioning
 * Displays achievement relevance, skills alignment, experience fit, and competitive positioning
 */

export default function AppealAnalysisCard({ analysis, className = '' }: BaseAnalysisCardProps) {
  const appealFeedback = getAppealFeedback(analysis)
  const appealScores = analysis.result?.detailed_scores?.appeal_analysis?.scores

  // Don't render if no appeal data
  if (!appealFeedback || !appealScores) {
    return null
  }

  // Category order for appeal analysis: scr_framework → quantitative_impact → appeal_point
  const categoryOrder: Record<string, number> = {
    scr_framework: 1,
    quantitative_impact: 2,
    appeal_point: 3
  }

  const sortedFeedback = appealFeedback.specific_feedback
    ? [...appealFeedback.specific_feedback].sort(
        (a, b) => (categoryOrder[a.category] || 99) - (categoryOrder[b.category] || 99)
      )
    : []

  return (
    <Card className={`border-2 border-purple-300 ${className}`}>
      <CardHeader className="bg-purple-50">
        <h2 className="text-xl font-bold text-neutral-900 flex items-center">
          <span className="text-2xl mr-2">🎯</span>
          業界魅力分析
        </h2>
      </CardHeader>
      <CardContent className="p-6 space-y-6">
        {/* 4 Appeal Scores */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">📊 4つのスコア / Scores</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ScoreBar label="成果関連性" score={appealScores.achievement_relevance} />
            <ScoreBar label="スキル整合性" score={appealScores.skills_alignment} />
            <ScoreBar label="経験適合性" score={appealScores.experience_fit} />
            <ScoreBar label="競合優位性" score={appealScores.competitive_positioning} />
          </div>
        </div>

        {/* Strengths */}
        {appealFeedback.strengths && appealFeedback.strengths.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center">
              <span className="mr-2">✅</span>
              強み / Strengths ({appealFeedback.strengths.length})
            </h3>
            <ul className="space-y-2">
              {appealFeedback.strengths.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-sm">
                  <span className="text-green-500 mt-1">•</span>
                  <span className="text-gray-700">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Improvement Areas */}
        {appealFeedback.improvement_areas && appealFeedback.improvement_areas.length > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-orange-700 mb-3 flex items-center">
              <span className="mr-2">⚠️</span>
              改善点 / Improvement Areas ({appealFeedback.improvement_areas.length})
            </h3>
            <ul className="space-y-2">
              {appealFeedback.improvement_areas.map((item, idx) => (
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
              具体的なフィードバック / Specific Feedback ({sortedFeedback.length})
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
