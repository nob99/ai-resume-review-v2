'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import { Card, CardHeader, CardContent, CandidateSelector } from '@/components/ui'
import { useHistoryData } from '@/features/history/hooks'
import { HistoryTable, AnalysisDetailModal } from '@/features/history/components'
import Pagination from '@/features/admin/components/Pagination'

/**
 * Review History Page
 * Displays list of all past resume analyses with filtering and detail view
 */
const HistoryPage: React.FC = () => {
  const router = useRouter()
  const {
    analyses,
    loading,
    error,
    totalCount,
    page,
    pageSize,
    selectedCandidate,
    handlePageChange,
    handleCandidateChange
  } = useHistoryData()

  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null)

  const handleViewDetails = (analysisId: string) => {
    setSelectedAnalysisId(analysisId)
  }

  const handleCloseModal = () => {
    setSelectedAnalysisId(null)
  }

  const handleUploadClick = () => {
    router.push('/upload')
  }

  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <main className="py-8">
          <Container size="lg">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                Review History
              </h1>
              <p className="text-lg text-neutral-600">
                View and manage all past resume analyses
              </p>
            </div>

            {/* Filters */}
            <Card className="mb-6">
                <CardHeader>
                  <h2 className="text-lg font-semibold text-neutral-900">
                    Filter Reviews
                  </h2>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-2">
                        Filter by Candidate
                      </label>
                      <CandidateSelector
                        value={selectedCandidate}
                        onSelect={handleCandidateChange}
                        placeholder="All candidates"
                        required={false}
                      />
                    </div>
                    <div className="flex items-end">
                      {selectedCandidate && (
                        <button
                          onClick={() => handleCandidateChange(null)}
                          className="px-4 py-2 text-sm font-medium text-neutral-700 hover:text-neutral-900 underline"
                        >
                          Clear filter
                        </button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Results Summary */}
              {!loading && analyses.length > 0 && (
                <div className="mb-4 text-sm text-neutral-600">
                  Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount} review{totalCount !== 1 ? 's' : ''}
                </div>
              )}

              {/* Error State */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                  <p className="text-red-800">{error}</p>
                </div>
              )}

              {/* History Table */}
              <HistoryTable
                analyses={analyses}
                loading={loading}
                onViewDetails={handleViewDetails}
                onUploadClick={analyses.length === 0 && !selectedCandidate ? handleUploadClick : undefined}
              />

            {/* Pagination */}
            {!loading && totalPages > 1 && (
              <div className="mt-6">
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                />
              </div>
            )}
          </Container>
        </main>

        {/* Analysis Detail Modal */}
        <AnalysisDetailModal
          analysisId={selectedAnalysisId}
          isOpen={!!selectedAnalysisId}
          onClose={handleCloseModal}
        />
      </div>
    </ProtectedRoute>
  )
}

export default HistoryPage