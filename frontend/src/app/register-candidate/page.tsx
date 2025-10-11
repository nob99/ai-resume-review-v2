'use client'

import React from 'react'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import CandidateRegistrationForm from '@/components/forms/CandidateRegistrationForm'

const RegisterCandidatePage: React.FC = () => {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <main className="py-8">
          <Container size="lg">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                候補者の登録
              </h1>
              <p className="text-lg text-neutral-600">
                新しい候補者をシステムに登録してレジュメを分析できます
              </p>
            </div>

            <CandidateRegistrationForm />
          </Container>
        </main>
      </div>
    </ProtectedRoute>
  )
}

export default RegisterCandidatePage