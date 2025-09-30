# Frontend Integration Guide: Candidate Registration

## Overview
This document provides comprehensive integration guidelines for implementing candidate registration in the frontend. It covers exact API contracts, field mappings, validation rules, and business logic flows to prevent common frontend/backend mismatches.

## 📋 Complete Field Mapping

### Database → API → Frontend Field Mapping
| Database Field | API Request Field | API Response Field | Frontend Form Field | TypeScript Type | Validation Rules |
|---|---|---|---|---|---|
| `first_name` | `first_name` | `first_name` | `firstName` | `string` | **Required**, 1-100 chars |
| `last_name` | `last_name` | `last_name` | `lastName` | `string` | **Required**, 1-100 chars |
| `email` | `email` | `email` | `email` | `string \| undefined` | **Optional**, must contain '@' if provided |
| `phone` | `phone` | `phone` | `phone` | `string \| undefined` | **Optional**, max 50 chars |
| `current_company` | `current_company` | `current_company` | `currentCompany` | `string \| undefined` | **Optional**, max 255 chars |
| `current_position` | `current_position` | `current_position` | `currentPosition` | `string \| undefined` | **Optional**, max 255 chars |
| `years_experience` | `years_experience` | `years_experience` | `yearsExperience` | `number \| undefined` | **Optional**, integer 0-50 |
| `id` | N/A | `id` | `id` | `string` | UUID format (response only) |
| `status` | N/A | `status` | `status` | `string` | Always 'active' for new candidates |
| `created_at` | N/A | `created_at` | `createdAt` | `string` | ISO 8601 format |

### ⚠️ Critical Naming Notes
- **Backend uses `current_position` NOT `current_role`**
- **API uses snake_case, Frontend uses camelCase**
- **UUIDs are always string format in API responses**

## 🔗 API Contract

### Endpoint
```
POST /api/v1/candidates/
```

### Headers
```typescript
{
  'Content-Type': 'application/json',
  'Authorization': 'Bearer <jwt_token>' // REQUIRED
}
```

### Request Schema (TypeScript)
```typescript
interface CandidateCreateRequest {
  first_name: string;        // REQUIRED - 1-100 characters
  last_name: string;         // REQUIRED - 1-100 characters
  email?: string;            // OPTIONAL - validated if provided
  phone?: string;            // OPTIONAL - max 50 characters
  current_company?: string;  // OPTIONAL - max 255 characters
  current_position?: string; // OPTIONAL - max 255 characters (NOT current_role!)
  years_experience?: number; // OPTIONAL - integer between 0-50
}
```

### Response Schema (TypeScript)
```typescript
interface CandidateCreateResponse {
  success: boolean;
  message: string;
  candidate?: {
    id: string;                    // UUID format
    first_name: string;
    last_name: string;
    email?: string;
    phone?: string;
    current_company?: string;
    current_position?: string;
    years_experience?: number;
    status: string;                // Always 'active' for new candidates
    created_at: string;            // ISO 8601 format: "2024-01-15T10:30:00Z"
  };
  error?: string;
}
```

### Example Request/Response
```typescript
// REQUEST
const requestData = {
  first_name: "John",
  last_name: "Doe",
  email: "john.doe@example.com",
  current_company: "Tech Corp",
  current_position: "Senior Developer",
  years_experience: 5
};

// RESPONSE (Success)
{
  "success": true,
  "message": "Candidate created successfully",
  "candidate": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "current_company": "Tech Corp",
    "current_position": "Senior Developer",
    "years_experience": 5,
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## 🔄 Complete Business Logic Flow

### Step-by-Step Registration Sequence
```
1. [Frontend] → Validate form data locally
2. [Frontend] → Submit POST request with JWT token
3. [Backend] → Validate JWT token (401 if invalid/expired)
4. [Backend] → Validate request fields (422 if validation errors)
5. [Backend] → Start database transaction
6. [Backend] → Create Candidate record (status: 'active')
7. [Backend] → Database FLUSH (generate candidate.id)
8. [Backend] → Auto-create UserCandidateAssignment (type: 'primary')
9. [Backend] → Commit transaction (rollback if any step fails)
10. [Backend] → Return success response
11. [Frontend] → Update local state and navigate
```

### 🚨 Critical Business Rules Frontend Must Understand

#### Auto-Assignment Logic
- **EVERY** created candidate is automatically assigned to the creator
- Assignment type is **always** 'primary' for creators
- This happens **atomically** - no separate API call needed
- **DO NOT** attempt to make separate assignment API calls

#### Role-Based Access Control
```typescript
// Frontend UI logic should match these backend rules:
if (userRole === 'admin' || userRole === 'senior_recruiter') {
  // Can see ALL candidates in the system
  // Can assign candidates to other users
  // Show admin/management features
} else if (userRole === 'junior_recruiter') {
  // Can only see candidates assigned to them
  // Cannot assign candidates to others
  // Hide admin features
}
```

#### Transaction Atomicity
- Candidate creation and assignment are **all-or-nothing**
- If any step fails → entire operation rolls back
- Frontend should **NOT** attempt partial recovery
- Always treat as single atomic operation

## ❌ Error Handling Specification

### Error Response Format
```typescript
interface ErrorResponse {
  detail: string | ValidationError[];
  error?: string;
  message?: string;
  type?: string;
}

interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
```

### Error Handling Decision Tree
```typescript
async function handleCandidateCreation(data: CandidateCreateRequest) {
  try {
    const response = await fetch('/api/v1/candidates/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAccessToken()}`
      },
      body: JSON.stringify(data)
    });

    if (response.status === 401) {
      // Token expired/invalid → trigger token refresh or login
      await handleTokenRefresh();
      return; // Retry after refresh
    }

    if (response.status === 422) {
      // Validation errors → show field-specific errors
      const errorData = await response.json();
      showFieldValidationErrors(errorData.detail);
      return;
    }

    if (response.status === 500) {
      // Server error → show generic message, allow retry
      showError("Unable to create candidate. Please try again.");
      return;
    }

    if (response.ok) {
      const result = await response.json();
      handleSuccess(result.candidate);
    }

  } catch (error) {
    // Network error → show connection error
    showError("Connection failed. Please check your internet connection.");
  }
}
```

### Field Validation Error Mapping
```typescript
function showFieldValidationErrors(errors: ValidationError[]) {
  errors.forEach(error => {
    const fieldName = error.loc[error.loc.length - 1];
    const message = error.msg;

    switch (fieldName) {
      case 'first_name':
        setFirstNameError(message);
        break;
      case 'last_name':
        setLastNameError(message);
        break;
      case 'email':
        setEmailError(message);
        break;
      // ... handle other fields
    }
  });
}
```

## 🎯 Frontend State Management

### What to Update After Successful Creation
```typescript
function handleSuccess(candidate: CandidateInfo) {
  // 1. Add candidate to local state (don't wait for refetch)
  addCandidateToList(candidate);

  // 2. Update total count
  incrementCandidateCount();

  // 3. Clear form
  resetForm();

  // 4. Show success message
  showSuccessMessage("Candidate created successfully");

  // 5. Navigate (choose one approach)
  // Option A: Stay on list page
  // Option B: Navigate to candidate detail
  navigate(`/candidates/${candidate.id}`);

  // 6. Optional: Refresh candidate list after delay
  setTimeout(() => refreshCandidateList(), 1000);
}
```

### What NOT to Do
- ❌ Don't make separate assignment API calls (auto-assigned)
- ❌ Don't assume candidate ID before API response
- ❌ Don't partially update on validation errors (atomic operation)
- ❌ Don't cache responses without proper invalidation strategy

## 🕐 Performance Expectations

```typescript
const PERFORMANCE_EXPECTATIONS = {
  TYPICAL_RESPONSE_TIME: 500, // ms for candidate creation
  TIMEOUT_THRESHOLD: 10000,   // ms before showing timeout error
  RETRY_DELAY: 2000,          // ms before allowing retry after error
  AUTO_REFRESH_DELAY: 1000,   // ms before refreshing candidate list

  // Loading states
  SHOW_LOADING_AFTER: 200,    // ms before showing loading spinner
  MIN_LOADING_DURATION: 300   // ms minimum loading state duration
};
```

## 🔒 Security Considerations

### Authentication Requirements
- **JWT token required** for all candidate operations
- Include `Authorization: Bearer <token>` header
- Handle token expiration gracefully with refresh flow
- Never cache tokens in localStorage (use secure httpOnly cookies)

### Input Sanitization
```typescript
// Frontend should sanitize inputs before sending
function sanitizeInput(value: string): string {
  return value
    .trim()
    .replace(/<script.*?>.*?<\/script>/gi, '') // Remove script tags
    .substring(0, 255); // Respect max length
}
```

## 📝 Testing Checklist

### Unit Tests Required
- [ ] Form validation (all field types and constraints)
- [ ] API request/response transformation (snake_case ↔ camelCase)
- [ ] Error handling for each status code (401, 422, 500)
- [ ] State management updates after success/failure
- [ ] Role-based UI rendering logic

### Integration Tests Required
- [ ] Complete registration flow (form → API → success state)
- [ ] Token refresh flow during registration
- [ ] Network error recovery
- [ ] Validation error display and recovery
- [ ] Auto-assignment verification (candidate appears in user's list)

### Manual Testing Scenarios
- [ ] Register candidate with minimum required fields
- [ ] Register candidate with all optional fields
- [ ] Test with invalid email format
- [ ] Test with expired JWT token
- [ ] Test with network disconnection during request
- [ ] Verify role-based access (different user roles)
- [ ] Verify candidate auto-assignment to creator

## 🚀 Implementation Tips

### Recommended Form Libraries
- **React Hook Form** + **Zod** for TypeScript validation
- **Formik** + **Yup** for schema validation
- Native form validation with proper error handling

### API Client Setup
```typescript
// Use axios with interceptors for token handling
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

// Auto-retry on token expiration
apiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      await refreshToken();
      return apiClient.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

### TypeScript Configuration
```typescript
// Create strict type definitions
interface CandidateFormData {
  firstName: string;
  lastName: string;
  email?: string;
  phone?: string;
  currentCompany?: string;
  currentPosition?: string;  // NOT currentRole!
  yearsExperience?: number;
}

// Transform function for API calls
function transformToApiFormat(formData: CandidateFormData): CandidateCreateRequest {
  return {
    first_name: formData.firstName,
    last_name: formData.lastName,
    email: formData.email,
    phone: formData.phone,
    current_company: formData.currentCompany,
    current_position: formData.currentPosition,
    years_experience: formData.yearsExperience,
  };
}
```

## 🔗 Related Documentation
- [Backend API Documentation](http://localhost:8000/docs) - Complete OpenAPI specification
- [Authentication Flow](./frontend/docs/auth-integration.md) - JWT token handling
- [Error Handling Patterns](./frontend/docs/error-handling.md) - Application-wide error patterns
- [Testing Guidelines](./frontend/docs/testing.md) - Frontend testing standards

---

**Last Updated**: 2024-01-15
**API Version**: v1
**Contact**: dev@airesumereview.com