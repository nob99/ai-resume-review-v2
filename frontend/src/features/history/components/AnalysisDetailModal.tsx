'use client'

import React, { useState, useEffect } from 'react'
import { Modal, ModalHeader, ModalContent } from '@/components/ui'
import { Loading } from '@/components/ui'
import { analysisApi } from '@/lib/api'
import AnalysisResults from '@/features/upload/components/AnalysisResults'
import { INDUSTRY_OPTIONS } from '@/features/upload/types'
import { AnalysisStatusResponse } from '@/types'

interface AnalysisDetailModalProps {
  analysisId: string | null
  isOpen: boolean
  onClose: () => void
}

const AnalysisDetailModal: React.FC<AnalysisDetailModalProps> = ({
  analysisId,
  isOpen,
  onClose
}) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [analysisData, setAnalysisData] = useState<AnalysisStatusResponse | null>(null)

  useEffect(() => {
    if (!isOpen || !analysisId) {
      setAnalysisData(null)
      setError(null)
      return
    }

    const fetchAnalysisDetail = async () => {
      setLoading(true)
      setError(null)

      try {
        const result = await analysisApi.getAnalysisStatus(analysisId)

        if (result.success && result.data) {
          setAnalysisData(result.data)
        } else {
          setError(result.error?.message || 'Failed to load analysis details')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred')
      } finally {
        setLoading(false)
      }
    }

    fetchAnalysisDetail()
  }, [analysisId, isOpen])

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalHeader
        title="Analysis Details"
        onClose={onClose}
        showCloseButton={true}
      />
      <ModalContent>
        <div className="max-w-4xl mx-auto py-4">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loading size="lg" />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
              <h3 className="text-lg font-semibold text-red-900 mb-2">
                Error Loading Analysis
              </h3>
              <p className="text-red-700">{error}</p>
            </div>
          )}

          {!loading && !error && analysisData && (
            <div>
              {analysisData.status === 'completed' && analysisData.result ? (
                <AnalysisResults
                  analysis={analysisData}
                  industryOptions={INDUSTRY_OPTIONS}
                  onAnalyzeAgain={() => {}} // Not needed in history view
                  onUploadNew={() => {}}    // Not needed in history view
                />
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                  <h3 className="text-lg font-semibold text-yellow-900 mb-2">
                    Analysis Not Completed
                  </h3>
                  <p className="text-yellow-700">
                    This analysis is currently {analysisData.status}. Please check back later.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </ModalContent>
    </Modal>
  )
}

export default AnalysisDetailModal