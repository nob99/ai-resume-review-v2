import { AnalysisStatusResponse, SpecificFeedbackItem } from '@/types'
import { getStructureFeedback, getAppealFeedback } from './analysisParser'

/**
 * Copy Formatters
 * Pure functions to format analysis data for clipboard copy
 * Outputs clean, readable plain text
 */

/**
 * Format executive summary for copying
 */
export function formatExecutiveSummary(summary: string): string {
  return `=== サマリ / Summary ===\n${summary}`
}

/**
 * Format a list section (strengths, improvements, etc.)
 */
export function formatListSection(title: string, items: string[]): string {
  if (!items || items.length === 0) return ''

  const formattedItems = items.map(item => `• ${item}`).join('\n')
  return `=== ${title} (${items.length}) ===\n${formattedItems}`
}

/**
 * Format a single specific feedback item
 */
export function formatFeedbackItem(item: SpecificFeedbackItem): string {
  const categoryLabels: Record<string, string> = {
    grammar: '体言止め/文法',
    structure: '基本構造',
    scr_framework: 'SCRフレームワーク',
    quantitative_impact: '定量的インパクト',
    appeal_point: 'アピールポイント'
  }

  const categoryLabel = categoryLabels[item.category] || item.category
  const parts = [`[${categoryLabel}]`]

  if (item.target_text) {
    parts.push(`対象テキスト: "${item.target_text}"`)
  }

  parts.push(`改善点: ${item.issue}`)
  parts.push(`提案: ${item.suggestion}`)

  return parts.join('\n')
}

/**
 * Format all specific feedback items
 */
export function formatAllFeedback(items: SpecificFeedbackItem[]): string {
  if (!items || items.length === 0) return ''

  const formattedItems = items.map((item, idx) => {
    const itemText = formatFeedbackItem(item)
    return `${idx + 1}. ${itemText}`
  }).join('\n\n')

  return `=== 具体的なフィードバック / Specific Feedback (${items.length}) ===\n${formattedItems}`
}

/**
 * Format structure scores
 */
function formatStructureScores(analysis: AnalysisStatusResponse): string {
  const scores = analysis.result?.detailed_scores?.structure_analysis?.scores
  if (!scores) return ''

  return `=== 4つのスコア / Scores ===
フォーマット / Format: ${scores.format.toFixed(1)}
整理 / Organization: ${scores.organization.toFixed(1)}
トーン / Tone: ${scores.tone.toFixed(1)}
完全性 / Completeness: ${scores.completeness.toFixed(1)}`
}

/**
 * Format appeal scores
 */
function formatAppealScores(analysis: AnalysisStatusResponse): string {
  const scores = analysis.result?.detailed_scores?.appeal_analysis?.scores
  if (!scores) return ''

  return `=== 4つのスコア / Scores ===
成果関連性 / Achievement Relevance: ${scores.achievement_relevance.toFixed(1)}
スキル整合性 / Skills Alignment: ${scores.skills_alignment.toFixed(1)}
経験適合性 / Experience Fit: ${scores.experience_fit.toFixed(1)}
競合優位性 / Competitive Positioning: ${scores.competitive_positioning.toFixed(1)}`
}

/**
 * Format entire structure analysis card
 */
export function formatStructureCard(analysis: AnalysisStatusResponse): string {
  const structureFeedback = getStructureFeedback(analysis)
  if (!structureFeedback) return ''

  const parts = ['🏗️ レジュメ構造分析 / Resume Structure Analysis']

  // Scores
  const scoresText = formatStructureScores(analysis)
  if (scoresText) parts.push(scoresText)

  // Strengths
  if (structureFeedback.strengths && structureFeedback.strengths.length > 0) {
    parts.push(formatListSection('✅ 強み / Strengths', structureFeedback.strengths))
  }

  // Improvement areas
  if (structureFeedback.improvement_areas && structureFeedback.improvement_areas.length > 0) {
    parts.push(formatListSection('⚠️ 改善点 / Improvement Areas', structureFeedback.improvement_areas))
  }

  // Specific feedback
  if (structureFeedback.specific_feedback && structureFeedback.specific_feedback.length > 0) {
    parts.push(formatAllFeedback(structureFeedback.specific_feedback))
  }

  return parts.join('\n\n')
}

/**
 * Format entire appeal analysis card
 */
export function formatAppealCard(analysis: AnalysisStatusResponse): string {
  const appealFeedback = getAppealFeedback(analysis)
  if (!appealFeedback) return ''

  const parts = ['🎯 応募業界へのアピール度分析 / Industry Appeal Analysis']

  // Scores
  const scoresText = formatAppealScores(analysis)
  if (scoresText) parts.push(scoresText)

  // Strengths
  if (appealFeedback.strengths && appealFeedback.strengths.length > 0) {
    parts.push(formatListSection('✅ 強み / Strengths', appealFeedback.strengths))
  }

  // Improvement areas
  if (appealFeedback.improvement_areas && appealFeedback.improvement_areas.length > 0) {
    parts.push(formatListSection('⚠️ 改善点 / Improvement Areas', appealFeedback.improvement_areas))
  }

  // Specific feedback
  if (appealFeedback.specific_feedback && appealFeedback.specific_feedback.length > 0) {
    parts.push(formatAllFeedback(appealFeedback.specific_feedback))
  }

  return parts.join('\n\n')
}

/**
 * Format entire analysis results (all cards combined)
 */
export function formatCompleteAnalysis(analysis: AnalysisStatusResponse): string {
  const result = analysis.result
  if (!result) return ''

  const parts = ['🎯 AI分析結果 / AI Analysis Results']

  // Overall score
  parts.push(`\n総合スコア / Overall Score: ${result.overall_score.toFixed(1)}`)

  // Executive summary
  if (result.executive_summary) {
    parts.push(`\n${formatExecutiveSummary(result.executive_summary)}`)
  }

  // Structure analysis
  parts.push(`\n${formatStructureCard(analysis)}`)

  // Appeal analysis
  parts.push(`\n${formatAppealCard(analysis)}`)

  return parts.join('\n')
}
