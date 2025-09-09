# Database Migration Notes - Schema v1.1

**From**: Database Engineering Team  
**To**: Backend Engineering Team  
**Date**: September 9, 2025  
**Migration Status**: ✅ **COMPLETE** - Database ready for backend integration

---

## 🎯 **URGENT: Backend Integration Required**

The database has been successfully migrated from **file-centric** to **candidate-centric** architecture. **Your FastAPI application will not work until you update the SQLAlchemy models and related code.**

---

## 📊 **What Changed in the Database**

### **🆕 NEW TABLES (You need to create models for these):**
```sql
candidates (11 records)                    -- 🔥 CRITICAL: Main business entity
user_candidate_assignments (11 records)   -- 🔥 CRITICAL: Role-based access control
resumes (11 records)                       -- 🔥 CRITICAL: Replaces file_uploads
resume_sections (11 records)              -- 🔥 CRITICAL: Section-level AI feedback
review_requests (11 records)              -- 🔥 CRITICAL: Replaces analysis_requests
review_results (0 records)                -- 🔥 CRITICAL: Replaces analysis_results
review_feedback_items (0 records)         -- ⚡ NEW: Precise AI feedback
prompt_usage_history (6 records)          -- ⚡ NEW: Replaces prompt_history
activity_logs (3 records)                 -- 📝 NEW: Audit trail
```

### **📝 UPDATED TABLES:**
```sql
users (217 records)                       -- ⚠️  MODIFIED: Role enum changed
prompts (3 records)                       -- ⚠️  MODIFIED: Added agent_type
```

### **🗑️ REMOVED TABLES (Your models reference these - WILL BREAK!):**
```sql
❌ file_uploads                   → Now: resumes
❌ analysis_requests              → Now: review_requests  
❌ analysis_results               → Now: review_results
❌ prompt_history                 → Now: prompt_usage_history
❌ refresh_tokens                 → Moved to Redis (future)
```

---

## 🚨 **CRITICAL ISSUES IN YOUR CURRENT CODE**

### **Issue #1: Broken Model Imports**
```python
# ❌ BROKEN - This file was found in your code:
# backend/app/features/file_upload/repository.py:15
from database.models.files import FileUpload, FileStatus

# 🔥 PROBLEM: 'file_uploads' table no longer exists!
# ✅ FIX: Update to use new 'resumes' table with candidate relationship
```

### **Issue #2: Missing Critical Models**
```python
# ❌ MISSING - You need to create these models:
class Candidate(Base):          # No equivalent exists in your code
class UserCandidateAssignment(Base):  # No equivalent exists  
class Resume(Base):             # Must replace FileUpload
class ReviewRequest(Base):      # Must replace AnalysisRequest
```

### **Issue #3: Wrong Table Names in Existing Models**
```python
# ❌ Your existing models point to renamed/removed tables:
class FileUpload(Base):
    __tablename__ = 'file_uploads'  # ❌ Table renamed to 'resumes'

class AnalysisRequest(Base):
    __tablename__ = 'analysis_requests'  # ❌ Table renamed to 'review_requests'
```

---

## 🛠️ **REQUIRED ACTIONS FOR BACKEND TEAM**

### **Phase 1: Create New SQLAlchemy Models (HIGH PRIORITY)**

#### **1.1 Create Candidate Model**
```python
# NEW FILE: backend/app/database/models/candidate.py
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base

class Candidate(Base):
    __tablename__ = 'candidates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    current_company = Column(String(255))
    current_position = Column(String(255))  # Note: DB has 'current_position' not 'current_role'
    years_experience = Column(Integer)
    status = Column(String(20), default='active')
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    created_by = relationship("User", back_populates="created_candidates")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    assignments = relationship("UserCandidateAssignment", back_populates="candidate")
```

#### **1.2 Create User-Candidate Assignment Model**
```python
# NEW FILE: backend/app/database/models/assignment.py
class UserCandidateAssignment(Base):
    __tablename__ = 'user_candidate_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)
    assignment_type = Column(String(20), default='primary')
    assigned_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    unassigned_at = Column(TIMESTAMP(timezone=True))
    assigned_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    unassigned_reason = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="assignments")
    candidate = relationship("Candidate", back_populates="assignments")
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
```

#### **1.3 Replace FileUpload with Resume Model**
```python
# UPDATE FILE: backend/app/database/models/resume.py (rename from files.py)
class Resume(Base):  # REPLACES FileUpload
    __tablename__ = 'resumes'  # NOT 'file_uploads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)  # 🆕 NEW
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    version_number = Column(Integer, default=1)  # 🆕 NEW
    status = Column(String(20), default='pending')
    progress = Column(Integer, default=0)
    extracted_text = Column(Text)
    word_count = Column(Integer)
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships  
    candidate = relationship("Candidate", back_populates="resumes")  # 🆕 NEW
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_user_id])
    sections = relationship("ResumeSection", back_populates="resume", cascade="all, delete-orphan")
    review_requests = relationship("ReviewRequest", back_populates="resume")
```

#### **1.4 Update User Model**
```python
# UPDATE FILE: backend/app/database/models/user.py
from sqlalchemy import Enum

class User(Base):
    # ... existing fields ...
    
    # ⚠️  CRITICAL: Update role enum
    role = Column(Enum('junior_recruiter', 'senior_recruiter', 'admin', name='user_roles'), 
                 nullable=False, default='junior_recruiter')  # NOT 'consultant'
    
    # 🆕 Add new relationships
    created_candidates = relationship("Candidate", back_populates="created_by")
    assignments = relationship("UserCandidateAssignment", 
                             foreign_keys="UserCandidateAssignment.user_id", 
                             back_populates="user")
```

### **Phase 2: Update Repository Classes**

#### **2.1 Replace FileUploadRepository**
```python
# UPDATE FILE: backend/app/features/file_upload/repository.py
# Change ALL instances of:
❌ FileUpload → Resume
❌ file_uploads → resumes  
❌ FileUploadRepository → ResumeRepository

# Add candidate relationship handling:
async def create_resume(
    self,
    candidate_id: uuid.UUID,  # 🆕 NEW PARAMETER
    filename: str,
    original_filename: str,
    # ... other params
) -> Resume:
    resume = Resume(
        candidate_id=candidate_id,  # 🆕 REQUIRED
        stored_filename=filename,   # Note: field renamed
        original_filename=original_filename,
        # ...
    )
```

#### **2.2 Create CandidateRepository**
```python
# NEW FILE: backend/app/features/candidate/repository.py
class CandidateRepository(BaseRepository[Candidate]):
    
    async def get_candidates_for_user(self, user_id: uuid.UUID, user_role: str) -> List[Candidate]:
        """Get candidates based on user role and assignments."""
        if user_role == 'junior_recruiter':
            # Only assigned candidates
            query = (
                self.db.query(Candidate)
                .join(UserCandidateAssignment)
                .filter(
                    UserCandidateAssignment.user_id == user_id,
                    UserCandidateAssignment.is_active == True
                )
            )
        elif user_role in ['senior_recruiter', 'admin']:
            # All candidates
            query = self.db.query(Candidate)
        else:
            return []
            
        return query.all()
```

### **Phase 3: Update Service Classes**

#### **3.1 Update FileUploadService → ResumeService**
```python
# RENAME FILE: backend/app/features/file_upload/ → backend/app/features/resume/
# UPDATE: All services to work with candidate-resume relationship

class ResumeService:  # REPLACES FileUploadService
    
    async def upload_resume(
        self, 
        candidate_id: uuid.UUID,  # 🆕 REQUIRED
        file_data: UploadFile, 
        uploaded_by_user_id: uuid.UUID
    ) -> Resume:
        # 1. Verify user has access to candidate
        # 2. Create resume linked to candidate
        # 3. Process file as before
```

#### **3.2 Create CandidateService**
```python
# NEW FILE: backend/app/features/candidate/service.py
class CandidateService:
    
    async def create_candidate(self, candidate_data: dict, created_by_user_id: uuid.UUID) -> Candidate:
        # Create candidate and auto-assign to creator
        
    async def assign_candidate(self, candidate_id: uuid.UUID, user_id: uuid.UUID, assigned_by: uuid.UUID):
        # Handle candidate assignment with history tracking
```

### **Phase 4: Update API Endpoints**

#### **4.1 New Endpoints Required**
```python
# NEW FILE: backend/app/api/v1/endpoints/candidates.py
@router.get("/candidates/")
async def get_candidates(current_user: User = Depends(get_current_user)):
    """Get candidates based on user role and assignments."""
    
@router.post("/candidates/")  
async def create_candidate(candidate: CandidateCreate, current_user: User = Depends(get_current_user)):
    """Create new candidate with auto-assignment."""

@router.post("/candidates/{candidate_id}/resumes/")
async def upload_resume(candidate_id: UUID, file: UploadFile, current_user: User = Depends(get_current_user)):
    """Upload resume for specific candidate."""
```

#### **4.2 Update Existing Endpoints**
```python
# UPDATE: backend/app/api/v1/endpoints/files.py → resumes.py
# Change all file upload endpoints to work with candidate context
```

---

## 🔧 **TESTING REQUIREMENTS**

### **Critical Tests to Update:**
1. **Model Tests**: All existing model tests will fail - update for new schema
2. **Repository Tests**: Update for candidate-resume relationships  
3. **Service Tests**: Test role-based access control
4. **API Tests**: Update endpoints for candidate-centric workflow

### **New Tests Required:**
1. **Candidate Management**: Create, assign, access control
2. **Role-Based Access**: Junior vs Senior recruiter permissions
3. **Resume-Candidate Linking**: Ensure proper relationships
4. **Assignment History**: Track candidate reassignments

---

## 📋 **MIGRATION VALIDATION CHECKLIST**

### **Before You Start:**
- [ ] ✅ Database migration completed (already done)
- [ ] ✅ Backup tables cleaned up (already done)
- [ ] ⏳ Backend models need updating (YOUR TASK)

### **Your Tasks:**
- [ ] Create new SQLAlchemy models (Candidate, UserCandidateAssignment, etc.)
- [ ] Update existing models (User role enum, Resume replaces FileUpload)
- [ ] Update all repository classes
- [ ] Update all service classes  
- [ ] Update all API endpoints
- [ ] Create new candidate management endpoints
- [ ] Update all tests
- [ ] Test role-based access control
- [ ] Verify complete workflow: create candidate → upload resume → request review

### **Success Criteria:**
- [ ] FastAPI server starts without errors
- [ ] All existing functionality works (login, file upload, etc.)
- [ ] New candidate functionality works
- [ ] Role-based access control works
- [ ] All tests pass

---

## 🆘 **SUPPORT & RESOURCES**

### **Database Schema Reference:**
- **Complete Documentation**: `/database/docs/schema_v1.1_draft.md`
- **Migration Details**: `/database/docs/migration_plan_v1.0_to_v1.1.md`
- **Integration Tests**: `/database/docs/BACKEND_INTEGRATION_TEST_PLAN.md`

### **Database Connection (if needed):**
```bash
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev
```

### **Current Database State:**
- ✅ 217 users (10 admin, 18 senior, 189 junior recruiters)
- ✅ 11 candidates with complete assignment tracking
- ✅ 11 resumes ready for processing
- ✅ All relationships and constraints working perfectly
- ✅ Performance optimized (57 indexes, sub-millisecond queries)

### **Emergency Rollback:**
If integration fails catastrophically, we have `backup_v1.0_20250909_160321.sql` for emergency rollback (135KB).

---

## ⚡ **GET STARTED NOW**

1. **Start with models** - Create the new model files first
2. **Update imports** - Fix all broken imports in existing code  
3. **Test incrementally** - Test each model as you create it
4. **Focus on core workflow** - Get basic candidate + resume creation working first
5. **Add role permissions** - Implement junior vs senior access control

**The database is production-ready. Your backend integration is the only remaining blocker!** 🚀

---

**Questions?** Database team is available for support during integration.

*Database Engineering Team - September 9, 2025*