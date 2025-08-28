# Backend Requirements

## 1. Overview
The backend service built with FastAPI handles authentication, file processing, AI agent orchestration, and result management. It follows a simple, scalable design with configurable LLM support and minimal external dependencies.

### Key Principles
- Single analysis at a time per user (no concurrency)
- Raw XML output from AI agents passed to frontend
- Configurable LLM providers (OpenAI for MVP)
- 24-hour session duration
- Soft delete for user accounts

## 2. Business Logic Rules

### 2.1 Authentication & Authorization
- **User Roles**: 
  - Admin: Full access + user management
  - Consultant: Upload resumes, view own results
- **Session Duration**: 24 hours from login
- **Password Policy**: No complexity requirements (MVP)
- **Password Reset**: 
  - Admin only: Manual process via Slack request
  - Admin generates new password in UI

### 2.2 User Management
- **User Creation**: Admin only
- **User Deletion**: Soft delete (keeps data, marks inactive)
- **Data Access**: Deleted user's analyses remain in DB
- **Concurrent Users**: Unlimited

### 2.3 Analysis Constraints
- **Concurrent Analyses**: One per user at a time
- **File Types**: PDF and DOCX documents only
- **File Size**: Maximum 10MB
- **Processing Queue**: Sequential per user

## 3. AI Agent Behavior Details

### 3.1 LLM Configuration
- **Supported Providers** (Future):
  - OpenAI (GPT-5)
  - Anthropic (Claude)
  - Google (Gemini)
- **MVP Provider**: OpenAI only
- **Configuration**: Environment variables for API keys
- **Model Selection**: Configurable via settings

### 3.2 Agent Architecture
- **Structure Agent**: 
  - General resume quality analysis
  - Fixed prompt for all industries
  - Returns score (1-10), comments, recommendations
  
- **Appeal Point Agent**:
  - Industry-specific analysis
  - Dynamic prompt based on selected industry
  - Returns score (1-10), comments, recommendations

### 3.3 Prompt Management
- **Storage**: Separate prompt files (not hardcoded)
- **Format**: Text files or Python modules
- **Updates**: Easy to modify without code changes
- **Variables**: Support for industry-specific prompts

## 4. Processing Workflows

### 4.1 Resume Analysis Flow
1. **Receive Upload**: Accept file from frontend
2. **Validate File**: Check type and size only
3. **Extract Text**: 
   - Parse PDF/Word to plain text
   - Ignore images and complex formatting
4. **Structure Analysis**:
   - Call LLM with structure prompt
   - Parse response to XML format
5. **Appeal Point Analysis**:
   - Call LLM with industry-specific prompt
   - Parse response to XML format
6. **Combine Results**: 
   - Merge both agent outputs
   - Return raw XML to frontend
7. **Store Results**: Save to database

### 4.2 Error Handling Flow
- **File Errors**: Return validation error
- **LLM Errors**: Log error, return generic message
- **No Retry Logic**: Fail fast (MVP)
- **User Notification**: Simple error message

## 5. Data Transformations

### 5.1 Input Processing
- **Resume Files**:
  - PDF → Plain text extraction
  - DOCX → Plain text extraction
  - Encoding: UTF-8
  - Images: Ignored

### 5.2 AI Response Format
- **LLM Output**: Natural language response
- **XML Structure**: Backend formats to XML
```xml
<analysis>
  <agent type="structure">
    <score>8</score>
    <comments>Well organized resume...</comments>
    <recommendations>Consider adding...</recommendations>
    <sources>
      <source page="1" section="header"/>
    </sources>
  </agent>
  <agent type="appeal_point">
    <score>7</score>
    <comments>Strong consulting experience...</comments>
    <recommendations>Highlight more...</recommendations>
    <sources>
      <source page="2" section="experience"/>
    </sources>
  </agent>
</analysis>
```

### 5.3 Storage Format
- **Database**: Structured data (normalized)
- **Response Cache**: Raw XML stored

## 6. Error Handling

### 6.1 Application Errors
- **Invalid Credentials**: 401 Unauthorized
- **Invalid File Type**: 400 Bad Request
- **File Too Large**: 413 Payload Too Large
- **LLM API Error**: 503 Service Unavailable
- **Analysis in Progress**: 409 Conflict

### 6.2 System Errors
- **Database Connection**: 500 Internal Server Error
- **File Processing Error**: 500 Internal Server Error
- **Unexpected Errors**: 500 with generic message

### 6.3 Error Response Format
```json
{
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "File size must be under 10MB"
  }
}
```

### 6.4 Logging Strategy
- **Error Level**: All errors with stack traces
- **Info Level**: API requests, analysis starts/completes
- **Debug Level**: Detailed processing steps (dev only)
- **No Audit Logs**: Not required for MVP