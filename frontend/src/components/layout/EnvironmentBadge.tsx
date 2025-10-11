'use client'

import React from 'react'
import { cn } from '@/lib/utils'

/**
 * EnvironmentBadge displays the current environment (dev, staging, prod)
 * in the header to help developers identify which environment they're using.
 *
 * Environment is determined by the NEXT_PUBLIC_ENV_NAME environment variable
 * which is set during build time:
 * - dev: Local development
 * - staging: Staging environment on GCP
 * - prod: Production environment (badge is hidden by default)
 */
const EnvironmentBadge: React.FC = () => {
  const envName = process.env.NEXT_PUBLIC_ENV_NAME || 'dev'

  // Hide badge in production to keep it clean
  if (envName === 'prod') {
    return null
  }

  // Color scheme based on environment
  const badgeStyles = {
    dev: 'bg-blue-100 text-blue-700 border-blue-300',
    staging: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  }

  const style = badgeStyles[envName as keyof typeof badgeStyles] || badgeStyles.dev

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border',
        'uppercase tracking-wide',
        style
      )}
      title={`Environment: ${envName}`}
      aria-label={`Current environment: ${envName}`}
    >
      {envName}
    </span>
  )
}

export default EnvironmentBadge
