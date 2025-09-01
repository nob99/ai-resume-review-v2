'use client'

import React, { useState } from 'react'
import { TextExtractionResult, ResumeSection } from '@/types'
import { Card, CardHeader, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui'

interface ExtractedTextPreviewProps {
  extractionResult: TextExtractionResult
  showFullText?: boolean
  className?: string
}

interface SectionDisplayProps {
  section: ResumeSection
  isExpanded: boolean
  onToggle: () => void
}

const SectionDisplay: React.FC<SectionDisplayProps> = ({ section, isExpanded, onToggle }) => {
  const confidenceColor = section.confidence >= 0.8 
    ? 'text-green-600' 
    : section.confidence >= 0.6 
    ? 'text-yellow-600' 
    : 'text-red-600'

  return (
    <div className="border border-gray-200 rounded-lg mb-2">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 text-left flex items-center justify-between bg-gray-50 rounded-t-lg hover:bg-gray-100 transition-colors"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center space-x-3">
          <span className="font-medium text-gray-900">
            {section.section_name}
          </span>
          <span className={`text-xs px-2 py-1 rounded-full bg-gray-200 ${confidenceColor}`}>
            {Math.round(section.confidence * 100)}% confidence
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {isExpanded && (
        <div className="px-4 py-3 bg-white rounded-b-lg">
          <div className="text-sm text-gray-600 mb-2">
            Characters: {section.start_position} - {section.end_position} ({section.end_position - section.start_position} chars)
          </div>
          <div className="text-sm text-gray-900 whitespace-pre-wrap break-words bg-gray-50 p-3 rounded border-l-4 border-blue-200">
            {section.content}
          </div>
        </div>
      )}
    </div>
  )
}

export const ExtractedTextPreview: React.FC<ExtractedTextPreviewProps> = ({
  extractionResult,
  showFullText: initialShowFullText = false,
  className = ''
}) => {
  const [showFullText, setShowFullText] = useState(initialShowFullText)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())

  const toggleSection = (sectionName: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionName)) {
      newExpanded.delete(sectionName)
    } else {
      newExpanded.add(sectionName)
    }
    setExpandedSections(newExpanded)
  }

  const toggleAllSections = () => {
    if (expandedSections.size === extractionResult.sections.length) {
      setExpandedSections(new Set())
    } else {
      setExpandedSections(new Set(extractionResult.sections.map(s => s.section_name)))
    }
  }

  const previewText = extractionResult.extracted_text || extractionResult.processed_text || ''
  const displayText = showFullText ? previewText : previewText.slice(0, 300)
  const hasMoreText = previewText.length > 300

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString()
  }

  return (
    <div className={`w-full space-y-4 ${className}`}>
      {/* Summary Card */}
      <Card variant="outlined">
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              Extracted Text Summary
            </h3>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full">
                {extractionResult.extraction_status}
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Word Count:</span>
              <p className="text-gray-900">{extractionResult.word_count.toLocaleString()}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Sections:</span>
              <p className="text-gray-900">{extractionResult.sections.length}</p>
            </div>
            <div>
              <span className="font-medium text-gray-600">Extracted:</span>
              <p className="text-gray-900">{formatTimestamp(extractionResult.created_at)}</p>
            </div>
            {extractionResult.extraction_time && (
              <div>
                <span className="font-medium text-gray-600">Processing Time:</span>
                <p className="text-gray-900">{(extractionResult.extraction_time * 1000).toFixed(0)}ms</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Text Preview */}
      {previewText && (
        <Card variant="outlined">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h4 className="text-md font-medium text-gray-900">
                Extracted Text
              </h4>
              {hasMoreText && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowFullText(!showFullText)}
                >
                  {showFullText ? 'Show Less' : 'Show More'}
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="bg-gray-50 p-4 rounded border text-sm text-gray-900 whitespace-pre-wrap break-words max-h-64 overflow-y-auto">
              {displayText}
              {!showFullText && hasMoreText && (
                <span className="text-gray-500">... (truncated)</span>
              )}
            </div>
            {hasMoreText && (
              <div className="mt-2 text-xs text-gray-500">
                Showing {showFullText ? previewText.length : displayText.length} of {previewText.length} characters
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Sections */}
      {extractionResult.sections.length > 0 && (
        <Card variant="outlined">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h4 className="text-md font-medium text-gray-900">
                Detected Resume Sections ({extractionResult.sections.length})
              </h4>
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleAllSections}
              >
                {expandedSections.size === extractionResult.sections.length ? 'Collapse All' : 'Expand All'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {extractionResult.sections
                .sort((a, b) => b.confidence - a.confidence) // Sort by confidence descending
                .map((section) => (
                <SectionDisplay
                  key={section.section_name}
                  section={section}
                  isExpanded={expandedSections.has(section.section_name)}
                  onToggle={() => toggleSection(section.section_name)}
                />
              ))}
            </div>
            
            {extractionResult.sections.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <p>No resume sections were detected in the extracted text.</p>
                <p className="text-sm mt-1">This could indicate the document structure is unclear or non-standard.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {extractionResult.error_message && (
        <Card variant="outlined">
          <CardContent className="bg-red-50 border-red-200">
            <div className="flex items-center text-red-600 mb-2">
              <svg 
                className="w-4 h-4 mr-2" 
                fill="currentColor" 
                viewBox="0 0 20 20"
              >
                <path 
                  fillRule="evenodd" 
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" 
                  clipRule="evenodd" 
                />
              </svg>
              <span className="font-semibold">Extraction Error</span>
            </div>
            <p className="text-sm text-red-700">{extractionResult.error_message}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}