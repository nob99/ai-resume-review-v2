'use client'

import { useState } from 'react'
import { Container, Section, Header } from '@/components/layout'
import { FileUpload } from '@/components/upload'
import { Card, Alert } from '@/components/ui'
import { ProtectedRoute, useAuth } from '@/lib/auth-context'
import { uploadApi } from '@/lib/api'
import { AuthExpiredError } from '@/types'

export default function UploadPage() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [uploadError, setUploadError] = useState<string | null>(null)
  const { handleAuthExpired } = useAuth()

  const handleFilesSelected = (files: File[]) => {
    console.log('Files selected:', files)
    setUploadedFiles(files)
    setUploadError(null)
  }

  const handleUpload = async (files: File[]) => {
    console.log('Uploading files:', files)
    setUploadError(null)
    
    try {
      // Upload files one by one and collect upload IDs
      const uploadIds: string[] = []
      
      for (const file of files) {
        const result = await uploadApi.uploadResume(file)
        
        if (!result.success) {
          if (result.error instanceof AuthExpiredError) {
            handleAuthExpired()
            return uploadIds
          }
          throw result.error
        }
        
        if (result.data) {
          uploadIds.push(result.data.id)
        }
      }
      
      console.log('Upload completed! IDs:', uploadIds)
      return uploadIds
      
    } catch (error) {
      console.error('Upload error:', error)
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
      throw error
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-50">
        <Header />
        <Container>
          <Section>
          <div className="max-w-4xl mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900">Upload Resume</h1>
              <p className="mt-2 text-lg text-gray-600">
                Upload resume files for AI-powered analysis. We support PDF, DOC, and DOCX formats.
              </p>
            </div>

            <Card className="p-6">
              <FileUpload
                onFilesSelected={handleFilesSelected}
                onUpload={handleUpload}
                multiple={true}
              />
            </Card>

            {uploadError && (
              <Alert 
                type="error" 
                className="mt-4"
                onClose={() => setUploadError(null)}
              >
                {uploadError}
              </Alert>
            )}

            {uploadedFiles.length > 0 && (
              <Card className="mt-6 p-6">
                <h2 className="text-lg font-semibold mb-4">Ready for Analysis</h2>
                <p className="text-gray-600">
                  {uploadedFiles.length} file{uploadedFiles.length !== 1 ? 's' : ''} selected and validated.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Click the upload button above to proceed with analysis.
                </p>
              </Card>
            )}
          </div>
          </Section>
        </Container>
      </div>
    </ProtectedRoute>
  )
}