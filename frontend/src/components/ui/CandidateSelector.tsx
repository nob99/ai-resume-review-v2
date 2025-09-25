import React, { useState, useEffect } from 'react'
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
  placeholder = 'Select a candidate...',
  disabled = false,
  required = false,
  className
}) => {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  const handleSelectChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = event.target.value
    if (selectedValue) {
      onSelect(selectedValue)
    }
  }

  if (loading) {
    return (
      <div className={cn('flex items-center space-x-2', className)}>
        <Loading size="sm" />
        <span className="text-sm text-neutral-600">Loading candidates...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn('text-sm text-red-600', className)}>
        {error}
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      <label className="block text-sm font-medium text-neutral-700">
        Select Candidate {required && <span className="text-red-500">*</span>}
      </label>
      <select
        value={value || ''}
        onChange={handleSelectChange}
        disabled={disabled}
        required={required}
        className={cn(
          'block w-full px-3 py-2 border border-neutral-300 rounded-md',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
          'bg-white text-neutral-900',
          'disabled:bg-neutral-100 disabled:text-neutral-500 disabled:cursor-not-allowed',
          className
        )}
      >
        <option value="">{placeholder}</option>
        {candidates.map((candidate) => (
          <option key={candidate.id} value={candidate.id}>
            {candidate.first_name} {candidate.last_name}
            {candidate.email && ` (${candidate.email})`}
          </option>
        ))}
      </select>

      {candidates.length === 0 && (
        <p className="text-sm text-neutral-600">
          No candidates found. You may need to create one first.
        </p>
      )}
    </div>
  )
}