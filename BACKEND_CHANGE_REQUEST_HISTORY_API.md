# Backend Change Request: Fix History API Candidate Data

**Date:** September 30, 2025
**Requested by:** Frontend Team
**Priority:** High 🔴
**Type:** Bug Fix

---

## **Summary**

The `/api/v1/analysis/` endpoint (GET) is crashing when called from the Review History page because it cannot access candidate information from resume objects. This prevents the frontend from displaying the history list.

---

## **Current Issue** ❌

### **Error Message:**
```
AnalysisException: Failed to list analyses:
'FileUploadResponse' object has no attribute 'candidate'
```

### **Error Location:**
- **File:** `backend/app/features/resume_analysis/service.py`
- **Method:** `list_user_analyses()`
- **Lines:** ~461-471

### **What's Happening:**
1. Frontend calls: `GET /api/v1/analysis/?page=1&page_size=25`
2. Backend service tries to get resume data via `self.resume_service.get_upload()`
3. This returns a `FileUploadResponse` DTO (Pydantic schema)
4. Code tries to access `resume.candidate.first_name`
5. **Crash:** `FileUploadResponse` has no `candidate` attribute
6. No response sent to frontend → CORS error appears in browser

### **Backend Log Evidence:**
```
File "/app/app/features/resume_analysis/service.py", line 487, in list_user_analyses
    raise AnalysisException(f"Failed to list analyses: {str(e)}")
app.features.resume_analysis.service.AnalysisException:
Failed to list analyses: 'FileUploadResponse' object has no attribute 'candidate'
```

---

## **Root Cause** 🔍

The `list_user_analyses()` method incorrectly uses the **Upload Service** to fetch resume data:

```python
# Current broken code (line ~461):
resume = await self.resume_service.get_upload(request.resume_id, user_id)
# Returns: FileUploadResponse (DTO without relationships)

# Then tries to access (line ~471):
candidate_name = f"{resume.candidate.first_name} {resume.candidate.last_name}"
#                      ^^^^^^^^^^^^^^^^
#                      ❌ AttributeError: 'FileUploadResponse' has no 'candidate'
```

**Problem:** `FileUploadResponse` is a Pydantic schema (DTO) that only has:
- `id`, `filename`, `candidate_id`, `size`, etc.
- **NO** `candidate` relationship

**What we need:** Access to the `Resume` SQLAlchemy model with the `candidate` relationship loaded.

---

## **Requested Fix** ✅

### **File to Modify:**
`backend/app/features/resume_analysis/service.py`

### **Method to Fix:**
`list_user_analyses()` (approximately lines 422-487)

### **Recommended Solution:**

Replace the resume fetching logic with a direct database query that loads the candidate relationship:

```python
# Instead of this (BROKEN):
resume = await self.resume_service.get_upload(request.resume_id, user_id)

# Do this (WORKING):
from database.models import Resume
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Query Resume with candidate relationship loaded
stmt = select(Resume).where(Resume.id == request.resume_id).options(
    selectinload(Resume.candidate)
)
result = await self.db.execute(stmt)
resume = result.scalar_one_or_none()

if not resume:
    continue  # Skip this analysis if resume not found

# Now this works:
candidate_name = f"{resume.candidate.first_name} {resume.candidate.last_name}"
```

---

## **Alternative Solution** (If Above Doesn't Fit Architecture)

If you prefer not to query Resume directly in the service, you could:

### **Option A: Fetch Candidate Separately**
```python
# Get resume (current way)
resume = await self.resume_service.get_upload(request.resume_id, user_id)

# Then fetch candidate by ID
from database.models import Candidate
candidate = await self.db.get(Candidate, resume.candidate_id)

if candidate:
    candidate_name = f"{candidate.first_name} {candidate.last_name}"
```

### **Option B: Add Candidate to FileUploadResponse**
Modify the `ResumeUploadService.get_upload()` method to include candidate data in the response schema.

---

## **Expected Response Format** 📦

After the fix, the API should return:

```json
{
  "analyses": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "file_name": "john_doe_resume.pdf",
      "candidate_name": "John Doe",           // ✅ This is what's missing
      "candidate_id": "789e4567-e89b-12d3-a456-426614174999",
      "industry": "tech_consulting",
      "overall_score": 85,
      "status": "completed",
      "created_at": "2025-09-30T10:30:00Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 25
}
```

---

## **Testing Instructions** 🧪

### **How to Test the Fix:**

1. **Start the backend:**
   ```bash
   ./scripts/docker-dev.sh up
   ```

2. **Create test data (if needed):**
   - Upload a resume for a candidate
   - Analyze the resume

3. **Test the endpoint:**
   ```bash
   # Get auth token first
   TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"password"}' \
     | jq -r '.access_token')

   # Test the history endpoint
   curl -X GET "http://localhost:8000/api/v1/analysis/?page=1&page_size=25" \
     -H "Authorization: Bearer $TOKEN" \
     | jq
   ```

4. **Expected result:**
   - ✅ Status code: 200
   - ✅ JSON response with analyses array
   - ✅ Each analysis has `candidate_name` field
   - ❌ NO exceptions in backend logs

5. **Frontend verification:**
   - Navigate to http://localhost:3000/history
   - Should see table with candidate names
   - No CORS errors in browser console

---

## **Impact Assessment** 📊

### **Affected Components:**
- ✅ Review History feature (frontend)
- ✅ Analysis listing API (backend)

### **Not Affected:**
- Database schema (no changes needed)
- Other API endpoints (isolated fix)
- Frontend code (no changes needed)

### **Risk Level:** Low
- Small, focused change in one method
- No schema migrations required
- No breaking changes to other features

---

## **Database Schema Reference** 🗄️

For your reference, the relationships are already set up correctly:

```python
# database/models/resume.py
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID, primary_key=True)
    candidate_id = Column(UUID, ForeignKey("candidates.id"))

    # Relationship (already exists)
    candidate = relationship("Candidate", back_populates="resumes")

# database/models/candidate.py
class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)

    # Relationship (already exists)
    resumes = relationship("Resume", back_populates="candidate")
```

---

## **Questions for Backend Team** ❓

1. **Which solution do you prefer?**
   - Direct Resume query with `selectinload`
   - Separate Candidate query
   - Modify upload service response

2. **Do you want us to:**
   - Wait for your fix
   - Provide a PR with the fix
   - Work together on the solution

3. **Timeline:**
   - This is blocking the Review History feature
   - Can this be prioritized this sprint?

---

## **Contact** 📧

**Frontend Team**
For questions about this request, please reach out to the frontend team.

**Related Files:**
- Frontend: `frontend/src/app/history/page.tsx`
- Frontend Hook: `frontend/src/features/history/hooks/useHistoryData.ts`
- Backend Service: `backend/app/features/resume_analysis/service.py` (needs fix)
- Backend API: `backend/app/features/resume_analysis/api.py` (no changes needed)

---

## **Priority Justification** 🔥

**Why this is High Priority:**

1. ✅ Feature is complete on frontend
2. ✅ Backend endpoint exists but is broken
3. ✅ Blocks user-facing functionality
4. ✅ Simple fix (30 minutes of backend work)
5. ✅ No database migrations or complex changes needed

**User Impact:**
- Users cannot view their review history
- Page crashes with CORS error
- Poor user experience

---

**Thank you for your support!** 🙏

We look forward to collaborating on this fix.