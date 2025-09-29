import api from '@/lib/api'
import { ApiResult } from '@/types'

export interface DashboardStats {
  totalResumes: number
  recentReviews: number
  averageScore: number
  lastActivityDate: string | null
}

export interface RecentActivity {
  id: string
  type: 'upload' | 'review' | 'analysis'
  title: string
  description: string
  timestamp: string
  metadata?: Record<string, any>
}

/**
 * Dashboard Service
 * Handles dashboard-related API operations
 */
export const dashboardService = {
  /**
   * Get dashboard statistics
   * Currently returns mock data - will be connected to backend in future
   */
  async getStats(): Promise<ApiResult<DashboardStats>> {
    try {
      // TODO: Replace with actual API endpoint when available
      // const response = await api.get<DashboardStats>('/dashboard/stats')

      // Mock data for now
      return {
        success: true,
        data: {
          totalResumes: 0,
          recentReviews: 0,
          averageScore: 0,
          lastActivityDate: null
        }
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to fetch dashboard stats')
      }
    }
  },

  /**
   * Get recent activity
   * Currently returns empty array - will be connected to backend in future
   */
  async getRecentActivity(limit: number = 10): Promise<ApiResult<RecentActivity[]>> {
    try {
      // TODO: Replace with actual API endpoint when available
      // const response = await api.get<RecentActivity[]>(`/dashboard/activity?limit=${limit}`)

      // Mock empty array for now
      return {
        success: true,
        data: []
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error : new Error('Failed to fetch recent activity')
      }
    }
  }
}

export default dashboardService