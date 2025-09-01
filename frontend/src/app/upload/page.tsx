'use client'

import { useState } from 'react'
import { Container, Section, Header } from '@/components/layout'
import { FileUpload } from '@/components/upload'
import { Card } from '@/components/ui'
import { ProtectedRoute } from '@/lib/auth-context'

export default function UploadPage() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])

  const handleFilesSelected = (files: File[]) => {
    console.log('Files selected:', files)
    setUploadedFiles(files)
  }

  const handleUpload = async (files: File[]) => {
    console.log('Uploading files:', files)
    
    // Simulate upload delay
    await new Promise(resolve => setTimeout(resolve, 3000))
    
    // TODO: Implement actual upload to backend
    console.log('Upload completed!')
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