# Backend Integration Test Execution Plan - Schema v1.1 Migration

**Date**: September 9, 2025  
**Purpose**: Test existing business logic compatibility with new candidate-centric database schema  
**Status**: Ready for execution  
**Database**: Schema v1.1 migration completed ✅

---

## **Executive Summary**

The database has been successfully migrated from v1.0 (file-centric) to v1.1 (candidate-centric). This document provides a **practical, step-by-step testing approach** to verify that existing business logic works with the new schema.

### **Key Changes:**
- `file_uploads` → `resumes` (linked to candidates)
- `analysis_requests/results` → `review_requests/results` (linked to resumes)
- User roles: `consultant/admin` → `junior_recruiter/senior_recruiter/admin`
- New candidate-centric architecture with role-based access control

### **Testing Philosophy:**
1. **Test existing features first** (auth, file upload, analysis)
2. **Fix migration issues** before building new features
3. **Preserve all business logic** - no functionality should be lost
4. **Build candidate logic** only after core features are stable

---

## **PRIORITY 1: AUTH SYSTEM TESTING** 🔴 CRITICAL

**Why First**: Auth is the foundation - if it breaks, everything breaks.

### **Schema Changes Affecting Auth:**
```sql
-- OLD CONSTRAINT:
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('consultant', 'admin'));

-- NEW CONSTRAINT: 
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('junior_recruiter', 'senior_recruiter', 'admin'));
```

### **Expected Issues:**
- Existing users with `role='consultant'` may fail login
- Permission checks may need role mapping updates
- JWT token validation may reject old roles

### **Test Execution Steps:**

#### **Step 1.1: Database Role Compatibility Check**
```bash
# Check current user roles in database
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT role, COUNT(*) as user_count 
FROM users 
GROUP BY role 
ORDER BY user_count DESC;
"

# Expected result: Should show role distribution
# junior_recruiter: 189
# senior_recruiter: 18  
# admin: 10
```

#### **Step 1.2: Auth Integration Tests**
```bash
cd backend

# Test existing auth functionality
pytest app/features/auth/tests/integration/test_auth_flow.py -v

# Specific test cases:
pytest app/features/auth/tests/integration/test_auth_flow.py::TestAuthServiceIntegration::test_complete_registration_login_flow -v
pytest app/features/auth/tests/integration/test_auth_flow.py::TestAuthServiceIntegration::test_login_with_invalid_credentials -v
pytest app/features/auth/tests/integration/test_auth_flow.py::TestAuthServiceIntegration::test_token_refresh_flow -v
```

#### **Step 1.3: Auth Unit Tests**
```bash
# Test auth business logic
pytest app/features/auth/tests/unit/ -v

# Specific focus on role-related tests
pytest app/features/auth/tests/unit/ -v -k "role"
```

#### **Step 1.4: Auth API Tests**  
```bash
# Test API endpoints
pytest app/features/auth/tests/integration/test_auth_flow.py::TestAuthAPIIntegration -v

# Test specific endpoints:
# - POST /api/v1/auth/login
# - POST /api/v1/auth/refresh  
# - GET /api/v1/auth/me
# - POST /api/v1/auth/logout
```

### **Expected Results:**
- ✅ **PASS**: Login/logout functionality works
- ✅ **PASS**: Token refresh works  
- ✅ **PASS**: Session management works
- ⚠️ **POTENTIAL FAIL**: Role-based permission checks
- ⚠️ **POTENTIAL FAIL**: User registration with new roles

### **Success Criteria:**
- [ ] All existing auth tests pass
- [ ] Users can login with existing credentials
- [ ] JWT tokens work correctly
- [ ] Role-based permissions function properly
- [ ] Session management unchanged

---

## **PRIORITY 2: FILE UPLOAD TESTING** 🟡 HIGH

**Why Second**: Core functionality that users interact with daily.

### **Schema Changes Affecting File Upload:**
```sql
-- OLD: file_uploads table (standalone)
-- NEW: resumes table (linked to candidates)

-- Key changes:
-- file_uploads.user_id → resumes.uploaded_by_user_id
-- file_uploads.id → resumes.id  
-- New: resumes.candidate_id (foreign key to candidates)
```

### **Expected Issues:**
- FileUploadService may fail due to table name changes
- Foreign key constraints may cause failures
- Business logic may need candidate relationship handling

### **Test Execution Steps:**

#### **Step 2.1: Database Migration Verification**
```bash
# Verify data migration completed successfully
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT 
    'resumes' as table_name, COUNT(*) as record_count FROM resumes
UNION ALL
SELECT 'candidates', COUNT(*) FROM candidates
UNION ALL  
SELECT 'user_candidate_assignments', COUNT(*) FROM user_candidate_assignments;
"

# Expected: 11 resumes, 11 candidates, 11 assignments
```

#### **Step 2.2: File Upload Service Tests**
```bash
# Test file upload business logic (will likely fail initially)
pytest app/features/file_upload/tests/unit/test_service.py -v

# Key test cases:
pytest app/features/file_upload/tests/unit/test_service.py::TestFileUploadService::test_process_upload_success -v
pytest app/features/file_upload/tests/unit/test_service.py::TestFileUploadService::test_validate_file_success -v
pytest app/features/file_upload/tests/unit/test_service.py::TestFileUploadService::test_extract_text_from_txt -v
```

#### **Step 2.3: File Upload Repository Tests** 
```bash
# Test database layer (create if doesn't exist)
# Need to verify FileUploadRepository works with resumes table

# Manual database test:
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT id, original_filename, status, uploaded_by_user_id, candidate_id 
FROM resumes 
LIMIT 3;
"
```

#### **Step 2.4: File Upload API Integration Tests**
```bash
# Test API endpoints (will likely fail initially)
# Need to create integration tests for file upload API

# Manual API test using curl:
# curl -X POST "http://localhost:8000/api/v1/files/upload" 
#      -H "Authorization: Bearer <token>"
#      -F "file=@test_resume.pdf"
```

### **Expected Results:**
- ⚠️ **LIKELY FAIL**: FileUploadService due to table schema changes
- ⚠️ **LIKELY FAIL**: Database queries due to column name changes
- ✅ **SHOULD PASS**: File validation logic (unchanged)
- ✅ **SHOULD PASS**: Text extraction logic (unchanged)

### **Issues to Address:**
1. **Table Name Changes**: `file_uploads` → `resumes`
2. **Column Mapping**: `user_id` → `uploaded_by_user_id`  
3. **Foreign Key**: Need `candidate_id` for new resumes
4. **Business Logic**: How to create/link candidates?

### **Success Criteria:**
- [ ] File upload validation works (10MB, PDF/DOC/DOCX/TXT)
- [ ] Text extraction works (PDF, DOCX parsing)  
- [ ] Rate limiting works (10 uploads/minute)
- [ ] Metadata calculation works (word count, email detection)
- [ ] Files are properly linked to candidates

---

## **PRIORITY 3: RESUME ANALYSIS TESTING** 🟡 HIGH

**Why Third**: Complex AI-integrated feature that depends on file upload.

### **Schema Changes Affecting Analysis:**
```sql
-- OLD: analysis_requests/analysis_results tables
-- NEW: review_requests/review_results tables

-- Key changes:
-- analysis_requests → review_requests (linked to resumes vs file_uploads)
-- analysis_results → review_results  
-- New relationships: review_requests.resume_id → resumes.id
```

### **Expected Issues:**
- AnalysisService may fail due to table relationship changes
- AI orchestrator integration may need updates
- Business logic may need resume-aware modifications

### **Test Execution Steps:**

#### **Step 3.1: Analysis Data Migration Verification**
```bash
# Verify analysis data migration
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT 
    'review_requests' as table_name, COUNT(*) as record_count FROM review_requests
UNION ALL
SELECT 'review_results', COUNT(*) FROM review_results
UNION ALL
SELECT 'resume_sections', COUNT(*) FROM resume_sections;
"

# Expected: 11 review_requests, 0 review_results, 11 resume_sections
```

#### **Step 3.2: Analysis Business Logic Tests**
```bash
# Test analysis models and business logic
pytest app/features/resume_analysis/tests/unit/test_models.py -v

# Key test cases:
pytest app/features/resume_analysis/tests/unit/test_models.py::TestModels::test_analysis_request_validation -v
pytest app/features/resume_analysis/tests/unit/test_models.py::TestModels::test_score_details -v
pytest app/features/resume_analysis/tests/unit/test_models.py::TestModels::test_legacy_compatibility -v
```

#### **Step 3.3: Analysis Service Tests** 
```bash
# Test analysis service (will likely fail initially)
# Need to create service tests or update existing ones

# Check if AnalysisService can handle new schema
# Manual test: Try to create an analysis request
```

#### **Step 3.4: AI Integration Tests**
```bash
# Test AI orchestrator integration
# Verify LangChain/LangGraph agents still work

# Check prompts migration:
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT id, name, agent_type, is_active 
FROM prompts 
WHERE is_active = true;
"

# Expected: 3 prompts (base_agent, structure_agent, appeal_agent)
```

### **Expected Results:**
- ✅ **SHOULD PASS**: Analysis request validation (unchanged)
- ✅ **SHOULD PASS**: Industry validation (5 industries)
- ✅ **SHOULD PASS**: Text validation (100-50000 characters)
- ⚠️ **LIKELY FAIL**: AnalysisService due to table relationship changes
- ⚠️ **LIKELY FAIL**: Database queries due to foreign key changes

### **Issues to Address:**
1. **Table Relationships**: Link to `resumes` instead of `file_uploads`
2. **Foreign Keys**: `review_requests.resume_id` → `resumes.id`
3. **Business Logic**: Resume access control via candidates
4. **AI Integration**: Verify orchestrator still works

### **Success Criteria:**
- [ ] Analysis request validation works
- [ ] Industry specialization works (5 industries)
- [ ] Rate limiting works (5 analyses per 5 minutes)
- [ ] AI orchestrator integration works
- [ ] Scoring algorithm works (market tier calculation)
- [ ] Reviews are properly linked to resumes/candidates

---

## **PRIORITY 4: CANDIDATE BUSINESS LOGIC** 🟢 NEW FEATURE

**Why Last**: New functionality that depends on working auth/file/analysis.

### **New Business Logic Required:**
```python
# Candidate creation and management
class CandidateService:
    async def create_candidate_from_resume_upload()
    async def get_candidates_for_user()  # Role-based access
    async def assign_candidate()         # Senior/admin only
```

### **Business Rules to Implement:**
1. **Auto-assignment**: Resume upload creates candidate if needed
2. **Role-based access**: Junior sees assigned, senior sees all
3. **Assignment management**: Only senior/admin can assign
4. **Access control**: Users access resumes through candidate assignments

### **Test Development Strategy:**

#### **Step 4.1: Design Candidate Tests**
```python
# Define test scenarios first
test_candidate_creation_from_resume_upload()
test_role_based_candidate_access() 
test_candidate_assignment_permissions()
test_resume_access_via_candidate_assignment()
```

#### **Step 4.2: Implement Candidate Service**
```python
# Build CandidateService with business logic
# Implement role-based access control
# Add assignment management
```

#### **Step 4.3: Test Candidate Integration**
```python
# Test integration with existing features
# Verify file upload → candidate creation
# Verify analysis → candidate access control
```

### **Success Criteria:**
- [ ] Candidates auto-created from resume uploads
- [ ] Role-based candidate access working
- [ ] Assignment management functional
- [ ] Resume access controlled via candidate assignments

---

## **EXECUTION TIMELINE**

### **Week 1: Foundation Testing**
- **Day 1**: Auth system testing and fixes
- **Day 2-3**: File upload testing and service updates  
- **Day 4-5**: Analysis testing and service updates

### **Week 2: Integration & New Features**
- **Day 1-2**: Candidate business logic implementation
- **Day 3-4**: End-to-end workflow testing
- **Day 5**: Performance and integration testing

---

## **TESTING COMMANDS SUMMARY**

### **Quick Health Check:**
```bash
# 1. Database connectivity
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "\dt"

# 2. Data verification
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'candidates', COUNT(*) FROM candidates  
UNION ALL SELECT 'resumes', COUNT(*) FROM resumes
UNION ALL SELECT 'review_requests', COUNT(*) FROM review_requests;
"
```

### **Feature Testing Sequence:**
```bash
# 3. Auth testing
cd backend
pytest app/features/auth/tests/ -v

# 4. File upload testing  
pytest app/features/file_upload/tests/ -v

# 5. Analysis testing
pytest app/features/resume_analysis/tests/ -v

# 6. Full integration testing (after fixes)
pytest -v
```

---

## **SUCCESS METRICS**

### **Must-Have Criteria:**
- ✅ **Zero data loss** - All migrated data accessible
- ✅ **Feature parity** - All existing functionality works
- ✅ **Performance maintained** - No regression in response times
- ✅ **API compatibility** - Frontend continues working

### **Business Continuity:**
- ✅ **Existing users** can login and access their data
- ✅ **File uploads** work with same validation rules
- ✅ **Resume analysis** produces same quality results
- ✅ **Rate limiting** enforced identically

---

## **RISK MITIGATION**

### **Rollback Plan:**
- Database backup tables available (`file_uploads_backup_v1_0`, etc.)
- Code rollback procedures documented
- Performance baselines established

### **Issue Tracking:**
- Document all test failures with root cause analysis
- Track business logic changes required
- Monitor performance during testing

---

*Backend Integration Test Plan v1.0*  
*Created: September 9, 2025*  
*Ready for execution by backend engineering team*