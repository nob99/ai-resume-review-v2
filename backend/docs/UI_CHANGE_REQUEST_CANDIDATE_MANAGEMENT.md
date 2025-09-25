# UI Change Request: Candidate Management & Resume Upload Integration

**Date**: September 24, 2025
**From**: Backend Engineering Team
**To**: Frontend Engineering Team
**Priority**: HIGH 🔴
**Blocking**: Resume Upload & Analysis Features

## Executive Summary

The backend has been refactored to implement a **candidate-centric architecture** where all resumes must be associated with a candidate record. The current frontend lacks the necessary UI components to create and select candidates before uploading resumes. This document outlines the required UI changes to enable the complete resume upload → analysis workflow.

## Background

### Architecture Change
We've moved from a simple file upload system to a two-feature architecture:
1. **Resume Upload**: Manages resume storage with candidate association
2. **Resume Analysis**: Performs AI analysis on uploaded resumes

### Key Requirement
**Every resume MUST be associated with a candidate.** This ensures:
- Proper access control and permissions
- Resume version management per candidate
- Organized data structure for recruitment consultants

## Current Backend API Endpoints

### 1. Candidate Management
```
GET    /api/v1/candidates/candidates/              # List all candidates for the user
POST   /api/v1/candidates/candidates/              # Create a new candidate
GET    /api/v1/candidates/candidates/{id}          # Get candidate details
PUT    /api/v1/candidates/candidates/{id}          # Update candidate
DELETE /api/v1/candidates/candidates/{id}          # Delete candidate
POST   /api/v1/candidates/candidates/{id}/assign/{user_id}  # Assign candidate to user
```

### 2. Resume Upload
```
POST   /api/v1/candidates/{candidate_id}/resumes   # Upload resume for candidate
GET    /api/v1/candidates/{candidate_id}/resumes   # List all resumes for candidate
GET    /api/v1/resumes/{resume_id}                # Get specific resume
DELETE /api/v1/resumes/{resume_id}                # Delete resume
```

### 3. Resume Analysis
```
POST   /api/v1/analysis/resumes/{resume_id}/analyze  # Request analysis
GET    /api/v1/analysis/analysis/{analysis_id}/status # Poll analysis status
GET    /api/v1/analysis/analysis/{analysis_id}       # Get analysis results
GET    /api/v1/analysis/resumes/{resume_id}/analyses # Get analysis history
```

## Required UI Changes

### 1. Candidate Management Page (NEW) 📋

Create a new page/section for managing candidates with the following features:

#### 1.1 Candidate List View
- **Table/Grid** displaying all candidates
- **Columns**: Name, Email, Phone, Created Date, # of Resumes
- **Search/Filter**: By name, email
- **Sort**: By name, date created
- **Actions**: View, Edit, Delete, Upload Resume

#### 1.2 Create Candidate Modal/Form
```javascript
// Required fields
{
  first_name: string,     // Required
  last_name: string,      // Required
  email: string,          // Optional but recommended
  phone: string,          // Optional
  linkedin_url: string,   // Optional
  notes: string          // Optional
}
```

#### 1.3 Quick Create Option
Add a "Quick Create" button in the resume upload flow for users who want to create a candidate on-the-fly.

### 2. Resume Upload Flow Modification 📤

#### Current Flow (Broken)
```
User clicks "Upload Resume" → File picker → Upload fails (no candidate)
```

#### Required New Flow
```
Option A: From Candidate Page
1. User navigates to Candidates page
2. Selects/creates a candidate
3. Clicks "Upload Resume" for that candidate
4. File picker opens
5. Resume uploads with candidate_id

Option B: From Upload Page (with candidate selection)
1. User clicks "Upload Resume"
2. Modal appears with:
   - Candidate dropdown/search
   - "Create New Candidate" button
3. User selects/creates candidate
4. File picker opens
5. Resume uploads with candidate_id
```

### 3. Component Implementation Suggestions

#### 3.1 CandidateSelector Component
```tsx
interface CandidateSelectorProps {
  onSelect: (candidateId: string) => void;
  allowCreate?: boolean;
  required?: boolean;
}

// Features:
// - Searchable dropdown
// - Recent candidates section
// - "Create New" option
// - Shows candidate email for disambiguation
```

#### 3.2 CandidateQuickCreate Component
```tsx
interface CandidateQuickCreateProps {
  onCreated: (candidate: Candidate) => void;
  onCancel: () => void;
}

// Minimal form with just:
// - First Name (required)
// - Last Name (required)
// - Email (optional)
// - Auto-closes and returns created candidate
```

#### 3.3 ResumeUploadButton Component Update
```tsx
// Add candidate context
interface ResumeUploadButtonProps {
  candidateId?: string;  // If provided, skip selection
  onUploadComplete: (resumeId: string) => void;
}

// If candidateId not provided, show candidate selector first
```

### 4. User Experience Flows

#### 4.1 Recruitment Consultant Workflow
1. **Morning**: Receives 10 resumes via email
2. **Batch Process**:
   - Goes to Candidates page
   - Creates candidates for new applicants
   - Uploads resumes to respective candidates
   - Bulk analyzes resumes
   - Reviews analysis results

#### 4.2 Quick Review Workflow
1. **Urgent**: Single resume needs quick review
2. **Quick Process**:
   - Click "Upload Resume"
   - Use "Quick Create" to add candidate
   - Upload and analyze in one flow
   - Get results immediately

### 5. API Integration Examples

#### 5.1 Create Candidate
```javascript
POST /api/v1/candidates/candidates/
Authorization: Bearer {token}
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com",
  "phone": "+1-555-0123"
}

Response:
{
  "id": "d72eaab2-2dfb-47cb-b888-4fb4f3405593",
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com",
  "created_at": "2025-09-24T04:50:00Z"
}
```

#### 5.2 Upload Resume for Candidate
```javascript
POST /api/v1/candidates/{candidate_id}/resumes
Authorization: Bearer {token}
Content-Type: multipart/form-data

FormData:
- file: resume.pdf

Response:
{
  "id": "resume-uuid",
  "file": {...},
  "status": "completed",
  "extractedText": "..."
}
```

#### 5.3 Request Analysis
```javascript
POST /api/v1/analysis/resumes/{resume_id}/analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "industry": "strategy_tech",
  "analysis_depth": "standard",
  "focus_areas": ["structure", "content"],
  "compare_to_market": true
}

Response:
{
  "success": true,
  "analysis_id": "analysis-uuid",
  "status": "processing"
}
```

### 6. Error Handling

Please handle these common error cases:

#### 6.1 No Candidate Selected
```javascript
if (!candidateId) {
  showError("Please select or create a candidate before uploading a resume");
  showCandidateSelector();
}
```

#### 6.2 Duplicate Candidate
```javascript
// Backend returns 409 if email already exists
if (error.status === 409) {
  showMessage("A candidate with this email already exists");
  // Option to use existing candidate
}
```

#### 6.3 Upload Without Authentication
```javascript
if (error.status === 401) {
  redirectToLogin();
}
```

### 7. Testing Support

We've created test candidates for development:

| Name | Email | Candidate ID |
|------|-------|--------------|
| John Smith | john.smith@example.com | `d72eaab2-2dfb-47cb-b888-4fb4f3405593` |
| Sarah Johnson | sarah.johnson@example.com | `1b36c029-b9f0-413e-8fc2-8c2e43d37630` |
| Michael Chen | michael.chen@example.com | `03d5e3e1-36ab-41f1-84db-6a5363ae3ebc` |

Use these for testing the upload flow before the candidate UI is complete.

## Implementation Priority

### Phase 1: Minimum Viable Implementation (URGENT)
1. **Candidate Quick Create** - Simple modal with name/email
2. **Candidate Selector** - Dropdown in upload flow
3. **Update Upload API** - Include candidate_id in requests

### Phase 2: Full Candidate Management (NEXT WEEK)
1. **Candidate List Page** - Full CRUD interface
2. **Candidate Details View** - Show all resumes/analyses
3. **Bulk Operations** - Select multiple candidates for actions

### Phase 3: Enhanced Features (FUTURE)
1. **Candidate Import** - CSV/Excel upload
2. **Candidate Tags/Categories** - Organization features
3. **Candidate Pipeline** - Track recruitment stages

## Success Criteria

✅ Users can create a candidate before uploading resumes
✅ All resume uploads are associated with a candidate
✅ Users can view all resumes for a candidate
✅ Users can manage their candidate database
✅ The upload → analyze workflow is seamless

## Questions for Frontend Team

1. Do you prefer a modal or dedicated page for candidate management?
2. Should we implement keyboard shortcuts for quick candidate creation?
3. Do you want to cache candidate data locally for offline support?
4. Should we add candidate profile photos support?
5. What's your preference for the candidate selector UI component?

## Backend Support

The backend team is available to:
- Add any additional API endpoints needed
- Modify response formats if required
- Provide test data generation scripts
- Assist with API integration issues

## Contact

**Backend Team Lead**: backend@airesumereview.com
**API Documentation**: http://localhost:8000/docs
**Test Environment**: http://localhost:8000

---

**Note**: This is a breaking change. The resume upload feature will not work until these UI changes are implemented. We recommend implementing Phase 1 immediately to unblock the core functionality.