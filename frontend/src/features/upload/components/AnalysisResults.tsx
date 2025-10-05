'use client'

import React from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui'
import { AnalysisStatusResponse } from '@/types'
import { parseAIFeedback, formatMarketTier } from '../utils/analysisParser'
import FeedbackSection from './FeedbackSection'
import DetailedScores from './DetailedScores'

interface AnalysisResultsProps {
  analysis: AnalysisStatusResponse
  industryOptions: Array<{ value: string; label: string }>
  onAnalyzeAgain: () => void
  onUploadNew: () => void
  className?: string
}

export default function AnalysisResults({
  analysis,
  industryOptions,
  onAnalyzeAgain,
  onUploadNew,
  className = ''
}: AnalysisResultsProps) {
  const result = analysis.result
  const feedback = parseAIFeedback(analysis)

  if (!result) {
    return (
      <Card className={`border-2 border-gray-300 ${className}`}>
        <CardContent className="p-6 text-center">
          <p className="text-gray-500">閲覧可能な分析結果がありません / No analysis result available</p>
        </CardContent>
      </Card>
    )
  }

  if (!feedback) {
    return (
      <Card className={`border-2 border-yellow-300 ${className}`}>
        <CardHeader className="bg-yellow-50">
          <h2 className="text-xl font-bold text-neutral-900">AI分析結果 / Analysis Results (Basic View)</h2>
        </CardHeader>
        <CardContent className="p-6">
          <div className="text-center">
            <div className="text-4xl font-bold text-primary-600 mb-2">
              {result.overall_score}/100
            </div>
            <div className="text-sm text-neutral-600 mb-4">全体スコア / Overall Score</div>
            {result.executive_summary && (
              <div className="mt-4">
                <h3 className="font-semibold text-neutral-900 mb-2">要約 / Summary</h3>
                <p className="text-neutral-700">{result.executive_summary}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Overall Summary */}
      <Card className="border-2 border-green-500">
        <CardHeader className="bg-green-50">
          <h2 className="text-xl font-bold text-neutral-900 flex items-center">
            <span className="text-2xl mr-2">🎯</span>
            AI分析結果 / AI Resume Analysis Results
          </h2>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Main Scores Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary-600">
                {result.overall_score}/100
              </div>
              <div className="text-sm text-neutral-600">全体スコア / Overall Score</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-semibold text-blue-600">
                {result.ats_score}/100
              </div>
              <div className="text-sm text-neutral-600">ATS互換性 / ATS Compatibility</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-semibold text-purple-600">
                {result.content_score}/100
              </div>
              <div className="text-sm text-neutral-600">記載内容の品質 / Content Quality</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-semibold text-orange-600">
                {result.formatting_score}/100
              </div>
              <div className="text-sm text-neutral-600">フォーマット / Formatting</div>
            </div>
          </div>

          {/* Industry and Market Tier */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-200">
            <div className="text-center">
              <div className="text-lg font-semibold text-neutral-900">
                {industryOptions.find(i => i.value === result.industry)?.label || result.industry}
              </div>
              <div className="text-sm text-neutral-600">対象業界 / Target Industry</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-neutral-900">
                {formatMarketTier(feedback.marketTier)}
              </div>
              <div className="text-sm text-neutral-600">マーケットにおける位置づけ / Market Tier</div>
            </div>
          </div>

          {/* Executive Summary */}
          {result.executive_summary && (
            <div className="pt-4 border-t border-gray-200">
              <h3 className="font-semibold text-neutral-900 mb-3 flex items-center">
                <span className="text-lg mr-2">📋</span>
                要約 / Executive Summary
              </h3>
              <p className="text-neutral-700 leading-relaxed">{result.executive_summary}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* スコア詳細 / Detailed Score Breakdown */}
      <DetailedScores
        structureScores={feedback.structureScores}
        appealScores={feedback.appealScores}
      />

      {/* フィードバックセクション / Feedback Sections Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Issues Found */}
        <FeedbackSection
          title="問題点 / Issues Found"
          items={feedback.issues}
          type="issues"
          icon="⚠️"
        />

        {/* Recommendations */}
        <FeedbackSection
          title="推奨事項 / Recommendations"
          items={feedback.recommendations}
          type="recommendations"
          icon="💡"
        />

        {/* 不足しているセクション / Missing Sections */}
        <FeedbackSection
          title="不足しているセクション / Missing Sections"
          items={feedback.missingSection}
          type="missing"
          icon="❌"
        />

        {/* 強み / Strengths */}
        <FeedbackSection
          title="強み / Strengths"
          items={feedback.strengths}
          type="strengths"
          icon="✅"
        />
      </div>

      {/* スキル分析セクション / Skills Analysis Section */}
      <Card>
        <CardHeader>
          <h3 className="text-xl font-semibold text-neutral-900 flex items-center">
            <span className="text-2xl mr-2">🎯</span>
            スキル & 業界分析 / Skills & Industry Analysis
          </h3>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 関連する成果 / Relevant Achievements */}
            <FeedbackSection
              title="関連する成果 / Relevant Achievements"
              items={feedback.relevantAchievements}
              type="achievements"
              icon="🏆"
              className="border-0 shadow-none"
            />

            {/* 不足しているスキル / Missing Skills */}
            <FeedbackSection
              title="不足しているスキル / Missing Skills"
              items={feedback.missingSkills}
              type="skills"
              icon="🎓"
              className="border-0 shadow-none"
            />

            {/* 競合優位性 / Competitive Advantages */}
            <FeedbackSection
              title="競合優位性 / Competitive Advantages"
              items={feedback.competitiveAdvantages}
              type="advantages"
              icon="⭐"
              className="border-0 shadow-none"
            />

            {/* 改善点 / Improvement Areas */}
            <FeedbackSection
              title="改善点 / Priority Improvements"
              items={feedback.improvementAreas}
              type="improvements"
              icon="🔧"
              className="border-0 shadow-none"
            />
          </div>

          {/* 転職先でも発揮できる経験値 / Transferable Experience */}
          {feedback.transferableExperience.length > 0 && (
            <div className="pt-4 border-t border-gray-200">
              <FeedbackSection
                title="転職先でも発揮できる経験値 / Transferable Experience"
                items={feedback.transferableExperience}
                type="advantages"
                icon="🔄"
                className="border-0 shadow-none"
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* レジュメメタデータ / Resume Metadata */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-neutral-900 flex items-center">
            <span className="text-xl mr-2">📄</span>
            Resume Statistics
          </h3>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">{feedback.metadata.total_sections}</div>
              <div className="text-sm text-gray-500">セクション数 / Total Sections</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">{feedback.metadata.word_count}</div>
              <div className="text-sm text-gray-500">単語数 / Word Count</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">{feedback.metadata.reading_time}min</div>
              <div className="text-sm text-gray-500">読み時間 / Reading Time</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* アクションボタン / Action Buttons */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={onAnalyzeAgain}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
            >
              Analyze Different Industry / 異なる業界で分析
            </button>
            <button
              onClick={onUploadNew}
              className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-md font-medium transition-colors"
            >
              Upload New Resume / 新しいレジュメをアップロード
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}