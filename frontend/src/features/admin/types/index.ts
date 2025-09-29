/**
 * Admin Feature Types
 */

export interface AdminUser {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  email_verified: boolean
  created_at: string
  last_login_at?: string
  full_name: string
  assigned_candidates_count?: number
}

export interface CreateUserRequest {
  email: string
  first_name: string
  last_name: string
  role: string
  temporary_password: string
}

export interface UpdateUserRequest {
  first_name?: string
  last_name?: string
  role?: string
  is_active?: boolean
}

export interface ResetPasswordRequest {
  new_password: string
  force_password_change: boolean
}

export interface UsersListResponse {
  users: AdminUser[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface UserFormData {
  email: string
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  temporary_password: string
}

export type UserRole = 'admin' | 'junior_recruiter' | 'senior_recruiter'

export const USER_ROLES: Record<UserRole, string> = {
  admin: 'Admin',
  junior_recruiter: 'Junior Recruiter',
  senior_recruiter: 'Senior Recruiter'
}