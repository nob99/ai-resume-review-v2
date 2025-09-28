'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardHeader } from '../ui'

interface FeedbackSectionProps {
  title: string
  items: string[]
  type: 'issues' | 'recommendations' | 'missing' | 'strengths' | 'achievements' | 'skills' | 'advantages' | 'improvements'
  icon: string
  className?: string
  maxInitialItems?: number
}

export default function FeedbackSection({
  title,
  items,
  type,
  icon,
  className = '',
  maxInitialItems = 3
}: FeedbackSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!items || items.length === 0) {
    return (
      <Card className={`${className}`}>
        <CardHeader className="pb-3">
          <div className="flex items-center space-x-2">
            <span className="text-lg">{icon}</span>
            <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-500 italic">No {title.toLowerCase()} found</p>
        </CardContent>
      </Card>
    )
  }

  const getTypeStyles = () => {
    switch (type) {
      case 'issues':
        return {
          headerBg: 'bg-red-50',
          borderColor: 'border-red-200',
          iconColor: 'text-red-600',
          textColor: 'text-red-800'
        }
      case 'recommendations':
        return {
          headerBg: 'bg-blue-50',
          borderColor: 'border-blue-200',
          iconColor: 'text-blue-600',
          textColor: 'text-blue-800'
        }
      case 'missing':
        return {
          headerBg: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          iconColor: 'text-yellow-600',
          textColor: 'text-yellow-800'
        }
      case 'strengths':
      case 'achievements':
      case 'advantages':
        return {
          headerBg: 'bg-green-50',
          borderColor: 'border-green-200',
          iconColor: 'text-green-600',
          textColor: 'text-green-800'
        }
      case 'skills':
      case 'improvements':
        return {
          headerBg: 'bg-purple-50',
          borderColor: 'border-purple-200',
          iconColor: 'text-purple-600',
          textColor: 'text-purple-800'
        }
      default:
        return {
          headerBg: 'bg-gray-50',
          borderColor: 'border-gray-200',
          iconColor: 'text-gray-600',
          textColor: 'text-gray-800'
        }
    }
  }

  const styles = getTypeStyles()
  const displayItems = isExpanded ? items : items.slice(0, maxInitialItems)
  const hasMore = items.length > maxInitialItems

  return (
    <Card className={`${styles.borderColor} ${className}`}>
      <CardHeader className={`${styles.headerBg} pb-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className={`text-lg ${styles.iconColor}`}>{icon}</span>
            <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
            <span className="text-sm text-neutral-500">({items.length})</span>
          </div>
          {hasMore && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
            >
              {isExpanded ? 'Show Less' : 'Show All'}
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <ul className="space-y-3">
          {displayItems.map((item, index) => (
            <li key={index} className="flex items-start space-x-3">
              <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${styles.iconColor.replace('text-', 'bg-')}`} />
              <span className={`text-sm ${styles.textColor} leading-relaxed`}>
                {item}
              </span>
            </li>
          ))}
        </ul>

        {hasMore && !isExpanded && (
          <div className="mt-4 pt-3 border-t border-gray-100">
            <button
              onClick={() => setIsExpanded(true)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors"
            >
              +{items.length - maxInitialItems} more {title.toLowerCase()}...
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}