# Upload Error Investigation - Complete Analysis

## Executive Summary
**Issue:** Backend 500 Error - `AttributeError: 'ResumeUploadRepository' object has no attribute 'db'`
**Root Cause:** Multiple architecture mismatches between ResumeUploadRepository and the system design
**Risk Level:** HIGH - But fixable without breaking other features
**Status:** Root cause identified, solution documented

## Critical Findings

### 1. PRIMARY ISSUE: Wrong Attribute Name
- **Problem:** ResumeUploadRepository uses `self.db` throughout (lines 38, 59, 60, 61, 107, 108, etc.)
- **Reality:** BaseRepository stores the session as `self.session` not `self.db`
- **Location:** `/backend/app/features/resume_upload/repository.py`

### 2. SECONDARY ISSUE: Wrong Parameter Order
- **Problem:** ResumeUploadRepository calls `super().__init__(Resume, db)`
- **Reality:** BaseRepository expects `super().__init__(session, model_class)`
- **Location:** Line 23 of repository.py

### 3. ARCHITECTURE MISMATCH: Sync vs Async
- **Problem:** ResumeUploadRepository imports regular `Session` and uses sync operations
- **Reality:** BaseRepository is designed for `AsyncSession` with async operations
- **Evidence:**
  - BaseRepository uses `await self.session.execute()`
  - Auth repository (working) uses `AsyncSession`
  - ResumeUploadRepository uses sync `self.db.query()`, `self.db.add()`, `self.db.commit()`

### 4. DEPENDENCY INJECTION CHAIN
Current flow:
```
API endpoint → get_db() returns Session (sync)
     ↓
ResumeUploadService(db: Session)
     ↓
ResumeUploadRepository(db: Session)
     ↓
BaseRepository expects AsyncSession ❌
```

## Comparison with Working Code

### Auth Repository (WORKING)
```python
# Uses AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)  # Correct order

    async def get_by_email(self, email: str):
        query = select(User).where(...)
        result = await self.session.execute(query)  # Uses self.session
```

### Resume Upload Repository (BROKEN)
```python
# Uses regular Session
from sqlalchemy.orm import Session

class ResumeUploadRepository(BaseRepository[Resume]):
    def __init__(self, db: Session):
        super().__init__(Resume, db)  # Wrong order!

    async def create_resume(self, ...):
        existing_resumes = self.db.query(Resume)...  # Uses self.db (doesn't exist)
        self.db.add(resume)  # Sync operation, not async
```

## Safe Fix Strategy

### Option A: Minimal Fix (Quick, Lower Risk)
Don't inherit from BaseRepository, just fix the attribute issue:

1. Remove inheritance from BaseRepository
2. Add `self.db = db` to __init__
3. Keep all existing sync operations

**Pros:**
- Minimal changes
- Won't affect other features
- Quick to implement

**Cons:**
- Doesn't follow architecture pattern
- Technical debt

### Option B: Full Architecture Alignment (Recommended)
Align with the working auth pattern:

1. Change to use `self.session` instead of `self.db`
2. Fix super().__init__ parameter order
3. Convert to async SQLAlchemy operations
4. Update service to handle async repository

**Pros:**
- Follows established patterns
- Consistent with other features
- Proper async support

**Cons:**
- More changes required
- Need to test thoroughly

## Files Requiring Changes

### For Option A (Minimal):
1. `/backend/app/features/resume_upload/repository.py`
   - Remove BaseRepository inheritance
   - Add `self.db = db` to __init__

### For Option B (Full):
1. `/backend/app/features/resume_upload/repository.py`
   - Change all `self.db` to `self.session`
   - Fix super().__init__ order
   - Convert queries to async pattern

2. `/backend/app/features/resume_upload/service.py`
   - May need to handle async repository methods

3. `/backend/app/features/resume_upload/api.py`
   - May need async session injection

## Error Evidence From Logs

```
2025-09-26 23:13:03,099 - app.features.resume_upload.service - ERROR - File upload failed for 福元(飛行機領収書).pdf: 'ResumeUploadRepository' object has no attribute 'db'
```

This error occurs at line 85 in service.py when calling:
```python
db_upload = await self.repository.create_resume(...)
```

Which then fails in repository.py at line 38:
```python
existing_resumes = self.db.query(Resume).filter(...)  # self.db doesn't exist!
```

## Testing Requirements

After fix implementation:
1. Test upload with the known working case (35KB PDF)
2. Test other endpoints to ensure nothing broke
3. Run integration tests for resume_upload feature
4. Verify auth and candidate features still work

## Recommendation

**Go with Option B (Full Architecture Alignment)** because:
1. The codebase already has async infrastructure in place
2. Auth feature proves the pattern works
3. Reduces technical debt
4. Makes future maintenance easier

However, if time is critical, Option A can be a temporary fix.

## Next Steps

1. Create a feature branch for the fix
2. Implement chosen option
3. Test thoroughly
4. Update unit tests if needed
5. Document any API changes

## Previous Frontend Issues (Already Resolved)

The frontend had issues that were fixed in commit `ad19fd8`:
- Complex dual state management simplified
- AbortController race conditions resolved
- FormData transmission corrected

The frontend is now correctly sending multipart/form-data with the file, but the backend crashes when trying to process it due to the repository issues described above.

---
*Investigation completed: September 27, 2025*
*Backend Team Investigation*