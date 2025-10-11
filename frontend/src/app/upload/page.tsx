'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/contexts/AuthContext'
import { Container, Header } from '@/components/layout'
import { Card, CardHeader, CardContent, Button, CandidateSelector } from '@/components/ui'
import FileUpload from '@/features/upload/components/FileUpload'
import FileList from '@/features/upload/components/FileList'
import IndustrySelector from '@/features/upload/components/IndustrySelector'
import AnalysisResults from '@/features/upload/components/AnalysisResults'
import useUploadFlow from '@/features/upload/hooks/useUploadFlow'
import { INDUSTRY_OPTIONS } from '@/features/upload/types'

/**
 * Upload Page Component
 * Main upload and analysis workflow
 */
const UploadPage: React.FC = () => {
  const router = useRouter()
  const {
    state,
    pendingFiles,
    uploadingFiles,
    successFiles,
    errorFiles,
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
                {/* Candidate Selection */}
                <Card>
                  <CardHeader>
                    <h2 className="text-xl font-semibold text-neutral-900">
                      Step 1: 候補者の選択
                    </h2>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-4">
                    <CandidateSelector
                      value={state.selectedCandidate}
                      onSelect={setSelectedCandidate}
                      placeholder="Select a candidate..."
                      required={true}
                    />

                    {/* Helper: Register new candidate */}
                    <div className="p-3 bg-neutral-50 border border-neutral-200 rounded-md">
                      <p className="text-sm text-neutral-700 mb-2">
                        候補者が見つからない場合は、まず候補者を登録してください  {' '}
                        <button
                          onClick={() => router.push('/register-candidate')}
                          className="font-medium text-blue-600 hover:text-blue-700 underline"
                        >
                          [候補者登録ページ]
                        </button>
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Step 2: File Upload */}
                <Card className={!state.selectedCandidate ? 'opacity-60' : ''}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <h2 className="text-xl font-semibold text-neutral-900">
                        Step 2: レジュメの選択
                      </h2>
                      {!state.selectedCandidate && (
                        <span className="text-sm text-neutral-500 bg-neutral-100 px-3 py-1 rounded-full">
                          Step 1を完了してください
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-4">
                    <FileUpload
                      onFilesSelected={fileHandlers.onFilesSelected}
                      onError={fileHandlers.onUploadError}
                      disabled={state.isUploading || !state.selectedCandidate}
                      multiple={false}
                      maxFiles={1}
                    />
                    {!state.selectedCandidate && (
                      <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                        <p className="text-sm text-yellow-800">
                          候補者を選択してからレジュメをアップロードしてください
                        </p>
                      </div>
                    )}

                    {/* File List */}
                    {state.files.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="font-semibold text-neutral-900">
                          Selected Files ({state.files.length})
                        </h3>
                        <FileList
                          files={state.files}
                          onCancelFile={fileHandlers.onCancelFile}
                          onRetryFile={fileHandlers.onRetryFile}
                          onRemoveFile={fileHandlers.onRemoveFile}
                        />
                      </div>
                    )}

                    {/* Upload Button */}
                    {pendingFiles.length > 0 && (
                      <Button
                        size="lg"
                        onClick={fileHandlers.onStartUpload}
                        disabled={state.isUploading || !state.selectedCandidate}
                        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
                      >
                        {state.isUploading ? (
                          <>
                            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-3"></div>
                            Uploading...
                          </>
                        ) : (
                          `Upload ${pendingFiles.length} File${pendingFiles.length !== 1 ? 's' : ''}`
                        )}
                      </Button>
                    )}
                  </CardContent>
                </Card>

                {/* Step 3: Industry Selection & Analysis */}
                <Card className={successFiles.length === 0 ? 'opacity-60' : ''}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <h2 className="text-xl font-semibold text-neutral-900">
                        Step 3: 応募する業界の選択 & AI分析
                      </h2>
                      {successFiles.length === 0 && (
                        <span className="text-sm text-neutral-500 bg-neutral-100 px-3 py-1 rounded-full">
                          Step 2を完了してください
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="pt-6">
                    {successFiles.length === 0 ? (
                      <div className="p-8 text-center bg-neutral-50 rounded-lg border-2 border-dashed border-neutral-200">
                        <div className="text-4xl mb-3">📊</div>
                        <p className="text-neutral-600 font-medium mb-1">
                          業界の選択
                        </p>
                        <p className="text-sm text-neutral-500">
                          レジュメをアップロードしてStep 2を完了してください
                        </p>
                      </div>
                    ) : (
                      <IndustrySelector
                        selectedIndustry={state.selectedIndustry}
                        onIndustryChange={setSelectedIndustry}
                        onStartAnalysis={analysisHandlers.onStartAnalysis}
                        isAnalyzing={state.isAnalyzing}
                        analysisStatus={state.analysisStatus}
                        industryOptions={INDUSTRY_OPTIONS}
                        elapsedTime={state.elapsedTime}
                      />
                    )}
                  </CardContent>
                </Card>

                {/* Analysis Results */}
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