import { useState, useEffect } from 'react'
import { useToastActions } from '@/components/ui/Toast'
import { adminApi } from '@/lib/api'
import { AdminUser, UserFormData } from '../types'

/**
 * Map backend role to display-friendly format
 */
export const mapRoleForDisplay = (backendRole: string): string => {
  switch (backendRole) {
    case 'admin':
      return 'Admin'
    case 'junior_recruiter':
      return 'Junior Recruiter'
    case 'senior_recruiter':
      return 'Senior Recruiter'
    default:
      return 'Consultant'
  }
}

/**
 * Generate temporary password
 * In production, use a more secure method
 */
const generateTempPassword = (): string => {
  return 'TempPass123!'
}

/**
 * Custom hook for user management functionality
 */
export function useUserManagement() {
  const { showSuccess, showError } = useToastActions()

  // State management
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Load users from API
  const loadUsers = async () => {
    setLoading(true)
    try {
      const result = await adminApi.getUsers({
        page: currentPage,
        page_size: 20,
        search: searchTerm || undefined
      })

      if (result.success && result.data) {
        setUsers(result.data.users || [])
        setTotalUsers(result.data.total || 0)
        setTotalPages(result.data.total_pages || 0)
      } else {
        showError('Failed to load users')
      }
    } catch (error) {
      showError('Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  // Load users when dependencies change
  useEffect(() => {
    loadUsers()
  }, [currentPage, searchTerm])

  // Handle search with page reset
  const handleSearch = (term: string) => {
    setSearchTerm(term)
    setCurrentPage(1) // Reset to first page when searching
  }

  // Handle user creation/update
  const handleSaveUser = async (userData: UserFormData, editingUser?: AdminUser | null) => {
    try {
      if (editingUser) {
        // Update existing user
        const updatePayload = {
          first_name: userData.first_name,
          last_name: userData.last_name,
          is_active: userData.is_active,
          role: userData.role
        }

        const result = await adminApi.updateUser(editingUser.id, updatePayload)

        if (result.success) {
          showSuccess('User updated successfully')
          loadUsers() // Reload users
          return true
        } else {
          showError('Failed to update user')
          return false
        }
      } else {
        // Create new user
        const createPayload = {
          email: userData.email,
          first_name: userData.first_name,
          last_name: userData.last_name,
          role: userData.role,
          temporary_password: userData.temporary_password
        }

        const result = await adminApi.createUser(createPayload)

        if (result.success) {
          showSuccess('User created successfully')
          loadUsers() // Reload users
          return true
        } else {
          showError('Failed to create user')
          return false
        }
      }
    } catch (error) {
      showError(editingUser ? 'Failed to update user' : 'Failed to create user')
      return false
    }
  }

  // Handle user status toggle
  const handleToggleUserStatus = async (userId: string) => {
    const user = users.find(u => u.id === userId)
    if (!user) return

    try {
      const result = await adminApi.updateUser(userId, { is_active: !user.is_active })

      if (result.success) {
        showSuccess('User status updated successfully')
        loadUsers() // Reload users to get updated data
      } else {
        showError('Failed to update user status')
      }
    } catch (error) {
      showError('Failed to update user status')
    }
  }

  // Handle password reset
  const handleResetPassword = async (user: AdminUser) => {
    const newPassword = generateTempPassword()

    try {
      const result = await adminApi.resetPassword(user.id, {
        new_password: newPassword,
        force_password_change: true
      })

      if (result.success) {
        showSuccess(`Password reset for ${user.email}. New password: ${newPassword}`)
      } else {
        showError('Failed to reset password')
      }
    } catch (error) {
      showError('Failed to reset password')
    }
  }

  return {
    // State
    users,
    loading,
    searchTerm,
    currentPage,
    totalUsers,
    totalPages,

    // Actions
    handleSearch,
    setCurrentPage,
    handleSaveUser,
    handleToggleUserStatus,
    handleResetPassword,
    loadUsers
  }
}

export default useUserManagement