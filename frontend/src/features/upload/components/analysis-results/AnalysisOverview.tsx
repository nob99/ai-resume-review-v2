'use client'

import React from 'react'
import { Card, CardHeader, CardContent } from '@/components/ui'
import { AnalysisOverviewProps } from './types'
import { formatScore, formatMarketTier } from '@/features/upload/utils/analysisParser'

/**
 * AnalysisOverview Component
 * Domain: High-level assessment and summary
 * Displays overall scores, averages, executive summary, and metadata
 */

/**
 * Format milliseconds to human-readable time
 */
function formatElapsedTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  if (minutes > 0) {
    return `${minutes}分${seconds}秒 / ${minutes}m ${seconds}s`
  }
  return `${seconds}秒 / ${seconds}s`
}

export default function AnalysisOverview({
  analysis,
  industryOptions = [],
  elapsedTime = 0,
  className = ''
}: AnalysisOverviewProps) {
  const result = analysis.result

  if (!result) {
    return null
  }

  const detailedScores = result.detailed_scores
  const structureScores = detailedScores?.structure_analysis?.scores
  const appealScores = detailedScores?.appeal_analysis?.scores
  const metadata = detailedScores?.structure_analysis?.metadata
  const marketTier = detailedScores?.market_tier || 'unknown'

  // Calculate averages
  const structureAvg = structureScores
    ? (structureScores.format + structureScores.organization + structureScores.tone + structureScores.completeness) / 4
    : 0
  const appealAvg = appealScores
    ? (appealScores.achievement_relevance + appealScores.skills_alignment + appealScores.experience_fit + appealScores.competitive_positioning) / 4
    : 0

  return (
    <Card className={`border-2 border-green-500 ${className}`}>
      <CardHeader className="bg-green-50">
        <h2 className="text-xl font-bold text-neutral-900 flex items-center">
          <span className="text-2xl mr-2">🎯</span>
          AI分析結果
        </h2>
      </CardHeader>
      <CardContent className="p-6 space-y-6">
        {/* Main Scores Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-primary-50 rounded-lg">
            <div className="text-3xl font-bold text-primary-600">{formatScore(result.overall_score)}</div>
            <div className="text-xs text-gray-600 mt-1">総合</div>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <div className="text-3xl font-bold text-blue-600">{formatScore(structureAvg)}</div>
            <div className="text-xs text-gray-600 mt-1">基本構造</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-3xl font-bold text-purple-600">{formatScore(appealAvg)}</div>
            <div className="text-xs text-gray-600 mt-1">魅力の伝わりやすさ</div>
          </div>
          <div className="text-center p-4 bg-amber-50 rounded-lg">
            <div className="text-lg font-bold text-amber-700 uppercase">{formatMarketTier(marketTier)}</div>
            <div className="text-xs text-gray-600 mt-1">ティア(参考)</div>
          </div>
        </div>

        {/* Executive Summary */}
        {result.executive_summary && (
          <div className="pt-4 border-t border-gray-200">
            <h3 className="font-semibold text-neutral-900 mb-3 flex items-center">
              <span className="text-lg mr-2">📋</span>
              サマリ
            </h3>
            <p className="text-neutral-700 leading-relaxed bg-gray-50 p-4 rounded-lg">{result.executive_summary}</p>
          </div>
        )}

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200 text-sm">
          <div className="text-center">
            <div className="font-semibold text-gray-900">
              {industryOptions.find(i => i.value === result.industry)?.label || result.industry}
            </div>
            <div className="text-xs text-gray-500">業界</div>
          </div>
          {metadata && (
            <>
              <div className="text-center">
                <div className="font-semibold text-gray-900">{metadata.total_sections}</div>
                <div className="text-xs text-gray-500">セクション</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-gray-900">{metadata.word_count}</div>
                <div className="text-xs text-gray-500">単語数</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-gray-900">{metadata.reading_time}min</div>
                <div className="text-xs text-gray-500">読了時間</div>
              </div>
            </>
          )}
          {elapsedTime > 0 && (
            <div className="text-center col-span-2 md:col-span-4">
              <div className="font-semibold text-green-600">{formatElapsedTime(elapsedTime)}</div>
              <div className="text-xs text-gray-500">処理時間</div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
