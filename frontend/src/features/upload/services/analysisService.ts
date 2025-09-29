import { analysisApi } from '@/lib/api'
import { ApiResult, AnalysisStatusResponse } from '@/types'

export interface AnalysisRequest {
  analysis_id: string
  status: string
  requested_at: string
}

/**
 * Analysis Service
 * Handles resume analysis operations
 */
export const analysisService = {
  /**
   * Request resume analysis
   */
  async requestAnalysis(
    resumeId: string,
    industry: string
  ): Promise<ApiResult<AnalysisRequest>> {
    return analysisApi.requestAnalysis(resumeId, industry)
  },

  /**
   * Get analysis status and results
   */
  async getAnalysisStatus(
    analysisId: string
  ): Promise<ApiResult<AnalysisStatusResponse>> {
    return analysisApi.getAnalysisStatus(analysisId)
  },

  /**
   * Get analysis history for a candidate
   */
  async getAnalysisHistory(
    candidateId: string
  ): Promise<ApiResult<AnalysisStatusResponse[]>> {
    return analysisApi.getAnalysisHistory(candidateId)
  }
}

export default analysisService