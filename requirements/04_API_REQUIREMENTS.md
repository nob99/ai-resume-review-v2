# API Requirements

## 1. Overview
RESTful API built with FastAPI to serve the Next.js frontend. Uses JWT authentication with httpOnly cookies, standard HTTP status codes, and JSON for all requests/responses.

### Key Principles
- **RESTful design**: Standard HTTP methods and status codes
- **JSON format**: All requests and responses
- **Secure by default**: httpOnly cookies, CORS restrictions
- **Simple versioning**: No versioning for MVP

## 2. Request/Response Formats

### 2.1 Standard Response Formats

#### Success Response
```json
{
  "data": {
    // Response payload
  },
  "meta": {
    "timestamp": "2024-11-28T10:30:00Z"
  }
}
```

#### Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Optional additional error context
    }
  }
}
```

#### List Response
```json
{
  "data": [
    // Array of items
  ],
  "meta": {
    "total": 50,
    "page": 1,
    "per_page": 20,
    "timestamp": "2024-11-28T10:30:00Z"
  }
}
```

### 2.2 File Upload Format
- **Method**: Multipart form data
- **Field name**: `resume_file`
- **Supported formats**: PDF, DOCX
- **Max size**: 10MB
- **Encoding**: UTF-8 for text extraction

### 2.3 Common HTTP Status Codes
- **200**: Success (GET, PUT)
- **201**: Created (POST)
- **204**: No Content (DELETE)
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (not logged in)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **409**: Conflict (e.g., analysis in progress)
- **413**: Payload Too Large (file > 10MB)
- **500**: Internal Server Error
- **503**: Service Unavailable (e.g., LLM API down)

## 3. Authentication and Authorization

### 3.1 JWT Configuration
- **Storage**: httpOnly cookies (not localStorage)
- **Cookie name**: `auth_token`
- **Expiration**: 24 hours
- **Algorithm**: HS256
- **Claims**:
  ```json
  {
    "user_id": 123,
    "email": "user@example.com",
    "role": "consultant",
    "exp": 1701234567
  }
  ```

### 3.2 Cookie Settings
```python
cookie_settings = {
    "httponly": True,
    "secure": True,  # HTTPS only in production
    "samesite": "lax",
    "max_age": 86400  # 24 hours
}
```

### 3.3 Authorization Rules
- **Public endpoints**: `/api/auth/login`, `/api/health`
- **Authenticated endpoints**: All others require valid JWT
- **Admin-only endpoints**: `/api/users/*` (except own profile)

## 4. API Endpoints

### 4.1 Authentication
```
POST   /api/auth/login      # Login with email/password
POST   /api/auth/logout     # Clear auth cookie
GET    /api/auth/me         # Get current user info
```

### 4.2 User Management (Admin only)
```
GET    /api/users           # List all users
POST   /api/users           # Create new user
PUT    /api/users/{id}/password  # Reset user password
DELETE /api/users/{id}      # Soft delete user
```

### 4.3 Resume Analysis
```
POST   /api/analyses        # Upload resume and start analysis
GET    /api/analyses        # List user's analyses (paginated)
GET    /api/analyses/{id}   # Get specific analysis result
GET    /api/analyses/{id}/download?format=pdf|txt  # Download as PDF or TXT
```

### 4.4 Configuration
```
GET    /api/industries      # List available industries
```

### 4.5 System
```
GET    /api/health          # Health check
```

### 4.6 Request Examples

#### POST /api/analyses
```
Content-Type: multipart/form-data

candidate_name: John Doe
target_industry: technology_consulting
resume_file: [binary PDF/DOCX data]
```

#### GET /api/analyses Response
```json
{
  "data": [
    {
      "id": 123,
      "candidate_name": "John Doe",
      "target_industry": "technology_consulting",
      "status": "completed",
      "created_at": "2024-11-28T10:30:00Z"
    }
  ],
  "meta": {
    "total": 25,
    "page": 1,
    "per_page": 20
  }
}
```

#### GET /api/analyses/{id} Response
```json
{
  "data": {
    "id": 123,
    "candidate_name": "John Doe",
    "target_industry": "technology_consulting",
    "status": "completed",
    "result_xml": "<analysis>...</analysis>",
    "created_at": "2024-11-28T10:30:00Z"
  }
}
```

## 5. Rate Limiting Rules

### 5.1 Global Rate Limits
- **General API**: 100 requests per minute per IP
- **Login endpoint**: 5 attempts per 15 minutes per IP
- **Implementation**: Redis or in-memory cache

### 5.2 Rate Limit Response
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later."
  }
}
```

## 6. CORS Configuration

### 6.1 Allowed Origins
```python
# Development
allowed_origins = [
    "http://localhost:3000",  # Next.js dev server
]

# Production
allowed_origins = [
    "https://your-domain.com",  # Your production frontend
]
```

### 6.2 CORS Settings
- **Methods**: GET, POST, PUT, DELETE
- **Headers**: Content-Type, Authorization
- **Credentials**: True (for cookies)

## 7. Error Codes

### 7.1 Standard Error Codes
- `VALIDATION_ERROR`: Invalid input data
- `AUTHENTICATION_FAILED`: Invalid credentials
- `UNAUTHORIZED`: Not logged in
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource state conflict
- `FILE_TOO_LARGE`: Upload exceeds 10MB
- `INVALID_FILE_TYPE`: Not PDF or DOCX
- `ANALYSIS_IN_PROGRESS`: User has active analysis
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error
- `SERVICE_UNAVAILABLE`: External service down

### 7.2 Validation Error Details
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "fields": {
        "email": "Invalid email format",
        "password": "Field required"
      }
    }
  }
}
```

## 8. API Documentation
- **Tool**: FastAPI automatic docs
- **Endpoints**: `/docs` (Swagger UI), `/redoc` (ReDoc)
- **Access**: Development only (disabled in production)