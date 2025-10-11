'use client'

import React from 'react'
import { SpecificFeedbackItem } from '@/types'

/**
 * FeedbackItemCard Component
 * Displays a single specific feedback item with category styling
 * Used in both Structure and Appeal analysis domains
 */

/**
 * Get category icon and color styling for specific feedback items
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

interface FeedbackItemCardProps {
  item: SpecificFeedbackItem
}

export default function FeedbackItemCard({ item }: FeedbackItemCardProps) {
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
              <span className="font-medium">対象テキスト:</span> &quot;{item.target_text}&quot;
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
