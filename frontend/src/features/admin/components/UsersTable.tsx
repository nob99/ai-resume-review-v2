'use client'

import React from 'react'
import { AdminUser } from '../types'
import { mapRoleForDisplay } from '../hooks/useUserManagement'

export interface UsersTableProps {
  users: AdminUser[]
  loading: boolean
  searchTerm: string
  onEditUser: (user: AdminUser) => void
  onToggleUserStatus: (userId: string) => void
  onResetPassword: (user: AdminUser) => void
}

/**
 * Users Table Component
 * Displays list of users in a table format
 */
const UsersTable: React.FC<UsersTableProps> = ({
  users,
  loading,
  searchTerm,
  onEditUser,
  onToggleUserStatus,
  onResetPassword
}) => {
  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500 mx-auto"></div>
        <p className="text-neutral-500 mt-2">Loading users...</p>
      </div>
    )
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-neutral-500">
          {searchTerm ? 'No users found matching your search.' : 'No users found.'}
        </p>
      </div>
    )
  }

  return (
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
                    onClick={() => onEditUser(user)}
                  >
                    Edit
                  </button>
                  <button
                    className={`px-3 py-1 text-sm rounded transition-colors ${
                      user.is_active
                        ? 'bg-red-600 text-white hover:bg-red-700'
                        : 'bg-green-600 text-white hover:bg-green-700'
                    }`}
                    onClick={() => onToggleUserStatus(user.id)}
                  >
                    {user.is_active ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    className="px-3 py-1 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 transition-colors"
                    onClick={() => onResetPassword(user)}
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
  )
}

export default UsersTable