import { useState, useEffect, useCallback } from 'react'
import { historyApi } from '@/lib/api'
import { useToastActions } from '@/components/ui/Toast'

export interface AnalysisHistoryItem {
  id: string
  file_name?: string
  candidate_name?: string
  candidate_id?: string
  industry: string
  overall_score?: number
  status: string
  created_at: string
}

export interface HistoryDataState {
  analyses: AnalysisHistoryItem[]
  loading: boolean
  error: string | null
  totalCount: number
  page: number
  pageSize: number
}

export function useHistoryData() {
  const [state, setState] = useState<HistoryDataState>({
    analyses: [],
    loading: false,
    error: null,
    totalCount: 0,
    page: 1,
    pageSize: 25
  })

  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null)
  const { showError } = useToastActions()

  const fetchHistory = useCallback(async (
    page: number = 1,
    candidateId?: string | null
  ) => {
    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const params: {
        page: number
        page_size: number
        candidate_id?: string
      } = {
        page,
        page_size: state.pageSize
      }

      if (candidateId) {
        params.candidate_id = candidateId
      }

      const result = await historyApi.getHistory(params)

      if (result.success && result.data) {
        setState(prev => ({
          ...prev,
          analyses: result.data.analyses || [],
          totalCount: result.data.total_count || 0,
          page: result.data.page || page,
          pageSize: result.data.page_size || prev.pageSize,
          loading: false
        }))
      } else {
        const errorMsg = result.error?.message || 'Failed to load review history'
        setState(prev => ({ ...prev, loading: false, error: errorMsg }))
        showError(errorMsg)
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'An unexpected error occurred'
      setState(prev => ({ ...prev, loading: false, error: errorMsg }))
      showError(errorMsg)
    }
  }, [state.pageSize, showError])

  // Initial load
  useEffect(() => {
    fetchHistory(1, selectedCandidate)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCandidate])

  const handlePageChange = useCallback((newPage: number) => {
    fetchHistory(newPage, selectedCandidate)
  }, [fetchHistory, selectedCandidate])

  const handleCandidateChange = useCallback((candidateId: string | null) => {
    setSelectedCandidate(candidateId)
    // fetchHistory will be triggered by useEffect when selectedCandidate changes
  }, [])

  const refetch = useCallback(() => {
    fetchHistory(state.page, selectedCandidate)
  }, [fetchHistory, state.page, selectedCandidate])

  return {
    ...state,
    selectedCandidate,
    handlePageChange,
    handleCandidateChange,
    refetch
  }
}