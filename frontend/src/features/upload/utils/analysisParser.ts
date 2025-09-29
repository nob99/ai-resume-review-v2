import { AnalysisStatusResponse, ParsedAIFeedback } from '../types'

/**
 * Parse the detailed_scores from API response into a more usable format
 */
export function parseAIFeedback(analysisResult: AnalysisStatusResponse): ParsedAIFeedback | null {
  const detailedScores = analysisResult.result?.detailed_scores

  if (!detailedScores) return null

  return {
    // Structure feedback
    issues: detailedScores.structure_analysis?.feedback?.issues || [],
    recommendations: detailedScores.structure_analysis?.feedback?.recommendations || [],
    missingSection: detailedScores.structure_analysis?.feedback?.missing_sections || [],
    strengths: detailedScores.structure_analysis?.feedback?.strengths || [],

    // Appeal feedback
    relevantAchievements: detailedScores.appeal_analysis?.feedback?.relevant_achievements || [],
    missingSkills: detailedScores.appeal_analysis?.feedback?.missing_skills || [],
    competitiveAdvantages: detailedScores.appeal_analysis?.feedback?.competitive_advantages || [],
    improvementAreas: detailedScores.appeal_analysis?.feedback?.improvement_areas || [],
    transferableExperience: detailedScores.appeal_analysis?.feedback?.transferable_experience || [],

    // Detailed scores
    structureScores: detailedScores.structure_analysis?.scores || {
      format: 0,
      organization: 0,
      tone: 0,
      completeness: 0
    },
    appealScores: detailedScores.appeal_analysis?.scores || {
      achievement_relevance: 0,
      skills_alignment: 0,
      experience_fit: 0,
      competitive_positioning: 0
    },

    // Metadata
    marketTier: detailedScores.market_tier || 'unknown',
    metadata: detailedScores.structure_analysis?.metadata || {
      total_sections: 0,
      word_count: 0,
      reading_time: 0
    }
  }
}

/**
 * Format score for display (0-100 range)
 */
export function formatScore(score: number): string {
  return Math.round(score).toString()
}

/**
 * Get color class for score (for styling)
 */
export function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  if (score >= 40) return 'text-orange-600'
  return 'text-red-600'
}

/**
 * Get progress bar color for score
 */
export function getScoreBarColor(score: number): string {
  if (score >= 80) return 'bg-green-500'
  if (score >= 60) return 'bg-yellow-500'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-red-500'
}

/**
 * Format market tier for display
 */
export function formatMarketTier(tier: string): string {
  return tier?.replace('_', ' ').toUpperCase() || 'UNKNOWN'
}