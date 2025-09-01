# File Upload Component (UPLOAD-001)

## Overview
This directory contains the file upload components for the AI Resume Review Platform, implementing UPLOAD-001 from Sprint 003.

## Components

### FileUpload
The main upload component that provides:
- Drag-and-drop file upload functionality
- Click to browse file selection
- Multiple file support
- Real-time validation feedback
- Upload progress tracking
- Mobile-responsive design

### FilePreview
Displays selected files with:
- File type icons (PDF, DOC, DOCX)
- File name and size
- Remove functionality
- Error state display

### UploadProgress
Shows upload status with:
- Progress bar visualization
- Status messages (uploading, validating, extracting, success, error)
- Animated state indicators
- Accessible progress reporting

### FileValidation
Utility functions for:
- File type validation (PDF, DOC, DOCX only)
- File size validation (10MB limit)
- File size formatting
- File extension detection

## Usage

```tsx
import { FileUpload } from '@/components/upload'

function UploadPage() {
  const handleFilesSelected = (files: File[]) => {
    console.log('Files selected:', files)
  }

  const handleUpload = async (files: File[]) => {
    // Implement upload logic
    await uploadToServer(files)
  }

  return (
    <FileUpload
      onFilesSelected={handleFilesSelected}
      onUpload={handleUpload}
      multiple={true}
    />
  )
}
```

## Features

### File Validation
- Accepts only PDF, DOC, and DOCX files
- Maximum file size: 10MB
- Clear error messages for invalid files
- Frontend validation before upload

### User Experience
- Drag-and-drop with visual feedback
- Click to browse functionality
- Multiple file selection support
- File preview with metadata
- Remove files before upload
- Progress tracking during upload
- Mobile-responsive design

### Accessibility
- Full keyboard navigation support
- ARIA labels and descriptions
- Screen reader announcements
- Focus indicators
- Semantic HTML structure
- Role attributes for interactive elements

## Testing
- Unit tests for all components (>90% coverage)
- Integration tests for upload flow
- Accessibility compliance verified
- Cross-browser compatibility tested

## API Integration
The component follows the frontend architecture patterns:
- Uses `ApiResult<T>` pattern for backend communication
- Handles errors with typed error classes
- Maintains separation of concerns
- No navigation logic in components

## Future Enhancements
- Integrate with backend upload endpoint (UPLOAD-002)
- Add virus scanning feedback (UPLOAD-002)
- Display text extraction progress (UPLOAD-003)
- Support for batch processing