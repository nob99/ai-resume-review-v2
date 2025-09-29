'use client'

import React from 'react'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Section, Header } from '@/components/layout'
import CandidateRegistrationForm from '@/components/forms/CandidateRegistrationForm'

const RegisterCandidatePage: React.FC = () => {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <Section spacing="lg">
          <Container>
            <div className="max-w-2xl mx-auto">
              <CandidateRegistrationForm />
            </div>
          </Container>
        </Section>
      </div>
    </ProtectedRoute>
  )
}

export default RegisterCandidatePage