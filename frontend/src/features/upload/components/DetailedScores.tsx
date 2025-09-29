'use client'

import React from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui'
import { StructureScores, AppealScores } from '@/types'
import { formatScore, getScoreColor, getScoreBarColor } from '../utils/analysisParser'

interface DetailedScoresProps {
  structureScores: StructureScores
  appealScores: AppealScores
  className?: string
}

interface ScoreItemProps {
  label: string
  score: number
  description?: string
}

function ScoreItem({ label, score, description }: ScoreItemProps) {
  const scoreColor = getScoreColor(score)
  const barColor = getScoreBarColor(score)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-medium text-neutral-700">{label}</span>
          {description && (
            <p className="text-xs text-neutral-500 mt-1">{description}</p>
          )}
        </div>
        <span className={`text-lg font-bold ${scoreColor}`}>
          {formatScore(score)}/100
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${barColor} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  )
}

export default function DetailedScores({
  structureScores,
  appealScores,
  className = ''
}: DetailedScoresProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <h3 className="text-xl font-semibold text-neutral-900 flex items-center">
          <span className="text-2xl mr-2">📊</span>
          Detailed Score Breakdown
        </h3>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Structure Analysis Scores */}
        <div>
          <h4 className="text-lg font-medium text-neutral-800 mb-4 flex items-center">
            <span className="text-xl mr-2">🏗️</span>
            Resume Structure Analysis
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ScoreItem
              label="Format"
              score={structureScores.format}
              description="Professional formatting and layout"
            />
            <ScoreItem
              label="Organization"
              score={structureScores.organization}
              description="Logical flow and section structure"
            />
            <ScoreItem
              label="Tone"
              score={structureScores.tone}
              description="Professional language and style"
            />
            <ScoreItem
              label="Completeness"
              score={structureScores.completeness}
              description="Required sections and information"
            />
          </div>
        </div>

        {/* Appeal Analysis Scores */}
        <div className="pt-6 border-t border-gray-200">
          <h4 className="text-lg font-medium text-neutral-800 mb-4 flex items-center">
            <span className="text-xl mr-2">🎯</span>
            Industry Appeal Analysis
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ScoreItem
              label="Achievement Relevance"
              score={appealScores.achievement_relevance}
              description="How well achievements align with industry"
            />
            <ScoreItem
              label="Skills Alignment"
              score={appealScores.skills_alignment}
              description="Match with required skills for industry"
            />
            <ScoreItem
              label="Experience Fit"
              score={appealScores.experience_fit}
              description="Relevance of work experience"
            />
            <ScoreItem
              label="Competitive Positioning"
              score={appealScores.competitive_positioning}
              description="Differentiation from other candidates"
            />
          </div>
        </div>

        {/* Average Scores Summary */}
        <div className="pt-6 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {formatScore((structureScores.format + structureScores.organization + structureScores.tone + structureScores.completeness) / 4)}/100
              </div>
              <div className="text-sm text-blue-700 font-medium">Structure Average</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">
                {formatScore((appealScores.achievement_relevance + appealScores.skills_alignment + appealScores.experience_fit + appealScores.competitive_positioning) / 4)}/100
              </div>
              <div className="text-sm text-purple-700 font-medium">Appeal Average</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}