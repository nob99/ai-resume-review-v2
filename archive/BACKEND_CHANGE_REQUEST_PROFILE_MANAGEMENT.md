# Backend Change Request: Profile Management Feature

**Date**: December 19, 2024
**Requested By**: Frontend Team
**Priority**: Medium
**Branch**: `refactor/admin-simplification`
**Frontend Commit**: `c35cad2`

---

## Executive Summary

The frontend team has implemented a user profile management feature that allows users to:
1. Edit their personal information (first name, last name)
2. Change their password (with current password verification)

This document outlines the required backend API endpoints to support these features.

---

## Database Schema Reference

Based on `database/docs/schema_v1.1.md` and `database/models/auth.py`, the **users** table has the following relevant fields:

### Editable Fields (Self-Service)
- `first_name` (String(100), nullable=False)
- `last_name` (String(100), nullable=False)
- `password_hash` (String(255), nullable=False) - via `set_password()` method

### Read-Only Fields (Display Only)
- `id` (UUID, primary key)
- `email` (String(255), unique, nullable=False) - **CANNOT be changed**
- `role` (String(50), nullable=False) - **CANNOT be self-edited** (admin only)
- `is_active` (Boolean, nullable=False) - **CANNOT be self-edited** (admin only)
- `email_verified` (Boolean, nullable=False)
- `created_at` (DateTime(timezone=True))
- `updated_at` (DateTime(timezone=True))
- `last_login_at` (DateTime(timezone=True))
- `password_changed_at` (DateTime(timezone=True))
- `failed_login_attempts` (Integer)
- `locked_until` (DateTime(timezone=True))

---

## Required Backend Implementation

### 1. Create Profile Feature Module

Follow the existing backend architecture pattern:

```
backend/app/features/profile/
├── __init__.py
├── api.py           # HTTP endpoints
├── service.py       # Business logic
├── schemas.py       # Pydantic models
└── tests/
    ├── __init__.py
    ├── unit/
    │   └── test_profile_service.py
    └── integration/
        └── test_profile_api.py
```

---

### 2. API Endpoint Specifications

#### 2.1. Update Profile Information

**Endpoint**: `PATCH /api/v1/profile/me`
**Authentication**: Required (JWT Bearer token)
**Authorization**: Current user only (cannot update other users)

**Request Body**:
```json
{
  "first_name": "John",
  "last_name": "Doe"
}
```

**Request Schema** (Pydantic):
```python
class ProfileUpdate(BaseModel):
    """User updating their own profile."""
    first_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    last_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)

    # Validation
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError('Name cannot be empty')
        return value.strip()
```

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john.doe@company.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "senior_recruiter",
  "is_active": true,
  "created_at": "2025-09-09T10:00:00Z",
  "updated_at": "2025-12-19T15:30:00Z"
}
```

**Response Schema** (Pydantic):
```python
class ProfileResponse(BaseModel):
    """Profile response (excludes sensitive fields)."""
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

**Error Responses**:
- `401 Unauthorized` - Invalid or expired token
- `400 Bad Request` - Validation errors
- `500 Internal Server Error` - Database errors

**Business Logic**:
1. Get current user from JWT token
2. Validate input (names not empty, max length)
3. Update only `first_name` and `last_name` fields
4. Set `updated_at = utc_now()`
5. Commit to database
6. Return updated user object (excluding sensitive fields)

**Security Notes**:
- ❌ User CANNOT update: `email`, `role`, `is_active`, `email_verified`
- ❌ User CANNOT update other users (only their own profile)
- ✅ No admin privilege required (self-service)
- ✅ Audit log not required (simple self-service update)

---

#### 2.2. Change Password

**Endpoint**: `POST /api/v1/profile/change-password`
**Authentication**: Required (JWT Bearer token)
**Authorization**: Current user only

**Request Body**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword456!"
}
```

**Request Schema** (Pydantic):
```python
class PasswordChange(BaseModel):
    """User changing their own password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, password):
        """Validate password strength using existing password_hasher."""
        from app.core.security import password_hasher
        validation_result = password_hasher.validate_password(password)
        if not validation_result.is_valid:
            raise ValueError(f"Password validation failed: {', '.join(validation_result.errors)}")
        return password
```

**Response** (200 OK):
```json
{
  "message": "Password changed successfully",
  "success": true
}
```

**Response Schema** (Pydantic):
```python
class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True
```

**Error Responses**:
- `401 Unauthorized` - Invalid or expired token
- `400 Bad Request` - Current password incorrect, validation errors
- `422 Unprocessable Entity` - New password same as current
- `500 Internal Server Error` - Database errors

**Business Logic**:
1. Get current user from JWT token
2. **Verify current password** using `user.check_password(current_password)`
3. If verification fails:
   - Return 400 with "Current password is incorrect"
   - **DO NOT increment failed_login_attempts** (this is not a login attempt)
4. Validate new password strength (use existing `password_hasher.validate_password()`)
5. Check new password is different from current:
   ```python
   if password_hasher.verify_password(new_password, user.password_hash):
       raise ValueError("New password must be different from current password")
   ```
6. Update password using `user.set_password(new_password)`
   - This automatically updates `password_changed_at`
   - Resets `failed_login_attempts = 0`
   - Clears `locked_until = None`
7. Commit to database
8. Return success message

**Security Notes**:
- ✅ Must verify current password before allowing change
- ✅ Use existing `password_hasher` for validation and hashing
- ✅ User model's `set_password()` method handles:
  - Password hashing (bcrypt, 12 rounds minimum)
  - Updating `password_changed_at` timestamp
  - Resetting `failed_login_attempts` to 0
  - Clearing `locked_until`
- ✅ New password must meet strength requirements (min 8 chars, complexity rules)
- ✅ New password must be different from current password
- ❌ Do NOT increment failed_login_attempts on incorrect current password
- ❌ Do NOT invalidate existing sessions (user stays logged in)

---

### 3. Service Layer Implementation

**File**: `backend/app/features/profile/service.py`

```python
"""
Profile service layer for user self-service operations.
Handles business logic for profile updates and password changes.
"""

from typing import Optional
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import password_hasher
from app.core.datetime_utils import utc_now
from app.features.auth.repository import UserRepository
from database.models.auth import User
from .schemas import ProfileUpdate, PasswordChange

logger = logging.getLogger(__name__)


class ProfileService:
    """
    Profile service for user self-service operations.

    Handles profile updates and password changes with proper validation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def update_profile(
        self,
        user_id: UUID,
        profile_data: ProfileUpdate
    ) -> User:
        """
        Update user's profile information.

        Args:
            user_id: Current user's ID
            profile_data: Profile update data

        Returns:
            Updated user object

        Raises:
            ValueError: If user not found
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Update fields
        user.first_name = profile_data.first_name.strip()
        user.last_name = profile_data.last_name.strip()
        user.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(user)

        logger.info(f"User {user_id} updated their profile")

        return user

    async def change_password(
        self,
        user_id: UUID,
        password_data: PasswordChange
    ) -> bool:
        """
        Change user's password.

        Args:
            user_id: Current user's ID
            password_data: Password change data

        Returns:
            True if successful

        Raises:
            ValueError: If current password is incorrect or validation fails
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not user.check_password(password_data.current_password):
            raise ValueError("Current password is incorrect")

        # Check new password is different
        if password_hasher.verify_password(
            password_data.new_password,
            user.password_hash
        ):
            raise ValueError("New password must be different from current password")

        # Set new password (automatically updates password_changed_at)
        user.set_password(password_data.new_password)

        await self.session.commit()

        logger.info(f"User {user_id} changed their password")

        return True
```

---

### 4. API Layer Implementation

**File**: `backend/app/features/profile/api.py`

```python
"""
Profile API endpoints for user self-service.
Provides endpoints for profile updates and password changes.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.features.auth.dependencies import get_current_user
from database.models.auth import User
from .service import ProfileService
from .schemas import (
    ProfileUpdate,
    ProfileResponse,
    PasswordChange,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_profile_service(
    session: AsyncSession = Depends(get_async_session)
) -> ProfileService:
    """Dependency to get profile service."""
    return ProfileService(session)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """
    Update current user's profile information.

    Allows users to update their first name and last name.
    Email, role, and account status cannot be changed.

    Required: Authentication
    """
    try:
        updated_user = await service.update_profile(
            current_user.id,
            profile_data
        )

        logger.info(f"User {current_user.email} updated their profile")

        return ProfileResponse.model_validate(updated_user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service)
):
    """
    Change current user's password.

    Requires verification of current password before setting new password.
    New password must meet strength requirements and be different from current.

    Required: Authentication
    """
    try:
        await service.change_password(current_user.id, password_data)

        logger.info(f"User {current_user.email} changed their password")

        return MessageResponse(
            message="Password changed successfully",
            success=True
        )

    except ValueError as e:
        # Handle validation errors (incorrect current password, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
```

---

### 5. Router Registration

**File**: `backend/app/main.py` (or wherever API routes are registered)

```python
from app.features.profile.api import router as profile_router

# Register profile routes
app.include_router(
    profile_router,
    prefix="/api/v1/profile",
    tags=["profile"]
)
```

---

### 6. Testing Requirements

#### 6.1. Unit Tests

**File**: `backend/app/features/profile/tests/unit/test_profile_service.py`

Test cases:
- ✅ `test_update_profile_success` - Valid profile update
- ✅ `test_update_profile_user_not_found` - User doesn't exist
- ✅ `test_update_profile_empty_names` - Validation errors
- ✅ `test_change_password_success` - Valid password change
- ✅ `test_change_password_wrong_current` - Incorrect current password
- ✅ `test_change_password_same_as_current` - New password same as current
- ✅ `test_change_password_weak_password` - Password doesn't meet requirements
- ✅ `test_change_password_updates_timestamp` - Verify password_changed_at updated

#### 6.2. Integration Tests

**File**: `backend/app/features/profile/tests/integration/test_profile_api.py`

Test cases:
- ✅ `test_update_profile_authenticated` - Successful profile update
- ✅ `test_update_profile_unauthenticated` - 401 without token
- ✅ `test_update_profile_invalid_data` - 400 with validation errors
- ✅ `test_change_password_authenticated` - Successful password change
- ✅ `test_change_password_wrong_current` - 400 with incorrect current password
- ✅ `test_change_password_weak_new` - 400 with weak new password
- ✅ `test_change_password_same_as_current` - 400 when new = current

---

## Frontend Integration

### Frontend Endpoints Already Implemented

The frontend is calling these endpoints:

1. **Profile Update**:
   - `PATCH /api/v1/profile/me`
   - Request: `{ first_name: string, last_name: string }`
   - Expected response: `User` object

2. **Password Change**:
   - `POST /api/v1/profile/change-password`
   - Request: `{ current_password: string, new_password: string }`
   - Expected response: `{ message: string, success: boolean }`

### Frontend Error Handling

The frontend handles these error scenarios:
- Network errors → Shows "Network error. Please try again."
- Validation errors → Shows error message from API
- Auth expired → Redirects to login (via AuthContext)
- Generic errors → Shows "Failed to update profile" or "Failed to change password"

### Frontend Commit Reference

- **Branch**: `refactor/admin-simplification`
- **Commit**: `c35cad2`
- **Files Changed**:
  - `frontend/src/app/profile/page.tsx` (new file, 374 lines)
  - `frontend/src/components/layout/Header.tsx` (updated navigation)
  - `frontend/src/lib/api.ts` (added `profileApi.updateProfile()` and `profileApi.changePassword()`)

---

## Implementation Checklist

### Phase 1: Core Implementation
- [ ] Create `backend/app/features/profile/` directory
- [ ] Implement `schemas.py` with Pydantic models
- [ ] Implement `service.py` with business logic
- [ ] Implement `api.py` with FastAPI endpoints
- [ ] Register routes in `main.py`

### Phase 2: Testing
- [ ] Write unit tests for `ProfileService`
- [ ] Write integration tests for API endpoints
- [ ] Test with real database (not mocked)
- [ ] Verify password validation works correctly
- [ ] Verify `password_changed_at` timestamp updates

### Phase 3: Integration
- [ ] Test with frontend (local development)
- [ ] Verify CORS configuration allows requests
- [ ] Test error scenarios (wrong password, validation errors)
- [ ] Verify JWT authentication works
- [ ] Test with different user roles

### Phase 4: Deployment
- [ ] Update API documentation (Swagger/OpenAPI)
- [ ] Add logging for security monitoring
- [ ] Deploy to development environment
- [ ] Run smoke tests
- [ ] Deploy to production

---

## Security Considerations

### Critical Security Requirements

1. **Authentication**: Both endpoints require valid JWT token
2. **Authorization**: Users can only update their OWN profile (cannot update others)
3. **Password Verification**: Current password MUST be verified before change
4. **Password Hashing**: Use existing `password_hasher` (bcrypt, 12 rounds)
5. **Password Validation**: Use existing `password_hasher.validate_password()`
6. **No Session Invalidation**: Password change doesn't log user out

### What Users CANNOT Do

- ❌ Change email address (unique identifier, requires verification flow)
- ❌ Change role (admin privilege required)
- ❌ Change account status (admin privilege required)
- ❌ Update other users' profiles
- ❌ Bypass current password verification

### Audit Trail

- ✅ Log profile updates: `User {id} updated their profile`
- ✅ Log password changes: `User {id} changed their password`
- ❌ Do NOT log passwords (plain or hashed) in logs
- ❌ Do NOT increment failed_login_attempts on incorrect current password

---

## Database Impact

### Tables Modified
- **users** table:
  - Updated fields: `first_name`, `last_name`, `password_hash`, `password_changed_at`, `updated_at`
  - Read fields: `id`, `email`, `role`, `is_active`, `created_at`

### Schema Changes Required
- ❌ **None** - All required fields already exist in schema v1.1

### Migration Required
- ❌ **None** - No schema changes needed

---

## Dependencies

### Existing Components to Reuse

1. **UserRepository** (`app.features.auth.repository.UserRepository`)
   - `get_by_id(user_id)` - Get user by ID
   - Already implements all database operations needed

2. **User Model** (`database.models.auth.User`)
   - `set_password(password)` - Hash and set password
   - `check_password(password)` - Verify password
   - `password_changed_at` - Automatic timestamp update

3. **Password Hasher** (`app.core.security.password_hasher`)
   - `validate_password(password)` - Check password strength
   - `hash_password(password)` - Hash password (bcrypt)
   - `verify_password(password, hash)` - Verify password

4. **Authentication** (`app.features.auth.dependencies.get_current_user`)
   - JWT token verification
   - Returns current User object

5. **Datetime Utils** (`app.core.datetime_utils.utc_now`)
   - Use for timestamp updates (NOT `datetime.utcnow()`)

---

## API Documentation

### Swagger/OpenAPI

The endpoints should appear in the API documentation at `/docs`:

```
Profile Management
├── PATCH /api/v1/profile/me
│   Summary: Update current user's profile information
│   Tags: profile
│   Security: Bearer JWT
│
└── POST /api/v1/profile/change-password
    Summary: Change current user's password
    Tags: profile
    Security: Bearer JWT
```

---

## Questions or Clarifications?

If you need any clarification on this change request, please contact:
- **Frontend Team**: For UI/UX behavior questions
- **Architecture Team**: For design pattern questions
- **Security Team**: For password policy questions

---

## Acceptance Criteria

### Profile Update Endpoint
- ✅ User can update first_name and last_name
- ✅ Changes are persisted to database
- ✅ updated_at timestamp is updated
- ✅ Returns updated User object
- ✅ User cannot update email, role, or is_active
- ✅ Requires valid JWT authentication
- ✅ Returns 400 for validation errors
- ✅ Returns 401 for missing/invalid token

### Password Change Endpoint
- ✅ User can change password with current password verification
- ✅ Current password must be correct
- ✅ New password must meet strength requirements
- ✅ New password must be different from current
- ✅ password_changed_at timestamp is updated
- ✅ failed_login_attempts is reset to 0
- ✅ locked_until is cleared
- ✅ Returns 400 for incorrect current password
- ✅ Returns 400 for weak new password
- ✅ Returns 401 for missing/invalid token
- ✅ Does NOT log user out after password change

### Testing
- ✅ Unit tests pass (>80% coverage)
- ✅ Integration tests pass
- ✅ Works with real database
- ✅ Works with frontend application

---

**End of Change Request**