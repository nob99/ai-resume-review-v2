'use client'

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth-context'
import { ProtectedRoute } from '@/lib/auth-context'
import { Container, Section, Header } from '@/components/layout'
import { Card, CardHeader, CardContent, Button } from '@/components/ui'
import { useToastActions } from '@/components/ui/Toast'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import { adminApi } from '@/lib/api'

// User interface for admin (matches backend response)
interface AdminUser {
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

// Role mapping from backend to frontend display
const mapRoleForDisplay = (backendRole: string): string => {
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

const AdminPage: React.FC = () => {
  const { user } = useAuth()
  const { showSuccess, showError } = useToastActions()

  // State management (simple)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalUsers, setTotalUsers] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  // Load users on component mount
  useEffect(() => {
    loadUsers()
  }, [currentPage, searchTerm])

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

  // Access control - only admin users can access this page
  if (user?.role !== 'admin') {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <Card className="text-center p-8">
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">
            Access Denied
          </h2>
          <p className="text-neutral-600">
            This page is only accessible to administrators.
          </p>
        </Card>
      </div>
    )
  }

  // Handle search with debounce
  const handleSearch = (term: string) => {
    setSearchTerm(term)
    setCurrentPage(1) // Reset to first page when searching
  }

  // Handle user actions
  const handleCreateUser = () => {
    setEditingUser(null)
    setShowCreateModal(true)
  }

  const handleEditUser = (user: AdminUser) => {
    setEditingUser(user)
    setShowCreateModal(true)
  }

  const handleToggleUserStatus = async (userId: string) => {
    const user = users.find(u => u.id === userId)
    if (!user) return

    try {
      const result = await adminApi.updateUser(userId, {
        is_active: !user.is_active
      })

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

  const handleResetPassword = async (user: AdminUser) => {
    const newPassword = 'TempPass123!' // In real app, generate secure password

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

  const handleSaveUser = async (userData: any) => {
    try {
      if (editingUser) {
        // Update existing user
        const result = await adminApi.updateUser(editingUser.id, {
          is_active: userData.is_active,
          role: userData.role
        })

        if (result.success) {
          showSuccess('User updated successfully')
          loadUsers() // Reload users
        } else {
          showError('Failed to update user')
          return
        }
      } else {
        // Create new user
        const result = await adminApi.createUser({
          email: userData.email,
          first_name: userData.first_name,
          last_name: userData.last_name,
          role: userData.role,
          temporary_password: userData.temporary_password
        })

        if (result.success) {
          showSuccess('User created successfully')
          loadUsers() // Reload users
        } else {
          showError('Failed to create user')
          return
        }
      }

      setShowCreateModal(false)
      setEditingUser(null)
    } catch (error) {
      showError(editingUser ? 'Failed to update user' : 'Failed to create user')
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <Section spacing="lg">
          <Container>
            <div className="space-y-6">
              {/* Page Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-neutral-900">
                    User Management
                  </h1>
                  <p className="text-neutral-600 mt-1">
                    Manage system users and their permissions
                  </p>
                </div>
                <Button onClick={handleCreateUser}>
                  + Add User
                </Button>
              </div>

              {/* Search */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <Input
                        type="search"
                        placeholder="Search users by name or email..."
                        value={searchTerm}
                        onChange={(e) => handleSearch(e.target.value)}
                      />
                    </div>
                    <Button onClick={() => handleSearch('')}>
                      Clear
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Users Table */}
              <Card>
                <CardHeader title={`Users (${totalUsers})`} />
                <CardContent className="p-0">
                  {loading && (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
                      <p className="text-neutral-500 mt-2">Loading users...</p>
                    </div>
                  )}

                  {!loading && (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-neutral-50 border-b border-neutral-200">
                          <tr>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Name</th>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Email</th>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Role</th>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Status</th>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Last Login</th>
                            <th className="text-left py-3 px-4 font-medium text-neutral-700">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {users.map((user, index) => (
                            <tr
                              key={user.id}
                              className={index % 2 === 0 ? 'bg-white' : 'bg-neutral-25'}
                            >
                              <td className="py-3 px-4">
                                <div className="font-medium text-neutral-900">
                                  {user.first_name} {user.last_name}
                                </div>
                              </td>
                              <td className="py-3 px-4 text-neutral-600">
                                {user.email}
                              </td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                  user.role === 'admin'
                                    ? 'bg-blue-100 text-blue-800'
                                    : 'bg-green-100 text-green-800'
                                }`}>
                                  {mapRoleForDisplay(user.role)}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                  user.is_active
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-red-100 text-red-800'
                                }`}>
                                  {user.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-neutral-600">
                                {user.last_login_at
                                  ? new Date(user.last_login_at).toLocaleDateString()
                                  : 'Never'
                                }
                              </td>
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-2">
                                  <button
                                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                                    onClick={() => handleEditUser(user)}
                                  >
                                    Edit
                                  </button>
                                  <button
                                    className={`px-3 py-1 text-sm rounded transition-colors ${
                                      user.is_active
                                        ? 'bg-red-600 text-white hover:bg-red-700'
                                        : 'bg-green-600 text-white hover:bg-green-700'
                                    }`}
                                    onClick={() => handleToggleUserStatus(user.id)}
                                  >
                                    {user.is_active ? 'Disable' : 'Enable'}
                                  </button>
                                  <button
                                    className="px-3 py-1 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 transition-colors"
                                    onClick={() => handleResetPassword(user)}
                                  >
                                    Reset
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {!loading && users.length === 0 && (
                    <div className="text-center py-8">
                      <p className="text-neutral-500">
                        {searchTerm ? 'No users found matching your search.' : 'No users found.'}
                      </p>
                    </div>
                  )}

                  {/* Pagination */}
                  {!loading && totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200">
                      <div className="text-sm text-neutral-500">
                        Page {currentPage} of {totalPages}
                      </div>
                      <div className="flex gap-2">
                        <button
                          className="px-3 py-1 text-sm bg-neutral-200 text-neutral-700 rounded hover:bg-neutral-300 disabled:opacity-50 transition-colors"
                          onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                          disabled={currentPage <= 1}
                        >
                          Previous
                        </button>
                        <button
                          className="px-3 py-1 text-sm bg-neutral-200 text-neutral-700 rounded hover:bg-neutral-300 disabled:opacity-50 transition-colors"
                          onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                          disabled={currentPage >= totalPages}
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </Container>
        </Section>

        {/* Create/Edit User Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => {
            setShowCreateModal(false)
            setEditingUser(null)
          }}
          title={editingUser ? 'Edit User' : 'Create New User'}
          size="md"
        >
          <UserForm
            user={editingUser}
            onSave={handleSaveUser}
            onCancel={() => {
              setShowCreateModal(false)
              setEditingUser(null)
            }}
          />
        </Modal>
      </div>
    </ProtectedRoute>
  )
}

// Simple User Form Component
interface UserFormProps {
  user?: AdminUser | null
  onSave: (userData: any) => void
  onCancel: () => void
}

const UserForm: React.FC<UserFormProps> = ({ user, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    email: user?.email || '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    role: user?.role || 'junior_recruiter',
    is_active: user?.is_active ?? true,
    temporary_password: ''
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            First Name *
          </label>
          <Input
            type="text"
            value={formData.first_name}
            onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Last Name *
          </label>
          <Input
            type="text"
            value={formData.last_name}
            onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Email Address *
        </label>
        <Input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Role *
        </label>
        <select
          value={formData.role}
          onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
          className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          required
        >
          <option value="junior_recruiter">Junior Recruiter</option>
          <option value="senior_recruiter">Senior Recruiter</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {!user && (
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Temporary Password *
          </label>
          <Input
            type="password"
            value={formData.temporary_password}
            onChange={(e) => setFormData(prev => ({ ...prev, temporary_password: e.target.value }))}
            placeholder="Enter temporary password"
            required={!user}
          />
        </div>
      )}

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
          className="rounded border-neutral-300"
        />
        <label htmlFor="is_active" className="text-sm text-neutral-700">
          Active user
        </label>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          className="px-4 py-2 text-sm border border-neutral-300 rounded hover:bg-neutral-50 transition-colors"
          onClick={onCancel}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          {user ? 'Update User' : 'Create User'}
        </button>
      </div>
    </form>
  )
}

export default AdminPage