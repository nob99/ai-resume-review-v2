'use client'

import React from 'react'
import { useCopyToClipboard } from '@/features/upload/hooks/useCopyToClipboard'
import { cn } from '@/lib/utils'

interface CopyButtonProps {
  text: string
  variant?: 'icon' | 'text'
  size?: 'sm' | 'md'
  label?: string
  className?: string
}

/**
 * CopyButton Component
 * Simple, reusable copy-to-clipboard button with inline feedback
 * - Supports icon-only and icon+text variants
 * - Shows checkmark on success, X on error
 * - Auto-resets after timeout
 */
export default function CopyButton({
  text,
  variant = 'icon',
  size = 'sm',
  label = 'Copy',
  className = ''
}: CopyButtonProps) {
  const { copyText, status } = useCopyToClipboard()

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    copyText(text)
  }

  // Size styles
  const sizeClasses = {
    sm: 'p-1.5 text-xs',
    md: 'p-2 text-sm'
  }

  // Status-based styling
  const getStatusColor = () => {
    if (status === 'copied') return 'text-green-600 hover:text-green-700'
    if (status === 'error') return 'text-red-600 hover:text-red-700'
    return 'text-gray-500 hover:text-gray-700'
  }

  // Status-based icon
  const getIcon = () => {
    if (status === 'copied') {
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )
    }
    if (status === 'error') {
      return (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )
    }
    return (
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    )
  }

  // Status-based label
  const getLabel = () => {
    if (status === 'copied') return 'Copied!'
    if (status === 'error') return 'Failed'
    return label
  }

  const ariaLabel = status === 'copied' ? 'Copied to clipboard' : status === 'error' ? 'Copy failed' : `Copy ${label}`

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center gap-1.5',
        'rounded transition-colors duration-200',
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1',
        sizeClasses[size],
        getStatusColor(),
        className
      )}
    >
      {getIcon()}
      {variant === 'text' && (
        <span className="font-medium whitespace-nowrap">
          {getLabel()}
        </span>
      )}
    </button>
  )
}
