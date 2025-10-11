'use client'

import React from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui'
import { AnalysisStatusResponse, SpecificFeedbackItem } from '@/types'
import { getStructureFeedback, getAppealFeedback, formatScore, getScoreColor, getScoreBarColor, formatMarketTier } from '../utils/analysisParser'

interface AnalysisResultsProps {
  analysis: AnalysisStatusResponse
  industryOptions?: Array<{ value: string; label: string }>
  onAnalyzeAgain?: () => void
  onUploadNew?: () => void
  className?: string
  elapsedTime?: number
}

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

/**
 * Get category icon and color for specific feedback items
 */
function getCategoryStyle(category: string) {
  const styles = {
    grammar: { icon: '📝', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
    structure: { icon: '🏗️', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200' },
    scr_framework: { icon: '📖', color: 'text-purple-600', bg: 'bg-purple-50', border: 'border-purple-200' },
    quantitative_impact: { icon: '📊', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
    appeal_point: { icon: '🎯', color: 'text-indigo-600', bg: 'bg-indigo-50', border: 'border-indigo-200' },
  }
  return styles[category as keyof typeof styles] || { icon: '💡', color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' }
}

/**
 * Specific Feedback Item Component
 */
function FeedbackItemCard({ item }: { item: SpecificFeedbackItem }) {
  const style = getCategoryStyle(item.category)

  return (
    <div className={`p-4 rounded-lg border-l-4 ${style.border} ${style.bg}`}>
      <div className="flex items-start space-x-3">
        <span className="text-2xl flex-shrink-0">{style.icon}</span>
        <div className="flex-1 space-y-2">
          <div className={`text-xs font-bold uppercase tracking-wide ${style.color}`}>
            {item.category.replace('_', ' ')}
          </div>
          {item.target_text && (
            <div className="text-sm text-gray-700 bg-white p-2 rounded border border-gray-200">
              <span className="font-medium">対象テキスト:</span> "{item.target_text}"
            </div>
          )}
          <div className="text-sm">
            <span className="font-semibold text-gray-900">改善点:</span>
            <p className="text-gray-700 mt-1">{item.issue}</p>
          </div>
          <div className="text-sm">
            <span className="font-semibold text-gray-900">提案:</span>
            <p className="text-gray-700 mt-1">{item.suggestion}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Score Bar Component
 */
function ScoreBar({ label, score }: { label: string; score: number }) {
  const scoreColor = getScoreColor(score)
  const barColor = getScoreBarColor(score)

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-lg font-bold ${scoreColor}`}>{formatScore(score)}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`${barColor} h-2 rounded-full transition-all`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
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
  const structureFeedback = getStructureFeedback(analysis)
  const appealFeedback = getAppealFeedback(analysis)

  if (!result) {
    return (
      <Card className={`border-2 border-gray-300 ${className}`}>
        <CardContent className="p-6 text-center">
          <p className="text-gray-500">閲覧可能な分析結果がありません</p>
        </CardContent>
      </Card>
    )
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
    <div className={`space-y-6 ${className}`}>
      {/* Card 1: Summary */}
      <Card className="border-2 border-green-500">
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

      {/* Card 2: Structure Analysis */}
      {structureFeedback && structureScores && (
        <Card className="border-2 border-blue-300">
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
            {structureFeedback.specific_feedback && structureFeedback.specific_feedback.length > 0 && (
              <div className="pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">📝</span>
                  具体的なフィードバック ({structureFeedback.specific_feedback.length})
                </h3>
                <div className="space-y-3">
                  {(() => {
                    // Structure Analysis category order: grammar → structure
                    const categoryOrder: Record<string, number> = {
                      grammar: 1,
                      structure: 2
                    }
                    const sortedFeedback = [...structureFeedback.specific_feedback].sort(
                      (a, b) => (categoryOrder[a.category] || 99) - (categoryOrder[b.category] || 99)
                    )
                    return sortedFeedback.map((item, idx) => (
                      <FeedbackItemCard key={idx} item={item} />
                    ))
                  })()}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Card 3: Appeal Analysis */}
      {appealFeedback && appealScores && (
        <Card className="border-2 border-purple-300">
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
            {appealFeedback.specific_feedback && appealFeedback.specific_feedback.length > 0 && (
              <div className="pt-4 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center">
                  <span className="mr-2">📝</span>
                  具体的なフィードバック / Specific Feedback ({appealFeedback.specific_feedback.length})
                </h3>
                <div className="space-y-3">
                  {(() => {
                    // Appeal Analysis category order: scr_framework → quantitative_impact → appeal_point
                    const categoryOrder: Record<string, number> = {
                      scr_framework: 1,
                      quantitative_impact: 2,
                      appeal_point: 3
                    }
                    const sortedFeedback = [...appealFeedback.specific_feedback].sort(
                      (a, b) => (categoryOrder[a.category] || 99) - (categoryOrder[b.category] || 99)
                    )
                    return sortedFeedback.map((item, idx) => (
                      <FeedbackItemCard key={idx} item={item} />
                    ))
                  })()}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      {(onAnalyzeAgain || onUploadNew) && (
        <Card>
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
      )}
    </div>
  )
}
