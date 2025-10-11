'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardHeader, CardContent, CandidateSelector } from '@/components/ui'

/**
 * CandidateSelectionSection Component
 * Main section component for Step 1: Candidate Selection
 * Handles candidate selection with helper text to register new candidates
 */

interface CandidateSelectionSectionProps {
  selectedCandidate: string
  onSelectCandidate: (candidateId: string) => void
}

export default function CandidateSelectionSection({
  selectedCandidate,
  onSelectCandidate
}: CandidateSelectionSectionProps) {
  const router = useRouter()

  return (
    <Card>
      <CardHeader>
        <h2 className="text-xl font-semibold text-neutral-900">
          Step 1: 候補者の選択
        </h2>
      </CardHeader>
      <CardContent className="pt-6 space-y-4">
        <CandidateSelector
          value={selectedCandidate}
          onSelect={onSelectCandidate}
          placeholder="Select a candidate..."
          required={true}
        />

        {/* Helper: Register new candidate */}
        <div className="p-3 bg-neutral-50 border border-neutral-200 rounded-md">
          <div className="flex items-center gap-1 text-sm text-neutral-700">
            <span>候補者が見つからない場合は、まず候補者を登録してください</span>
            <button
              onClick={() => router.push('/register-candidate')}
              className="font-medium text-blue-600 hover:text-blue-700 underline"
            >
              [候補者登録ページ]
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
