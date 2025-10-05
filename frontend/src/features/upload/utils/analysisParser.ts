import { AnalysisStatusResponse, ParsedAIFeedback, StructureFeedback, AppealFeedback } from '@/types'

/**
 * Parse the detailed_scores from API response into a more usable format
 * Supports both v1.1 (specific_feedback) and v1.0 (deprecated fields) formats
 */
export function parseAIFeedback(analysisResult: AnalysisStatusResponse): ParsedAIFeedback | null {
  const detailedScores = analysisResult.result?.detailed_scores

  if (!detailedScores) return null

  const structureFeedback = detailedScores.structure_analysis?.feedback as StructureFeedback
  const appealFeedback = detailedScores.appeal_analysis?.feedback as AppealFeedback

  return {
    // V1.0: Structure feedback (deprecated, kept for backward compatibility)
    issues: structureFeedback?.issues || [],
    recommendations: structureFeedback?.recommendations || [],
    missingSection: structureFeedback?.missing_sections || [],
    strengths: structureFeedback?.strengths || [],

    // V1.0: Appeal feedback (deprecated, kept for backward compatibility)
    relevantAchievements: appealFeedback?.relevant_achievements || [],
    missingSkills: appealFeedback?.missing_skills || [],
    competitiveAdvantages: appealFeedback?.competitive_advantages || [],
    improvementAreas: appealFeedback?.improvement_areas || [],
    transferableExperience: appealFeedback?.transferable_experience || [],

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
 * Get structure feedback in v1.1 format (two-level feedback with specific items)
 */
export function getStructureFeedback(analysisResult: AnalysisStatusResponse): StructureFeedback | null {
  const structureFeedback = analysisResult.result?.detailed_scores?.structure_analysis?.feedback as StructureFeedback
  return structureFeedback || null
}

/**
 * Get appeal feedback in v1.1 format (two-level feedback with specific items)
 */
export function getAppealFeedback(analysisResult: AnalysisStatusResponse): AppealFeedback | null {
  const appealFeedback = analysisResult.result?.detailed_scores?.appeal_analysis?.feedback as AppealFeedback
  return appealFeedback || null
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