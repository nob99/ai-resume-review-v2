# UPLOAD-001 API Requirements for Backend Implementation

**Document Version**: 1.0  
**Created**: September 2, 2025  
**Frontend Implementation**: ✅ Complete  
**Backend Implementation**: 🔄 Required  
**Sprint**: Sprint-003  

---

## 🎯 Overview

The frontend file upload system (UPLOAD-001) has been fully implemented and tested. This document specifies the exact API requirements that the backend must implement to support the frontend functionality.

**Frontend Status**: Complete with comprehensive testing, progress tracking, and error handling  
**Backend Required**: API endpoints and business logic as specified below

---

## 📋 Required API Endpoints

### 1. **File Upload Endpoint**

```http
POST /api/v1/upload/resume
Content-Type: multipart/form-data
Authorization: Bearer {jwt_token}
```

**Request Format:**
```typescript
FormData {
  file: File,                    // PDF, DOC, or DOCX file
  targetRole?: string,           // Optional: target job role
  targetIndustry?: string,       // Optional: target industry  
  experienceLevel?: string       // Optional: 'junior'|'mid'|'senior'
}
```

**Success Response (200):**
```json
{
  "id": "uuid-string",
  "status": "pending",
  "filename": "resume.pdf",
  "size": 1048576,
  "uploadedAt": "2025-09-02T10:30:00Z"
}
```

**Error Responses:**
- `400` - File validation failed
- `401` - Authentication required/invalid
- `413` - File size exceeds limit
- `415` - Unsupported file type
- `429` - Rate limit exceeded
- `500` - Server error

---

### 2. **Upload Status Tracking**

```http
GET /api/v1/upload/{uploadId}/status
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "id": "uuid-string",
  "status": "extracting",
  "progress": 75,
  "filename": "resume.pdf",
  "size": 1048576,
  "uploadedAt": "2025-09-02T10:30:00Z",
  "extractedText": null,
  "error": null,
  "processingTime": 2500
}
```

**Status Values:**
- `pending` - File uploaded, queued for processing
- `validating` - File validation and security scan in progress
- `extracting` - Text extraction in progress  
- `completed` - Processing complete, text extracted
- `error` - Processing failed

---

### 3. **Upload Management**

**List Uploads:**
```http
GET /api/v1/upload/list?page=1&per_page=10
Authorization: Bearer {jwt_token}
```

**Response:**
```json
{
  "uploads": [
    {
      "id": "uuid-string",
      "filename": "resume.pdf",
      "status": "completed",
      "uploadedAt": "2025-09-02T10:30:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 10
}
```

**Delete Upload:**
```http
DELETE /api/v1/upload/{uploadId}
Authorization: Bearer {jwt_token}
```

**Response:** `204 No Content`

---

## 🛡️ File Validation Requirements

### **File Type Validation**

**Allowed MIME Types:**
- `application/pdf`
- `application/msword` (DOC)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX)

**Validation Logic:**
1. Check file extension (`.pdf`, `.doc`, `.docx`)
2. Verify MIME type from HTTP headers
3. **CRITICAL**: Validate file signature/magic numbers (not just extension)
4. Ensure MIME type matches file content

### **File Size Limits**
- **Maximum**: 10MB per file
- **Minimum**: 1KB (detect empty/corrupted files)
- **Frontend Display**: Shows "Max 10MB" to users

### **Security Requirements**
- **Virus Scanning**: Integration with ClamAV or cloud-based scanning
- **Filename Validation**: Safe characters only, no path traversal
- **Memory Limits**: Prevent DoS attacks with large files
- **Rate Limiting**: Max 10 uploads per user per hour

---

## 🔤 Text Extraction Pipeline

### **Processing Stages**

1. **File Validation** (status: `validating`)
   - MIME type verification
   - File signature check
   - Virus/malware scan
   - Size validation

2. **Text Extraction** (status: `extracting`)
   - **PDF**: Use PyPDF2/pdfplumber for text extraction
   - **DOC/DOCX**: Use python-docx for Word documents
   - Handle various formatting (columns, tables, headers)
   - Preserve text structure where possible

3. **Text Processing** (status: `extracting`)
   - Clean extracted text
   - Normalize whitespace and encoding
   - Remove excessive line breaks
   - Structure detection (sections, headers)

4. **Completion** (status: `completed`)
   - Return cleaned text in structured format
   - Clean up temporary files
   - Update final status

### **Text Extraction Output Format**

When status is `completed`, include:
```json
{
  "extractedText": "JOHN DOE\n\nSENIOR SOFTWARE ENGINEER\n\nEXPERIENCE\n...",
  "metadata": {
    "wordCount": 450,
    "characterCount": 2800,
    "extractionMethod": "pdfplumber",
    "sections": ["contact", "experience", "education", "skills"]
  },
  "processingTime": 2500
}
```

---

## ⚠️ Error Handling Specifications

### **Standard Error Response Format**
```json
{
  "detail": "Human-readable error message",
  "status_code": 400,
  "error_code": "FILE_TOO_LARGE",
  "timestamp": "2025-09-02T10:30:00Z"
}
```

### **Common Error Scenarios**

**File Validation Errors (400):**
```json
{
  "detail": "File type not supported. Please upload PDF, DOC, or DOCX files only.",
  "status_code": 400,
  "error_code": "INVALID_FILE_TYPE"
}
```

**File Size Errors (413):**
```json
{
  "detail": "File size exceeds 10MB limit. Current size: 15.2MB",
  "status_code": 413,
  "error_code": "FILE_TOO_LARGE"
}
```

**Security Errors (400):**
```json
{
  "detail": "File failed security scan. Upload rejected.",
  "status_code": 400,
  "error_code": "SECURITY_SCAN_FAILED"
}
```

**Text Extraction Errors (422):**
```json
{
  "detail": "Text extraction failed. File may be corrupted or password-protected.",
  "status_code": 422,
  "error_code": "EXTRACTION_FAILED"
}
```

**Rate Limiting (429):**
```json
{
  "detail": "Too many upload requests. Please try again in 10 minutes.",
  "status_code": 429,
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

---

## 🚀 Performance Requirements

### **Response Time Targets**
- **File upload endpoint**: <2 seconds initial response
- **Text extraction**: <15 seconds for typical resume (2-4 pages)
- **Status polling**: <500ms response time
- **Total processing**: <30 seconds for 10MB files

### **Concurrency Requirements**
- Support **10 simultaneous uploads** per server instance
- Queue system for handling peak loads
- Graceful degradation under high load

### **Memory Management**
- **Maximum memory per upload**: 500MB
- Stream processing for large files
- Immediate cleanup of temporary files
- No persistent file storage (privacy requirement)

---

## 🔐 Security & Privacy Requirements

### **Data Privacy**
- **NO persistent file storage** - process and delete immediately
- Files exist only in memory during processing
- Complete cleanup on success/failure
- No file content logged (only metadata)

### **Authentication**
- JWT Bearer token required for all endpoints
- Token validation on every request
- Automatic token refresh handling (frontend implemented)
- User-scoped uploads (users only see their own)

### **Security Headers**
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY  
X-XSS-Protection: 1; mode=block
```

### **Rate Limiting**
- **Upload endpoint**: 10 requests/hour per user
- **Status endpoint**: 100 requests/minute per user
- IP-based blocking for abuse detection

### **Logging Requirements**
```json
{
  "timestamp": "2025-09-02T10:30:00Z",
  "user_id": "user-uuid",
  "action": "file_upload",
  "filename": "resume.pdf",
  "file_size": 1048576,
  "status": "completed",
  "processing_time": 2500,
  "ip_address": "192.168.1.100"
}
```

**DO NOT LOG**: File content, extracted text, or sensitive data

---

## 🧪 Testing Requirements

### **Test Coverage Required**
- Unit tests for file validation logic
- Integration tests for text extraction pipeline
- Security tests for malware/virus scenarios
- Performance tests with various file sizes
- Error handling for all failure scenarios

### **Test Data Needed**
- Sample PDFs with various layouts
- Sample DOC/DOCX files
- Malformed/corrupted files
- Password-protected documents
- Large files (8-10MB) for performance testing

---

## 📊 Monitoring & Metrics

### **Key Metrics to Track**
- Upload success rate (target: >98%)
- Text extraction accuracy (manual spot-checks)
- Average processing time by file type/size
- Error rates by error type
- Memory usage during processing
- Concurrent upload handling

### **Alerts Configuration**
- Processing time > 30 seconds
- Memory usage > 500MB per upload
- Error rate > 5% over 10 minutes
- Queue backlog > 50 items

---

## 🔗 Integration Points

### **Frontend Integration**
- Frontend polls status endpoint every 2 seconds during processing
- Progress updates trigger UI state changes
- Error responses display user-friendly messages
- Success completion enables "Proceed to Analysis" button

### **Future AI Integration (Sprint 004)**
- Extracted text format ready for AI processing
- Upload completion triggers available for AI pipeline
- User metadata (role, industry, experience) passed to AI analysis

---

## ✅ Definition of Done

Backend implementation is complete when:

- [ ] All API endpoints implemented and tested
- [ ] File validation with security scanning working
- [ ] Text extraction for PDF/DOC/DOCX formats
- [ ] Progress tracking with real-time status updates
- [ ] Comprehensive error handling with user-friendly messages
- [ ] Performance benchmarks met (15 seconds extraction)
- [ ] Security requirements implemented (no persistent storage)
- [ ] Rate limiting and authentication working
- [ ] Unit and integration tests passing (>80% coverage)
- [ ] Frontend integration tested and working
- [ ] Monitoring and logging implemented
- [ ] Documentation updated in `backend/README.md`

---

## 📞 Frontend Team Contact

For questions about this specification or integration testing:
- **Frontend Implementation**: Fully complete with tests
- **API Contract**: This document is the definitive specification
- **Integration Support**: Available for joint testing sessions

**Next Step**: Backend team implements APIs per this specification, then joint integration testing.

---

*Document prepared by Frontend Team based on complete UPLOAD-001 implementation*