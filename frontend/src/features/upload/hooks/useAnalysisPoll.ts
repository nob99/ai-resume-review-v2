import { useState, useEffect } from 'react'
import { AnalysisStatusResponse } from '@/types'
import { analysisApi } from '@/lib/api'
import { ANALYSIS_POLL_INTERVAL_MS, AnalysisStatus } from '../constants'

/**
 * Analysis Poll State
 */
export interface AnalysisPollState {
  analysisId: string | null
  analysisResult: AnalysisStatusResponse | null
  analysisStatus: string
  isAnalyzing: boolean
}

/**
 * Analysis Poll Actions
 */
export interface AnalysisPollActions {
  startAnalysis: (resumeId: string, industry: string) => Promise<void>
  resetAnalysis: () => void
}

/**
 * Toast notification functions
 */
interface ToastFunctions {
  success: (title: string, message: string) => void
  error: (title: string, message: string) => void
}

/**
 * Custom hook for managing resume analysis polling
 * Handles analysis request, status polling, and completion
 */
export function useAnalysisPoll(
  toast: ToastFunctions
): {
  state: AnalysisPollState
  actions: AnalysisPollActions
} {
  const [state, setState] = useState<AnalysisPollState>({
    analysisId: null,
    analysisResult: null,
    analysisStatus: '',
    isAnalyzing: false
  })

  // Analysis polling effect
  useEffect(() => {
    if (!state.analysisId || state.analysisResult) return

    // Track if component is still mounted to prevent state updates after unmount
    let isActive = true

    const pollInterval = setInterval(async () => {
      try {
        const result = await analysisApi.getAnalysisStatus(state.analysisId!)

        // Only update state if component is still mounted
        if (!isActive) return

        if (result.success && result.data) {
          setState(prev => ({ ...prev, analysisStatus: result.data!.status }))

          if (result.data.status === AnalysisStatus.COMPLETED) {
            setState(prev => ({
              ...prev,
              analysisResult: result.data!,
              isAnalyzing: false
            }))
            clearInterval(pollInterval)
            toast.success(
              'Analysis Complete',
              'Your resume analysis is ready!'
            )
          } else if (result.data.status === AnalysisStatus.ERROR) {
            setState(prev => ({ ...prev, isAnalyzing: false }))
            clearInterval(pollInterval)
            const errorMsg = (result.data as any).error || 'Analysis failed'
            toast.error('Analysis Failed', errorMsg)
          }
        }
      } catch (error) {
        // Only log if component is still mounted
        if (!isActive) return
        console.error('Failed to poll analysis status:', error)
      }
    }, ANALYSIS_POLL_INTERVAL_MS)

    return () => {
      isActive = false
      clearInterval(pollInterval)
    }
  }, [state.analysisId, state.analysisResult, toast])

  // Start analysis
  const startAnalysis = async (resumeId: string, industry: string) => {
    setState(prev => ({
      ...prev,
      isAnalyzing: true,
      analysisResult: null,
      analysisStatus: AnalysisStatus.REQUESTING
    }))

    try {
      const result = await analysisApi.requestAnalysis(resumeId, industry)

      if (result.success && result.data) {
        setState(prev => ({
          ...prev,
          analysisId: result.data!.analysis_id,
          analysisStatus: result.data!.status
        }))
        toast.success(
          'Analysis Started',
          'Your resume is being analyzed...'
        )
      } else {
        throw result.error || new Error('Failed to start analysis')
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start analysis'
      setState(prev => ({ ...prev, isAnalyzing: false }))
      toast.error('Analysis Failed', errorMessage)
    }
  }

  // Reset analysis state
  const resetAnalysis = () => {
    setState({
      analysisResult: null,
      analysisId: null,
      analysisStatus: '',
      isAnalyzing: false
    })
  }

  const actions: AnalysisPollActions = {
    startAnalysis,
    resetAnalysis
  }

  return {
    state,
    actions
  }
}

export default useAnalysisPoll