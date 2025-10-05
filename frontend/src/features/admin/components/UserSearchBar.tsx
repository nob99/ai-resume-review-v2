'use client'

import React from 'react'
import { Card, CardContent, Button, Input } from '@/components/ui'

export interface UserSearchBarProps {
  searchTerm: string
  onSearch: (term: string) => void
}

/**
 * User Search Bar Component
 * Search functionality for filtering users
 */
const UserSearchBar: React.FC<UserSearchBarProps> = ({
  searchTerm,
  onSearch
}) => {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Input
              type="search"
              placeholder="名前またはメールアドレスでユーザーを検索 / Search users by name or email..."
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
  )
}

export default UserSearchBar