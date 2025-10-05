'use client'

import React, { useState } from 'react'
import { Button, Input } from '@/components/ui'
import { AdminUser, UserFormData, USER_ROLES } from '../types'

export interface UserFormProps {
  user?: AdminUser | null
  onSave: (userData: UserFormData) => void
  onCancel: () => void
}

/**
 * User Form Component
 * Form for creating or editing user information
 */
const UserForm: React.FC<UserFormProps> = ({ user, onSave, onCancel }) => {
  const [formData, setFormData] = useState<UserFormData>({
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
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            First Name <span className="text-red-500">*</span>
          </label>
          <Input
            type="text"
            placeholder="Enter first name"
            value={formData.first_name}
            onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Last Name <span className="text-red-500">*</span>
          </label>
          <Input
            type="text"
            placeholder="Enter last name"
            value={formData.last_name}
            onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Email Address <span className="text-red-500">*</span>
        </label>
        <Input
          type="email"
          placeholder="Enter email address"
          value={formData.email}
          onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
          required
          disabled={!!user} // Disable email editing for existing users
        />
        {user && (
          <p className="mt-1.5 text-xs text-neutral-500 flex items-start gap-1.5">
            <span className="text-base leading-none">ℹ️</span>
            <span>Email cannot be changed after account creation</span>
          </p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Role <span className="text-red-500">*</span>
        </label>
        <select
          value={formData.role}
          onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
          className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
          required
        >
          <option value="junior_recruiter">{USER_ROLES.junior_recruiter}</option>
          <option value="senior_recruiter">{USER_ROLES.senior_recruiter}</option>
          <option value="admin">{USER_ROLES.admin}</option>
        </select>
      </div>

      {!user && (
        <div>
          <label className="block text-sm font-medium text-neutral-700 mb-1">
            Temporary Password <span className="text-red-500">*</span>
          </label>
          <Input
            type="password"
            placeholder="Enter temporary password"
            value={formData.temporary_password}
            onChange={(e) => setFormData(prev => ({ ...prev, temporary_password: e.target.value }))}
            required={!user}
          />
          <div className="mt-2 p-2.5 bg-neutral-50 border border-neutral-200 rounded text-xs">
            <p className="text-neutral-700 font-medium mb-1.5">
              Create a secure temporary password that includes:
            </p>
            <ul className="text-neutral-600 space-y-0.5 ml-4">
              <li>✓ 8 or more characters</li>
              <li>✓ At least one UPPERCASE letter</li>
              <li>✓ At least one lowercase letter</li>
              <li>✓ At least one number</li>
              <li>✓ At least one special character (!@#$%^&*(),.?&quot;:&#123;&#125;|&lt;&gt;)</li>
            </ul>
            <p className="text-neutral-600 mt-1.5">
              Try: <span className="font-mono font-medium">Welcome202x!</span> or <span className="font-mono font-medium">TempPass123!</span>
            </p>
          </div>
          <p className="mt-1.5 text-xs text-neutral-600 flex items-start gap-1.5">
            <span className="text-base leading-none">💡</span>
            <span>Share this password with the user. They will be required to change it on first login.</span>
          </p>
        </div>
      )}

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_active"
          checked={formData.is_active}
          onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
          className="h-4 w-4 text-blue-600 border-neutral-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="is_active" className="text-sm text-neutral-700">
          Active user
        </label>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
        >
          {user ? 'Update User' : 'Create User'}
        </Button>
      </div>
    </form>
  )
}

export default UserForm