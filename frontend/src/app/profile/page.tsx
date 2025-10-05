'use client'

import React, { useState, useEffect } from 'react'
import { useAuth, ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import { Card, CardContent, CardHeader, Button, Input } from '@/components/ui'
import { useToastActions } from '@/components/ui/Toast'
import { profileApi } from '@/lib/api'

/**
 * Profile Settings Page Component
 * Allows users to edit their own profile information and change password
 */
const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth()
  const { showSuccess, showError } = useToastActions()

  // Profile form state
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  // Password form state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
  const [isPasswordLoading, setIsPasswordLoading] = useState(false)

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || ''
      })
    }
  }, [user])

  // Track if form has changes
  useEffect(() => {
    if (user) {
      const changed =
        formData.first_name !== user.first_name ||
        formData.last_name !== user.last_name
      setHasChanges(changed)
    }
  }, [formData, user])

  // Handle profile form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!formData.first_name.trim() || !formData.last_name.trim()) {
      showError('First name and last name are required')
      return
    }

    setIsLoading(true)

    try {
      const result = await profileApi.updateProfile({
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim()
      })

      if (result.success) {
        // Refresh user data in context
        await refreshUser()
        showSuccess('Profile updated successfully')
        setHasChanges(false)
      } else {
        showError(result.error?.message || 'Failed to update profile')
      }
    } catch (error) {
      showError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  // Handle cancel
  const handleCancel = () => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || ''
      })
      setHasChanges(false)
    }
  }

  // Handle password change
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validation
    if (!passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password) {
      showError('All password fields are required')
      return
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      showError('New passwords do not match')
      return
    }

    if (passwordData.new_password.length < 8) {
      showError('New password must be at least 8 characters')
      return
    }

    if (passwordData.new_password === passwordData.current_password) {
      showError('New password must be different from current password')
      return
    }

    setIsPasswordLoading(true)

    try {
      const result = await profileApi.changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      })

      if (result.success) {
        showSuccess('Password changed successfully')
        // Clear password form
        setPasswordData({
          current_password: '',
          new_password: '',
          confirm_password: ''
        })
      } else {
        showError(result.error?.message || 'Failed to change password')
      }
    } catch (error) {
      showError('An unexpected error occurred')
    } finally {
      setIsPasswordLoading(false)
    }
  }

  // Handle password cancel
  const handlePasswordCancel = () => {
    setPasswordData({
      current_password: '',
      new_password: '',
      confirm_password: ''
    })
  }

  // Get role badge color
  const getRoleBadgeColor = (role: string) => {
    if (role === 'admin') return 'bg-blue-100 text-blue-800'
    if (role === 'senior_recruiter') return 'bg-green-100 text-green-800'
    return 'bg-gray-100 text-gray-800'
  }

  // Format role display
  const formatRole = (role: string) => {
    return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-neutral-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <main className="py-8">
          <Container size="md">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-2">
                プロファイル設定 / Profile Settings
              </h1>
              <p className="text-neutral-600">
                あなたのプロファイル設定を変更できます / Manage your personal information and security settings
              </p>
            </div>

            <div className="space-y-6">
              {/* Profile Information Card */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    プロファイル設定 / Personal Information
                  </h2>
                </CardHeader>
                <CardContent className="pt-6">
                  <form onSubmit={handleSubmit} className="space-y-6">
                    {/* First Name */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        ファーストネーム / First Name <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="text"
                        placeholder="Enter first name"
                        value={formData.first_name}
                        onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                        disabled={isLoading}
                        required
                      />
                    </div>

                    {/* Last Name */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        ラストネーム / Last Name <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="text"
                        placeholder="Enter last name"
                        value={formData.last_name}
                        onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                        disabled={isLoading}
                        required
                      />
                    </div>

                    {/* Email (Read-only) */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        メールアドレス / Email
                      </label>
                      <p className="text-base text-neutral-600">
                        {user.email}
                      </p>
                    </div>

                    {/* Role (Read-only with badge) */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        ロール / Role
                      </label>
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getRoleBadgeColor(user.role)}`}>
                        {formatRole(user.role)}
                      </span>
                    </div>

                    {/* Buttons */}
                    <div className="flex justify-end gap-3 pt-4">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={handleCancel}
                        disabled={isLoading || !hasChanges}
                      >
                        キャンセル / Cancel
                      </Button>
                      <Button
                        type="submit"
                        variant="primary"
                        disabled={isLoading || !hasChanges}
                      >
                        {isLoading ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                            保存中... / Saving...
                          </>
                        ) : (
                          '保存 / Save Changes'
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>

              {/* Password Change Card */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    パスワード変更 / Change Password
                  </h2>
                </CardHeader>
                <CardContent className="pt-6">
                  <form onSubmit={handlePasswordSubmit} className="space-y-6">
                    {/* Current Password */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        現在のパスワード / Current Password <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="password"
                        placeholder="Enter current password"
                        value={passwordData.current_password}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, current_password: e.target.value }))}
                        disabled={isPasswordLoading}
                        required
                      />
                    </div>

                    {/* New Password */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        新しいパスワード / New Password <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="password"
                        placeholder="Enter new password (min 8 characters)"
                        value={passwordData.new_password}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, new_password: e.target.value }))}
                        disabled={isPasswordLoading}
                        required
                      />
                    </div>

                    {/* Confirm New Password */}
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1">
                        新しいパスワード再入力 / Confirm New Password <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="password"
                        placeholder="Confirm new password"
                        value={passwordData.confirm_password}
                        onChange={(e) => setPasswordData(prev => ({ ...prev, confirm_password: e.target.value }))}
                        disabled={isPasswordLoading}
                        required
                      />
                    </div>

                    {/* Buttons */}
                    <div className="flex justify-end gap-3 pt-4">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={handlePasswordCancel}
                        disabled={isPasswordLoading}
                      >
                         キャンセル / Cancel
                      </Button>
                      <Button
                        type="submit"
                        variant="primary"
                        disabled={isPasswordLoading}
                      >
                        {isPasswordLoading ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                            変更中... / Changing...
                          </>
                        ) : (
                          'パスワード変更 / Change Password'
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </div>
          </Container>
        </main>
      </div>
    </ProtectedRoute>
  )
}

export default ProfilePage