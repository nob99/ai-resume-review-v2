'use client'

import React from 'react'
import { Button } from '@/components/ui'
import { AnalysisHistoryItem } from '../hooks/useHistoryData'
import { formatDistanceToNow } from 'date-fns'

interface HistoryTableProps {
  analyses: AnalysisHistoryItem[]
  loading: boolean
  onViewDetails: (analysisId: string) => void
  onUploadClick?: () => void
}

const HistoryTable: React.FC<HistoryTableProps> = ({
  analyses,
  loading,
  onViewDetails,
  onUploadClick
}) => {
  const getScoreColor = (score?: number) => {
    if (!score) return 'text-gray-500'
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getIndustryBadgeColor = (industry: string) => {
    const colors: Record<string, string> = {
      'strategy_consulting': 'bg-purple-100 text-purple-800',
      'tech_consulting': 'bg-blue-100 text-blue-800',
      'ma_consulting': 'bg-indigo-100 text-indigo-800',
      'financial_advisory': 'bg-green-100 text-green-800',
      'full_service_consulting': 'bg-orange-100 text-orange-800',
      'system_integrator': 'bg-cyan-100 text-cyan-800'
    }
    return colors[industry] || 'bg-gray-100 text-gray-800'
  }

  const formatIndustryName = (industry: string) => {
    return industry
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true })
    } catch {
      return dateString
    }
  }

  // Loading skeleton
  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                  候補者
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                  業界
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                  スコア
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                  日付
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                  アクション
                </th>
              </tr>
            </thead>
            <tbody>
              {[...Array(5)].map((_, i) => (
                <tr key={i} className="border-b border-neutral-200">
                  <td className="px-6 py-4">
                    <div className="h-4 bg-neutral-200 rounded animate-pulse w-32"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-6 bg-neutral-200 rounded animate-pulse w-24"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-8 bg-neutral-200 rounded animate-pulse w-16"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-4 bg-neutral-200 rounded animate-pulse w-20"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-8 bg-neutral-200 rounded animate-pulse w-16"></div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // Empty state
  if (!analyses || analyses.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-neutral-200 p-12">
        <div className="text-center">
          <div className="w-16 h-16 bg-neutral-100 text-neutral-400 rounded-lg flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-neutral-900 mb-2">
            No review history found
          </h3>
          <p className="text-neutral-500 mb-4">
            {onUploadClick ?
              "Upload your first resume to get started with AI analysis" :
              "Try adjusting your filters or upload a new resume"
            }
          </p>
          {onUploadClick && (
            <Button onClick={onUploadClick}>
              Upload Resume
            </Button>
          )}
        </div>
      </div>
    )
  }

  // Data table
  return (
    <div className="bg-white rounded-lg border border-neutral-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                候補者
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                業界
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                スコア
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                日付
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
                アクション
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {analyses.map((analysis) => (
              <tr
                key={analysis.id}
                className="hover:bg-neutral-50 cursor-pointer transition-colors"
                onClick={() => onViewDetails(analysis.id)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-neutral-900">
                    {analysis.candidate_name || 'Unknown Candidate'}
                  </div>
                  {analysis.file_name && (
                    <div className="text-sm text-neutral-500 truncate max-w-xs" title={analysis.file_name}>
                      {analysis.file_name}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getIndustryBadgeColor(analysis.industry)}`}>
                    {formatIndustryName(analysis.industry)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {analysis.overall_score !== null && analysis.overall_score !== undefined ? (
                    <div className="flex items-center">
                      <span className={`text-2xl font-bold ${getScoreColor(analysis.overall_score)}`}>
                        {analysis.overall_score}
                      </span>
                      <span className="text-sm text-neutral-500 ml-1">/100</span>
                    </div>
                  ) : (
                    <span className="text-sm text-neutral-400">
                      {analysis.status === 'pending' || analysis.status === 'processing' ? 'Processing...' : 'N/A'}
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
                  {formatDate(analysis.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      onViewDetails(analysis.id)
                    }}
                  >
                    View Details
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default HistoryTable