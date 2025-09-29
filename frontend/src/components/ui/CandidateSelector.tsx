import React, { useState, useEffect, useRef, useCallback } from 'react'
import { cn } from '../../lib/utils'
import { BaseComponentProps, Candidate } from '../../types'
import { candidateApi } from '../../lib/api'
import { Loading } from './Loading'

export interface CandidateSelectorProps extends BaseComponentProps {
  value?: string
  onSelect: (candidateId: string) => void
  placeholder?: string
  disabled?: boolean
  required?: boolean
}

export const CandidateSelector: React.FC<CandidateSelectorProps> = ({
  value,
  onSelect,
  disabled = false,
  required = false,
  className
}) => {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  // Refs
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // ============================================================================
  // DATA FETCHING
  // ============================================================================
  useEffect(() => {
    const loadCandidates = async () => {
      try {
        setLoading(true)
        setError(null)

        const result = await candidateApi.getCandidates()

        if (result.success && result.data) {
          setCandidates(result.data)
        } else {
          setError('Failed to load candidates')
        }
      } catch (err) {
        setError('Failed to load candidates')
        console.error('Error loading candidates:', err)
      } finally {
        setLoading(false)
      }
    }

    loadCandidates()
  }, [])

  // ============================================================================
  // COMPUTED VALUES
  // ============================================================================
  const filteredCandidates = useCallback(() => {
    if (!searchTerm) return candidates.slice(0, 10) // Show first 10 when no search
    const fullName = (candidate: Candidate) =>
      `${candidate.first_name} ${candidate.last_name}`.toLowerCase()

    return candidates.filter(candidate =>
      fullName(candidate).includes(searchTerm.toLowerCase())
    )
  }, [candidates, searchTerm])()

  const getDisplayValue = useCallback(() => {
    if (value && !searchTerm) {
      const selectedCandidate = candidates.find(c => c.id === value)
      return selectedCandidate ? `${selectedCandidate.first_name} ${selectedCandidate.last_name}` : ''
    }
    return searchTerm
  }, [value, searchTerm, candidates])

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  const handleCandidateSelect = useCallback((candidateId: string) => {
    const selectedCandidate = candidates.find(c => c.id === candidateId)
    if (selectedCandidate) {
      setSearchTerm(`${selectedCandidate.first_name} ${selectedCandidate.last_name}`)
      setIsDropdownOpen(false)
      setHighlightedIndex(-1)
      onSelect(candidateId)
    }
  }, [candidates, onSelect])

  const handleClearSearch = useCallback(() => {
    setSearchTerm('')
    setIsDropdownOpen(false)
    setHighlightedIndex(-1)
    onSelect('')
  }, [onSelect])

  const handleInputFocus = useCallback(() => {
    setIsDropdownOpen(true)
  }, [])

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setSearchTerm(newValue)
    setIsDropdownOpen(true)
    setHighlightedIndex(-1)

    // Clear selection if user is typing and doesn't match exactly
    if (value) {
      const selectedCandidate = candidates.find(c => c.id === value)
      if (selectedCandidate) {
        const exactMatch = `${selectedCandidate.first_name} ${selectedCandidate.last_name}`
        if (newValue !== exactMatch) {
          onSelect('')
        }
      }
    }
  }, [value, candidates, onSelect])

  const handleToggleDropdown = useCallback(() => {
    setIsDropdownOpen(!isDropdownOpen)
  }, [isDropdownOpen])

  // ============================================================================
  // KEYBOARD NAVIGATION
  // ============================================================================
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Open dropdown if closed
    if (!isDropdownOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsDropdownOpen(true)
        return
      }
    }

    const maxIndex = filteredCandidates.length - 1

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex(prev => prev < maxIndex ? prev + 1 : 0)
        break

      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : maxIndex)
        break

      case 'Enter':
        e.preventDefault()
        if (highlightedIndex >= 0 && highlightedIndex <= maxIndex) {
          handleCandidateSelect(filteredCandidates[highlightedIndex].id)
        }
        break

      case 'Escape':
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        inputRef.current?.blur()
        break
    }
  }, [isDropdownOpen, filteredCandidates, highlightedIndex, handleCandidateSelect])

  // ============================================================================
  // CLICK OUTSIDE DETECTION
  // ============================================================================
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
      }
    }

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isDropdownOpen])

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================
  const renderLoadingState = () => (
    <div className={cn('flex items-center space-x-2', className)}>
      <Loading size="sm" />
      <span className="text-sm text-neutral-600">Loading candidates...</span>
    </div>
  )

  const renderErrorState = () => (
    <div className={cn('text-sm text-red-600', className)}>
      {error}
    </div>
  )

  const renderEmptyState = () => (
    <div className="text-sm text-neutral-600">
      No candidates found. You may need to create one first.
    </div>
  )

  const renderDropdownTrigger = () => (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={getDisplayValue()}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onKeyDown={handleKeyDown}
        placeholder="Type to search candidates..."
        disabled={disabled}
        required={required}
        className={cn(
          'block w-full px-3 py-2 pr-10 border border-neutral-300 rounded-md',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          'bg-white text-neutral-900 placeholder-neutral-400',
          'disabled:bg-neutral-100 disabled:text-neutral-500 disabled:cursor-not-allowed',
          isDropdownOpen && 'border-blue-500 ring-2 ring-blue-500'
        )}
      />

      {renderDropdownArrow()}
      {renderClearButton()}
    </div>
  )

  const renderDropdownArrow = () => (
    <button
      type="button"
      onClick={handleToggleDropdown}
      disabled={disabled}
      className="absolute right-8 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none"
      aria-label="Toggle dropdown"
    >
      <svg
        className={cn('w-4 h-4 transition-transform', isDropdownOpen && 'rotate-180')}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  )

  const renderClearButton = () => {
    if (!(searchTerm || value)) return null

    return (
      <button
        type="button"
        onClick={handleClearSearch}
        disabled={disabled}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none"
        aria-label="Clear selection"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    )
  }

  const renderDropdownList = () => {
    if (!isDropdownOpen) return null

    return (
      <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-300 rounded-md shadow-lg max-h-60 overflow-y-auto">
        {filteredCandidates.length > 0 ? (
          filteredCandidates.map((candidate, index) => renderCandidateItem(candidate, index))
        ) : (
          <div className="px-3 py-2 text-sm text-neutral-500">
            {searchTerm ? `No candidates match "${searchTerm}"` : 'No candidates available'}
          </div>
        )}
      </div>
    )
  }

  const renderCandidateItem = (candidate: Candidate, index: number) => (
    <button
      key={candidate.id}
      type="button"
      onClick={() => handleCandidateSelect(candidate.id)}
      className={cn(
        'w-full px-3 py-2 text-left hover:bg-blue-50 focus:bg-blue-50 focus:outline-none border-none',
        'first:rounded-t-md last:rounded-b-md',
        highlightedIndex === index && 'bg-blue-50',
        value === candidate.id && 'bg-blue-100 text-blue-900 font-medium'
      )}
      onMouseEnter={() => setHighlightedIndex(index)}
    >
      <div className="flex flex-col">
        <span className="text-sm font-medium text-neutral-900">
          {candidate.first_name} {candidate.last_name}
        </span>
        {candidate.email && (
          <span className="text-xs text-neutral-500">
            {candidate.email}
          </span>
        )}
      </div>
    </button>
  )

  const renderStatusInfo = () => {
    if (candidates.length === 0) return null

    return (
      <p className="text-xs text-neutral-500">
        {searchTerm ? (
          <>Showing {filteredCandidates.length} of {candidates.length} candidates</>
        ) : (
          <>Total: {candidates.length} candidates</>
        )}
      </p>
    )
  }

  // ============================================================================
  // MAIN RENDER
  // ============================================================================
  if (loading) return renderLoadingState()
  if (error) return renderErrorState()

  return (
    <div className={cn('space-y-2', className)}>
      <label className="block text-sm font-medium text-neutral-700">
        Select Candidate {required && <span className="text-red-500">*</span>}
      </label>

      {candidates.length > 0 ? (
        <div className="relative" ref={dropdownRef}>
          {renderDropdownTrigger()}
          {renderDropdownList()}
        </div>
      ) : (
        renderEmptyState()
      )}

      {renderStatusInfo()}
    </div>
  )
}