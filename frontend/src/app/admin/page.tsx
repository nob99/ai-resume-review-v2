'use client'

import React, { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import { Card, CardHeader, CardContent } from '@/components/ui'
import Modal, { ModalContent } from '@/components/ui/Modal'
import UserSearchBar from '@/features/admin/components/UserSearchBar'
import UsersTable from '@/features/admin/components/UsersTable'
import UserForm from '@/features/admin/components/UserForm'
import Pagination from '@/features/admin/components/Pagination'
import useUserManagement from '@/features/admin/hooks/useUserManagement'
import { AdminUser } from '@/features/admin/types'

/**
 * Admin Page Component
 * Main admin panel for user management
 */
const AdminPage: React.FC = () => {
  const { user } = useAuth()
  const {
    users,
    loading,
    searchTerm,
    currentPage,
    totalUsers,
    totalPages,
    handleSearch,
    setCurrentPage,
    handleSaveUser,
    handleToggleUserStatus,
    handleResetPassword
  } = useUserManagement()

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null)

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

  // Handle modal actions
  const handleCreateUser = () => {
    setEditingUser(null)
    setShowCreateModal(true)
  }

  const handleEditUser = (user: AdminUser) => {
    setEditingUser(user)
    setShowCreateModal(true)
  }

  const handleCloseModal = () => {
    setShowCreateModal(false)
    setEditingUser(null)
  }

  const handleSaveUserWithModal = async (userData: any) => {
    const success = await handleSaveUser(userData, editingUser)
    if (success) {
      handleCloseModal()
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <main className="py-8">
          <Container size="lg">
            {/* Page Header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                  User Management
                </h1>
                <p className="text-lg text-neutral-600">
                  Manage system users and their permissions
                </p>
              </div>
              <button
                onClick={handleCreateUser}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
              >
                + Add User
              </button>
            </div>

            {/* Search Bar */}
            <UserSearchBar
              searchTerm={searchTerm}
              onSearch={handleSearch}
            />

            {/* Users Table */}
            <Card>
              <CardHeader title={`Users (${totalUsers})`} />
              <CardContent className="p-0">
                <UsersTable
                  users={users}
                  loading={loading}
                  searchTerm={searchTerm}
                  onEditUser={handleEditUser}
                  onToggleUserStatus={handleToggleUserStatus}
                  onResetPassword={handleResetPassword}
                />

                {/* Pagination */}
                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                />
              </CardContent>
            </Card>
          </Container>
        </main>

        {/* Create/Edit User Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={handleCloseModal}
          title={editingUser ? 'Edit User' : 'Create New User'}
          size="md"
        >
          <ModalContent>
            <UserForm
              user={editingUser}
              onSave={handleSaveUserWithModal}
              onCancel={handleCloseModal}
            />
          </ModalContent>
        </Modal>
      </div>
    </ProtectedRoute>
  )
}

export default AdminPage