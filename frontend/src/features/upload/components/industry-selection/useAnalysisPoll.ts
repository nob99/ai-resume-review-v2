import { useState, useEffect } from 'react'
import { AnalysisStatusResponse } from '@/types'
import { analysisApi } from '@/lib/api'
import { ANALYSIS_POLL_INTERVAL_MS, AnalysisStatus } from '../../constants'

/**
 * Analysis Poll State
 */
export interface AnalysisPollState {
  analysisId: string | null
  analysisResult: AnalysisStatusResponse | null
  analysisStatus: string
  isAnalyzing: boolean
  analysisStartTime: number | null
  analysisEndTime: number | null
  elapsedTime: number
}

/**
 * Analysis Poll Actions
 */
export interface AnalysisPollActions {
  startAnalysis: (resumeId: string, industry: string) => Promise<void>
  resetAnalysis: () => void
}

/**
 * Custom hook for managing resume analysis polling
 * Handles analysis request, status polling, and completion
 */
export function useAnalysisPoll(): {
  state: AnalysisPollState
  actions: AnalysisPollActions
} {
  const [state, setState] = useState<AnalysisPollState>({
    analysisId: null,
    analysisResult: null,
    analysisStatus: '',
    isAnalyzing: false,
    analysisStartTime: null,
    analysisEndTime: null,
    elapsedTime: 0
  })

  // Timer effect - updates elapsed time every second
  useEffect(() => {
    if (!state.isAnalyzing || !state.analysisStartTime || state.analysisEndTime) return

    const timerInterval = setInterval(() => {
      const elapsed = Date.now() - state.analysisStartTime!
      setState(prev => ({ ...prev, elapsedTime: elapsed }))
    }, 1000)

    return () => {
      clearInterval(timerInterval)
    }
  }, [state.isAnalyzing, state.analysisStartTime, state.analysisEndTime])

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
            const endTime = Date.now()
            const totalDuration = endTime - (state.analysisStartTime || endTime)

            setState(prev => ({
              ...prev,
              analysisResult: result.data!,
              isAnalyzing: false,
              analysisEndTime: endTime,
              elapsedTime: totalDuration
            }))
            clearInterval(pollInterval)
          } else if (result.data.status === AnalysisStatus.ERROR) {
            setState(prev => ({
              ...prev,
              isAnalyzing: false,
              analysisEndTime: Date.now()
            }))
            clearInterval(pollInterval)
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
  }, [state.analysisId, state.analysisResult, state.analysisStartTime])

  // Start analysis
  const startAnalysis = async (resumeId: string, industry: string) => {
    const startTime = Date.now()

    setState(prev => ({
      ...prev,
      isAnalyzing: true,
      analysisResult: null,
      analysisStatus: AnalysisStatus.REQUESTING,
      analysisStartTime: startTime,
      analysisEndTime: null,
      elapsedTime: 0
    }))

    try {
      const result = await analysisApi.requestAnalysis(resumeId, industry)

      if (result.success && result.data) {
        setState(prev => ({
          ...prev,
          analysisId: result.data!.analysis_id,
          analysisStatus: result.data!.status
        }))
      } else {
        throw result.error || new Error('Failed to start analysis')
      }
    } catch (error) {
      console.error('Failed to start analysis:', error)
      setState(prev => ({
        ...prev,
        isAnalyzing: false,
        analysisEndTime: Date.now()
      }))
    }
  }

  // Reset analysis state
  const resetAnalysis = () => {
    setState({
      analysisResult: null,
      analysisId: null,
      analysisStatus: '',
      isAnalyzing: false,
      analysisStartTime: null,
      analysisEndTime: null,
      elapsedTime: 0
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