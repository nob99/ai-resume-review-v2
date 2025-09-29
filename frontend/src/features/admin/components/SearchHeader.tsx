'use client'

import React from 'react'
import { Card, CardContent, Button, Input } from '@/components/ui'

export interface SearchHeaderProps {
  searchTerm: string
  onSearch: (term: string) => void
  onCreateUser: () => void
}

/**
 * Search Header Component
 * Header with search functionality and create user button
 */
const SearchHeader: React.FC<SearchHeaderProps> = ({
  searchTerm,
  onSearch,
  onCreateUser
}) => {
  return (
    <>
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">
            Admin Page for User Management
          </h1>
          <p className="text-neutral-600 mt-1">
            Manage system users and their permissions
          </p>
        </div>
        <Button onClick={onCreateUser}>
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
                onChange={(e) => onSearch(e.target.value)}
              />
            </div>
            <Button onClick={() => onSearch('')}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

export default SearchHeader