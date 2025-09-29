'use client'

import React from 'react'
import { Container, Section, Header } from '@/components/layout'
import { Card, CardHeader, CardContent, Button, CandidateSelector } from '@/components/ui'
import FileUpload from '../components/FileUpload'
import FileList from '../components/FileList'
import IndustrySelector from '../components/IndustrySelector'
import UploadStats from '../components/UploadStats'
import AnalysisResults from '../components/AnalysisResults'
import useUploadFlow from '../hooks/useUploadFlow'
import { INDUSTRY_OPTIONS } from '../types'

/**
 * Upload Page Component
 * Main upload and analysis workflow
 */
const UploadPage: React.FC = () => {
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
    <div className="min-h-screen bg-neutral-50">
      <Header />

      <main className="py-8">
        <Container size="lg">
          <div className="max-w-4xl mx-auto">
            {/* Page Header */}
            <Section className="text-center mb-8">
              <h1 className="text-3xl font-bold text-neutral-900 mb-4">
                Upload Resume Files
              </h1>
              <p className="text-lg text-neutral-600 max-w-2xl mx-auto">
                Upload your resume files to get started with AI-powered analysis.
                Support for PDF and Word documents up to 10MB each.
              </p>
            </Section>

            <div className="space-y-8">
              {/* Candidate Selection */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Step 1: Select Candidate
                  </h2>
                </CardHeader>
                <CardContent>
                  <CandidateSelector
                    value={state.selectedCandidate}
                    onSelect={setSelectedCandidate}
                    placeholder="Select a candidate..."
                    required={true}
                  />
                </CardContent>
              </Card>

              {/* File Upload */}
              <Card>
                <CardHeader>
                  <h2 className="text-xl font-semibold text-neutral-900">
                    Step 2: Select Resume Files
                  </h2>
                </CardHeader>
                <CardContent>
                  <FileUpload
                    onFilesSelected={fileHandlers.onFilesSelected}
                    onError={fileHandlers.onUploadError}
                    disabled={state.isUploading || !state.selectedCandidate}
                    multiple={true}
                    maxFiles={5}
                  />
                  {!state.selectedCandidate && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                      <p className="text-sm text-yellow-800">
                        Please select a candidate first before uploading files.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* File List */}
              {state.files.length > 0 && (
                <Card>
                  <CardHeader>
                    <h2 className="text-xl font-semibold text-neutral-900">
                      Selected Files ({state.files.length})
                    </h2>
                  </CardHeader>
                  <CardContent>
                    <FileList
                      files={state.files}
                      onCancelFile={fileHandlers.onCancelFile}
                      onRetryFile={fileHandlers.onRetryFile}
                      onRemoveFile={fileHandlers.onRemoveFile}
                    />
                  </CardContent>
                </Card>
              )}

              {/* Upload Actions */}
              {state.files.length > 0 && (
                <div className="flex justify-center space-x-4">
                  {pendingFiles.length > 0 && (
                    <Button
                      size="lg"
                      onClick={fileHandlers.onStartUpload}
                      disabled={state.isUploading || !state.selectedCandidate}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white"
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

                  {successFiles.length > 0 && uploadingFiles.length === 0 && !state.analysisResult && (
                    <IndustrySelector
                      selectedIndustry={state.selectedIndustry}
                      onIndustryChange={setSelectedIndustry}
                      onStartAnalysis={analysisHandlers.onStartAnalysis}
                      isAnalyzing={state.isAnalyzing}
                      analysisStatus={state.analysisStatus}
                      industryOptions={INDUSTRY_OPTIONS}
                    />
                  )}
                </div>
              )}

              {/* Analysis Results */}
              {state.analysisResult && (
                <AnalysisResults
                  analysis={state.analysisResult}
                  industryOptions={INDUSTRY_OPTIONS}
                  onAnalyzeAgain={analysisHandlers.onAnalyzeAgain}
                  onUploadNew={analysisHandlers.onUploadNew}
                />
              )}

              {/* Summary Stats */}
              <UploadStats
                files={state.files}
                uploadingFiles={uploadingFiles}
                successFiles={successFiles}
                errorFiles={errorFiles}
              />
            </div>
          </div>
        </Container>
      </main>
    </div>
  )
}

export default UploadPage