'use client'

import React from 'react'

export interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

/**
 * Pagination Component
 * Handles navigation between pages
 */
const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange
}) => {
  if (totalPages <= 1) {
    return null
  }

  return (
    <div className="flex items-center justify-between px-6 py-4 border-t border-neutral-200">
      <div className="text-sm text-neutral-500">
        Page {currentPage} of {totalPages}
      </div>
      <div className="flex gap-2">
        <button
          className="px-3 py-1 text-sm bg-neutral-200 text-neutral-700 rounded hover:bg-neutral-300 disabled:opacity-50 transition-colors"
          onClick={() => onPageChange(Math.max(1, currentPage - 1))}
          disabled={currentPage <= 1}
        >
          Previous
        </button>
        <button
          className="px-3 py-1 text-sm bg-neutral-200 text-neutral-700 rounded hover:bg-neutral-300 disabled:opacity-50 transition-colors"
          onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
          disabled={currentPage >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  )
}

export default Pagination