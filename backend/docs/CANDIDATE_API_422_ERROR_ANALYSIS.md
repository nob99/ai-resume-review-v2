# 🔍 Candidate API 422 Error - Root Cause Analysis

## Executive Summary

The frontend receives a **422 Unprocessable Entity** error when calling `/api/v1/candidates` because of a **route conflict** in the backend. A generic catch-all route `/{file_id}` is intercepting the request before it reaches the correct candidate handler.

---

## 📊 Request Flow Diagram

### 1. Overall Request Flow

```
┌─────────────────────────────┐
│   Frontend (Port 3000)      │
│                             │
│  CandidateSelector.tsx      │
└──────────┬──────────────────┘
           │
           │ 1. Component mounts
           ▼
┌─────────────────────────────┐
│   loadCandidates()          │
│   "Need to fetch candidates"│
└──────────┬──────────────────┘
           │
           │ 2. Call API function
           ▼
┌─────────────────────────────┐
│   api.ts                    │
│   candidateApi.getCandidates│
└──────────┬──────────────────┘
           │
           │ 3. HTTP Request
           ▼
┌─────────────────────────────┐
│  GET /api/v1/candidates     │
│  Headers:                   │
│  - Authorization: Bearer ... │
└──────────┬──────────────────┘
           │
           │ 4. Request reaches backend
           ▼
┌─────────────────────────────┐
│   Backend (Port 8000)       │
│   FastAPI Router            │
└──────────┬──────────────────┘
           │
           │ 5. Route matching begins
           ▼
```

### 2. Route Matching Process (Where It Fails)

```
FastAPI Route Matcher
│
├─► Check Route #1: /api/v1/{file_id}
│   │
│   ├─ Pattern: /api/v1/[anything]
│   ├─ Source: resume_upload_router
│   ├─ Registered at: main.py line 164
│   │
│   └─► ✅ MATCHES! "candidates" captured as {file_id}
│       │
│       ├─► Try to validate: Is "candidates" a UUID?
│       │   │
│       │   └─► ❌ NO! "candidates" is not a valid UUID
│       │       │
│       │       └─► Return 422 Unprocessable Entity
│                   {
│                     "loc": ["path", "file_id"],
│                     "msg": "Input should be a valid UUID",
│                     "input": "candidates"
│                   }
│
├─► Check Route #2: /api/v1/candidates  ← ⚠️ NEVER REACHED!
│   │
│   ├─ Pattern: /api/v1/candidates
│   ├─ Source: candidate_router
│   └─ Registered at: main.py line 158
│
└─► (Other routes never checked...)
```

---

## 🎯 The Core Problem

### What's Happening (Wrong Path)

```
Request: GET /api/v1/candidates
           │
           ▼
    Route Matching Order:
    1. /api/v1/{file_id}     ← Catches EVERYTHING at /api/v1/*
    2. /api/v1/candidates    ← Never reached
           │
           ▼
    "candidates" parsed as {file_id}
           │
           ▼
    UUID Validation Fails
           │
           ▼
    422 Error Response
```

### What Should Happen (Correct Path)

```
Request: GET /api/v1/candidates
           │
           ▼
    Route Matching Order:
    1. /api/v1/uploads/{file_id}  ← Specific path, won't match
    2. /api/v1/candidates         ← MATCHES!
           │
           ▼
    Execute get_candidates()
           │
           ▼
    Return candidate list
```

---

## 📁 Code Locations

### Backend Route Registration (`backend/app/main.py`)

```python
# Line 158 - Candidate router (should handle /api/v1/candidates)
app.include_router(candidate_router, prefix="/api/v1/candidates", tags=["candidates"])

# Line 164 - Resume upload router (THE PROBLEM - too broad prefix!)
app.include_router(resume_upload_router, prefix="/api/v1", tags=["resumes"])
#                                                    ^^^^^^
#                                         This makes /{file_id} match EVERYTHING!
```

### Resume Upload Routes (`backend/app/features/resume_upload/api.py`)

```python
@router.get("/{file_id}")  # Line 193
# With prefix="/api/v1", this becomes: /api/v1/{file_id}
# This catches: /api/v1/candidates, /api/v1/anything, etc.
```

### Candidate Routes (`backend/app/features/candidate/api.py`)

```python
@router.get("/")  # Line 72
# With prefix="/api/v1/candidates", this becomes: /api/v1/candidates
# But it's never reached due to route order!
```

---

## 🔄 Route Registration Timeline

```
Application Startup
│
├─ 1. Register Auth Router
│    └─ Prefix: /api/v1/auth
│         └─ Routes: /api/v1/auth/login, /api/v1/auth/refresh, etc.
│
├─ 2. Register Candidate Router
│    └─ Prefix: /api/v1/candidates
│         └─ Routes: /api/v1/candidates, /api/v1/candidates/{id}
│
├─ 3. Register Resume Upload Router  ⚠️ PROBLEM HERE
│    └─ Prefix: /api/v1  (TOO BROAD!)
│         └─ Routes: /api/v1/{file_id}  ← Catches everything!
│                     /api/v1/batch
│                     /api/v1/stats/summary
│
└─ 4. Register Analysis Router
     └─ Prefix: /api/v1/analysis
          └─ Routes: /api/v1/analysis/*, etc.
```

---

## ✅ Solution Options

### Option 1: Change Resume Upload Prefix (RECOMMENDED)

```python
# In backend/app/main.py, line 164
# Change from:
app.include_router(resume_upload_router, prefix="/api/v1", tags=["resumes"])

# To:
app.include_router(resume_upload_router, prefix="/api/v1/uploads", tags=["resumes"])
```

**Result**: Routes become:
- `/api/v1/uploads/{file_id}` - No longer conflicts
- `/api/v1/candidates` - Works correctly

### Option 2: Reorder Route Registration

```python
# Register specific routes BEFORE generic ones
app.include_router(candidate_router, prefix="/api/v1/candidates", tags=["candidates"])
# ... other specific routers ...
app.include_router(resume_upload_router, prefix="/api/v1", tags=["resumes"])  # Last!
```

**Result**: Specific routes checked first, but fragile solution

### Option 3: Modify Resume Upload Routes

```python
# In backend/app/features/resume_upload/api.py
# Change from:
@router.get("/{file_id}")

# To:
@router.get("/files/{file_id}")
```

**Result**: More RESTful, clear separation

---

## 🧪 Testing & Verification

### Current Behavior (Broken)

```bash
# This fails with 422
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/candidates
# Error: "Input should be a valid UUID"

# This also fails with 422 (same issue)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/anything

# This would work (if valid UUID provided)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/550e8400-e29b-41d4-a716-446655440000
```

### After Fix

```bash
# This will work
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/candidates
# Returns: {"candidates": [...], "total_count": 14, ...}
```

---

## 📝 Summary

### The Problem Is NOT:
- ❌ Authentication issues (token is valid)
- ❌ Database problems (data exists)
- ❌ Pydantic schema issues (models are correct)
- ❌ Frontend code bugs (request is correct)

### The Problem IS:
- ✅ **Route conflict**: Generic `/{file_id}` pattern matches before specific `/candidates`
- ✅ **Registration order**: Resume upload router has overly broad prefix `/api/v1`
- ✅ **Pattern matching**: FastAPI matches routes in registration order, first match wins

### Impact:
- All requests to `/api/v1/[non-uuid]` fail with 422
- Candidate dropdown cannot load data
- Resume upload feature blocks other API endpoints

### Recommended Fix:
Change the resume upload router prefix from `/api/v1` to `/api/v1/uploads` or `/api/v1/files` to avoid the conflict.

---

## 📚 References

- FastAPI Route Order Documentation: https://fastapi.tiangolo.com/tutorial/path-params/
- Pydantic Validation Errors: https://docs.pydantic.dev/latest/errors/validation_errors/
- Backend Code: `backend/app/main.py` (lines 158-164)