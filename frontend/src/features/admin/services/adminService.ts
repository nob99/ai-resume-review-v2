import { adminApi } from '@/lib/api'
import { ApiResult } from '@/types'
import {
  AdminUser,
  CreateUserRequest,
  UpdateUserRequest,
  ResetPasswordRequest,
  UsersListResponse
} from '../types'

/**
 * Admin Service
 * Handles all admin-related API operations
 */
export const adminService = {
  /**
   * Get list of users with pagination and search
   */
  async getUsers(params?: {
    page?: number
    page_size?: number
    search?: string
  }): Promise<ApiResult<UsersListResponse>> {
    return adminApi.getUsers(params)
  },

  /**
   * Create a new user
   */
  async createUser(userData: CreateUserRequest): Promise<ApiResult<AdminUser>> {
    return adminApi.createUser(userData)
  },

  /**
   * Update an existing user
   */
  async updateUser(userId: string, userData: UpdateUserRequest): Promise<ApiResult<AdminUser>> {
    return adminApi.updateUser(userId, userData)
  },

  /**
   * Reset user password
   */
  async resetPassword(userId: string, data: ResetPasswordRequest): Promise<ApiResult<void>> {
    return adminApi.resetPassword(userId, data)
  },

  /**
   * Toggle user active status
   */
  async toggleUserStatus(userId: string, isActive: boolean): Promise<ApiResult<AdminUser>> {
    return adminApi.updateUser(userId, { is_active: isActive })
  }
}

export default adminService