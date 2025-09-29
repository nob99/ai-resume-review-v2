import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export interface DashboardStats {
  totalResumes: number
  recentReviews: number
  averageScore: number
  lastActivityDate: string | null
}

/**
 * Custom hook for fetching dashboard data
 * Currently returns mock data - will be connected to API in future
 */
export function useDashboardData() {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats>({
    totalResumes: 0,
    recentReviews: 0,
    averageScore: 0,
    lastActivityDate: null
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Simulate API call - replace with actual API call in future
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true)

        // Mock delay
        await new Promise(resolve => setTimeout(resolve, 500))

        // Mock data - replace with actual API call
        setStats({
          totalResumes: 0,
          recentReviews: 0,
          averageScore: 0,
          lastActivityDate: null
        })
      } catch (err) {
        setError('Failed to load dashboard data')
        console.error('Dashboard data error:', err)
      } finally {
        setIsLoading(false)
      }
    }

    if (user) {
      fetchDashboardData()
    }
  }, [user])

  return { stats, isLoading, error }
}

export default useDashboardData