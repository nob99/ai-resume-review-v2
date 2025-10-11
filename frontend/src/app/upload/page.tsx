'use client'

import React from 'react'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import { CandidateSelectionSection } from '@/features/upload/components/candidate-selection'
import { FileUploadSection } from '@/features/upload/components/file-upload'
import { IndustrySelectionSection } from '@/features/upload/components/industry-selection'
import { AnalysisResults } from '@/features/upload/components/analysis-results'
import useUploadFlow from '@/features/upload/hooks/useUploadFlow'
import { INDUSTRY_OPTIONS } from '@/features/upload/types'

/**
 * Upload Page Component
 * Main upload and analysis workflow with 4 clear steps
 */
const UploadPage: React.FC = () => {
  const {
    state,
    pendingFiles,
    successFiles,
    fileHandlers,
    analysisHandlers,
    setSelectedCandidate,
    setSelectedIndustry
  } = useUploadFlow()

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />

        <main className="py-8">
          <Container size="lg">
            {/* Page Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                レジュメのアップロード&AI分析
              </h1>
              <p className="text-lg text-neutral-600">
                レジュメファイルをアップロードして、AI分析を開始しましょう。PDF及びWordドキュメント（各30MBまで）に対応しています
              </p>
            </div>

            <div className="space-y-8">
              {/* Step 1: Candidate Selection */}
              <CandidateSelectionSection
                selectedCandidate={state.selectedCandidate}
                onSelectCandidate={setSelectedCandidate}
              />

              {/* Step 2: File Upload */}
              <FileUploadSection
                files={state.files}
                pendingFilesCount={pendingFiles.length}
                isUploading={state.isUploading}
                disabled={!state.selectedCandidate}
                onFilesSelected={fileHandlers.onFilesSelected}
                onUploadError={fileHandlers.onUploadError}
                onStartUpload={fileHandlers.onStartUpload}
                onCancelFile={fileHandlers.onCancelFile}
                onRetryFile={fileHandlers.onRetryFile}
                onRemoveFile={fileHandlers.onRemoveFile}
              />

              {/* Step 3: Industry Selection & Analysis */}
              <IndustrySelectionSection
                selectedIndustry={state.selectedIndustry}
                onIndustryChange={setSelectedIndustry}
                onStartAnalysis={analysisHandlers.onStartAnalysis}
                isAnalyzing={state.isAnalyzing}
                analysisStatus={state.analysisStatus}
                industryOptions={INDUSTRY_OPTIONS}
                elapsedTime={state.elapsedTime}
                disabled={successFiles.length === 0}
                hasResults={!!state.analysisResult}
              />

              {/* Step 4: Analysis Results */}
              {state.analysisResult && (
                <AnalysisResults
                  analysis={state.analysisResult}
                  industryOptions={INDUSTRY_OPTIONS}
                  onAnalyzeAgain={analysisHandlers.onAnalyzeAgain}
                  onUploadNew={analysisHandlers.onUploadNew}
                  elapsedTime={state.elapsedTime}
                />
              )}
            </div>
          </Container>
        </main>
      </div>
    </ProtectedRoute>
  )
}

export default UploadPage
