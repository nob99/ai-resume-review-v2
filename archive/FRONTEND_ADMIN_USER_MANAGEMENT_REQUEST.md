# Frontend Implementation Request: Admin User Management

**Date**: September 28, 2025
**Backend Team**: Claude Code
**Target Sprint**: Sprint 004
**Priority**: High

## 📋 Overview

The backend team has implemented a complete user management system for admin users. We need the frontend team to create the UI components and pages to interact with these new API endpoints.

## 🎯 Requested Features

### 1. Admin User Management Dashboard
- **Page**: `/admin/users` (admin-only access)
- **Purpose**: Central hub for managing all users in the system

### 2. User Creation Form
- **Modal/Page**: Create new user with temporary password
- **Trigger**: "Add User" button on dashboard

### 3. User List with Search/Filter
- **Component**: Paginated table with search and filtering capabilities
- **Features**: Search by name/email, filter by role/status

### 4. User Detail View
- **Page/Modal**: `/admin/users/:id`
- **Purpose**: View comprehensive user information and statistics

### 5. User Edit Functions
- **Actions**: Update user status, role, reset password
- **UI**: Inline editing or modal forms

## 🔗 API Endpoints & Exact Schemas

### Authentication Flow
```
1. User must be logged in with 'admin' role
2. All requests require: Authorization: Bearer <access_token>
3. 403 Forbidden if not admin role
4. 401 Unauthorized if token invalid/expired
```

### 1. Create User
```http
POST /api/v1/admin/users
Content-Type: application/json
Authorization: Bearer <admin_token>

REQUEST BODY:
{
  "email": "newuser@example.com",           // string, required, valid email
  "first_name": "John",                     // string, required, 1-100 chars
  "last_name": "Doe",                       // string, required, 1-100 chars
  "role": "junior_recruiter",               // enum: "junior_recruiter" | "senior_recruiter" | "admin"
  "temporary_password": "TempPass123!"      // string, required, 8-128 chars, must be strong
}

RESPONSE (201 Created):
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "newuser@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "junior_recruiter",
  "is_active": true,
  "email_verified": false,
  "created_at": "2025-09-28T10:00:00Z",
  "last_login_at": null,
  "full_name": "John Doe"                   // computed field
}

ERROR RESPONSES:
400 Bad Request: Email already exists, password validation failed
403 Forbidden: Not admin user
422 Unprocessable Entity: Invalid field values
```

### 2. List Users (with Pagination & Filtering)
```http
GET /api/v1/admin/users?page=1&page_size=20&search=john&role=junior_recruiter&is_active=true
Authorization: Bearer <admin_token>

QUERY PARAMETERS:
- page: integer, default=1, min=1
- page_size: integer, default=20, min=1, max=100
- search: string, optional (searches email, first_name, last_name)
- role: enum, optional ("junior_recruiter" | "senior_recruiter" | "admin")
- is_active: boolean, optional

RESPONSE (200 OK):
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "role": "junior_recruiter",
      "is_active": true,
      "email_verified": true,
      "last_login_at": "2025-09-28T09:00:00Z",
      "created_at": "2025-01-01T10:00:00Z",
      "assigned_candidates_count": 5,          // integer, only for junior_recruiters
      "full_name": "John Doe"                  // computed field
    }
  ],
  "total": 150,                              // total records matching filter
  "page": 1,                                 // current page
  "page_size": 20,                           // items per page
  "total_pages": 8                           // total pages
}
```

### 3. Get User Details
```http
GET /api/v1/admin/users/{user_id}
Authorization: Bearer <admin_token>

RESPONSE (200 OK):
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "junior_recruiter",
  "is_active": true,
  "email_verified": true,
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-09-28T10:00:00Z",
  "last_login_at": "2025-09-28T09:00:00Z",
  "password_changed_at": "2025-01-01T10:00:00Z",
  "failed_login_attempts": 0,                // integer
  "locked_until": null,                      // string (ISO date) or null
  "assigned_candidates_count": 5,            // integer
  "total_resumes_uploaded": 12,              // integer
  "total_reviews_requested": 8,              // integer
  "full_name": "John Doe",                   // computed field
  "is_locked": false                         // computed field
}

ERROR RESPONSES:
404 Not Found: User not found
403 Forbidden: Not admin user
```

### 4. Update User
```http
PATCH /api/v1/admin/users/{user_id}
Content-Type: application/json
Authorization: Bearer <admin_token>

REQUEST BODY (all fields optional):
{
  "is_active": false,                        // boolean, optional
  "role": "senior_recruiter",                // enum, optional
  "email_verified": true                     // boolean, optional
}

RESPONSE (200 OK):
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "senior_recruiter",                // updated
  "is_active": false,                        // updated
  "email_verified": true,
  "created_at": "2025-01-01T10:00:00Z",
  "last_login_at": "2025-09-28T09:00:00Z",
  "full_name": "John Doe"
}

ERROR RESPONSES:
400 Bad Request: Cannot deactivate own account
404 Not Found: User not found
403 Forbidden: Not admin user
```

### 5. Reset User Password
```http
POST /api/v1/admin/users/{user_id}/reset-password
Content-Type: application/json
Authorization: Bearer <admin_token>

REQUEST BODY:
{
  "new_password": "NewTempPass123!",         // string, required, 8-128 chars, must be strong
  "force_password_change": true              // boolean, default=true
}

RESPONSE (200 OK):
{
  "message": "Password reset successfully. User must change password on next login.",
  "success": true
}

ERROR RESPONSES:
404 Not Found: User not found
400 Bad Request: Password validation failed
403 Forbidden: Not admin user
```

### 6. User Directory (for Senior Recruiters)
```http
GET /api/v1/admin/directory
Authorization: Bearer <senior_or_admin_token>

RESPONSE (200 OK):
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "full_name": "John Doe",
      "role": "junior_recruiter",
      "is_active": true
    }
  ],
  "total": 50
}

ERROR RESPONSES:
403 Forbidden: Not senior recruiter or admin
```

## 📊 Database Schema Mapping

### User Table Fields → API Response Fields
```
Database Field          → API Field              → Type       → Notes
==================================================================================
id                     → id                     → UUID       → Primary key
email                  → email                  → string     → Unique, lowercase
password_hash          → [NEVER EXPOSED]        → -          → Security sensitive
first_name             → first_name             → string     → 1-100 chars
last_name              → last_name              → string     → 1-100 chars
role                   → role                   → enum       → DB: string, API: enum
is_active              → is_active              → boolean    → Account status
email_verified         → email_verified         → boolean    → Email confirmation
created_at             → created_at             → datetime   → ISO 8601 format
updated_at             → updated_at             → datetime   → ISO 8601 format
last_login_at          → last_login_at          → datetime   → Can be null
password_changed_at    → password_changed_at    → datetime   → Password history
failed_login_attempts  → failed_login_attempts  → integer    → Security tracking
locked_until           → locked_until           → datetime   → Can be null
[computed]             → full_name              → string     → first_name + last_name
[computed]             → is_locked              → boolean    → locked_until check
[joined]               → assigned_candidates_count → integer → From assignments table
[joined]               → total_resumes_uploaded → integer    → From resumes table
[joined]               → total_reviews_requested → integer   → From reviews table
```

### Role Enum Values
```typescript
type UserRole = 'junior_recruiter' | 'senior_recruiter' | 'admin'

// Role Hierarchy (for UI permissions):
junior_recruiter: Can only see own assigned candidates
senior_recruiter: Can see all candidates + user directory
admin: Full access to user management
```

## 🎨 UI/UX Specifications

### 1. Admin Dashboard Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Admin Dashboard                                    [ + Add User] │
├─────────────────────────────────────────────────────────────┤
│ Search: [________________] Role: [All ▼] Status: [All ▼]    │
├─────────────────────────────────────────────────────────────┤
│ Name           │ Email              │ Role           │ Status │ Actions │
│ John Doe       │ john@example.com   │ Junior Recruiter│ Active │ [Edit][Reset] │
│ Jane Smith     │ jane@example.com   │ Senior Recruiter│ Active │ [Edit][Reset] │
│ Admin User     │ admin@example.com  │ Admin          │ Active │ [Edit][Reset] │
├─────────────────────────────────────────────────────────────┤
│ Showing 1-20 of 150 results    [< Prev] [1][2][3] [Next >] │
└─────────────────────────────────────────────────────────────┘
```

### 2. User Creation Modal
```
┌─────────────────────────────────────┐
│ Create New User                  [×] │
├─────────────────────────────────────┤
│ Email: [________________________]   │
│ First Name: [________________]       │
│ Last Name: [_________________]       │
│ Role: [Junior Recruiter ▼]          │
│ Temporary Password: [____________]   │
│ ☑ Force password change on login    │
├─────────────────────────────────────┤
│           [Cancel] [Create User]     │
└─────────────────────────────────────┘
```

### 3. User Detail View
```
┌─────────────────────────────────────────────────────────────┐
│ John Doe (john@example.com)                        [Edit] [Reset Password] │
├─────────────────────────────────────────────────────────────┤
│ Role: Junior Recruiter          Status: Active             │
│ Created: Jan 1, 2025           Last Login: Sep 28, 2025    │
│ Email Verified: Yes            Failed Attempts: 0          │
├─────────────────────────────────────────────────────────────┤
│ STATISTICS                                                  │
│ Assigned Candidates: 5                                      │
│ Resumes Uploaded: 12                                        │
│ Reviews Requested: 8                                        │
└─────────────────────────────────────────────────────────────┘
```

## ⚠️ Error Handling Scenarios

### 1. Authentication Errors
```typescript
// Token expired
Response: 401 Unauthorized
Action: Redirect to login page

// Insufficient permissions
Response: 403 Forbidden
UI: Show "Access denied" message, hide admin features

// No token
Response: 403 Forbidden
Action: Redirect to login page
```

### 2. Validation Errors
```typescript
// Email already exists
Response: 400 Bad Request
{ "detail": "User with email john@example.com already exists" }
UI: Show error under email field

// Weak password
Response: 422 Unprocessable Entity
{ "detail": [{"field": "temporary_password", "message": "Password validation failed: ..."}] }
UI: Show validation messages under password field

// Invalid role change
Response: 400 Bad Request
{ "detail": "Cannot deactivate your own account" }
UI: Show toast notification with error
```

### 3. Network Errors
```typescript
// Server error
Response: 500 Internal Server Error
UI: Show "Something went wrong" message with retry button

// Network timeout
No response
UI: Show "Network error" message with retry button
```

## 🧪 Testing Scenarios

### 1. Happy Path Tests
```typescript
// Test admin login → user list → create user → edit user → reset password
1. Login as admin user
2. Navigate to /admin/users
3. Verify user list loads with pagination
4. Click "Add User" → fill form → submit
5. Verify new user appears in list
6. Click user → edit role → save
7. Click "Reset Password" → confirm → verify success message
```

### 2. Permission Tests
```typescript
// Test role-based access control
1. Login as junior recruiter → try to access /admin/users → verify 403
2. Login as senior recruiter → access /admin/directory → verify success
3. Login as admin → access all admin features → verify success
```

### 3. Edge Cases
```typescript
// Test boundary conditions
1. Create user with existing email → verify error
2. Try to deactivate own account → verify prevention
3. Test pagination with 0 results
4. Test search with no matches
5. Test password reset with invalid user ID
```

## 📝 Implementation Notes

### 1. State Management
```typescript
// Suggested Redux/Zustand store structure
interface AdminState {
  users: {
    list: User[];
    total: number;
    loading: boolean;
    filters: {
      search: string;
      role: UserRole | null;
      isActive: boolean | null;
    };
    pagination: {
      page: number;
      pageSize: number;
    };
  };
  selectedUser: UserDetail | null;
  modals: {
    createUser: boolean;
    editUser: boolean;
    resetPassword: boolean;
  };
}
```

### 2. API Integration
```typescript
// Use existing API client pattern from auth module
import { apiClient } from '@/lib/api';

// GET users with query params
const getUsers = async (params: UserListParams) => {
  const response = await apiClient.get('/api/v1/admin/users', { params });
  return response.data;
};

// POST create user
const createUser = async (userData: CreateUserRequest) => {
  const response = await apiClient.post('/api/v1/admin/users', userData);
  return response.data;
};
```

### 3. Form Validation
```typescript
// Use existing validation patterns
import { z } from 'zod';

const createUserSchema = z.object({
  email: z.string().email(),
  first_name: z.string().min(1).max(100),
  last_name: z.string().min(1).max(100),
  role: z.enum(['junior_recruiter', 'senior_recruiter', 'admin']),
  temporary_password: z.string().min(8).max(128)
    .regex(/[A-Z]/, 'Must contain uppercase letter')
    .regex(/[!@#$%^&*]/, 'Must contain special character')
});
```

## 📋 Meeting Agenda: Frontend Admin User Management Implementation

### **1. Overview & Scope Review (10 min)**
- Review the 6 main features to be implemented
- Confirm priority and timeline expectations
- Align on sprint allocation

### **2. API Contract Deep Dive (20 min)**
**Focus**: Prevent API/schema mismatches
- **Exact Request/Response Schemas** - All JSON structures documented
- **Authentication Flow** - Token requirements and error scenarios
- **Query Parameters** - Pagination, filtering, search parameters
- **Error Response Format** - Standardized error handling
- **Status Code Mapping** - When to show what UI states

### **3. Database-to-API Field Mapping (15 min)**
**Focus**: Ensure frontend uses correct field names
- **Field Name Mapping Table** - DB field → API field → UI display
- **Computed Fields** - `full_name`, `is_locked`, statistics
- **Data Type Conversions** - DateTime formatting, enum handling
- **Null Handling** - Which fields can be null and how to display

### **4. Role-Based Access Control (10 min)**
**Focus**: Frontend permission implementation
- **Route Protection** - Who can access which pages
- **UI Element Visibility** - Hide/show based on user role
- **API Permission Errors** - How to handle 403 responses

### **5. UI/UX Specifications (15 min)**
**Focus**: Consistent user experience
- **Page Layouts** - Admin dashboard structure
- **Component Requirements** - Tables, modals, forms
- **User Interaction Flows** - Create → Edit → Delete workflows
- **Loading States** - When to show spinners/skeletons

### **6. Error Handling Strategy (10 min)**
**Focus**: Robust error management
- **Network Errors** - Timeout, server down scenarios
- **Validation Errors** - Form field validation display
- **Permission Errors** - Access denied handling
- **User Feedback** - Toast notifications vs inline errors

### **7. Testing Strategy (10 min)**
**Focus**: Comprehensive testing approach
- **Happy Path Scenarios** - Normal user workflows
- **Edge Cases** - Boundary conditions, empty states
- **Permission Testing** - Role-based access verification
- **Error Scenarios** - How to test error conditions

### **8. Technical Implementation Details (15 min)**
**Focus**: Development approach
- **State Management** - Redux/Zustand store structure
- **API Integration** - Reuse existing API client patterns
- **Form Validation** - Zod schema alignment with backend
- **TypeScript Types** - Interface definitions for all schemas

### **9. Acceptance Criteria Review (5 min)**
**Focus**: Definition of done
- **Must Have Features** - Core functionality requirements
- **Should Have Features** - Nice-to-have improvements
- **Testing Requirements** - What needs to be tested

### **10. Next Steps & Timeline (5 min)**
- Assign development tasks
- Set milestone deadlines
- Schedule follow-up reviews
- Establish communication channels

## ✅ Acceptance Criteria

### Must Have
- [ ] Admin can create new users with temporary passwords
- [ ] Admin can view paginated list of all users
- [ ] Admin can search users by name/email
- [ ] Admin can filter users by role and status
- [ ] Admin can view detailed user information
- [ ] Admin can activate/deactivate users
- [ ] Admin can change user roles
- [ ] Admin can reset user passwords
- [ ] Senior recruiters can access user directory
- [ ] Junior recruiters cannot access admin features
- [ ] All API responses match exact schemas above
- [ ] Error handling covers all scenarios
- [ ] Loading states shown during API calls

### Should Have
- [ ] Real-time updates when users are modified
- [ ] Export user list functionality
- [ ] Bulk actions (select multiple users)
- [ ] User activity timeline

### Nice to Have
- [ ] Advanced filtering options
- [ ] User avatar support
- [ ] Email notifications for password resets
- [ ] Audit log viewing

## 🚀 Deployment Notes

### Environment Variables
```bash
# No new environment variables needed
# Uses existing authentication and API configuration
```

### Testing Users
```bash
# Use these admin accounts for testing:
Email: admin@airesumereview.com
Password: AdminPass123!

# Database has multiple test admin users available
```

---

**Questions or Issues?**
Contact: Backend Team
Slack: #backend-support
Documentation: `/docs/backend/admin-api.md`